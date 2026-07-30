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

def ReplayTransactions(tlog=None,dbdir=None,idx=None, olddb=None):
    # There are two ways to handle this...

    # First is to build an EXACT copy of the original. I reject this as there are
    # to many ways for forgery and corruption.

    # The second way is to build an NEW database, acknowledging that it is a
    # RECONSTRUCTION. I think this is the better approach as its HONEST about the
    # data origin and expections. It also show clear and present transparency
    # about the process.

    if tlog is None or dbdir is None or idx is None:
        print("The transction log, new database and primary index are required.")
        sys.exit(0)

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
    print(f"Verification: {db.VerifyDatabase()}")
    print()

    # This section simulates a JDB from a previous backup and finding
    # the missing records.

    if olddb is None:
        return

    dbo=JRDB.JackrabbitDB(olddb,idx=[idx],syncDB=False)

    db.SetCursor(idx,0)
    dbo.SetCursor(idx,0)

    # New to old check
    while True:
        nrec=db.Next(idx)
        if not nrec:
            break

        offset=dbo.BinaryIndexSearch(idx,record=nrec)
        orec=dbo.Read(offset)

        if orec[idx]!=nrec[idx]:
            print("O:",orec)
            print("N:",nrec)

    # Old to new check
    while True:
        orec=dbo.Next(idx)
        if not orec:
            break

        offset=db.BinaryIndexSearch(idx,record=orec)
        nrec=db.Read(offset)

        if orec[idx]!=nrec[idx]:
            print("O:",orec)
            print("N:",nrec)

if __name__ == "__main__":
    args=[None] * 5
    for i in range(len(sys.argv)):
        args[i]=sys.argv[i]

    ReplayTransactions(args[1],args[2],args[3],args[4])
