#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Jackrabbit DB
# 2024-2026 Copyright © Robert APM Darin
# All rights reserved unconditionally.

# JackrabbitDB is a reference implementation of a tamper-evident, reconstructable,
# provenance-tracking data layer. Its design properties: append, only JSONL,
# per-record Blake3, deterministic replay, explicit reconstruction markers, make
# it technically suitable as a component in high-trust architectures. Formal
# certification, regulatory assessment, and production hardening are the
# responsibility of the integrating organization.

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
    def __init__(self,name,idx=None,syncDB=True,syncIDX=False,expire=10):
        # Main database
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

        # Create index table
        self.dbIndex={}
        if idx:
            for i in idx:
                self.dbIndex[i]=f"{self.dbDir}/Index.{i}.JIDX"

        # Create cursors
        self.dbCursor={}

        # Report errors, including duplicates
        self.Error=None

        # Make database directory
        FF.mkdir(self.dbDir)

        # Force rebuild the index files
        self.CheckIndexes(True)

    # Decorator for locking

    @staticmethod
    def AlwaysLock(func):
        def wrapper(self, *args, **kwargs):
            expire=getattr(self, 'expire', 10)  # Read at RUNTIME

            # if its already locked, not the function responsible for the lock.
            # Just run the function.

            status=self.dbLock.IsLocked(expire=self.expire, acquire=False).lower()
            if status=="locked":
                return func(self, *args, **kwargs)

            # If we are not the owner, we just wait our turn, break on any error.

            while True:
                status=self.dbLock.IsLocked(expire=self.expire, acquire=True).lower()
                if status!='notowner':
                    break
                time.sleep(0.1) # sleep 1/10th second

            if status!="locked":
                self.Error=f"Lock failed: {status}"
                raise Exception(self.Error)

            try:
                return func(self, *args, **kwargs)
            finally:
                self.dbLock.Unlock()
        return wrapper

    # Create a Blake hash. Argument is JSON. Test just incase JSONL is passed

    def Blake(self,text):
        if isinstance(text,dict):
            rec=json.dumps(text)
        else:
            rec=text
        h=blake3.blake3() #hashlib.Blake(digest_size=64)
        h.update(rec.encode('utf-8'))
        return h.hexdigest()

    # Verify the record hash as stable. Argument COULD be JSON or JSONL

    def VerifyBlake(self,record):
        if isinstance(record,dict):
            # Do NOT damage the original. CRITICAL!
            rec=record.copy()
        else:
            try:
                rec=json.loads(record)
            except Exception as err:
                self.Error=err
                raise Exception("Blake3 verification failed.")

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
            text=json.dumps(data)
        else:
            text=data.strip()

        record=f"{cmd}|{text}\n"
        FF.AppendFile(self.dbTransaction,record,sync=self.syncDB)

    # Recycle tombstones if possible.  Returns T/F,offset. True if recycled

    @AlwaysLock
    def GetNextOffset(self, record):
        if isinstance(record, dict):
            rec=json.dumps(record)+'\n'
        else:
            rec=record.strip()+'\n'

        needed=len(rec)

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
        self.RebuildIndex(idx)
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

    # Reset cursor. 0 is start, -1 is end.

    @AlwaysLock
    def SetCursor(self,cursor,pos=None):
        if cursor not in self.dbIndex:
            raise Exception('Index not loaded: cursor')

        # Cursor not initialized
        if cursor not in self.dbCursor:
            if not pos:
                pos=0
            fidx=self.dbIndex[cursor].replace("|",".")
            entries=FF.ReadFile2List(fidx,Unique=False)
            idxMtime=os.path.getmtime(fidx)
            self.dbCursor[cursor]={ "Position":pos, "idxMtime":idxMtime, "Entries":entries }
        # Cursor initialized
        else:
            if not pos:
                pos=0

            self.dbCursor[cursor]["Position"]=pos

        fidx=self.dbIndex[cursor].replace("|",".")
        idxMtime=os.path.getmtime(fidx)

        # if disk file is more up-to-date, reload and resync cursor by
        # key (future concept)

        if self.dbCursor[cursor]['idxMtime']<idxMtime:
            pos=0
            entries=FF.ReadFile2List(fidx,Unique=False)
            self.dbCursor[cursor]={ "Position":pos, "idxMtime":idxMtime, "Entries":entries }
            return json.loads(self.dbCursor[cursor]["Entries"][pos])['Offset']

        # Set the cursor
        if pos<0:
            l=len(self.dbCursor[cursor]["Entries"])+pos
            if l<0:
                l=0
            self.dbCursor[cursor]["Position"]=l
            pos=l
            return json.loads(self.dbCursor[cursor]["Entries"][pos])['Offset']
        if pos>len(self.dbCursor[cursor]["Entries"])-1:
            pos=len(self.dbCursor[cursor]["Entries"])-1

        self.dbCursor[cursor]["Position"]=pos
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
        if self.dbCursor[cursor]['idxMtime']<os.path.getmtime(fidx):
            self.SetCursor(cursor,0)

        pos=self.dbCursor[cursor]["Position"]
        idx=self.dbCursor[cursor]["Entries"][pos]

        return pos,json.loads(idx)

    # Get the next record

    @AlwaysLock
    def Next(self,cursor):
        pos,idx=self.GetCursor(cursor=cursor)
        offset=self.SetCursor(cursor,pos+1)
        data=self.Read(offset)
        return data

    # Get the previous record

    @AlwaysLock
    def Previous(self,cursor):
        pos,idx=self.GetCursor(cursor=cursor)
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
        r=json.dumps(record)+'\n'
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
    def Update(self,offset,record):
        if record is None:
            return None, None

        # Get versions and add to latest update
        oldrec=self.Read(offset)
        vers=oldrec.pop('jrdbVersions',[])
        vers.append(oldrec)
        record['jrdbVersions']=vers
        record['jrdbUpdated']=time.time()
        # The old hash MUST be removed before calculating the new hash
        # MUST happen before write to disk.
        record.pop('jrdbBlake',None)
        record['jrdbBlake']=self.Blake(record)
        # Add update to bottom
        roa,ptr=self.GetNextOffset(record)
        r=json.dumps(record)+'\n'
        self.WriteTransaction("UPDATE",record)
        if roa:
            # Recycle space
            FF.WriteSeek(self.dbName,ptr,r.encode('utf-8'),sync=self.syncDB)
        else:
            # Add to end of file
            FF.AppendFile(self.dbName,r,sync=self.syncDB)
        # Turn old record to tombstone
        self.Delete(offset=offset)
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
        if not offset:
            return False

        # Verify old record, boundary start/Blake3
        # This blocks random offset attacks or bad programming
        buf=self.Read(offset)
        if buf is None:
            raise Exception(f"Record damaged as {offset}")
        buf=json.dumps(buf)  # STRIPS \n from count, which leave it in file
        self.WriteTransaction("DELETE",buf)
        # Write the tombstone, take off \n. We need to fill exact space
        dashes="-"*(len(buf)) # REMEMBER no \n in count
        # Open for read/write
        FF.WriteSeek(self.dbName,offset,dashes.encode('utf-8'),sync=self.syncDB)
        if not self.CheckTombstones(offset):
            # Processed, \n NOT included
            self.dbTombstones.append([offset,len(buf)+1])
        # Reset cursors
        self.dbCursor={}
        return True

    # Read a record at a position
    @AlwaysLock
    def Read(self,offset):
        self.dbLock.Lock(expire=self.expire)
        fh=open(self.dbName,"rb")
        fh.seek(offset,os.SEEK_SET)
        line=fh.readline()
        fh.close()
        if not line:
            return None
        try:
            line=json.loads(line)
        except Exception as err:
            self.Error=f"JSON: {err}"
            return None
        if not self.VerifyBlake(line):
            self.Error=f"DB Corruption: {line}"
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

        entries = FF.ReadFile2List(fidx, Unique=False)
        newentries=self.BuildIndexEntries(idx, record, ptr)
        if newentries!=[]:
            entries.extend(newentries)
            entries = self.SortIndex(entries)
            FF.WriteList2File(fidx, entries, sync=self.syncIDX)

    # Internal function to split lists into indexable elements.
    # An example would be { "Keywords": [Word1, word2] }
    # AlwaysLock, in this case, just serves to reset the lock timeout

    @AlwaysLock
    def BuildIndexEntries(self, idx, record, ptr):
        entries = []
        if "|" in idx:
            # Compound index: expand any list fields into multiple entries (cartesian product)
            parts = idx.split('|')
            value_lists = []
            for part in parts:
                raw = record.get(part)
                if isinstance(raw, list):
                    value_lists.append([str(v) for v in raw])
                elif raw is not None:
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
            raw = record.get(idx)
            if isinstance(raw, list):
                for elem in raw:
                    entries.append(json.dumps({"Key": str(elem), "Offset": ptr}))
            elif raw is not None:
                entries.append(json.dumps({"Key": raw, "Offset": ptr}))
            else:
                return []
        return entries

    @AlwaysLock
    def SortIndex(self,entries):
