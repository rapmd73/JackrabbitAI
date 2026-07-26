#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Jackrabbit DB
# 2024-2026 Copyright © Robert APM Darin
# All rights reserved unconditionally.

# This is an ISAM random access hybrid database using only JSONL structures.

import sys
sys.path.append('/home/JackrabbitAI/Library')
import os
import blake3
import datetime
import time
import random
import json

import DecoratorFunctions as DF
import CoreFunctions as CF
import FileFunctions as FF

# primary=(time.time()*10000000).GetID()

class JackrabbitDB:
    def __init__(self,name,idx=[],syncDB=True,syncIDX=False):
        # Main database
        self.syncDB=syncDB
        self.syncIDX=syncIDX
        self.dbDir=name
        self.dbName=f"{self.dbDir}/Data.JDB"
        self.dbTransaction=f"{self.dbDir}/Transaction.log"
        self.dbTombstones=[]

        # Create index table
        self.dbIndex={}
        for i in idx:
            self.dbIndex[i]=f"{self.dbDir}/Index.{i}.JIDX"

        # Report errors, including duplicates
        self.Error=None

        FF.mkdir(self.dbDir)
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
            rec=json.loads(record)

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

    # Add a record to the database.  This also has to deal with all of
    # the indexes to prevent duplicates.

    def Add(self,record):
        self.CheckIndexes()
        if self.Error:
            raise Exception(f"Index stability check failed: {self.Error}")
        self.CheckDuplicates(record)
        if self.Error:
            return None, None

        record['jrdbAdded']=time.time()
        record['jrdbBlake']=self.Blake(record)
        ptr=FF.GetFileSize(self.dbName)
        r=json.dumps(record)+'\n'
        self.WriteTransaction("ADD",record)
        FF.AppendFile(self.dbName,r,sync=self.syncDB)
        self.UpdateIndexes(ptr,record)
        return ptr,record

    # Update: append new record.  turn old record into tombstones.
    def Update(self,offset,record):
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
        ptr=FF.GetFileSize(self.dbName)
        r=json.dumps(record)+'\n'
        self.WriteTransaction("UPDATE",record)
        FF.AppendFile(self.dbName,r,sync=self.syncDB)
        # Turn old record to tombstone
        self.Delete(offset=offset)
        # Rebuild indexes
        self.CheckIndexes()
        return ptr,record

    # Find offset in tombstone list

    def CheckTombstones(self,offset):
        for ts in self.dbTombstones:
            if offset==ts[0]:
                return True
        return False

    # Compact and merge tombstone list

    def TombstoneCompaction(self):
        # if nothing to merge, just return
        if len(self.dbTombstones) < 2:
            return

        # Make sure the order of offsets is sorted
        self.dbTombstones.sort(key=lambda x: x[0])

        # Merge adjacent tombstones
        merged=[]
        cur_off, cur_len=self.dbTombstones[0]
        for off, ln in self.dbTombstones[1:]:
            if off==cur_off+cur_len:
                # if 2 tombstones are adjacent to each other, merge them
                cur_len+=ln
            else:
                # Not adjacent, save and move to the next region
                merged.append([cur_off, cur_len])
                cur_off, cur_len=off,ln
        merged.append([cur_off, cur_len])
        self.dbTombstones=merged

    # Delete a record
    def Delete(self,offset=None):
        # One of these MUST be present
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

        self.TombstoneCompaction()
        return True

    # Read a record at a position
    def Read(self,offset):
        fh=open(self.dbName,"rb")
        fh.seek(offset,os.SEEK_SET)
        line=fh.readline()
        fh.close()
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
        self.Error=None
        # We need to walk every index file
        for idx in self.dbIndex.keys():
            self.UpdateSingleIndex(idx,ptr,record)

    def UpdateSingleIndex(self,idx,ptr,record):
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

    # Rebuild a single index

    def RebuildIndex(self,idx):
        self.Tombstones=[]
        # No DB, nothing to check.
        if not os.path.exists(self.dbName):
            return

        # Force rebuild
        self.Error=None
        entries=[]
        ptr=0
        fh=open(self.dbName,"rb")
        while True:
            bline=fh.readline()
            if not bline:
                break
            # Tomestone record
            if bline.startswith(b'---'):
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
                print(err)
                continue

            # Verify record integrity. Required to mintain a full "NO
            # TRUST" environment. There is a price to pay in latency and
            # overhead.

            if not self.VerifyBlake(record):
                self.Error=f"DB Corruption: {bline.strip()}"
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
            return

        # Build search key
        if "|" in idx:
            target="|".join(str(record[k]) for k in idx.split("|"))
        else:
            target=str(record[idx])

        # Binary search on entries list (already sorted by Key)
        lo, hi=0, len(entries) - 1
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
    db=JackrabbitDB("/tmp/FilesDB",idx=["ID","File","File|ID","LastAccessed|File"])
    # Add files as data set
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

    # Find all records with "bash" and edit them
    results=db.SearchContains("bash")
    lu=[] # Searching multiple indexes can give duplicate offsets.
    for res in results:
        if res['Offset'] not in lu:
            lu.append(res['Offset'])
            record=db.Read(res['Offset'])
            print(record)
            print()
            if not db.Error:
                record['EditCount']=record.get('EditCount',0)+1
                ptr,newrec=db.Update(res['Offset'],record)
                print(ptr,newrec)

    # Find and delete all records with python in them
    results=db.SearchContains("python")
    lu=[]
    for res in results:
        if res['Offset'] not in lu:
            lu.append(res['Offset'])
            if not db.Error:
                done=db.Delete(res['Offset'])
                print(done,res['Key'])

    # Print the tombstone list
    print(db.dbTombstones)

if __name__=="__main__":
    TestDB()
