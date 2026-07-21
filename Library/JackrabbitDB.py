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
        fidx=self.dbIndex[idx]
        if not os.path.exists(fidx):
            # Add new or overwrite old
            kvtbl={ "Key":record[idx], "Offset":ptr }
            entries=[ json.dumps(kvtbl) ]
            FF.WriteList2File(fidx,entries,sync=True)
            return

        # Read the actual index into a list
        entries=FF.ReadFile2List(fidx)
        kvtbl={}
        for line in entries:
            try:
                kvtbl=json.loads(line)
            except Exception as err:
                print(err)
                continue
            # Duplicate
            if record[idx]==kvtbl['Key']:
                self.Error="Duplicate"
                return

        # Add new or overwrite old
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
            self.IndexCheckDuplicate(idx,record)
            # something went wrong
            if self.Error:
                return

    def IndexCheckDuplicate(self,idx,record):
        fidx=self.dbIndex[idx]
        if os.path.exists(fidx):
            # Read the actual index into a list
            entries=FF.ReadFile2List(fidx)
            # Key is the index key from the record, ie "File"
            # Offset is the seek offetset into the main database.
            # Index: { "Key":"/bin/bash", "Offset":"123" }
            for line in entries:
                kvtbl=json.loads(line)

###
### End library
###
### Start test code
###

def TestDB():
    dir="/bin"
    db=JackrabbitDB("/tmp/FilesDB",idx=["File"])
    for file in os.listdir(dir):
        nr={}
        nr['ID']=CF.GetID(31,31)
        nr['File']=os.path.abspath(f"{dir}/{file}")
        nr['RealFile']=os.path.realpath(f"{dir}/{file}")
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
