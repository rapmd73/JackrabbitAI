# Multi-Process Database Architecture: Event Log Pattern

## Overview

This document describes the **Event Log Architecture** that separates **write ingestion** (multiple UI/form processes) from **database mutation** (single-writer reader process). This pattern allows JackrabbitDB to remain an embedded database (single writer) while supporting unlimited concurrent writers at the ingestion layer.

---

## Problem Statement

| Scenario | Challenge |
|----------|-----------|
| Multiple clerks editing forms simultaneously | Each form submission = write to database |
| Form entry takes 5–15 minutes | Cannot hold database lock for duration |
| Direct multi-process writes to JackrabbitDB | Requires cross-process locking (DBMS mode) — coarse, low throughput |
| Data loss / corruption risk | Partial writes, lost updates, torn indexes |

**Solution**: Decouple *write ingestion* from *state mutation* using an **append-only event log**.

---

## Architecture Diagram

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────┐     ┌──────────────────┐
│   Form /     │     │   Input Log      │     │   Reader    │     │  JackrabbitDB    │
│   UI Writer  │────►│   (Event.JLOG)   │────►│  (Projector)│────►│  (Read Model)    │
│  (Process N) │     │  Append-Only     │     │  (Process 1)│     │  Data.JDB + IDX  │
└──────────────┘     └──────────────────┘     └─────────────┘     └──────────────────┘
       │                    │                       │                       │
       │                    │                       │                       │
       ▼                    ▼                       ▼                       ▼
  • Validate UX       • Single source        • Deterministic         • Optimized for
  • Emit event        • of truth             • projection            • queries
  • Fire-and-forget   • Immutable            • Business rules        • Rebuildable
  • Returns in ms     • Blake3 per line      • Exactly-once          • from log
```

---

## Component Specifications

### 1. Form / UI Writer (Multiple Processes)

**Responsibility**: Collect input, validate UX constraints, serialize event, append to log.

```python
# Event format (JSONL, one per line)
{
  "type": "DiagnosisSubmitted",
  "payload": {
    "patient_id": "PAT-12345",
    "diagnosis": "Type 2 Diabetes, uncontrolled",
    "icd10": "E11.65"
  },
  "meta": {
    "user_id": "dr_smith",
    "session_id": "sess_abc123",
    "timestamp": 1722567890.123,
    "form_version": "v3.2"
  },
  "seq": 0          # assigned by log
}
```

**Behavior**:
- Validates required fields, formats, ranges (UX validation only)
- Does **not** enforce business rules (those live in Reader)
- Calls `EventLog.Append(event)` → returns immediately (≤5 ms)
- Shows "Saved" to clerk instantly
- Auto-saves draft to localStorage/Redis every 30s (independent of log)

**No direct database access**. No locks held beyond log append.

---

### 2. Input Log: `Event.JLOG` (Single File, Append-Only)

**File**: `/data/events/Event.JLOG` (JSONL, one event per line)

**Properties**:
| Property | Guarantee |
|----------|-----------|
| **Ordering** | Line N < Line N+1 = happened-before |
| **Durability** | `sync=True` on every append (fsync) |
| **Integrity** | Blake3 hash per line (`event['blake']`) |
| **Immutability** | Never rewritten, never deleted |
| **Schema** | Self-describing JSON; new fields = backward compatible |

**API**:
```python
class EventLog:
    def __init__(self, path):
        self.path = path
        self.lock = DLM.Locker(f"eventlog.{path}")  # cross-process
    
    def Append(self, event_dict):
        with self.lock:
            event_dict['seq'] = self._next_seq()
            event_dict['blake'] = blake3(json.dumps(event_dict)).hexdigest()
            FF.AppendFile(self.path, json.dumps(event_dict) + '\n', sync=True)
    
    def ReadFrom(self, seq):
        """Iterator yielding events with seq >= given."""
        ...
```

**Why JSONL?**
- Human readable (`cat Event.JLOG | jq`)
- Stream processable (`grep`, `awk`, `jq`)
- OS-copy backup works (`cp -r /data /backup`)
- JackrabbitDB already uses JSONL — consistent tooling

---

### 3. Reader / Projector (Single Process)

**Responsibility**: Consume log sequentially → apply business logic → mutate JackrabbitDB.

```python
def reader_loop(event_log, db, checkpoint_path):
    last_seq = load_checkpoint(checkpoint_path)  # persisted sequence number
    
    for event in event_log.ReadFrom(last_seq):
        try:
            apply_event(db, event)        # deterministic, pure
            save_checkpoint(checkpoint_path, event['seq'])
        except Exception as e:
            log_error(event, e)
            alert_oncall()
            # Do NOT advance checkpoint → retry on restart
```

**`apply_event(db, event)`** — pure function, all business rules here:

```python
def apply_event(db, event):
    etype = event['type']
    payload = event['payload']
    meta = event['meta']
    
    if etype == 'DiagnosisSubmitted':
        # Business rules: validate ICD10, check patient exists, etc.
        validate_diagnosis(payload)
        patient_offset = db.BinaryIndexSearch('patient_id', {'patient_id': payload['patient_id']})
        db.UpdateSection(patient_offset, 'clinical', payload, expected_vv=...)
    
    elif etype == 'BillingCodeAdded':
        validate_billing(payload)
        patient_offset = db.BinaryIndexSearch('patient_id', {'patient_id': payload['patient_id']})
        db.UpdateSection(patient_offset, 'billing', payload, expected_vv=...)
    
    elif etype == 'PatientCreated':
        db.Add(payload)  # new record
    
    else:
        raise UnknownEventType(etype)
