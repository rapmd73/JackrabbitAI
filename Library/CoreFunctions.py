#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Jackrabbit AI
# 2021 Copyright © Robert APM Darin
# All rights reserved unconditionally.

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

# Turn &#08 into a character

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

# Turn \u codes to the proper ASCII

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

# Get Yesterday's date

@DF.function_trapper('')
def Yesterday(ds=None):
    if ds!=None:
        date=datetime.datetime.strptime(date_str,'%Y-%m-%d')
    else:
        date=datetime.datetime.now()
    yesterday=date-datetime.timedelta(days=1)
    return yesterday.strftime('%Y-%m-%d')

# Elastic Delay. This is designed to prevent the VPS from being overloaded

@DF.function_trapper([])
def GetLoadAVG():
    fh=open('/proc/loadavg')
    l=fh.readline()
    fh.close()

    LoadAVG=l.split(' ')

    return(LoadAVG)

# Convert load average to seconds

@DF.function_trapper
def renice(n):
    try:
        os.setpriority(os.PRIO_PROCESS,0,n)
    except:
        pass

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

# Returns milliseconds

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

# Test STDIN if data is being piped in.

@DF.function_trapper(False)
def IsSTDIN():
    ready,_,_=select.select([sys.stdin],[],[],1)
    return ready

