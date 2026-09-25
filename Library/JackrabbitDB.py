#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Jackrabbit DB
# 2024-2026 Copyright © Robert APM Darin
# All rights reserved unconditionally.

# JackrabbitDB is a reference implementation of a tamper-evident,
# reconstructable, provenance-tracking data layer. Its design properties:
# append, only JSONL, per-record Blake3, deterministic replay, explicit
# reconstruction markers, make it technically suitable as a component in
# high-trust architectures. Formal certification, regulatory assessment, and
# production hardening are the responsibility of the integrating organization.

# Theory: This represents a single shard. Stacking shards creates concurrency.
# Shards are self contained fragments that interlink with a shard manager. For
# example: employ or product sharding can be A-Z or AA-ZZ or even timestamp
# based (daily or monthy).

import sys
sys.path.append('/home/JackrabbitAI/Library')
sys.path.append('/home/JackrabbitDLM')
import os
import blake3
import datetime
import time
import random
import json

import DLMLocker as DLM
import DecoratorFunctions as DF
import CoreFunctions as CF
import FileFunctions as FF

class JackrabbitDB:
    def __init__(self,name,idx=None,syncDB=True,syncIDX=False,expire=300):
        # Main database
        self.WalkDriver=False
        self.syncDB=syncDB
        self.syncIDX=syncIDX
        # Name of database becomes the directory name on disk
        self.dbDir=name
        self.dbName=f"{self.dbDir}/Data.JDB"
        self.dbTransaction=f"{self.dbDir}/Transaction.log"
        # locks have auto expire
        self.expire=expire
        self.dbLock=w1=DLM.Locker(f"dbLock.{self.dbDir}",Timeout=self.expire,Retry=7)
        # deleted records, time outs.
        self.dbTombstones=[]
        # Report errors, including duplicates
        self.Error=None
        # Create cursors
        self.dbCursor={}

        # Create index table
        self.dbIndex={}
        if idx:
            for i in idx:
                self.AddIndex(i)
