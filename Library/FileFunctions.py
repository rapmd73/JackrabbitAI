#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Jackrabit AI
# 2021-2025 Copyright © Robert APM Darin
# All rights reserved unconditionally.

# This Python script is a collection of utility functions designed to simplify
# common file operations. It begins by importing various standard Python
# libraries and custom modules, which provide essential tools for tasks like
# handling file paths, managing directories, reading and writing files, and
# processing data.

# The first set of functions focuses on directory and file management. The
# `mkdir` function ensures a directory exists at a specified path, creating it
# if necessary. This is useful for preparing storage locations before writing
# files. The `ReadFile` function reads the contents of a file, offering the
# flexibility to handle both text and binary files. It checks if the file
# exists and returns its content, or `None` if the file is not found. This
# function is particularly handy for loading data from files while gracefully
# handling potential errors.

# The `AppendFile` and `WriteFile` functions are straightforward tools for
# adding content to existing files or creating new ones. `AppendFile` adds text
# to the end of a file, ensuring that previous content remains intact, while
# `WriteFile` overwrites the file with new data. These functions are essential
# for logging, data storage, or any scenario requiring file updates.

# The `ReadFile2List` function takes file reading a step further by converting
# the file's content into a list of strings, with options to manipulate the
# text. It can remove empty lines, convert text to lowercase or uppercase, and
# handle non-existent files gracefully. This function is ideal for processing
# structured text data stored in files.

# Lastly, the `ReadTokens` function is specialized for reading and processing
# configuration files in JSON format, typically used for storing tokens or
# settings. It locates the token file based on provided parameters or defaults,
# reads its content, and parses it into a dictionary. The function also
# intelligently replaces token values with environment variables if specified,
# ensuring dynamic configuration. If the token file is missing or malformed,
# the function provides clear error messages and exits the program to prevent
# unexpected behavior.

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

# The `mkdir` function creates a new directory at the specified path `fn` if it
# does not already exist. It utilizes the `os.path.exists` function to check
# for the directory's existence and, if it's not found, uses `os.makedirs` with
# the `exist_ok=True` parameter to create the directory and all its parents if
# necessary, without raising an error if the directory is created concurrently.

@DF.function_trapper(None)
def mkdir(fn):
    if not os.path.exists(fn):
        os.makedirs(fn,exist_ok=True)

# The `ReadFile` function reads the contents of a file specified by the `fn`
# parameter and returns its contents as a string or bytes object. The function
# takes an optional `binary` parameter, which defaults to `False`, indicating
# whether to read the file in binary mode (`'rb'`) or text mode (`'r'`). If the
# file exists, it is opened, read, and then closed, with any leading or
# trailing whitespace stripped from the contents if not in binary mode. If the
# file does not exist, the function returns `None`. This provides a simple way
# to read files while handling potential file-not-found errors.

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

# The `AppendFile` function is a simple utility that appends a given text to
# the end of a specified file. It takes two parameters: `fname`, the name of
# the file to be appended, and `text`, the content to be added. The function
# opens the file in append mode (`'a+'`), writes the provided text to it, and
# then closes the file handle, ensuring that changes are saved and system
# resources are released. This function can be used to add content to existing
# files or create new ones if they do not already exist.

@DF.function_trapper(None)
def AppendFile(fname,text):
    fh=open(fname,'a+')
    fh.write(text)
    fh.close()

# The `WriteFile` function is a simple utility that writes data to a specified
# file. It takes two parameters: `fn`, the filename to be written to, and
# `data`, the content to be written. The function opens the file in write mode
# (`'w'`), writes the provided data to it using the `write` method, and then
# closes the file using the `close` method. This function does not include any
# error handling or checks for file existence, permissions, or data type,
# making it a basic implementation that assumes a straightforward writing
# operation.

@DF.function_trapper(None)
def WriteFile(fn,data):
    cf=open(fn,'w')
    cf.write(data)
    cf.close()

# The `ReadFile2List` function reads a file specified by the `fname` parameter
# and returns its contents as a list of strings. If the file does not exist,
# the function returns `None`. The function also provides optional parameters
# to modify the output: `ForceLower` and `ForceUpper` can be used to convert
# all strings to lowercase or uppercase, respectively, while `NoStripEmpty`
# controls whether empty lines are removed from the output. By default, empty
# lines are removed, and no case conversion is performed. The function uses
# another function called `ReadFile` to read the file contents, which are then
# split into lines and processed according to the specified options before
# being returned as a list.

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

# The `ReadTokens` function reads and processes token files in JSON format,
# returning a dictionary of tokens. It takes two optional parameters, `gid` and
# `userhome`, which determine the location of the token file. If `gid` is
# provided, the function looks for a token file named after it; otherwise, it
# uses the basename of the running program. The function checks if the token
# file exists and attempts to parse its contents as JSON. If successful, it
# replaces any token values starting with '!environment:' with the
# corresponding environment variable value, if set. If the token file is
# missing or not in JSON format, the function prints an error message and exits
# with a non-zero status code.

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
