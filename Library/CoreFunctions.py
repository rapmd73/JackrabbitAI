#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Jackrabbit AI
# 2021-2035 Copyright © Robert APM Darin
# All rights reserved unconditionally.

# This Python script is a collection of utility functions designed to handle
# various tasks, such as text processing, system monitoring, and input
# validation. It begins by importing several built-in Python modules, including
# those for system operations, file handling, date and time management, and
# regular expressions. Additionally, it imports a custom module named
# `DecoratorFunctions`, which likely contains decorators used to enhance or
# modify the behavior of the functions in this script.

# The script defines several global variables, including the name of the
# running script and a directory path for token storage. These variables are
# used throughout the script to maintain consistency and provide context for
# certain operations.

# One of the key functions, `DecodeHashCodes`, is designed to decode numeric
# character references in a string, such as `&#65;`, and replace them with
# their corresponding characters. It uses a regular expression to identify
# these patterns and a helper function to perform the conversion. Another
# function, `DecodeUnicode`, replaces various Unicode characters with their
# ASCII equivalents, making the text more compatible with systems that
# primarily use ASCII.

# The `Yesterday` function calculates the date of the previous day, either
# based on the current date or a provided date string. However, there appears
# to be a bug in this function, as it references an undefined variable instead
# of using the provided parameter correctly.

# Several functions are dedicated to system monitoring and resource management.
# `GetLoadAVG` retrieves the system's current load average by reading from a
# specific file, providing insight into the system's workload. The `renice`
# function adjusts the priority of the current process, allowing it to run at a
# higher or lower priority level, which can be useful for managing system
# resources. `ElasticSleep` introduces a delay in execution, optionally
# adjusting the sleep duration based on the system's load to prevent
# overloading. Similarly, `ElasticDelay` calculates a dynamic delay based on
# system load, ensuring that processes don't overwhelm the system.

# Text processing is another significant aspect of this script. The
# `NumberOnly` function validates whether a string represents a valid number,
# considering various numeric characters and look-alike symbols.
# `StripPunctuation` removes punctuation and high ASCII characters from text,
# replacing them with spaces to clean up the input. `jsonFilter` prepares a
# string for JSON processing by removing unwanted characters like newlines,
# tabs, and spaces. `GetWordList` processes a block of text into a list of
# lowercase words, removing any empty entries.

# Lastly, the `IsSTDIN` function checks if there is input available on the
# standard input within a one-second timeout. This is useful for determining
# whether a program should wait for user input or proceed with other tasks.

import sys
import os
import io
import copy
import itertools
import functools
import inspect
import traceback
import select
import datetime
import time
import random
import json
import string
import re

import DecoratorFunctions as DF

###
### Global variables to this file
###

RunningName=sys.argv[0]
TokenStorage='/home/JackrabbitAI/Tokens'

###
### Generic any purpose functions
###

# Get the starting nice value to measure and control OS load.

MasterNice=os.getpriority(os.PRIO_PROCESS,0)

# The `DecodeHashCodes` function is designed to decode numeric character
# references in a given input string. It utilizes a regular expression to
# identify patterns such as `&#65;` and replaces them with their corresponding
# characters. The function achieves this through a helper function,
# `replace_entity`, which extracts the numeric value from each match, converts
# it to a character using the `chr` function, and returns the character. If the
# conversion fails, it returns the original match. The main function then
# applies this replacement process to the entire input string using `re.sub`,
# ultimately returning the decoded string.

@DF.function_trapper('')
def DecodeHashCodes(input_string):
    def replace_entity(match):
        # Extract the numeric value from the match
        entity_code = match.group(1)
        try:
            # Convert the numeric value to a character
            return chr(int(entity_code))
        except ValueError:
            # Return the original match if conversion fails
            return match.group(0)

    # Regular expression to match numeric character references (e.g., &#65;)
    entity_pattern = r'&#(\d+);'
    return re.sub(entity_pattern, replace_entity, input_string)

# The `DecodeUnicode` function takes a string input `text` and replaces various
# Unicode characters with their corresponding ASCII equivalents. It uses a
# dictionary `replacements` to map Unicode characters, such as left and right
# single quotation marks, double quotation marks, en dashes, em dashes,
# ellipsis, and non-breaking spaces, to their ASCII counterparts. The function
# iterates through this dictionary, replacing each occurrence of the specified
# Unicode characters in the input text with the corresponding ASCII character,
# ultimately returning the modified string with all replacements made.

