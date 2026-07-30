#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ReplayTransactionLog.py Replay a Transaction.log into a new JackrabbitDB
# database

import sys
sys.path.append('/home/JackrabbitAI/Library')
import os
import time
import json

import FileFunctions as FF
import JackrabbitDB as JRDB

def ReplayTransactions(tlog=None,dbdir=None,idx=None):
    # There are two ways to handle this...

    # First is to build an EXACT copy of the original. I reject this as there are
    # to many ways for forgery and corruption.

    # The second way is to build an NEW database, acknowledging that it is a
    # RECONSTRUCTION. I think this is the better approach as its HONEST about the
    # data origin and expections. It also show clear and present transparency
    # about the process.

    db=JRDB.JackrabbitDB(dbdir,idx=[idx],syncDB=False)

    # Open transaction log
    fh=open(tlog,"r")

    while True:
        bline=fh.readline()
        if not bline:
            break

        cmd,line=bline.split("|",1)

        if not db.VerifyBlake(line):
            print(f"Transaction currupted: {line}")
            continue

        record=json.loads(line)

        record.pop("jrdbBlake",None)
        record["jrdbReconstruction"]=time.time()

        if cmd=='ADD':
            db.Add(record)

        if cmd=='UPDATE':
            id=record['ID']
            ptr=db.BinaryIndexSearch(idx,record=record)
            if ptr>=0:
                db.Update(ptr,record)
            else:
                print(f"Transaction ID NOT found: {id}")

        if cmd=='DELETE':
            id=record['ID']
            ptr=db.BinaryIndexSearch(idx,record=record)
            if ptr>=0:
                db.Delete(ptr)
            else:
                print(f"Transaction ID NOT found: {id}")
    fh.close()
    db.PackDatabase()
    print(db.VerifyDatabase())

if __name__ == "__main__":
    ReplayTransactions(sys.argv[1],sys.argv[2],sys.argv[3])
