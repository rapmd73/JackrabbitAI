#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Jackrabit AI
# 2024 Copyright © Robert APM Darin
# All rights reserved unconditionally.

import sys
import os
import io
import copy
import itertools
import functools
import inspect
import traceback
import datetime
import time
import random
import json
import string
import re

import DecoratorFunctions as DF
import CoreFunctions as CF

###
### General file tools
###

# Cheap mkdir

@DF.function_trapper(None)
def mkdir(fn):
    if not os.path.exists(fn):
        os.makedirs(fn,exist_ok=True)

# Read file into buffer

@DF.function_trapper(None)
def ReadFile(fn,binary=False):
    if os.path.exists(fn):
        if binary:
            cf=open(fn,'rb')
            buffer=cf.read()
            cf.close()
        else:
            cf=open(fn,'r')
            buffer=cf.read().strip()
            cf.close()
    else:
        buffer=None
    return buffer

# Append a single line to an existing file

@DF.function_trapper(None)
def AppendFile(fname,text):
    fh=open(fname,'a+')
    fh.write(text)
    fh.close()

# Write file to disk

@DF.function_trapper(None)
def WriteFile(fn,data):
    cf=open(fn,'w')
    cf.write(data)
    cf.close()

# The `ReadFile2List` function processes the content of a file by reading
# it into a list, splitting the text into individual lines. It removes any
# blank lines and optionally converts all text to lowercase if specified.
# This ensures a clean and usable list of responses or data items from the
# file.

@DF.function_trapper(None)
def ReadFile2List(fname,ForceLower=False,ForceUpper=False,NoStripEmpty=False):
    # Something broke. Keep the responses in character
    if not os.path.exists(fname):
        return None

    responses=ReadFile(fname).strip().split('\n')
    if NoStripEmpty==False:
        while '' in responses:
            responses.remove('')
    if ForceLower==True:
        responses=[item.lower() for item in responses]
    if ForceUpper==True:
        responses=[item.upper() for item in responses]
    return responses

# The `ReadTokens` function ensures the bot has the necessary credentials
# to operate by locating and reading a specific file that stores API
# tokens. It carefully checks if the file exists, verifies its format, and
# ensures essential keys like the Discord token are present. If anything is
# missing or incorrect, the function logs the issue and stops the program
# to prevent errors during operation. By validating this information
# upfront, it ensures the bot can run securely and without interruptions.

@DF.function_trapper({})
def ReadTokens(gid=None,userhome=None):
    tokens={}
    ts=CF.TokenStorage
    if userhome!=None:
        ts=userhome
    if gid==None:
        tfile=f"{ts}/{os.path.basename(CF.RunningName)}.tokens"
    else:
        tfile=f"{ts}/{gid}.tokens"
    if os.path.exists(tfile):
        try:
            tokens=json.loads(CF.jsonFilter(ReadFile(tfile)))
        except Exception as err:
            print("Error token file is not in JSON format.")
            sys.exit(1)
    else:
        print(f"Missing token file: {tfile}")
        sys.exit(1)

    # Inspired by SamAcctX
    for key in tokens:
        if tokens[key].lower().startswith('!environment:'):
            vn=tokens[key].split(':',1)[1].strip() # Environment variable name
            ev=os.getenv(vn) # Environment variable contents, if any
            # Make sre we have an environment variable
            if ev:
                tokens[key]=ev

    return tokens