@DF.function_trapper('')
def DecodeUnicode(text):
    replacements = {
        '\u2018': "'",   # Left single quotation mark
        '\u2019': "'",   # Right single quotation mark
        '\u201C': '"',   # Left double quotation mark
        '\u201D': '"',   # Right double quotation mark
        '\u2013': '-',   # En dash
        '\u2014': '-',   # Em dash
        '\u2026': '...', # Ellipsis
        '\u00A0': ' ',   # Non-breaking space
        '\u201A': ',',   # Single low-9 quotation mark
        '\u201E': '"',   # Double low-9 quotation mark
        '\u02C6': '^',   # Modifier letter circumflex accent
        '\u2039': '<',   # Single left-pointing angle quotation mark
        '\u203A': '>',   # Single right-pointing angle quotation mark
        '\u02DC': '~',   # Small tilde
        '\u00AB': '"',   # Left-pointing double angle quotation mark
        '\u00BB': '"',   # Right-pointing double angle quotation mark
    }
    for unicode_char, ascii_char in replacements.items():
        text = text.replace(unicode_char, ascii_char)
    return text

# The `Yesterday` function calculates and returns the date of yesterday in the
# format 'YYYY-MM-DD'. It takes an optional parameter `ds` which, if provided,
# is expected to be a date string in the format 'YYYY-MM-DD' that is then used
# as the reference date. If `ds` is not provided (i.e., it is `None`), the
# function uses the current date as the reference. The function then subtracts
# one day from the reference date to determine yesterday's date and returns it
# as a string. However, there seems to be a bug in the function as it
# references an undefined variable `date_str` instead of using the provided
# `ds` parameter for parsing the date string.

@DF.function_trapper('')
def Yesterday(ds=None):
    if ds!=None:
        date=datetime.datetime.strptime(date_str,'%Y-%m-%d')
    else:
        date=datetime.datetime.now()
    yesterday=date-datetime.timedelta(days=1)
    return yesterday.strftime('%Y-%m-%d')

# The `GetLoadAVG` function retrieves the system's current load average from
# the `/proc/loadavg` file. It opens the file, reads the first line, and then
# closes it. The line is then split into a list of values using spaces as
# delimiters, which are stored in the `LoadAVG` variable. Finally, the function
# returns this list of load average values, providing a snapshot of the
# system's current workload.

@DF.function_trapper([])
def GetLoadAVG():
    fh=open('/proc/loadavg')
    l=fh.readline()
    fh.close()

    LoadAVG=l.split(' ')

    return(LoadAVG)

# The `renice` function is a wrapper around the `os.setpriority` system call,
# which is used to set the niceness of the current process. The function takes
# a single argument `n`, representing the new niceness value, and attempts to
# set it using `os.setpriority` with the `PRIO_PROCESS` option, targeting the
# current process (identified by the pid `0`). If an error occurs during this
# operation, the function silently ignores it and continues execution without
# raising an exception, due to the bare `except: pass` block. The function is
# also decorated with `@DF.function_trapper`, suggesting that it may be part of
# a larger framework or library that provides additional functionality or error
# handling.

@DF.function_trapper
def renice(n):
    try:
        os.setpriority(os.PRIO_PROCESS,0,n)
    except:
        pass

# The `ElasticSleep` function is designed to introduce a delay in the execution
# of a program, with an optional "fuzzy" mode that adjusts the sleep duration
# based on the system's current load. When `Fuzzy` is `True`, the function
# calculates the system's load average and CPU count, and uses this information
# to determine a dynamic sleep duration. If the load is high, it reduces the
# process's priority and throttles the delay to prevent overloading the system.
# The sleep duration is then calculated based on the load average, with an
# additional throttle factor applied if the load exceeds the number of CPUs. If
# `Fuzzy` is `False`, the function simply sleeps for a fixed duration specified
# by the `s` parameter, without considering system load.

@DF.function_trapper
def ElasticSleep(s,Fuzzy=True):
    # Do we want a fuzzy sleep or an exact sleep?
    if Fuzzy:
        throttle=0
        LoadAVG=GetLoadAVG()
        c=os.cpu_count()
        d=float(max(LoadAVG[0],LoadAVG[1],LoadAVG[2]))/c
        n=os.getpriority(os.PRIO_PROCESS,0)

        # if load is greater then the number of cpus, the renice to the lowest priority
        if d>=c:
            renice(n+1)
        else:
            if n>MasterNice:
                renice(n-1)

        # Give up slice to kernal
        os.sched_yield()

        # Convert lo into seconds

        i=int(d)
        f=d-i

        delay=i+(f/100)

        # if load is greater then cpu count, begin throttling the delay factor.

        if (d>c):
            throttle=(d-c)*delay

        time.sleep(s+delay+throttle)
    else:
        time.sleep(s)

# The `ElasticDelay` function calculates a dynamic delay based on the system's
# current load average and CPU count. It retrieves the load average using
# `GetLoadAVG()` and determines the maximum value, which is then converted into
# a delay in milliseconds. If the load average exceeds the number of available
# CPUs, a throttle factor is applied to increase the delay, effectively slowing
# down the system to prevent overload. The function returns the total delay,
# which is the sum of the calculated delay and the throttle factor, allowing
# for adaptive adjustment of timing based on system resource utilization.

