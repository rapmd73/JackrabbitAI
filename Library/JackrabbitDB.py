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
    def __init__(self,name,idx=[]):
        # Main database
        self.dbDir=name
        self.dbName=f"{self.dbDir}/Data.JDB"

        # Create index table
        self.dbIndex={}
        for i in idx:
            self.dbIndex[i]=f"{self.dbDir}/Index.{i}.JIDX"

        # Report errors, including duplicates
        self.Error=None

        FF.mkdir(self.dbDir)

    # Add a record to the database.  This also has to deal with all of
    # the indexes to prevent duplicates.

    def Add(self,record):
        # Check indexes
        self.CheckIndexes()
        if self.Error:
            raise(f"Index stability check failed: {err}")

        # Check for a duplicate
        self.CheckDuplicates(record)
        # We have an error
        if self.Error:
            return

        # This becomes the seek point to the NEXT record. Files are kept
        # CLOSED as much as possible to prevent file corruption. ONLY
        # open when ABSOLUTELY neccessary. Penalty is higher latency, but
        # mitigated by SSD.

        ptr=FF.GetFileSize(self.dbName)

        # Write the actual record.
        r=json.dumps(record)+'\n'
        FF.AppendFile(self.dbName,r,sync=True)

        # Update all indexes
        self.UpdateIndexes(ptr,record)

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
            FF.WriteList2File(fidx,entries,sync=True)
            return

        entries=FF.ReadFile2List(fidx)
        kvtbl={}
        # Add new or overwrite old
        if "|" in idx:
            val="|".join(str(record[k]) for k in idx.split('|'))
            kvtbl={ "Key":val, "Offset":ptr }
        else:
            kvtbl={ "Key":record[idx], "Offset":ptr }
        entries.append(json.dumps(kvtbl))
        entries=self.SortIndex(entries)
        FF.WriteList2File(fidx,entries,sync=True)

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

            record=json.loads(bline)
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
        FF.WriteList2File(fidx,entries,sync=True)

    # Linear (brute force) search

    def LinearIndexSearch(self,idx,record):
        # Index: { "Key":"/bin/bash", "Offset":"123" }
        # Read the actual index into a list
        # Linear search
        fidx=self.dbIndex[idx].replace("|",".")
        entries=FF.ReadFile2List(fidx)
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
        fidx = self.dbIndex[idx].replace("|", ".")
        entries = FF.ReadFile2List(fidx)
        if not entries:
            return

        # Build search key
        if "|" in idx:
            target = "|".join(str(record[k]) for k in idx.split("|"))
        else:
            target = str(record[idx])

        # Binary search on entries list (already sorted by Key)
        lo, hi = 0, len(entries) - 1
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

###
### End library
###
### Start test code
###

def TestDB():
    dir="/bin"
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
        db.Add(nr)
        if db.Error:
            print(f"{db.Error} {nr['File']}")

if __name__=="__main__":
    TestDB()