#                self.dbIndex[i]=f"{self.dbDir}/Index.{i}.JIDX"

        # Make database directory
        FF.mkdir(self.dbDir)

        # Force rebuild the index files
        self.CheckIndexes()

    # Decorator for locking

    @staticmethod
    def AlwaysLock(func):
        def wrapper(self, *args, **kwargs):
            expire=getattr(self, 'expire', 300)  # Read at RUNTIME

            # if its already locked, not the function responsible for the lock.
            # Just run the function.

            status=self.IsLocked(False)
            if status=="locked":
                return func(self, *args, **kwargs)

            # If we are not the owner, we just wait our turn, break on any error.

            status=self.WaitLock()

            try:
                return func(self, *args, **kwargs)
            finally:
                self.Unlock()
        return wrapper

    # Locking primitives for DLM, ie db.IsLocked()

    # The goal here is a consistent way for a calling program to mnage
    # the lock.

    def IsLocked(self,acquire=False):
        return self.dbLock.IsLocked(expire=self.expire, acquire=acquire).lower()

    def Lock(self,expire=None):
        if not expire:
            expire=getattr(self, 'expire', 300)  # Read at RUNTIME

        status=self.dbLock.Lock(expire=expire)

        if status!="locked":
            self.Error=f"Lock failed: {status}"
            raise Exception(self.Error)

        return status

    def Unlock(self):
        return self.dbLock.Unlock()

    # Brutal and unforgiving, but stable
    def WaitLock(self):
        while True:
            status=self.IsLocked(True)
            if status!='notowner':
                break
            time.sleep(0.1) # sleep 1/10th second

        if status!="locked":
            self.Error=f"Lock failed: {status}"
            raise Exception(self.Error)

        return status

    # Create a Blake hash. Argument is JSON. Test just incase JSONL is passed

    def Blake(self,text):
        if isinstance(text,dict):
            rec=json.dumps(text,sort_keys=True,separators=(',', ':'))
        else:
            rec=text
        h=blake3.blake3() #hashlib.Blake(digest_size=64)
        h.update(rec.encode('utf-8'))
        return h.hexdigest()

    # Verify the record hash as stable. Argument COULD be JSON or JSONL

    @AlwaysLock
    def VerifyBlake(self,record):
        if isinstance(record,dict):
            # Do NOT damage the original. CRITICAL!
            rec=record.copy()
        else:
            try:
                rec=json.loads(record)
            except Exception as err:
                self.Error=f"Blake3 Verification failed: {err}"
                return False

        # Get old hash
        oldBlake=rec.get('jrdbBlake',None)

        # No hash, no match
        if oldBlake is None:
            return False

        # Get rid of the hash and generate the test hash.
        rec.pop('jrdbBlake',None)
        newBlake=self.Blake(rec)
        if newBlake==oldBlake:
            return True
        return False

    # Write out a transaction log

    @AlwaysLock
    def WriteTransaction(self,cmd,data):
        if isinstance(data,dict):
            text=json.dumps(data,sort_keys=True,separators=(',', ':'))
        else:
            text=data.strip()

        record=f"{cmd}|{text}\n"
        FF.AppendFile(self.dbTransaction,record,sync=self.syncDB)

    # Recycle tombstones if possible.  Returns T/F,offset. True if recycled

    @AlwaysLock
    def GetNextOffset(self, record):
        if isinstance(record, dict):
            rec=json.dumps(record,sort_keys=True,separators=(',', ':'))+'\n'
        else:
            rec=record.strip()+'\n'

        needed=len(rec)

        # First fit, probably should build a best fit version
        for i, (offset, length) in enumerate(self.dbTombstones):
            if length>=needed:
                # Exact fit - remove slot
                if length==needed:
                    self.dbTombstones.pop(i)
                # Partial fit - shrink slot
                else:
                    self.dbTombstones[i]=[offset+needed,length-needed]
                return True,offset
        return False,FF.GetFileSize(self.dbName)

    # Add index file

    @AlwaysLock
    def AddIndex(self,idx):
        # Alread added, nothing to do.
        if idx in self.dbIndex:
            return False

        # Register index path
        self.dbIndex[idx]=f"{self.dbDir}/Index.{idx}.JIDX"
        # Build index from existing data
        self.CheckSingleIndex(idx)
        if self.Error:
            self.RemoveIndex(idx)
            return False
        return True

    # Remove an index after initialization

    @AlwaysLock
    def RemoveIndex(self,idx,delete=False):
        # Not in list, nothing to do
        if idx not in self.dbIndex:
            return False

        fidx = self.dbIndex[idx].replace("|", ".")
        if os.path.exists(fidx) and delete:
            os.remove(fidx)
        self.dbIndex.pop(idx,None)
        self.dbCursor.pop(idx,None)
        return True

    # Reload the cursors from disk.

    @AlwaysLock
    def ReloadCursor(self,cursor,force=False):
        reload=False
        fidx=self.dbIndex[cursor].replace("|",".")

        # Make sure the file exists
        if not os.path.exists(fidx):
            self.dbCursor[cursor]={ "idxMtime":0, "Entries":[] }
            return True

        idxMtime=os.path.getmtime(fidx)

        # if disk file is more up-to-date, reload and resync cursor by
        # key (future concept)

        if force or self.dbCursor[cursor]['idxMtime']<idxMtime:
            reload=True
            entries=FF.ReadFile2List(fidx,Unique=False)
            self.dbCursor[cursor]={ "idxMtime":idxMtime, "Entries":entries }
        return reload

    # Reset cursor. 0 is start, -1 is end.

    @AlwaysLock
    def SetCursor(self,cursor,pos=None):
        if cursor not in self.dbIndex:
            raise Exception('Index not loaded: cursor')

        # Cursor not initialized
        if cursor not in self.dbCursor:
            if not pos:
                pos=0
            self.ReloadCursor(cursor,force=True)
            self.dbCursor[cursor]["Position"]=pos
        # Cursor initialized
        else:
            if not pos:
                pos=0
            self.dbCursor[cursor]["Position"]=pos

        # if disk file is more up-to-date, reload and resync cursor by
        # key (future concept)

        reload=self.ReloadCursor(cursor)
        if reload:
            pos=0
            self.dbCursor[cursor]["Position"]=pos
            # Only convert when ACTUALLY needed
            return json.loads(self.dbCursor[cursor]["Entries"][pos])['Offset']

        # Set the cursor
        if pos<0:
            l=len(self.dbCursor[cursor]["Entries"])+pos
            if l<0:
                l=0
            pos=l
        elif pos>len(self.dbCursor[cursor]["Entries"])-1:
            pos=len(self.dbCursor[cursor]["Entries"])-1

        self.dbCursor[cursor]["Position"]=pos
        # Only convert when ACTUALLY needed
        return json.loads(self.dbCursor[cursor]["Entries"][pos])['Offset']

    # Get cursor. Return both key and offset

    @AlwaysLock
    def GetCursor(self,cursor):
        if cursor not in self.dbIndex:
            raise Exception('Index not loaded: cursor')

        # Cursor not initialized
        if cursor not in self.dbCursor:
            offset=self.SetCursor(cursor,0)

        # Check staleness
        fidx = self.dbIndex[cursor].replace("|", ".")
        if os.path.exists(fidx) and self.dbCursor[cursor]['idxMtime']<os.path.getmtime(fidx):
            self.SetCursor(cursor,0)

        if self.dbCursor[cursor]["Entries"]==[]:
            pos=0
            idx={}
        else:
            pos=self.dbCursor[cursor]["Position"]
            idx=self.dbCursor[cursor]["Entries"][pos]

        return pos,json.loads(idx)

    # Get the next record

    @AlwaysLock
    def Next(self,cursor):
        pos,idx=self.GetCursor(cursor=cursor)
        if idx=={} or pos>=len(self.dbCursor[cursor]["Entries"])-1:
            return None
        offset=self.SetCursor(cursor,pos+1)
        data=self.Read(offset)
        return data

    # Get the previous record

    @AlwaysLock
    def Previous(self,cursor):
        pos,idx=self.GetCursor(cursor=cursor)
        if idx=={} or pos<=0:
            return None
        offset=self.SetCursor(cursor,pos-1)
        data=self.Read(offset)
        return data

    # Add a record to the database.  This also has to deal with all of
    # the indexes to prevent duplicates.

    @AlwaysLock
    def Add(self,record):
        self.CheckIndexes()
        if self.Error:
            raise Exception(f"Index stability check failed: {self.Error}")
        if self.CheckDuplicates(record):
            return None, None

        record['jrdbAdded']=time.time()
        record['jrdbBlake']=self.Blake(record)
        # Find next offset, recycle tombstones if possible
        roa,ptr=self.GetNextOffset(record)
        r=json.dumps(record,sort_keys=True,separators=(',', ':'))+'\n'
        self.WriteTransaction("ADD",record)
        if roa:
            # Recycle space
            FF.WriteSeek(self.dbName,ptr,r.encode('utf-8'),sync=self.syncDB)
        else:
            # Add to end of file
            FF.AppendFile(self.dbName,r,sync=self.syncDB)
        self.UpdateIndexes(ptr,record)
        # Reset cursors
        self.dbCursor={}
        return ptr,record

    # Update: append new record.  turn old record into tombstones.

    @AlwaysLock
    def Update(self,offset,record,override=False):
        if record is None:
            return None, None

        # Get versions and add to latest update
        oldrec=self.Read(offset,override=override)
        if oldrec==None:
            raise Exception(f"Corruption: {offset}/{record}")
        vc=oldrec.pop('jrdbVersionCount',0)
        vers=oldrec.pop('jrdbVersions',[])
        vers.append(oldrec)
        record['jrdbVersions']=vers
        record['jrdbVersionCount']=len(vers)
        record['jrdbUpdated']=time.time()
        # The old hash MUST be removed before calculating the new hash
        # MUST happen before write to disk.
        while 'jrdbBlake' in record:
            record.pop('jrdbBlake',None)
        record['jrdbBlake']=self.Blake(record)
        # Add update to bottom
        roa,ptr=self.GetNextOffset(record)
        r=json.dumps(record,sort_keys=True,separators=(',', ':'))+'\n'
        self.WriteTransaction("UPDATE",record)
        # Turn old record to tombstone
        self.Delete(offset=offset)
        # Write the new record
        if roa:
            # Recycle space
            FF.WriteSeek(self.dbName,ptr,r.encode('utf-8'),sync=self.syncDB)
        else:
            # Add to end of file
            FF.AppendFile(self.dbName,r,sync=self.syncDB)
        # Rebuild indexes
        self.CheckIndexes()
        # Reset cursors
        self.dbCursor={}
        return ptr,record

    # Find offset in tombstone list

    @AlwaysLock
    def CheckTombstones(self,offset):
        for ts in self.dbTombstones:
            if offset==ts[0]:
                return True
        return False

    # Delete a record
    @AlwaysLock
    def Delete(self,offset=None):
        if offset is None:
            return False

        # Verify old record, boundary start/Blake3
        # This blocks random offset attacks or bad programming
        buf=self.Read(offset)
        if buf is None:
            raise Exception(f"Record damage as {offset}")
        buf=json.dumps(buf,sort_keys=True,separators=(',', ':'))  # STRIPS \n from count, which leave it in file
        self.WriteTransaction("DELETE",buf)
        # Write the tombstone, take off \n. We need to fill exact space
        dashes="-"*(len(buf)) # REMEMBER no \n in count
        # Open for read/write
        FF.WriteSeek(self.dbName,offset,dashes.encode('utf-8'),sync=self.syncDB)
        if not self.CheckTombstones(offset):
            # Processed, \n NOT included
            self.dbTombstones.append([offset,len(buf)+1])
        # Rebuild indexes
        self.CheckIndexes()
        # Reset cursors
        self.dbCursor={}
        return True

    # Read a record at a position
    @AlwaysLock
    def Read(self,offset,override=False):
        self.dbLock.Lock(expire=self.expire)
        fh=open(self.dbName,"rb")
        fh.seek(offset,os.SEEK_SET)
        line=fh.readline()
        fh.close()

        if not line:
            fs=FF.GetFileSize(self.dbName)
            if offset>fs:
                self.Error="Read past end"
            return None
        try:
            line=json.loads(line)
        except Exception as err:
            self.Error=f"JSON: {err}"
            return None

        # Override allows reading the message with Blake3 fails. Critical
        # for diagnostics.
        if override:
            return line

        if not override and not self.VerifyBlake(line):
            self.Error=f"Read Corruption: {line}"
            raise Exception(self.Error)
        return line

    # Actually update ALL index files.

    @AlwaysLock
    def UpdateIndexes(self,ptr,record):
        self.Error=None
        # We need to walk every index file
        for idx in self.dbIndex.keys():
            self.UpdateSingleIndex(idx,ptr,record)

    @AlwaysLock
    def UpdateSingleIndex(self,idx,ptr,record):
        fidx = self.dbIndex[idx].replace("|", ".")
        if not os.path.exists(fidx):
            entries = self.BuildIndexEntries(idx, record, ptr)
            FF.WriteList2File(fidx, entries, sync=self.syncIDX)
            return

        # If there is no new entries, don't waste cycles resaving the
        # file.

        entries = FF.ReadFile2List(fidx, Unique=False)
        newentries=self.BuildIndexEntries(idx, record, ptr)
        if newentries!=[]:
            entries.extend(newentries)
            entries = self.SortIndex(entries,idx)
            FF.WriteList2File(fidx, entries, sync=self.syncIDX)

    # Internal function to split lists into indexable elements.
    # An example would be { "Keywords": [Word1, word2] }
    # AlwaysLock, in this case, just serves to reset the lock timeout

    @AlwaysLock
    def BuildIndexEntries(self, idx, record, ptr):
        entries = []
        if "|" in idx:

            # Compound index: expand any list fields into multiple entries
            # (cartesian product)

            # Reverse sorting marker doesn't matter here.

            parts = idx.split('|')
            value_lists = []
            for part in parts:
                raw = record.get(part.lstrip("!"),None)
                if isinstance(raw, list):
                    value_lists.append([str(v) for v in raw])
                elif raw is not None and raw!="":
                    value_lists.append([str(raw)])
                else:
                    return []

            # Compound list, a list of lists
            combos = [[]]
            for vl in value_lists:
                new_combos = []
                for prefix in combos:
                    for v in vl:
                        new_combos.append(prefix + [v])
                combos = new_combos

            # Build the index framing
            for combo in combos:
                val = "|".join(combo)
                entries.append(json.dumps({"Key": val, "Offset": ptr}))
        else:
            raw = record.get(idx,None)
            if isinstance(raw, list):
                for elem in raw:
                    entries.append(json.dumps({"Key": str(elem), "Offset": ptr}))
            elif raw is not None and raw!="":
                entries.append(json.dumps({"Key": raw, "Offset": ptr}))
            else:
                return []
        return entries

    # SortIndex

    # Unique situation in that multple parts (|) must be separated to get number
    # sorted numbers. Need to learn:

    # Build a tuple list from the index(es), including reverses
    # Sort the tuple list
    # build the return list from the tuple list.

    # Convert one '|' component to a comparable tuple:
    # numeric -> (0, real_float, imag_float, '')  (numbers sort before strings)
    # string  -> (1, 0.0, 0.0, lowered_string)   (strings sort after numbers)

    def inverseString(self,s):
        return ''.join(chr(0x10FFFF-ord(ch)) for ch in s)

    def ComparePartKey(self,p,reverse=False):
        s = str(p).strip()
        if s == '':
            return (1, 0.0, '')            # empty -> string-like
        try:
            # safe parse of Python literals (integers, floats, complex like
            # '2j', underscores allowed)

            v = float(s)
        except Exception:
            if reverse:
                return (1, 0.0, self.inverseString(s.lower()))    # not a literal number -> string
            else:
                return (1, 0.0, s.lower())
        # numeric types
        if isinstance(v, (int, float)):
            if reverse:
                return (0, -float(v), '')
            else:
                return (0, float(v), '')
        # anything else -> treat as string
        if reverse:
            return (1, 0.0, self.inverseString(s.lower()))    # not a literal number -> string
        else:
            return (1, 0.0, s.lower())

    # Compare ALL keys
    # Remove "!" from each part for reverse sorting
    # Used in searching

    def CompareAllKeys(self,s):
        tlist=[]
        for p in str(s).split('|'):
            if p.startswith("!"):
                tlist.append(self.ComparePartKey(p.lstrip("!"),reverse=True))
            else:
                tlist.append(self.ComparePartKey(p))
        return tuple(tlist)

    # Sorting an unknown number of keys is problematic, so we build ONE mater key,
    # most significant to least significant and sort that.

    @AlwaysLock
    def SortIndex(self, entries, idx):
        # Figure out the reverse map from the index
        rmap=[]
        for p in idx.split('|'):
            if p.startswith("!"):
                rmap.append(True)
            else:
                rmap.append(False)

        # Build tuple list, 4x fster (supposedly) over regular lists
        tlist=[]
        for entry in entries:
            tl=[]
            try:
                parts=json.loads(entry)['Key'].split("|")
            except Exception as err:
                tl.append([(2, 0.0, ''),entry])
                continue

            for p in range(len(parts)):
                tl.append(self.ComparePartKey(parts[p].lstrip("!"),reverse=rmap[p]))

            # For building the final sorted list, [0] is the combined sort key
            tlist.append([tuple(tl),entry])

        # Sort the tuples, ignore the data
        slist=sorted(tlist, key=lambda kv: kv[0])

        # Build final list and return, data at [-1]
        nlist=[]
        for i in range(len(slist)):
            nlist.append(slist[i][-1])
        return nlist

    @AlwaysLock
    def CheckDuplicates(self,record):
        self.Error=None
        dup=False
        # We need to walk every index file
        for idx in self.dbIndex.keys():
            # Skip missing keys
            nf=False
            for k in idx.split("|"):
                if k.lstrip("!") not in record:
                    nf=True
            if nf:
                continue
            # Find the proper offset
            fidx=self.dbIndex[idx].replace("|",".")
            if os.path.exists(fidx):
                result=self.BinaryIndexSearch(idx,record)
                # We have a duplicate
                if result>-1:   # -1 Not found
                    self.Error="Duplicate"
                    return True
        return False

    # Check Index age and force a rebuild if needed

    @AlwaysLock
    def CheckIndexes(self,force=False):
        # No DB, nothing to check. Also, if WalkDriver is active
        if not os.path.exists(self.dbName) or self.WalkDriver:
            return

        # Check the indexes
        self.Error=None
        dbMtime=os.path.getmtime(self.dbName)
        # We need to walk every index file
        for idx in self.dbIndex.keys():
            self.CheckSingleIndex(idx,force)

    # Check Index age and force a rebuild if needed

    @AlwaysLock
    def CheckSingleIndex(self,idx,force=False):
        # No DB, nothing to check. Also, if WalkDriver is active
        if not os.path.exists(self.dbName) or self.WalkDriver:
            return

        # Check the index
        self.Error=None
        dbMtime=os.path.getmtime(self.dbName)

        fidx=self.dbIndex[idx].replace("|",".")
        if os.path.exists(fidx) or force:
            iMtime=0
            if not force:
                iMtime=os.path.getmtime(fidx)
            if iMtime<dbMtime:
                self.RebuildIndex(idx)
        else:
            self.RebuildIndex(idx)

    # Rebuild a single index

    @AlwaysLock
    def RebuildIndex(self,idx):
        # No DB, nothing to check.
        if not os.path.exists(self.dbName):
            return

        # Force rebuild
        self.Error = None
        self.dbTombstones = []
        entries = []
        ptr = 0
        fh = open(self.dbName, "rb")
        while True:
            bline = fh.readline()
            # No more data
            if not bline:
                break
            # Tombstone record
            if not bline.startswith(b'{'):
                # Add to tombstone registry
                if not self.CheckTombstones(ptr):
                    # This is RAW line, \n included
                    self.dbTombstones.append([ptr, len(bline)])
                ptr+=len(bline)
                continue

            try:
                record = json.loads(bline)
            except Exception as err:
                ptr+=len(bline)
                print("REBUILD JSON:", err)
                print(bline)
                continue

            # If a key is NOT actually in the record, skip this record.
            nf=False
            for k in idx.split("|"):
                if k.lstrip("!") not in record:
                    nf=True
            if nf==True:
                # This should have been a "no brainer", but is was an
                # absolute nightmare to debug.
                ptr+=len(bline)
                continue

            # Use shared helper — expands lists, handles compound, skips None
            entries.extend(self.BuildIndexEntries(idx,record,ptr))
            ptr+=len(bline)
        fh.close()

        ####> Problem is index is sent in compound. This is BROKE. it sees the
        ####> ENTIRE list, not individual columns.

        entries = self.SortIndex(entries,idx)
        fidx = self.dbIndex[idx].replace("|", ".")
        FF.WriteList2File(fidx, entries, sync=self.syncIDX)

    # Verify the integrity of the database

    @AlwaysLock
    def VerifyDatabase(self,display=False):
        # No DB, nothing to check.
        if not os.path.exists(self.dbName):
            return False

        # Force rebuild
        self.Error=None
        ptr=0
        fh=open(self.dbName,"rb")
        while True:
            bline=fh.readline()
            if not bline:
                break
            # Tomestone or broken
            if not bline.startswith(b'{'):
                ptr+=len(bline)
                continue

            try:
                record=json.loads(bline)
            except Exception as err:
                ptr+=len(bline)
                self.Error="VerifyDB JSON: {err}"
                if display:
                    print(self.Error)
                    print(bline.decode('utf-8'))
                continue

            # Verify record integrity. Required to mintain a full "NO
            # TRUST" environment. There is a price to pay in latency and
            # overhead.

            if not self.VerifyBlake(record):
                self.Error="Corruption: Blake verification failed"
                if display:
                    print(f"Corruption: {bline.decode('utf-8')}")
        fh.close()

        if not self.Error:
            return True
        return False

    # Pack the database, remove tombstones

    # idx is a SINGLE index that will be used to force deduplicate the database on
    # a first come fist used approached.

    @AlwaysLock
    def PackDatabase(self,idx=None,RemoveCorrupt=False):
        # No DB, nothing to check.
        if not os.path.exists(self.dbName):
            return False

        # Make sure the work file does NOT exist
        packName=(f"{self.dbName}.packwork")
        if os.path.exists(packName):
            os.remove(packName)

        # the list we will use to verify NO duplicates if idx is NOT None.
        ilist=[]

        # Force pack
        self.Error=None
        fh=open(self.dbName,"r")
        while True:
            bline=fh.readline()
            if not bline:
                break

            # Tomestone or broken, skip
            if not bline.startswith('{'):
                continue

            try:
                record=json.loads(bline)
            except Exception as err:
                self.Error="VerifyDB JSON: {err}"
                print(self.Error)
                print(bline.decode('utf-8'))
                continue

            # Check for duplicate idx

            if idx:
                sidx=idx.lstrip("!")
                if sidx and record[sidx] in ilist:
                    continue

            # Verify record integrity. Required to mintain a full "NO
            # TRUST" environment. There is a price to pay in latency and
            # overhead.

            if not self.VerifyBlake(record):
                if RemoveCorrupt:
                    self.WriteTransaction("CORRUPT",bline)
                else:
                    self.Error="Corruption"
                    raise Exception(f"Corruption: {bline.strip()}")

            # Write out the new record
            if idx:
                ilist.append(record[idx])
            FF.AppendFile(packName,json.dumps(record,sort_keys=True,separators=(',', ':'))+'\n',sync=self.syncDB)
        fh.close()

        try:
            os.replace(self.dbName,f"{self.dbName}.backup")
            os.replace(packName,self.dbName)
        except Exception as err:
            self.Error="Pack Failure"
        if self.Error:
            return False
        return True

    # Linear (brute force) search

    @AlwaysLock
    def LinearIndexSearch(self,idx,record):
        # Index: { "Key":"/bin/bash", "Offset":"123" }
        # Read the actual index into a list
        # Linear search
        fidx=self.dbIndex[idx].replace("|",".")
        entries=FF.ReadFile2List(fidx,Unique=False)
        kvtbl={}
        for line in entries:
            try:
                kvtbl=json.loads(line)
            except Exception as err:
                print(err)
                continue
            # Duplicate
            if "|" in idx:
                val="|".join(str(record[k]) for k in idx.split('|'))
                if val==kvtbl['Key']:
                    self.Error="Duplicate"
                    return kvtbl['Offset']
            elif record[idx]==kvtbl['Key']:
                self.Error="Duplicate"
                return kvtbl['Offset']
        return None

    # Search inde records text ANYWHRE in the index key: search bash,
    # finds rbash.

    @AlwaysLock
    def LinearContainsSearch(self, idx, substr):
        fidx = self.dbIndex[idx].replace("|", ".")
        if not os.path.exists(fidx):
            return None
        entries = FF.ReadFile2List(fidx, Unique=False)
        if not entries:
            return None

        results = []
        for line in entries:
            try:
                kv = json.loads(line)
            except Exception:
                continue
            if substr.lower() in kv['Key'].lower():
                results.append(kv['Offset'])
        return results

    # Binary search.  Really nice is index is already sorted. record[] is JSON

    @AlwaysLock
    def BinaryIndexSearch(self, idx, record):
        fidx=self.dbIndex[idx].replace("|", ".")
        entries=FF.ReadFile2List(fidx,Unique=False)
        if not entries:
            return -1

        # Build search key
        if "|" in idx:
            target="|".join(str(record[k]) for k in idx.split("|"))
        else:
            target=str(record[idx])

        target=self.CompareAllKeys(target)

        # Binary search on entries list (already sorted by Key)
        hi=len(entries)-1
        lo=0
        while lo<=hi:
            mid=(lo+hi)//2
            kvtbl=json.loads(entries[mid])
            key=self.CompareAllKeys(kvtbl["Key"])
            if key==target:
                return kvtbl['Offset']
            elif key<target:
                lo=mid+1
            else:
                hi=mid-1
        return -1

    # Search a binary index for a prefix. Indexes MUST be unique, but
    # some thing might bot be, like filename or keyword.

    @AlwaysLock
    def BinaryPrefixSearch(self, idx, prefix):
        # Find ALL entries where Key starts with prefix.
        # idx = "Keywords|ID", prefix = "bombs|"
        # Returns list of offsets (may be empty).

        fidx = self.dbIndex[idx].replace("|", ".")
        entries = FF.ReadFile2List(fidx, Unique=False)
        if not entries:
            return None

        # Binary search for LEFTMOST entry >= prefix
        target=self.CompareAllKeys(prefix)
        lo=0
        hi=len(entries) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            kvtbl=json.loads(entries[mid])
            key=self.CompareAllKeys(kvtbl["Key"])
            if key>=target:
                hi = mid - 1
            else:
                lo = mid + 1

        # lo = first entry >= prefix. Scan forward while prefix matches.
        results = []
        for i in range(lo, len(entries)):
            kv = json.loads(entries[i])
            if kv['Key'].startswith(prefix):
                results.append(kv['Offset'])
            else:
                break
        return results

    # Blind search for a string in all indexes

    @AlwaysLock
    def SearchContains(self,srch):
        self.Error=None
        results=[]
        # We need to walk every index file
        for idx in self.dbIndex.keys():
            fidx=self.dbIndex[idx].replace("|",".")
            if os.path.exists(fidx):
                entries=FF.ReadFile2List(fidx,Unique=False)
                for line in entries:
                    try:
                        kvtbl=json.loads(line)
                    except Exception as err:
                        continue
                    # If srch string found, add to results list
                    if srch in kvtbl['Key'] and kvtbl['Key'] not in results:
                        kvtbl['SearchIndex']=idx
                        results.append(kvtbl)

        if results==[]:
            return None
        return results

    # Walk each record of the database and call a support function, could
    # be a verification, backup, so on.

    @AlwaysLock
    def Walk(self, idx, callback,override=False):
        if idx not in self.dbIndex:
            raise Exception(f"Index not loaded: {idx}")

        fidx = self.dbIndex[idx].replace("|", ".")
        if not os.path.exists(fidx):
            return 0

        self.WalkDriver=True
        entries = FF.ReadFile2List(fidx, Unique=False)
        count = 0

        for line in entries:
            try:
                kv = json.loads(line)
            except Exception:
                continue

            offset = kv["Offset"]
            record = self.Read(offset,override=override) # acquires lock, verifies Blake3
            if record is None:
                continue              # tombstone or corrupt

            if not callback(self, record, offset):
                break
            count+=1
        self.WalkDriver=False
        return count