@DF.function_trapper(0)
def ElasticDelay():
    throttle=0
    LoadAVG=GetLoadAVG()
    d=int(float(max(LoadAVG[0],LoadAVG[1],LoadAVG[2])))

    c=os.cpu_count()

    # Convert lo into seconds

    i=int(d)
    f=d-i

    delay=int((i+(f/100))*1000)

    # if load is greater then cpu count, begin throttling the delay factor.

    if (d>c):
        throttle=int((d-c)*delay)

    return delay+throttle

# The `NumberOnly` function checks if a given string can be considered a
# valid representation of a number, accounting for numeric characters,
# commas, periods, and various look-alike characters. It replaces common
# look-alike letters (like 'O' for '0' and 'I' for '1') with their numeric
# equivalents, trims whitespace, and validates the presence of digits while
# filtering out invalid characters. The function returns `True` if the
# string is a valid number, and `False` otherwise.

@DF.function_trapper(None)
def NumberOnly(s):
    # Replace common look-alikes with their numeric equivalents
    look_alike_replacements={
        'I': '1',  # Uppercase 'i' as '1'
        'l': '1',  # Lowercase 'L' as '1'
        'O': '0',  # Uppercase 'O' as '0'
    }

    # Replace look-alikes in the input string
    for look_alike, digit in look_alike_replacements.items():
        s=s.replace(look_alike, digit)

    s=s.strip().replace(' ','')

    # Define valid characters, including look-alikes and numeric equivalents
    valid_chars=set("0123456789.,")  # Regular digits, comma, and period
    look_alike_chars=set("٠١٢٣٤٥٦٧٨٩")  # Arabic-Indic digits
    full_width_digits=set("０１２３４５６７８９")  # Full-width digits

    # Combine all valid characters into one set
    valid_chars.update(look_alike_chars)
    valid_chars.update(full_width_digits)

    # Check each character in the string
    for char in s:
        if char not in valid_chars:
            return False

    # Basic number validation: ensure the string isn't just commas or periods
    if s.replace(",", "").replace(".", "").isdigit():
        return True

    return False

# The `StripPunctuation` function removes all punctuation and high ASCII
# characters from a given text by replacing them with spaces. It achieves
# this by using a translation table that maps these characters to spaces,
# ensuring the returned text is cleaned and ready for further processing,
# free from unwanted symbols.

@DF.function_trapper(None)
def StripPunctuation(text):
    # Define punctuation and high ASCII characters
    punctuation=string.punctuation
    high_ascii_chars=''.join(chr(i) for i in range(128, 256))

    # Create a translation table to map all punctuation and high ASCII characters to spaces
    translation_table=str.maketrans({**dict.fromkeys(punctuation, ' '), **dict.fromkeys(high_ascii_chars, ' ')})

    # Replace punctuation and high ASCII characters with spaces in the text
    cleaned_text=text.translate(translation_table)

    return cleaned_text

# The `jsonFilter` function cleans up a string by removing unwanted
# characters and formatting artifacts. It eliminates specific characters
# like newlines, tabs, and carriage returns, and optionally removes spaces
# based on a provided flag. This ensures the resulting string is stripped
# down and ready for reliable use in JSON processing or other structured
# tasks.

@DF.function_trapper(None)
def jsonFilter(s,FilterSpace=True):
    d=s.replace("\\n","").replace("\\t","").replace("\\r","")

    if FilterSpace==True:
        filterText='\t\r\n \u00A0'
    else:
        filterText='\t\r\n\u00A0'

    for c in filterText:
        d=d.replace(c,'')

    return(d)

# The `GetWordList` function takes a block of text and processes it into a
# list of individual words in lowercase. It splits the text using spaces,
# ensuring any unnecessary empty entries, such as extra spaces, are
# removed. This streamlined approach prepares the words for consistent and
# clean usage in further operations.

@DF.function_trapper(None)
def GetWordList(text):
    words=text.lower().split()
    return [word for word in words if word.strip()]

# This function, `IsSTDIN`, checks if there is input available on the standard
# input (STDIN) within a 1-second timeout. It uses the `select.select` method
# to monitor the STDIN file descriptor for readability, and returns a list of
# ready file descriptors. The function then returns this list, which will be
# non-empty (`True` in a boolean context) if input is available, and empty
# (`False` in a boolean context) otherwise. The `@DF.function_trapper(False)`
# decorator suggests that this function is part of a larger framework or
# library that provides error handling or other functionality.

@DF.function_trapper(False)
def IsSTDIN():
    ready,_,_=select.select([sys.stdin],[],[],1)
    return ready