#        ne=sorted(entries,key=lambda x: json.loads(x)['Key'])
        ne=sorted(entries,key=lambda x: float(json.loads(x)['Offset']))
        return ne

    @AlwaysLock
    def CheckDuplicates(self,record):
        self.Error=None
        dup=False
        # We need to walk every index file
        for idx in self.dbIndex.keys():
            # Skip missing keys
            nf=False
            for k in idx.split("|"):
                if k not in record:
                    nf=True
            if nf:
                continue
            # Find the proper offset
            fidx=self.dbIndex[idx].replace("|",".")
            if os.path.exists(fidx):
                result=self.BinaryIndexSearch(idx,record)
                # We have a duplicate
                if result is not None:
                    self.Error="Duplicate"
                    return True
        return False

    # Check Index age and force a rebuild if needed

    @AlwaysLock
    def CheckIndexes(self,force=False):
        # No DB, nothing to check.
        if not os.path.exists(self.dbName):
            return

        # Check the indexes
        self.Error=None
        dbMtime=os.path.getmtime(self.dbName)
        # We need to walk every index file
        for idx in self.dbIndex.keys():
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
                if k not in record:
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

        entries = self.SortIndex(entries)
        fidx = self.dbIndex[idx].replace("|", ".")
        FF.WriteList2File(fidx, entries, sync=self.syncIDX)

    # Verify the integrity of the database

    @AlwaysLock
    def VerifyDatabase(self):
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
                print(self.Error)
                print(bline.decode('utf-8'))
                continue

            # Verify record integrity. Required to mintain a full "NO
            # TRUST" environment. There is a price to pay in latency and
            # overhead.

            if not self.VerifyBlake(record):
                self.Error="Corruption"
                print(f"Corruption: {bline.decode('utf-8')}")
                raise Exception("Database curruption")
        fh.close()

        if not self.Error:
            return True
        return False

    # Pack the database, remove tombstones

    @AlwaysLock
    def PackDatabase(self):
        # No DB, nothing to check.
        if not os.path.exists(self.dbName):
            return False

        # Make sure the work file does NOT exist
        packName=(f"{self.dbName}.packwork")
        if os.path.exists(packName):
            os.remove(packName)

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

            # Verify record integrity. Required to mintain a full "NO
            # TRUST" environment. There is a price to pay in latency and
            # overhead.

            if not self.VerifyBlake(record):
                self.Error="Corruption"
                raise Exception(f"Corruption: {bline.decode('utf-8')}")

            # WWrite out the new record
            FF.AppendFile(packName,json.dumps(record)+'\n',sync=self.syncDB)
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
            if substr in kv['Key']:
                results.append(kv['Offset'])
        return results

    # Binary search.  Really nice is index is already sorted.

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

        # Binary search on entries list (already sorted by Key)
        lo, hi=0, len(entries)-1
        while lo<=hi:
            mid=(lo+hi)//2
            kvtbl=json.loads(entries[mid])
            key=kvtbl["Key"]
            if key==target:
                return kvtbl['Offset']
            elif key<target:
                lo=mid+1
            else:
                hi=mid-1
        return None

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
        target = prefix
        lo, hi = 0, len(entries) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            key = json.loads(entries[mid])['Key']
            if key >= target:
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

    """
    offset=db.SetCursor(cursor="File",pos=-3)
    record=db.Read(offset)
    print(record)

    # Get current cursor
    pos,idx=db.GetCursor(cursor="File")
    print("Cursor:",pos,idx)
    """

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

    """
    # Test Next and previous
    print("Next/Previous tests")
    nrec=db.Next("File")
    print("N:",nrec)
    prec=db.Previous("File")
    print("P:",prec)
    """

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

    """
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
    """

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
