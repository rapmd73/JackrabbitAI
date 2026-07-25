#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Jackrabit DB
# 2024-2026 Copyright © Robert APM Darin
# All rights reserved unconditionally.

# This is an ISAM random access hybrid database using only JSONL structures.

import sys
sys.path.append('/home/JackrabbitAI/Library')
import os
import hashlib
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
        self.dbTombstone=f"{self.dbDir}/Tombstone.log"

        # Create index table
        self.dbIndex={}
        for i in idx:
            self.dbIndex[i]=f"{self.dbDir}/Index.{i}.JIDX"

        # Report errors, including duplicates
        self.Error=None

        FF.mkdir(self.dbDir)

    # Create a Blake 2B hash. Argument is JSON

    def Blake2B(self,text):
        if isinstance(text,dict):
            rec=json.dumps(text)
        else:
            rec=text
        h=hashlib.blake2b(digest_size=64)
        h.update(rec.encode('utf-8'))
        return h.hexdigest()

    # Verify the record hash as stable. Argument COULD be JSON or STR

    def VerifyBlake2B(self,record):
        if isinstance(record,str):
            rec=json.loads(record)
        else:
            rec=record.copy()

        # Get old hash
        oldBlake2B=rec.get('jrdbBlake2B',None)

        # No hash, no match
        if oldBlake2B is None:
            return False

        # Get rid of the hash and generate the test hash.
        rec.pop('jrdbBlake2B',None)
        newBlake2B=self.Blake2B(rec)
        if newBlake2B==oldBlake2B:
            return True
        return False

    # Add a record to the database.  This also has to deal with all of
    # the indexes to prevent duplicates.

    def Add(self,record):
        self.CheckIndexes()
        if self.Error:
            raise Exception(f"Index stability check failed: {self.Error}")
        self.CheckDuplicates(record)
        if self.Error:
            return None, None

        record['jrdbBlake2B']=self.Blake2B(json.dumps(record))
        ptr=FF.GetFileSize(self.dbName)
        r=json.dumps(record)+'\n'
        FF.AppendFile(self.dbName,r,sync=self.syncDB)
        self.UpdateIndexes(ptr,record)
        return ptr,record

    # Update: append new record.  turn old record into tombstone.
    def Update(self,offset,record):
        # The old hash MUST be removed before calculating the new hash
        record.pop('jrdbBlake2B',None)
        record['jrdbBlake2B']=self.Blake2B(json.dumps(record))
        # Add update to bottom
        ptr=FF.GetFileSize(self.dbName)
        r=json.dumps(record)+'\n'
        FF.AppendFile(self.dbName,r,sync=self.syncDB)
        # Turn old record to tombstone
        self.WriteTombstone(offset)
        # Rebuild indexes
        self.CheckIndexes()
        return ptr,record

    # Write a tombstone
    def WriteTombstone(self,offset):
        # Open for read/wwwrite
        fh=open(self.dbName,"rb+")
        # Get the length
        fh.seek(offset,os.SEEK_SET)
        buf=fh.readline()
        FF.AppendFile(self.dbTombstone,buf.decode('utf-8').strip()+"\n")
        # Write the tombstone, take off \n. We need to fill exact space
        fh.seek(offset,os.SEEK_SET)
        dashes="-"*(len(buf)-1)
        line=fh.write(dashes.encode('utf-8'))
        # Sync the file
        if self.syncDB:
            fh.flush()
            os.fsync(fh.fileno())
        fh.close()

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
        if not self.VerifyBlake2B(line):
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

    def CheckIndexes(self):
        # No DB, nothing to check.
        if not os.path.exists(self.dbName):
            return

        # Check the indexes
        self.Error=None
        dbMtime=os.path.getmtime(self.dbName)
        # We need to walk every index file
        for idx in self.dbIndex.keys():
            fidx=self.dbIndex[idx].replace("|",".")
            if os.path.exists(fidx):
                iMtime=os.path.getmtime(fidx)
                if iMtime<dbMtime:
                    self.RebuildIndex(idx)
            else:
                self.RebuildIndex(idx)

    def RebuildIndex(self,idx):
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
            if bline.startswith(b'---'):
                ptr+=len(bline)
                continue

            try:
                record=json.loads(bline)
            except Exception as err:
                ptr+=len(bline)
                print(err)
                continue

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

    db=JackrabbitDB("/tmp/FilesDB",idx=["ID","File","LastAccessed|File"])
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
        nr['Added']=time.time()
        stime=time.time()
        db.Add(nr)
        etime=time.time()
        if db.Error and db.Error!="Duplicate":
            print(f"{db.Error} {nr['File']}")
#        else:
#            print(f"Elapsed: {etime-stime:.8f} seconds")
    results=db.SearchContains("bash")
    lu=[]
    for res in results:
        if res['Offset'] not in lu:
            lu.append(res['Offset'])
            record=db.Read(res['Offset'])
            print(record)
            print()
            if not db.Error:
                record['EditCount']=record.get('EditCount',0)+1
                record['Edited']=time.time()
                ptr,newrec=db.Update(res['Offset'],record)
                print(ptr,newrec)

if __name__=="__main__":
    TestDB()