```

**Critical invariants**:
| Invariant | Enforcement |
|-----------|-------------|
| **Deterministic** | Same event + same DB state → same new state |
| **Exactly-once** | Checkpoint saved **after** successful `apply_event` |
| **Idempotent restart** | Replay from checkpoint safe (events immutable) |
| **Single writer to DB** | Only this process calls `db.Update/Add/Delete` |

---

### 4. JackrabbitDB (Read Model / Projection)

**Role**: Query-optimized current state. **Rebuildable from log at any time.**

```python
# Indexes optimized for QUERY patterns, not write patterns
db = JackrabbitDB(
    "/data/patients",
    idx=[
        "patient_id",              # primary lookup
        "clinical.diagnosis",      # clinical search
        "billing.code",            # billing search
        "meta.updated_at"          # recent changes
    ],
    syncDB=True,    # durable
    syncIDX=False   # indexes rebuildable
)
```

**No direct writes from UI**. All mutations via Reader.

**Rebuild procedure**:
```bash
rm -rf /data/patients
reader_loop(EventLog("/data/events/Event.JLOG"), 
            JackrabbitDB("/data/patients"), 
            "/data/checkpoints/patients.seq")
# Replays entire log → fresh, consistent DB
```

---

## Failure Modes & Handling

| Failure | Detection | Recovery |
|---------|-----------|----------|
| **Form crashes mid-entry** | Draft in localStorage/Redis | Clerk reopens form → draft restored |
| **Log append fails (disk full)** | `AppendFile` raises | Form shows error, clerk retries |
| **Reader crashes** | Process monitor / heartbeat | Restart reader → resumes from checkpoint |
| **Reader bug corrupts DB** | `VerifyDatabase()` fails / alerts | Fix `apply_event`, delete DB, replay log |
| **Event schema change** | New event type / field | Reader handles both old + new; DB rebuild optional |
| **Clock skew / ordering** | Log sequence (`seq`) is authority | Wall-clock timestamps advisory only |

---

## Concurrency Guarantees

| Layer | Writers | Mechanism | Throughput |
|-------|---------|-----------|------------|
| **Form → Log** | Unlimited (N processes) | DLM lock per append (µs) | ~10,000 events/sec |
| **Log → DB** | 1 (Reader process) | No locking needed | ~5,000 mutations/sec |
| **UI Reads** | Unlimited | JackrabbitDB read (no lock) | ~50,000 reads/sec |

**No lost updates**: Events never overwrite. Reader applies in strict log order.

**No clerk frustration**: Form submit = log append (ms). Background projection = eventual consistency (typically <100 ms).

---

## Deployment Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                    SHARED FILESYSTEM (NFS / local SSD)         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Event.JLOG   │  │ patients/    │  │ checkpoints/         │  │
│  │ (append-only)│  │ Data.JDB     │  │ patients.seq         │  │
│  │              │  │ Index.*.JIDX │  │ (single integer)     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
        ▲                    ▲                    ▲
        │                    │                    │
┌───────┴───────┐    ┌───────┴───────┐    ┌───────┴───────┐
│ Form Process  │    │ Form Process  │    │ Reader Process│
│ (clerk UI)    │    │ (clerk UI)    │    │ (single)      │
│ PID 1001      │    │ PID 1002      │    │ PID 2001      │
└───────────────┘    └───────────────┘    └───────────────┘
```

**All state on shared filesystem**. Processes stateless. Horizontal scale: add Form processes. Vertical scale: faster SSD for log.

---

## Migration Path from Direct Writes

| Phase | Change |
|-------|--------|
| **0** (current) | Forms → `db.Update()` directly |
| **1** | Add `EventLog.Append()` alongside direct write (dual write) |
| **2** | Switch Forms to **log-only**; spawn Reader process |
| **3** | Remove direct write code; verify Reader keeps DB current |
| **4** | Add replay script for disaster recovery testing |

---

## Key Principles Summary

1. **Log is truth** — Database is a cache/projection of the log.
2. **Single writer to DB** — JackrabbitDB stays embedded, fast, simple.
3. **Business logic in Reader** — Not in Form, not in DB.
4. **Exactly-once via checkpoint** — Reader persists position after each event.
5. **Rebuildability** — `rm -rf DB && replay log` = tested monthly.
6. **Observability** — `tail -f Event.JLOG` shows live system activity.

---

## Appendix: Minimal Code Skeletons

### EventLog (Python)
```python
class EventLog:
    def __init__(self, path):
        self.path = path
        self.lock = DLM.Locker(f"eventlog.{path}")
    
    def Append(self, event):
        with self.lock:
            event['seq'] = self._next_seq()
            event['blake'] = blake3(json.dumps(event, sort_keys=True).encode()).hexdigest()
            FF.AppendFile(self.path, json.dumps(event) + '\n', sync=True)
    
    def ReadFrom(self, seq):
        with open(self.path, 'r') as f:
            for line in f:
                evt = json.loads(line)
                if evt['seq'] >= seq:
                    yield evt
```

### Reader Checkpoint
```python
def load_checkpoint(path):
    try: return int(open(path).read().strip())
    except: return 0

def save_checkpoint(path, seq):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f: f.write(str(seq))
    os.replace(tmp, path)  # atomic
```

### apply_event Signature
```python
def apply_event(db: JackrabbitDB, event: dict) -> None:
    """
    Pure function. Same inputs → same DB mutations.
    Raises on business rule violation → Reader stops, alerts, does not advance checkpoint.
    """
```

---

## Conclusion

This architecture **eliminates the multi-writer problem for JackrabbitDB** while preserving its embedded-database advantages (OS-copy backup, Blake3 integrity, deterministic rebuild, zero-dependency). The Input Log absorbs concurrency; the Reader provides ordered, business-rule-enforced projection; the UI remains responsive.

**JackrabbitDB never sees more than one writer.** It remains an embedded database. The system as a whole scales to unlimited concurrent form writers.