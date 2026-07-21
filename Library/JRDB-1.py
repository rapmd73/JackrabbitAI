#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Jackrabit DB
# 2024-2026 Copyright © Robert APM Darin
# All rights reserved unconditionally.

# This is an ISAM random access hybrid database using only JSONL structures.

import sys
sys.path.append('/home/JackrabbitAI/Library')
import os
import datetime
import time
import random
import json

import DecoratorFunctions as DF
import CoreFunctions as CF
import FileFunctions as FF

# primary = (time.time()*10000000).GetID()

class JackrabbitDB:
    def __init__(self, name, idx=None, unique=None):
        # Main database
        self.dbDir = name
        self.dbName = f"{self.dbDir}/Data.JDB"

        # Create index table
        # idx: list of field names to index
        # unique: dict mapping field name -> bool (True=unique, False=non-unique)
        self.dbIndex = {}
        self.dbUnique = {}
        
        if idx is None:
            idx = []
        if unique is None:
            unique = {}
            
        for i in idx:
            self.dbIndex[i] = f"{self.dbDir}/Index.{i}.JIDX"
            self.dbUnique[i] = unique.get(i, True)  # Default unique=True

        # Report errors, including duplicates
        self.Error = None

        FF.mkdir(self.dbDir)

    # Add a record to the database.  This also has to deal with all of
    # the indexes to prevent duplicates.

    def Add(self, record):
        # Check duplicates first (only for unique indexes)
        self.CheckDuplicates(record)
        if self.Error:
            return

        # Get current file size as offset for this record
        ptr = FF.GetFileSize(self.dbName)

        # Write the actual record (JSONL line)
        r = json.dumps(record) + '\n'
        FF.AppendFile(self.dbName, r, sync=True)

        # Update all indexes with this record's offset
        self.UpdateIndexes(ptr, record)

    # Actually update ALL index files.
    def UpdateIndexes(self, ptr, record):
        self.Error = None
        for idx in self.dbIndex.keys():
            self.UpdateSingleIndex(idx, ptr, record)

    def UpdateSingleIndex(self, idx, ptr, record):
        fidx = self.dbIndex[idx]
        key_value = record.get(idx)
        if key_value is None:
            return  # Field not in record, skip this index

        # Index entry format: {"Key": "value", "Offset": 123}
        new_entry = json.dumps({"Key": key_value, "Offset": ptr}) + '\n'

        if not os.path.exists(fidx):
            # New index file - just write the entry
            FF.WriteFile(fidx, new_entry, sync=True)
            return

        # Read existing index entries
        entries = FF.ReadFile2List(fidx, NoStripEmpty=True, Unique=False)
        if entries is None:
            entries = []

        # Parse each line as JSON
        parsed = []
        for line in entries:
            line = line.strip()
            if line:
                try:
                    parsed.append(json.loads(line))
                except:
                    pass

        # Insert new entry in sorted position (by Key)
        inserted = False
        for i, entry in enumerate(parsed):
            if key_value < entry["Key"]:
                parsed.insert(i, {"Key": key_value, "Offset": ptr})
                inserted = True
                break

        if not inserted:
            parsed.append({"Key": key_value, "Offset": ptr})

        # Write back as JSONL
        out_lines = [json.dumps(e) for e in parsed]
        FF.WriteList2File(fidx, out_lines, sync=True)

    def CheckDuplicates(self, record):
        self.Error = None
        for idx in self.dbIndex.keys():
            if self.dbUnique.get(idx, True):  # Only check unique indexes
                self.IndexCheckDuplicate(idx, record)
                if self.Error:
                    return

    def IndexCheckDuplicate(self, idx, record):
        fidx = self.dbIndex[idx]
        key_value = record.get(idx)
        if key_value is None:
            return

        if not os.path.exists(fidx):
            return

        # Check for duplicate key in sorted index file
        entries = FF.ReadFile2List(fidx, NoStripEmpty=True, Unique=False)
        if entries is None:
            return

        for line in entries:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("Key") == key_value:
                    self.Error = f"Duplicate key '{key_value}' in index '{idx}'"
                    return
            except:
                pass

    # Read a record by offset
    def ReadRecord(self, offset):
        if not os.path.exists(self.dbName):
            return None
        with open(self.dbName, 'r') as f:
            f.seek(offset)
            line = f.readline()
            if line:
                try:
                    return json.loads(line.strip())
                except:
                    pass
        return None

    # Get record by unique index key
    def Get(self, idx, key):
        if idx not in self.dbIndex:
            self.Error = f"Index '{idx}' does not exist"
            return None
        
        if not self.dbUnique.get(idx, True):
            self.Error = f"Index '{idx}' is not unique, use Search() instead"
            return None
            
        offset = self._FindOffset(idx, key)
        if offset is None:
            return None
        return self.ReadRecord(offset)

    # Search for all records matching index key (for non-unique indexes)
    def Search(self, idx, key):
        if idx not in self.dbIndex:
            self.Error = f"Index '{idx}' does not exist"
            return []
            
        offsets = self._FindAllOffsets(idx, key)
        results = []
        for offset in offsets:
            record = self.ReadRecord(offset)
            if record:
                results.append(record)
        return results

    # Binary search for single offset in sorted index file
    def _FindOffset(self, idx, key):
        fidx = self.dbIndex[idx]
        if not os.path.exists(fidx):
            return None
            
        entries = FF.ReadFile2List(fidx, NoStripEmpty=True, Unique=False)
        if entries is None:
            return None
            
        # Binary search since index is sorted
        low, high = 0, len(entries) - 1
        while low <= high:
            mid = (low + high) // 2
            try:
                entry = json.loads(entries[mid].strip())
                if entry["Key"] == key:
                    return entry["Offset"]
                elif entry["Key"] < key:
                    low = mid + 1
                else:
                    high = mid - 1
            except:
                return None
        return None

    # Find all offsets for a key (for non-unique indexes)
    def _FindAllOffsets(self, idx, key):
        fidx = self.dbIndex[idx]
        if not os.path.exists(fidx):
            return []
            
        entries = FF.ReadFile2List(fidx, NoStripEmpty=True, Unique=False)
        if entries is None:
            return []
            
        offsets = []
        for line in entries:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry["Key"] == key:
                    offsets.append(entry["Offset"])
            except:
                pass
        return offsets

    # Delete record by unique index key
    def Delete(self, idx, key):
        if idx not in self.dbIndex:
            self.Error = f"Index '{idx}' does not exist"
            return False
            
        if not self.dbUnique.get(idx, True):
            self.Error = f"Index '{idx}' is not unique, cannot delete by non-unique key"
            return False
            
        offset = self._FindOffset(idx, key)
        if offset is None:
            self.Error = f"Key '{key}' not found in index '{idx}'"
            return False
            
        # Append to tombstones file
        tombstone_file = f"{self.dbDir}/Tombstones.JDB"
        tombstone_entry = json.dumps({"Offset": offset, "Deleted": True}) + '\n'
        FF.AppendFile(tombstone_file, tombstone_entry, sync=True)
        
        # Remove from all indexes
        self._RemoveFromAllIndexes(offset)
        return True

    # Remove offset from all index files
    def _RemoveFromAllIndexes(self, offset):
        for idx in self.dbIndex.keys():
            self._RemoveFromIndex(idx, offset)

    def _RemoveFromIndex(self, idx, offset):
        fidx = self.dbIndex[idx]
        if not os.path.exists(fidx):
            return
            
        entries = FF.ReadFile2List(fidx, NoStripEmpty=True, Unique=False)
        if entries is None:
            return
            
        # Filter out entries with this offset
        filtered = []
        for line in entries:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry["Offset"] != offset:
                    filtered.append(line)
            except:
                pass
                
        # Write back
        FF.WriteList2File(fidx, filtered, sync=True)

    # Pack database - rewrite data file skipping tombstones, rebuild indexes
    def Pack(self):
        # Read tombstones
        tombstone_file = f"{self.dbDir}/Tombstones.JDB"
        tombstones = set()
        if os.path.exists(tombstone_file):
            entries = FF.ReadFile2List(tombstone_file, NoStripEmpty=True, Unique=False)
            if entries:
                for line in entries:
                    line = line.strip()
                    if line:
                        try:
                            t = json.loads(line)
                            tombstones.add(t["Offset"])
                        except:
                            pass
        
        # Read data file, write new compacted version
        new_data_file = f"{self.dbDir}/Data.JDB.new"
        new_offsets = {}  # old_offset -> new_offset
        
        if os.path.exists(self.dbName):
            with open(self.dbName, 'r') as f:
                while True:
                    offset = f.tell()
                    line = f.readline()
                    if not line:
                        break
                    line = line.strip()
                    if line and offset not in tombstones:
                        new_offset = FF.GetFileSize(new_data_file)
                        new_offsets[offset] = new_offset
                        FF.AppendFile(new_data_file, line + '\n', sync=True)
        
        # Replace old data file
        if os.path.exists(new_data_file):
            os.rename(new_data_file, self.dbName)
        
        # Rebuild all indexes with new offsets
        for idx in self.dbIndex.keys():
            self._RebuildIndex(idx, new_offsets)
        
        # Remove tombstones file
        if os.path.exists(tombstone_file):
            os.remove(tombstone_file)

    def _RebuildIndex(self, idx, offset_map):
        fidx = self.dbIndex[idx]
        new_fidx = fidx + ".new"
        
        if not os.path.exists(fidx):
            return
            
        entries = FF.ReadFile2List(fidx, NoStripEmpty=True, Unique=False)
        if entries is None:
            return
            
        for line in entries:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                old_offset = entry["Offset"]
                if old_offset in offset_map:
                    entry["Offset"] = offset_map[old_offset]
                    FF.AppendFile(new_fidx, json.dumps(entry) + '\n', sync=True)
            except:
                pass
        
        if os.path.exists(new_fidx):
            os.rename(new_fidx, fidx)

    # Rebuild index from data file (for ForceRebuild)
    def _RebuildIndexFromData(self, idx):
        fidx = self.dbIndex[idx]
        records = []
        
        if os.path.exists(self.dbName):
            with open(self.dbName, 'r') as f:
                while True:
                    offset = f.tell()
                    line = f.readline()
                    if not line:
                        break
                    line = line.strip()
                    if line:
                        try:
                            record = json.loads(line)
                            key_value = record.get(idx)
                            if key_value is not None:
                                records.append((key_value, offset))
                        except:
                            pass
        
        # Sort by key
        records.sort(key=lambda x: x[0])
        
        # Write as JSONL
        out_lines = [json.dumps({"Key": k, "Offset": o}) for k, o in records]
        FF.WriteList2File(fidx, out_lines, sync=True)

    # Force rebuild all indexes from data file
    def ForceRebuild(self):
        self.Error = None
        for idx in self.dbIndex.keys():
            self._RebuildIndexFromData(idx)

###
### End library
###
### Start test code
###

def TestDB():
    dir="/bin"
    db=JackrabbitDB("/tmp/FilesDB")
    for file in os.scandir("/bin"):
        nr={}
        nr['ID']=CF.GetID(31,31)
        nr['File']=os.path.realpath(f"{dir}/{file}")
        if os.path.isdir(nr['File']):
            nr['Type']='Directory'
        elif os.path.isfile(nr['File']):
            nr['Type']='File'
        elif os.path.islink(nr['File']):
            nr['Type']='SymLink'
        else:
            nr['Type']='Special'
        nr['Added']=time.time()
        db.Add(nr)

if __name__=="__main__":
    TestDB()