###
### End library
###
### Start test code
###

def TestDB():
    dir="/bin"
    if len(sys.argv)>1:
        dir=sys.argv[1]

    # Create/Open database
    db=JackrabbitDB("/tmp/FilesDB",idx=["ID","File"])

    # Add additional indexes
    db.AddIndex("File|ID")
    db.AddIndex("Filename|ID")
    db.AddIndex("LastAccessed|File")
    db.AddIndex("Pathway|ID")

    # Add files as data set
    print("Add data")
    for file in os.listdir(dir):
        nr={}
        nr['ID']=CF.GetID(31,31)
        nr['File']=os.path.abspath(f"{dir}/{file}")
        nr['Filename']=f"{file}"
        nr['Pathway']=nr['File'].split('/')
        while '' in nr['Pathway']:
            nr['Pathway'].remove('')
        nr['RealFile']=os.path.realpath(f"{dir}/{file}")
        nr['LastAccessed']=os.path.getatime(f"{dir}/{file}")
        if os.path.isdir(nr['File']):
            nr['Type']='Directory'
        elif os.path.isfile(nr['File']):
            nr['Type']='File'
        elif os.path.islink(nr['File']):
            nr['Type']='SymLink'
        else:
            nr['Type']='Special'
        stime=time.time()
        db.Add(nr)
        etime=time.time()
        if db.Error and db.Error!="Duplicate":
            print(f"{db.Error} {nr['File']}")

    # Force set cursor
    print("Cursor tests")
    offset=db.SetCursor(cursor="File",pos=6)
    record=db.Read(offset)
    print(record)

    offset=db.SetCursor(cursor="File",pos=-3)
    record=db.Read(offset)
    print(record)

    # Get current cursor
    pos,idx=db.GetCursor(cursor="File")
    print("Cursor:",pos,idx)

    # Binary index searching
    key=record['ID']
    result=db.BinaryIndexSearch("ID",record)
    print("Binary Index Search:",result)

    # Binary prefix searching
    result=db.BinaryPrefixSearch("Pathway|ID","bash")
    print("Binary Prefix Search:",result)
    print(db.Read(result[0]))

    # Linear Containment
    result=db.LinearContainsSearch("Filename|ID","bash")
    print("Linear Contains Search:",result)
    for offset in result:
        record=db.Read(offset)
        print(record)

    # Test Next and previous
    print("Next/Previous tests")
    nrec=db.Next("File")
    print("N:",nrec)
    prec=db.Previous("File")
    print("P:",prec)

    # Find all records with "bash" and edit them
    print("Edit tests")
    results=db.SearchContains("bash")
    if results:
        lu=[] # Searching multiple indexes can give duplicate offsets.
        for res in results:
            if res['Offset'] not in lu:
                lu.append(res['Offset'])
                record=db.Read(res['Offset'])
                if not db.Error:
                    record['EditCount']=record.get('EditCount',0)+1
                    ptr,newrec=db.Update(res['Offset'],record)

    # Find and delete all records with python in them
    print("Delete tests")
    results=db.SearchContains("python")
    if results:
        lu=[]
        for res in results:
            if res['Offset'] not in lu:
                lu.append(res['Offset'])
                if not db.Error:
                    done=db.Delete(res['Offset'])
                    print(done,res['Key'])
    # Verify cursor reset, Will actualy be recrord 1, Next of current (0)
    # from reset from modifications.

    print("Cursor invalidation test")
    nrec=db.Next("File")
    print("CIT:",nrec)

    # Remove additional indexes
    db.RemoveIndex("ID")
    db.RemoveIndex("File")
    db.RemoveIndex("Filename|ID")
    db.RemoveIndex("File|ID")
    db.RemoveIndex("LastAccessed|File")

    if not db.PackDatabase():
        print("Pack corruption.")
    if not db.VerifyDatabase():
        print("Verification FAILED: Database corruption.")

if __name__=="__main__":
    TestDB()
