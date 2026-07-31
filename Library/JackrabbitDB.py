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
    def __init__(self,name,idx=None,syncDB=True,syncIDX=False):
        # Main database
        self.syncDB=syncDB
        self.syncIDX=syncIDX
        self.dbDir=name
        self.dbName=f"{self.dbDir}/Data.JDB"
        self.dbTransaction=f"{self.dbDir}/Transaction.log"
        self.dbLock=w1=DLM.Locker(f"dbLock.{self.dbDir}",Timeout=10,Retry=7)
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

    def WriteTransaction(self,cmd,data):
        if isinstance(data,dict):
            text=json.dumps(data)
        else:
            text=data.strip()

        record=f"{cmd}|{text}\n"
        FF.AppendFile(self.dbTransaction,record,sync=self.syncDB)

    # Recycle tombstones if possible.  Returns T/F,offset. True if recycled

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

    def AddIndex(self,idx):
        # Alread added, nothing to do.
        if idx in self.dbIndex:
            return False

        self.dbLock.Lock(expire=10)
        # Register index path
        self.dbIndex[idx]=f"{self.dbDir}/Index.{idx}.JIDX"
        # Build index from existing data
        self.RebuildIndex(idx)
        self.dbLock.Unlock()
        if self.Error:
            self.dbIndex.pop(idx,None)
            return False
        return True

    # Remove an index after initialization

    def RemoveIndex(self,idx,delete=False):
        # Not in list, nothing to do
        if idx not in self.dbIndex:
            return False

        self.dbLock.Lock(expire=10)
        fidx = self.dbIndex[idx].replace("|", ".")
        if os.path.exists(fidx) and delete:
            os.remove(fidx)
        self.dbIndex.pop(idx,None)
        self.dbCursor.pop(idx,None)
        self.dbLock.Unlock()
        return True

    # Reset cursor. 0 is start, -1 is end.

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

    def GetCursor(self,cursor):
        if cursor not in self.dbIndex:
            raise Exception('Index not loaded: cursor')

        # Cursor not initialized
        if cursor not in self.dbCursor:
            pos=0
            fidx=self.dbIndex[cursor].replace("|",".")
            idxMtime=os.path.getmtime(fidx)
            entries=FF.ReadFile2List(fidx,Unique=False)
            self.dbCursor[cursor]={ "Position":pos, "idxMtime":idxMtime, "Entries":entries }

        pos=self.dbCursor[cursor]["Position"]
        idx=self.dbCursor[cursor]["Entries"][pos]

        return pos,json.loads(idx)

    # Get the next record

    def Next(self,cursor):
        pos,idx=self.GetCursor(cursor=cursor)
        data=self.Read(pos)
        self.SetCursor(cursor,pos+1)
        return data

    # Get the previous record

    def Previous(self,cursor):
        pos,idx=self.GetCursor(cursor=cursor)
        data=self.Read(pos)
        self.SetCursor(cursor,pos-1)

    # Add a record to the database.  This also has to deal with all of
    # the indexes to prevent duplicates.

    def Add(self,record):
        self.dbLock.Lock(expire=10)
        self.CheckIndexes()
        if self.Error:
            raise Exception(f"Index stability check failed: {self.Error}")
        self.CheckDuplicates(record)
        if self.Error:
            self.dbLock.Unlock()
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
        self.dbLock.Unlock()
        return ptr,record

    # Update: append new record.  turn old record into tombstones.
    def Update(self,offset,record):
        if record is None:
            return None, None

        self.dbLock.Lock(expire=10)
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
        self.dbLock.Unlock()
        return ptr,record

    # Find offset in tombstone list

    def CheckTombstones(self,offset):
        for ts in self.dbTombstones:
            if offset==ts[0]:
                return True
        return False

    # Delete a record
    def Delete(self,offset=None):
        if not offset:
            return False

        self.dbLock.Lock(expire=10)
        # Verify old record, boundary start/Blake3
        # This blocks random offset attacks or bad programming
        buf=self.Read(offset)
        if buf is None:
            self.dbLock.Unlock()
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
        self.dbLock.Unlock()
        return True

    # Read a record at a position
    def Read(self,offset):
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

    def UpdateIndexes(self,ptr,record):
        # If already locked, do NOT unlock it
        NoUnlock=not (self.dbLock.IsLocked(expire=10,acquire=False)=='Locked')
        self.dbLock.Lock(expire=10)
        self.Error=None
        # We need to walk every index file
        for idx in self.dbIndex.keys():
            self.UpdateSingleIndex(idx,ptr,record)
        if not NoUnlock:
            self.dbLock.Unlock()

    def UpdateSingleIndex(self,idx,ptr,record):
        # If already locked, do NOT unlock it
        NoUnlock=not (self.dbLock.IsLocked(expire=10,acquire=False)=='Locked')
        self.dbLock.Lock(expire=10)

        kvtbl={}
        fidx=self.dbIndex[idx].replace("|",".")
        if not os.path.exists(fidx):
            # Add new or overwrite old
            if "|" in idx:
                val="|".join(str(record[k]) for k in idx.split('|'))
                kvtbl={ "Key":val, "Offset":ptr }
            else:
                kvtbl={ "Key":record[idx], "Offset":ptr }
            entries=[ json.dumps(kvtbl) ]
            FF.WriteList2File(fidx,entries,sync=self.syncIDX)
            if not NoUnlock:
                self.dbLock.Unlock()
            return

        entries=FF.ReadFile2List(fidx,Unique=False)
        kvtbl={}
        # Add new or overwrite old
        if "|" in idx:
            val="|".join(str(record[k]) for k in idx.split('|'))
            kvtbl={ "Key":val, "Offset":ptr }
        else:
            kvtbl={ "Key":record[idx], "Offset":ptr }
        entries.append(json.dumps(kvtbl))
        entries=self.SortIndex(entries)
        FF.WriteList2File(fidx,entries,sync=self.syncIDX)
        if not NoUnlock:
            self.dbLock.Unlock()

    def SortIndex(self,entries):
        ne=sorted(entries,key=lambda x: json.loads(x)['Key'])
        return ne

    def CheckDuplicates(self,record):
        self.Error=None
        dup=False
        # We need to walk every index file
        for idx in self.dbIndex.keys():
            fidx=self.dbIndex[idx].replace("|",".")
            if os.path.exists(fidx):
                result=self.BinaryIndexSearch(idx,record)
                # We have a duplicate
                if result is not None:
                    self.Error="Duplicate"
                    return

    # Check Index age and force a rebuild if needed

    def CheckIndexes(self,force=False):
        # No DB, nothing to check.
        if not os.path.exists(self.dbName):
            return

        # If already locked, do NOT unlock it
        NoUnlock=not (self.dbLock.IsLocked(expire=10,acquire=False)=='Locked')
        self.dbLock.Lock(expire=10)
        # Check the indexes
        self.Error=None
        dbMtime=os.path.getmtime(self.dbName)
        # We need to walk every index file
        for idx in self.dbIndex.keys():
            fidx=self.dbIndex[idx].replace("|",".")
            if os.path.exists(fidx) or force:
                iMtime=os.path.getmtime(fidx)
                if iMtime<dbMtime:
                    self.RebuildIndex(idx)
            else:
                self.RebuildIndex(idx)
        if not NoUnlock:
            self.dbLock.Unlock()

    # Rebuild a single index

    def RebuildIndex(self,idx):
        # No DB, nothing to check.
        if not os.path.exists(self.dbName):
            return

        # If already locked, do NOT unlock it
        NoUnlock=not (self.dbLock.IsLocked(expire=10,acquire=False)=='Locked')
        self.dbLock.Lock(expire=10)
        # Force rebuild
        self.Error=None
        self.dbTombstones=[]
        entries=[]
        ptr=0
        fh=open(self.dbName,"rb")
        while True:
            bline=fh.readline()
            # No more data
            if not bline:
                break
            # Tomestone record
            if not bline.startswith(b'{'):
                # Add to tombstone registry
                if not self.CheckTombstones(ptr):
                    # This is RAW line, \n included
                    self.dbTombstones.append([ptr,len(bline)])
                ptr+=len(bline)
                continue

            try:
                record=json.loads(bline)
            except Exception as err:
                ptr+=len(bline)
                print("REBUILD JSON:",err)
                print(bline)
                continue

            # Verify record integrity. Required to mintain a full "NO
            # TRUST" environment. There is a price to pay in latency and
            # overhead.

            if not self.VerifyBlake(record):
                self.Error=f"DB Corruption: {bline.strip()}"
                if not NoUnlock:
                    self.dbLock.Unlock()
                raise Exception(self.Error)

            kvtbl={}
            # Add new or overwrite old
            if "|" in idx:
                val="|".join(str(record[k]) for k in idx.split('|'))
                kvtbl={ "Key":val, "Offset":ptr }
            else:
                kvtbl={ "Key":record[idx], "Offset":ptr }
            entries.append(json.dumps(kvtbl))
            ptr+=len(bline)
        fh.close()

        entries=self.SortIndex(entries)
        fidx=self.dbIndex[idx].replace("|",".")
        FF.WriteList2File(fidx,entries,sync=self.syncIDX)
        if not NoUnlock:
            self.dbLock.Unlock()

    # Verify the integrity of the database

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
        fh.close()

        if not self.Error:
            return True
        return False

    # Pack the database, remove tombstones

    def PackDatabase(self):
        # No DB, nothing to check.
        if not os.path.exists(self.dbName):
            return False

        # If already locked, do NOT unlock it
        NoUnlock=not (self.dbLock.IsLocked(expire=10,acquire=False)=='Locked')
        self.dbLock.Lock(expire=10)
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
                print(f"Corruption: {bline.decode('utf-8')}")

            # WWrite out the new record
            FF.AppendFile(packName,json.dumps(record)+'\n',sync=self.syncDB)
        fh.close()

        try:
            os.replace(self.dbName,f"{self.dbName}.backup")
            os.replace(packName,self.dbName)
        except Exception as err:
            self.Error="Pack Failure"

        if not NoUnlock:
            self.dbLock.Unlock()
        if self.Error:
            return False
        return True

    # Linear (brute force) search

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

    # Binary search.  Really nice is index is already sorted.

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

    # Blind search for a string in all indexes

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
    db=JackrabbitDB("/tmp/FilesDB")

    # Add files as data set
    print("Add data")
    for file in os.listdir(dir):
        nr={}
        nr['ID']=CF.GetID(31,31)
        nr['File']=os.path.abspath(f"{dir}/{file}")
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

    """
    # Add additional indexes
    db.AddIndex("ID")
    db.AddIndex("File")
    db.AddIndex("File|ID")
    db.AddIndex("LastAccessed|File")

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
    print("Binary Search:",result)

    # Test Next and previous

    print("Next/Previous tests")
    nrec=db.Next("File")
    print(nrec)
    prec=db.Previous("File")
    print(prec)

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
    print(nrec)

    # Remove additional indexes
    db.RemoveIndex("ID")
    db.RemoveIndex("File")
    db.RemoveIndex("File|ID")
    db.RemoveIndex("LastAccessed|File")
    """

#    if not db.PackDatabase():
#        print("Pack corruption.")
    if not db.VerifyDatabase():
        print("Database corruption.")

if __name__=="__main__":
    TestDB()
