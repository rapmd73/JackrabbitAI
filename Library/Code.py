#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Companion AI chatbot/moderation
# 2024 Copyright © Robert APM Darin
# All rights reserved unconditionally.

# This program uses both CamelCase (PascalCase) and snake_case. After 40+
# years of writting code in more languages then I remember, it really
# doesn't matter after a while. Even beginner programmers should get used
# to seeing multiple formats intermixed.

# Yes, I know Python is meant to be object oriented... When I started write the
# program, I never really expected it to grow beyound a fasination, let alone to where
# it is now. I litterally started with 2 functions (as seen in the Extra directory).
# As each itdea came, problems requiring solutions started to take the shape of
# functions. The program just grew and grew. At some point, I'll rewrite this... but
# for now, it works well and is quite fast.

# In progres: locking and lock management is a nightmare. Work is being done for a
# distrivuted locking manager that will provide muck better control over system
# resources and rate limits.

# Language transltions with AI is absolutely strange. Japanese seems to be an
# oddity compared to other asian languages. Will need a person of Jpanese to figure
# this one out.. So far OpenAI seems to be the only service that accurately
# translates Japanese to English consistently and reliably.

# ***** IMPORTANT:
#   This program MAY still require ADMINISTRATOR priviledges. Work is
#   being done to curb that.
#
# The following permissions are NOW required:
#    create_instant_invite, kick_members, ban_members,
#    manage_channels, manage_guild, add_reactions, view_audit_log,
#    view_channel, manage_roles, manage_permissions, manage_webhooks,
#    manage_emojis_and_stickers, send_messages, send_tts_messages,
#    manage_messages, embed_links, attach_files, read_message_history,
#    mention_everyone, manage_threads, use_embedded_activities,
#    send_messages_in_threads, use_application_commands, manage_events

# According to Discord documentation,
#   https://discord.com/community/permissions-on-discord-discord
#
# Without the Administrator permission:
#
#   The role cannot bypass channel-specific permissions unless explicitly granted
#   in each channel.
#
#   Cannot access permissions higher than its own role in the hierarchy. (This
#   appears to no longer work).

# Forum and thread support is a strange approach. Threads are treated like
# channels, with a few extra bits. Webhooks, slowdown mode, edits, even the way
# message are sent into the thread is effected. Activities have to be tested and
# is it is a thread, most of the time, you have to pull the parent channel.
# Webhooks and slowdown mode, in particular, do NOT have separate
# functionalities of a channel, even though discord treats them like a channel.

### *** At some point, I'm going to really have to rewrite this. The forum/thread
###     detection code is a stinking hot mess and scattered everywhere.

# Emotion scoring (classifier)
#
#   Emotional scoring (major scale): 10 (love) to -10 (hatred) sets the
#   overall tone of the AI towards the user. This can be translated the
#   scale of a warm and inviting conversation to a cold and distant one.
#   The system role could easily be adapted to act on this information.

#   (Minor scale) Assuming 0 is neurtal and the starting point of all
#   interactions, a monor scale could be used to evaluate each input from 1
#   (warm) to -1 (cold) to give that input a score. The scale needs to
#   adjust though to ensure the major scale doesn't climb too quickly in
#   either direction. For example, if the emotional score (major scale) is
#   1, then the minor scale range needs to be 0.9 to -1.

#   The minor scale is added or subtracted to/from the mahor scale to get the
#   final emotion score of the bot at the last interaction. This will carry
#   between channel towards the same user.  The bot will greet the same user
#   accross all channel with the same emotion resonance.

# Listed in order of when the service was added.

# added openai
# added ollama
# added together.ai     Free models available.
# added cohere          Trial key 1000 free requests per month
# added huggingface     free key is 1000 requests per day, fragmented responses, 1
#                       respons coud=8 requests or more
# added anthropic       token counting is a hot mess, but functional,
#                       no free credits, pay upfront
# added perplexity.ai   No free credits, pay upfront, search oriented, not
#                       good for conversational, but searching is outstanding.

# added openrouter.ai   Several free models limited to 200 requests per day,
#                       has just about every major provider, even some of the
#                       more difficult ones to build for. Paid models will have
#                       a premium for the normalization service. No direct model
#                       support like you would get directly from model vender
#                       (OpenAI, Anthropic, so on). Uses all OpenAI code. Token
#                       counting is a nighmare but the basic len/4 works
#                       reasonly well. toktoken() does NOT work.

# --> Not in a specific order, add support for the following engines (Maybe):

#   DeepInfra           https://deepinfra.com/pricing
#   fireworks.ai
#   Anyscale
#   Replicate
#   google.ai (genini)  This is a hot mess to try to develop for. There
#                       are a serious cascading issues from message
#                       format to usage consideration... The API is
#                       free, but the developement process is hideous.
#   Vertex AI           Now GoogleAI
#   AI21labs            Seriously broken in multiple ways. API does not work.
#                       Disappointing becuse this really looked put
#                       together with as much expertise as Open AI, even
#                       directly addressing token counting upfront.

# Special USER commands: (Completed)

#   %http           Read URLs, YouTube transcripts, and PDFs
#   %yttags         Get YouTube video tage, if there are any.
#   %Forget         Tell the AI to forget the conversation in the current channel
#   %AnagramSolver  Solve Anagrams

# Developer/Admin only: (Completed)

#   %PurgeRequests  Empty the server request queue
#   %CheckBot       Check if the AI is allowed in a channel

# Needed functionality

#   Purge memory that are older then X days automatically - completed
#   Imposter detection - completed
#   Auto slow mode - completed
#   Anti-raid - completed
#   Find a way to identify personal information: email, phone numbers, SSN, EIN,
#       Credit Card numbers - completed
#       Refine with an AI classifier - completed
#   URL check (abuseIPDB) verifications. - completed
#   Content Identification/Moderatation System (CIMS) - completed
#       Build a classifier to handle the following: (Mark with reactions):
#       "TOXICITY", "SEVERE_TOXICITY", "IDENTITY_ATTACK", "INSULT", "PROFANITY",
#       "THREAT", "SEXUALLY_EXPLICIT", "FLIRTATION", "PERSONAL ATTACK",
#       "INFLAMMATORY", "OBSCENE", "BULLYING"

# In consideration/progress
#   Need to somehow figure out suicide and self harm for CIMS....
#   Delete messages from other bots
#   Only allow X messages, auto delete any above X count
#   Anti nudity/gore/violence verification for images.
#   NO link edit
#   Anti nuke
#   Ticket management

# Disable 3rd party logging.
import warnings
warnings.filterwarnings('ignore')
import logging
logging.basicConfig(level=logging.CRITICAL)
logger=logging.getLogger('transformers')
logger.setLevel(logging.CRITICAL)
logger.handlers=[]

import sys
import os
import io
import copy
import itertools
import functools
import inspect
import traceback
from collections import deque
import datetime
import time
import random
import json
import string
import concurrent.futures
import threading
import urllib.request
from urllib.parse import urlparse
import requests
import socket
import re
import asyncio
import discord
from discord.ext import commands, tasks
import profanity_check as pc
import pdfplumber
import tiktoken
import openai
import ollama
import together
import cohere
from huggingface_hub import InferenceClient
import anthropic
import youtube_transcript_api
import scrapingant_client as Ant
from transformers import AutoTokenizer
from googleapiclient.discovery import build

# Active version

Version="0.0.0.0.1295"

# The running name of the program. Must be global and NEVER changing.

RunningName=sys.argv[0]

# Persona base folder. This is where all personas are stored.

# From SamAcctX
CompanionBase=os.getenv('COMPANION_BASE', '/home/Companion')
CompanionStorage=f'{CompanionBase}/Personas'
MemoryStorage=f'{CompanionBase}/Servers/Memory'
LoggingStorage=f'{CompanionBase}/Servers/Logs'
ConfigStorage=f'{CompanionBase}/Servers/Config'

# For anagram solver
AnagramWordList=f'{CompanionBase}/AnagramSolver.txt'

# This is a list of domains that are scams, frauds, or malitiouc. It is
# exists, it is read and message that have links listed are removed.
# Requires the persona text file as well for responses.

CompanionWhitelist=f'{CompanionBase}/Companion.whitelist'
CompanionScamURLS=f'{CompanionBase}/Companion.scam-urls'
CompanionAutoFilter=f'{CompanionBase}/Companion.autofilter'

# `GuildQueueLock`: Ensures safe modification of the guild queue structure
# during request management across different servers.

GuildQueue=deque()
GuildQueueLock=threading.Lock()
GuildQueueTimeout=60

# `ResponseLock`: Prevents simultaneous modifications when queuing
# responses for processing.

ResponseLock=threading.Lock()
ResponseTimeout=60

# `DeleteLock`: Manages safe scheduling of message deletions without
# conflicts.

DeleteLock=threading.Lock()
DeleteTimeout=60

# `DisectLock`: Ensures accurate logging by preventing overlapping writes
# during message dissection.

DisectLock=threading.Lock()
DisectTimeout=60

# `BabbleLock`: Provides concurrency control per server while allowing parallelism
# across different servers.

LoggingLock=threading.Lock()
LoggingTimeout=60

# Each server must have it own lock to insure concurrency under heavy
# load. Requests per server are still sequential. This should prevent
# active servers from hogging resources from smaller or less active
# servers.

BabbleLock={}
BabbleTimeout=60

# Constants For auto slowmode. Needs to be dymanic in the future
SlowModeMultiplier=3  # Seconds for individual slow mode
SlowwModeCooldown=307  # 5 minutes/7 secords cooldown for slow mode adjustments

# Dictionary to store the last slow mode change time for each channel
LastSlowmodeChange={}

# For counting active users per chanel
ActiveUsers={}

# For active member joins. anti raid messures. Will be a multiplier for slowdown
# mode if above 1% of total users.
ActiveJoins={}

# This is required for the bot to work properly.

intents=discord.Intents.all()
intents.presences=True
intents.guilds=True
intents.messages=True
intents.message_content=True
intents.members=True

# Create a Discord client
client=discord.Client(intents=intents)

### Really need to make these files on disk and not global memory lists, for
### sharding/multi process management.

# List to stowre timed messages for deletion
DeleteList=[]

###
### Special functions/Decorators
###

# The `function_timer` decorator measures and prints the execution time of
# both synchronous and asynchronous functions. For synchronous functions,
# it records the start and end times, calculates the elapsed duration, and
# outputs the time taken. For asynchronous functions, it uses the same
# approach but accommodates `await` for proper timing. This decorator helps
# in profiling and performance monitoring by providing precise timing
# information for each wrapped function.

def function_timer(func):
    @functools.wraps(func)
    def sync_timer(*args, **kwargs):
        start_time=time.perf_counter()
        result=func(*args, **kwargs)
        end_time=time.perf_counter()
        elapsed_time=end_time - start_time
        ErrorLog(f"{func.__name__}: {elapsed_time:.6f} seconds")
        return result

    @functools.wraps(func)
    async def async_timer(*args, **kwargs):
        start_time=time.perf_counter()
        result=await func(*args, **kwargs)
        end_time=time.perf_counter()
        elapsed_time=end_time - start_time
        ErrorLog(f"{func.__name__}: {elapsed_time:.6f} seconds")
        return result

    if inspect.iscoroutinefunction(func):
        return async_timer
    return sync_timer

# The `function_trapper` is a versatile decorator that wraps both
# synchronous and asynchronous functions to handle exceptions gracefully.
# When a wrapped function encounters an error, it logs the error details,
# including the function name and the line number where the error occurred,
# and then returns a predefined fallback result. This decorator ensures
# robust error handling while maintaining flexibility for both async and
# sync functions.

def function_trapper(failed_result=None):
    def decorator(func):
        if inspect.iscoroutinefunction(func):  # Handle async functions
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as err:
                    tb=traceback.extract_tb(err.__traceback__)
                    errline=tb[-1].lineno if tb else 'Unknown'
                    ErrorLog(f"{func.__name__}/{errline}: {err}")
                    return failed_result
            return async_wrapper
        else:  # Handle sync functions
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as err:
                    tb=traceback.extract_tb(err.__traceback__)
                    errline=tb[-1].lineno if tb else 'Unknown'
                    ErrorLog(f"{func.__name__}/{errline}: {err}")
                    return failed_result
            return sync_wrapper

    # Handle decorator usage with or without parentheses
    if callable(failed_result):  # Used without parentheses
        return decorator(failed_result)
    return decorator

###
### General file tools
###

# Cheap mkdir

@function_trapper(None)
def mkdir(fn):
    if not os.path.exists(fn):
        os.makedirs(fn,exist_ok=True)

# Read file into buffer

@function_trapper(None)
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

@function_trapper(None)
def AppendFile(fname,text):
    fh=open(fname,'a+')
    fh.write(text)
    fh.close()

# Write file to disk

@function_trapper(None)
def WriteFile(fn,data):
    cf=open(fn,'w')
    cf.write(data)
    cf.close()

# The `ReadFile2List` function processes the content of a file by reading
# it into a list, splitting the text into individual lines. It removes any
# blank lines and optionally converts all text to lowercase if specified.
# This ensures a clean and usable list of responses or data items from the
# file.

@function_trapper(None)
def ReadFile2List(fname,ForceLower=False):
    # Something broke. Keep the responses in character
    responses=ReadFile(fname).strip().split('\n')
    while '' in responses:
        responses.remove('')
    if ForceLower==True:
        responses=[item.lower() for item in responses]
    return responses

# The `PickRandomResponse` function selects and returns a random response
# from a given file. It first reads the file into a list of responses, then
# randomly picks one. If the selected response is a special placeholder
# (enclosed by `{[(*` and `*)]}`), the function treats it as a reference to
# another file, reads the content of that file, and returns it instead.
# Otherwise, it directly returns the selected response.

@function_trapper(None)
def PickRandomResponse(fname):
    responses=ReadFile2List(fname)
    selected_response=random.choice(responses)
    if selected_response.startswith('{[(*') and selected_response.endswith('*)]}'):
        buffer=ReadFile(selected_response[4:-4].strip()).strip()
        return buffer
    return selected_response

###
### Functions for AbuseIPDB
###

# This set of functions works together to identify potentially harmful or
# suspicious links in messages. It checks if a link is on a safe list or a
# known scam list. If the link isn’t on either list, it looks up its background
# using a service called AbuseIPDB, which evaluates whether the link’s
# associated IP address has been reported for malicious activity. If the link
# is flagged as dangerous, it’s marked as unsafe. This helps ensure that
# harmful links can be quickly identified and dealt with.

@function_trapper
def ExtractURLs(text):
    url_pattern=re.compile(r"https?://[^\s]+")
    return url_pattern.findall(text)

@function_trapper
def Domain2IP(domain):
    try:
        ip_address=socket.gethostbyname(domain)
        return ip_address
    except Exception as err:
        pass
    return None

@function_trapper
def ExtractDomains(url):
    parsed_url=urlparse(url)
    return parsed_url.netloc

@function_trapper
def CheckAbuseIPDB(domain,token):
    ipa=Domain2IP(domain)
    if ipa==None:
        return None,0
    url=f"https://api.abuseipdb.com/api/v2/check"
    params={"ipAddress": ipa}
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
             "Key": token, "Accept": "application/json"}

    try:
        response=requests.get(url, headers=headers, params=params,timeout=60)
        response.raise_for_status()
        data=response.json()
        if data.get("data", {}).get("abuseConfidenceScore", 0)>0:
            return True, data["data"]["abuseConfidenceScore"]
        else:
            return False, 0
    except requests.exceptions.RequestException as e:
        ErrorLog(f"Error checking AbuseIPDB: {e}")
        return False, 0

@function_trapper
def CheckMessageURLs(gid,text):
    # Check whitelist
    whiteurls=ReadFile2List(CompanionWhitelist)
    # Not in whitelist
    scamurls=ReadFile2List(CompanionScamURLS)

    # Extract URLs from the message
    Tokens=ReadTokens(gid)

    urls=ExtractURLs(text)

    if urls:
        for url in urls:
            domain=ExtractDomains(url)

            if domain in whiteurls:
                return False
            elif domain in scamurls:
                print(f"Scam URL: {domain}")
                return True
            elif 'AbuseIPDB' in Tokens:
                is_abusive, score=CheckAbuseIPDB(domain,Tokens['AbuseIPDB'])
                if is_abusive:
                    print(f"AbuseIPDB: {score}/{domain}")
                    return True
    return False

###
### Emotional Score functions
###

# The `CalculateMinorScale` function translates an emotional score,
# referred to as the "MajorScale," into a refined range of minor emotional
# variations, represented by `MinorMax` and `MinorMin`. The MajorScale,
# constrained between -10 and 10, determines the sensitivity of these
# minor emotional shifts. Positive scores reduce the upper range of
# variability, while negative scores lessen the lower range, and a neutral
# score provides a balanced range. This ensures that emotional intensity
# is scaled proportionally, with the output reflecting subtle fluctuations
# formatted to two decimal places for precision.

@function_trapper(0)
def CalculateMinorScale(MajorScale):
    # Ensure the MajorScale is within the allowed range
    MajorScale=int(MajorScale)
    if MajorScale>10:
        MajorScale=10
    elif MajorScale<-10:
        MajorScale=-10

    # Determine the range of the MinorScale based on the MajorScale
    if MajorScale==0:
        MinorMax=0.1
        MinorMin=-0.1
    elif MajorScale>0:
        MinorMax=0.1 - 0.01 * MajorScale
        MinorMin=-0.1
    else:  # MajorScale<0
        MinorMax=0.1
        MinorMin=-0.1 + 0.01 * abs(MajorScale)

    # Format MinorMax and MinorMin to one decimal place
    MinorMax=float(f"{MinorMax:.2f}")
    MinorMin=float(f"{MinorMin:.2f}")
    return MinorMax, MinorMin

# The `CalculateEmotionalScore` function evaluates and updates the
# emotional score (`escore`) of a conversation, using an external
# classifier to assess the sentiment of the provided text. Starting with a
# baseline `escore` (read from a file if available), it adjusts the
# scoring range based on the `CalculateMinorScale` function, which
# determines acceptable emotional variability. If the bot includes an
# emotional classifier, the function calculates an additional sentiment
# score (`mscore`) using the AI classifier and adjusts the `escore`
# accordingly. The updated score is written back to the file, and any
# placeholders in the response buffer (`buff`) are replaced with the new
# score, ensuring dynamic emotional feedback.

@function_trapper(None)
def CalculateEmotionalScore(fn,gid,bot,buff,text):
    # Don't waste cycles if theres no defined classifier
    if 'EmotionClassifier' not in bot:
        return buff

    # Figure out Emotional Score
    escore=0
    if os.path.exists(fn):
        try:
            escore=float(ReadFile(fn).strip())
        except:
            pass

    lval,rval=CalculateMinorScale(escore)
    mscore=0
    if 'EmotionClassifier' in bot:
        try:
            mscore=float(asyncio.run(AIClassifier(gid,bot['EmotionClassifier'],text,FailResp=0,lval=lval,rval=rval)))
        except:
            pass

    escore+=mscore
    WriteFile(fn,f"{escore:.2f}\n")
    if '{ESNEUTRAL}' in buff:
        buff=buff.replace('{ESNEUTRAL}',f'{escore:.2f}')
    return buff

###
### Random support functions
###

# The `NumberOnly` function checks if a given string can be considered a
# valid representation of a number, accounting for numeric characters,
# commas, periods, and various look-alike characters. It replaces common
# look-alike letters (like 'O' for '0' and 'I' for '1') with their numeric
# equivalents, trims whitespace, and validates the presence of digits while
# filtering out invalid characters. The function returns `True` if the
# string is a valid number, and `False` otherwise.

@function_trapper(None)
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

# Building the leet derivitives. This was a royal pain in the ass, but
# by doing so, if any user trying to bypass the edit detection can be
# persumed to have malicious intent.

# The BuildDerivatives function generates variations of a given word
# using common leetspeak substitutions. This is designed to catch
# altered forms of keywords that could be used to evade detection,
# ensuring that questions about sensitive topics (like age) are
# identified, even if disguised by replacing characters with
# similar-looking ones (e.g., "age" -> "4g3").

@function_trapper(None)
def BuildDerivitives(word):
    substitutions={
        'a': ['@','4'],
        'e': ['3'],
        'o': ['0'],
        'l': ['1', '|', '!', 'i'],
        'i': ['1', 'l', '|', '!', 'l'],
        's': ['z', '$', '5'],
        't': ['7', '+']
    }

    # Start the list
    dList=[ word ]

    # Forward in loop
    for x in range(len(word)):
        xword=list(word)
        if xword[x] in substitutions.keys():
            cList=substitutions[xword[x]]
            for y in range(len(cList)):
                xword[x]=cList[y]
                nword=''.join(xword)
                if nword not in dList:
                    dList.append(nword)

    # Forward reset at beginning
    xword=list(word)
    for x in range(len(word)):
        if xword[x] in substitutions.keys():
            cList=substitutions[xword[x]]
            for y in range(len(cList)):
                xword[x]=cList[y]
                nword=''.join(xword)
                if nword not in dList:
                    dList.append(nword)

    # Backwards
    xword=list(word)
    for x in range(len(word)-1,-1,-1):
        if xword[x] in substitutions.keys():
            cList=substitutions[xword[x]]
            for y in range(len(cList)):
                xword[x]=cList[y]
                nword=''.join(xword)
                if nword not in dList:
                    dList.append(nword)

    # return the list of words back to user
    return dList

# The BuildLeetList function creates a comprehensive list of leetspeak
# variations for a set of keywords. By applying the BuildDerivatives
# function to each word in the provided list, it generates leet-based
# variations that help detect keywords even when altered by character
# substitutions. This enables more reliable identification of disguised
# or intentionally modified words related to sensitive topics,
# supporting moderation efforts.

@function_trapper(None)
def BuildLeetList(side):
    leetlist=[]

    for i in range(len(side)):
        leet=BuildDerivitives(side[i])
        for j in range(len(leet)):
            if leet[j] not in leetlist:
                leetlist.append(leet[j])

    return leetlist

# The `StripPunctuation` function removes all punctuation and high ASCII
# characters from a given text by replacing them with spaces. It achieves
# this by using a translation table that maps these characters to spaces,
# ensuring the returned text is cleaned and ready for further processing,
# free from unwanted symbols.

@function_trapper(None)
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

@function_trapper(None)
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

@function_trapper(None)
def GetWordList(text):
    words=text.lower().split()
    return [word for word in words if word.strip()]

###
### Direct Companion functions
###

# The `ReadTokens` function ensures the bot has the necessary credentials
# to operate by locating and reading a specific file that stores API
# tokens. It carefully checks if the file exists, verifies its format, and
# ensures essential keys like the Discord token are present. If anything is
# missing or incorrect, the function logs the issue and stops the program
# to prevent errors during operation. By validating this information
# upfront, it ensures the bot can run securely and without interruptions.

@function_trapper({})
def ReadTokens(gid=None):
    tokens={}
    if gid==None:
        tfile=RunningName+'.tokens'
    else:
        tfile=f"{ConfigStorage}/{gid}/{gid}.tokens"
    if os.path.exists(tfile):
        try:
            tokens=json.loads(jsonFilter(ReadFile(tfile)))
        except Exception as err:
            ErrorLog("Error token file is not in JSON format. Please see README.md for new layout")
            sys.exit(1)
    else:
        ErrorLog(f"Missing token file: {tfile}")
        sys.exit(1)

    if gid==None and 'Discord' not in tokens:
        ErrorLog("The MUST be a Discord API reference in the tokens file")
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

# Raw dump. For diagnostics purposes to see the actual return response from the AI model.

def RawLog(text):
    if LoggingLock.acquire(timeout=LoggingTimeout):
        try:
            mkdir(LoggingStorage)
            fn=f'{LoggingStorage}/RAWDUMP.log'
            fh=open(fn,'w')
            fh.write(text)
            fh.close()
        except:
            pass
        LoggingLock.release()

# Bot record diagnostics

def BotLog(bot):
    if LoggingLock.acquire(timeout=LoggingTimeout):
        try:
            mkdir(LoggingStorage)
            fn=f'{LoggingStorage}/Bot.log'
            fh=open(fn,'w')
            fh.write(json.dumps(bot,indent=2))
            fh.close()
        except:
            pass
        LoggingLock.release()

# Logging

def WriteLog(gid,uid,channel,text):
    if LoggingLock.acquire(timeout=LoggingTimeout):
        try:
            txt=text.replace('\n','\\n').replace('\r','\\r')

            time=(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))

            s=f'{time} {uid} {channel} {txt}\n'

            dn=f'{LoggingStorage}/{gid}'
            mkdir(dn)
            fn=f'{dn}/{channel}.log'
            AppendFile(fn,s)
        except Exception as err:
            print(f'LOG Broke: {err}')
        LoggingLock.release()

# Log errors

def ErrorLog(text):
    if LoggingLock.acquire(timeout=LoggingTimeout):
        try:
            txt=text.replace('\n','\\n').replace('\r','\\r')

            time=(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))

            s=f'{time} {txt}\n'

            mkdir(LoggingStorage)
            fn=LoggingStorage+'/Errors.log'
            AppendFile(fn,s)

            # print to console
            print(txt)
        except:
            # print to console
            print(txt)

        LoggingLock.release()

# This function is designed to detect harmful or inappropriate content in a
# message using an AI classifier. It identifies categories like toxicity,
# insults, threats, or sexually explicit language. If the AI detects an issue,
# the bot reacts to the message with a corresponding emoji to highlight the
# type of violation. This quick response helps flag problematic content for
# review or moderation.

# Add ability to check each setting for deletion and respond with
# "inappropriate content for this server" (badcontent) message.

@function_trapper("NONE")
async def CheckCIMS(gid,bot,message,nsfw=False):
    cimsCategories={
        "TOXICITY": "\u2623",
        "SEVERE_TOXICITY": "\U0001F525",
        "IDENTITY_ATTACK": "\U0001F534",
        "INSULT": "\U0001F92C",
        "PROFANITY": "\U0001F4A2",
        "THREAT": "\u26A0",
        "SEXUALLY_EXPLICIT": "\U0001F51E",
        "FLIRTATION": "\U0001F48B",
        "PERSONAL_ATTACK": "\U0001F44A",
        "INFLAMMATORY": "\u26A1",
        "OBSCENE": "\U0001F621",
        "BIGOTRY": "\U0001F6AB",
        "BULLYING": "\U0001F6D1" }

    if CheckWhitelist(bot,'CIMSWhitelist',message):
        return False

    classifier=bot['CIMSClassifier']
    text=f"Classify this: '{message.content}'"
    AImatch=await AIClassifier(gid,classifier,text)
    AImatch=AImatch.upper().replace('\n',' ').replace('.','').replace('*','').strip()

    if AImatch!="NONE" and AImatch!='NO':
        await ModeratorNotify(bot,message.guild,f"{message.author.name}/{message.author.id} flagged for {AImatch.lower()} in {message.channel.name}")

    # Iterate through the toxic categories
    # if category is in the classifier, delete the message
    for category, emoji in cimsCategories.items():
        if category in AImatch:
            try:
                if category in classifier:
                    await ModeratorNotify(bot,message.guild,f"Deleted message from {message.author.name}/{message.author.id} for {category.lower()} in {message.channel.name}")
                    if not message.author.bot:
                        await send_response(bot,message,PickRandomResponse(bot['CIMS']),delete=57)
                    await message.delete()

                    # Once we hit a delete wall, the message is done and
                    # gone.
                    return True
                else:
                    await message.add_reaction(emoji)
            except Exception as err:
                ErrorLog(f"CIMS Failed to add reaction/delete message: {err}")
            # Each reaction is unique; move to the next word after reacting
    return False

# This function, `AIClassifier`, serves as a versatile interface to
# interact with different AI models from multiple providers. It accepts a
# `gid` (guild ID), a `classifier` configuration (which includes the AI
# engine type and model details), and a `text` input to be processed by
# the AI. The function first prepares the system and user messages by
# reading and formatting the provided instructions and text. It retrieves
# API tokens and settings from the `gid` and sets the relevant parameters,
# including a timeout and token limit. Based on the selected AI engine
# (e.g., OpenAI, Anthropic, Cohere, etc.), it sends the formatted request
# to the respective service and waits for a response. If an unrecognized
# engine is provided, it logs an error and returns a fallback response.
# The response from the AI is returned, completing the function's task.

@function_trapper('No')
async def AIClassifier(gid,classifier,text,FailResp="No",lval=None,rval=None,nsfw=False):
    startTime=time.time()
    # NSFW channel can have different classifier that may be less aggressive
    clinstr=classifier['Instructions']
    if nsfw:
        if os.path.exists(clinstr+'.nsfw'):
            clinstr+='.nsfw'

    msg=[]
    instr=ReadFile(clinstr).replace('\n',' ').strip()
    if lval:
        instr=instr.replace('{lval}',f'{lval}')
    if rval:
        instr=instr.replace('{rval}',f'{rval}')
    input=text.replace('\n',' ').replace("'","\'").replace('"',"'").strip()
    msg.append({ "role":"system", "content":instr })
    msg.append({ "role":"user", "content":input })

    Tokens=ReadTokens(gid)
    tout=classifier.get('Timeout',60)

    # Split multiple entries

    el=list(classifier['Engine'].split(','))       # Engine list
    ec=len(el)                              # Engine list length
    tl=list(classifier['MaxTokens'].split(','))    # Max Tokens list
    mt=len(tl)                              # Max Tokens list length
    ml=list(classifier['Model'].split(','))        # Model list
    mc=len(ml)                              # Model list length

    # The number of models MUST equal the number of engines. 1 model per engine

    if ec!=mc!=mt:
        ErrorLog(f"Broke AIClassifier ((models/Encoding)!=engines!=MaxTokens): {sys.exc_info()[-1].tb_lineno}/{err}")
        return None

    # Run through the engins/models until we have a response.

    response=None
    ecounter=0
    model=None
    while response==None and ecounter<ec:
        provider=el[ecounter].lower()
        pvn=el[ecounter]
        model=ml[ecounter]
        mts=int(tl[ecounter])

        try:
            if provider=='openai':
                response=GetOpenAI(Tokens['OpenAI'],msg,model,0,0,tout)
            elif provider=='openrouter':
                response=GetOpenRouter(Tokens['OpenRouter'],msg,model,0,0,tout)
            elif provider=='anthropic':
                response=GetAnthropic(Tokens['Anthropic'],msg,model,0,0,tout)
            elif provider=='togetherai':
                response=GetTogetherAI(Tokens['TogetherAI'],msg,model,0,0,tout)
            elif provider=='cohere':
                response=GetCohere(Tokens['Cohere'],msg,model,0,0,tout)
            elif provider=='ollama':
               response=GetOllama(None,msg,model,0,0,tout,seed=0,mt=mts)
            elif provider=='perplexity':
                response=GetPerplexity(Tokens['Perplexity'],msg,model,0,0,tout)
            elif provider=='huggingface':
                response,stop=GetHuggingFace(Tokens['HuggingFace'],msg,model,0,0,tout)
            else:
                ErrorLog(f"Invalid classifier engine: {provider}")
                return FailResp
            if response==None:
                ecounter+=1
            else:
                break
        except Exception as err:
            response=None

    if response==None:
        return FailResp

    endTime=time.time()
    AppendFile(f'{LoggingStorage}/{gid}.timing',f"{datetime.datetime.fromtimestamp(startTime).strftime('%Y-%m-%d %H:%M:%S')} {pvn} {model} {endTime-startTime:.6f}\n")

    return response

# This function scans a piece of text to identify sensitive personal information, such
# as Social Security numbers, phone numbers, email addresses, credit card numbers, IP
# addresses, and Employer Identification Numbers (EINs). By checking for specific
# patterns associated with each type of information, it aims to detect and label any
# sensitive data it finds, like an email or a phone number, within the text. If it
# identifies something sensitive, it returns the type of information and the exact
# pattern found; otherwise, it confirms that no personal information was detected. This
# process helps ensure privacy by flagging potentially sensitive data in a
# straightforward way.

@function_trapper(None)
async def DetectPII(gid,bot,text):
    async def detect_phone_number(text):
        # Define phone number patterns for different countries
        phone_patterns=[
            (r'(?<!\d)(\+?86)?1[3-9]\d{9}(?!\d)', 'China'),        # China (11 digits, starts with 13-19)
            (r'(?<!\d)(\+91)?[6789]\d{9}(?!\d)', 'India'),         # India (10 digits, starts with 6-9)
            (r'(?<!\d)(\+1)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)', 'USA/Canada'),  # USA/Canada (10 digits, area code optional)
            (r'(?<!\d)(\+1)?\d{10}(?!\d)', 'USA/Canada'),          # USA/Canada (10 digits, no spaces or symbols)
            (r'(?<!\d)(\+55)?\(?[1-9]\d\)?[\s.-]?\d{4,5}[\s.-]?\d{4}(?!\d)', 'Brazil'),  # Brazil (10-11 digits, area code 2-9)
            (r'(?<!\d)(\+62)?8\d{8,10}(?!\d)', 'Indonesia'),       # Indonesia (9-11 digits, starts with 8)
            (r'(?<!\d)(\+7)?9\d{9}(?!\d)', 'Russia'),              # Russia (10 digits, starts with 9 after +7)
            (r'(?<!\d)(\+81)?0\d{1,4}[\s.-]?\d{1,4}[\s.-]?\d{4}(?!\d)', 'Japan'),  # Japan (varied lengths, typically 10 digits)
            (r'(?<!\d)(\+52)?\(?\d{2,3}\)?[\s.-]?\d{4,5}[\s.-]?\d{4}(?!\d)', 'Mexico'),  # Mexico (10-11 digits, area code 2-3 digits)
            (r'(?<!\d)(\+49)?\(?\d{3,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{4}(?!\d)', 'Germany'),  # Germany (10-12 digits, various area codes)
            (r'(?<!\d)(\+44)?7\d{9}(?!\d)', 'UK')                 # UK (10 digits, starts with 7 after +44)
        ]

        # Step 1: Remove URLs from the text. This approach is needed because
        # URLs can be wrapped in markdown. Not perfect be far, but it does seem
        # to remove most false positives without the need of an AI classifier.

        inwords=text.lower().split()
        outwords=[]
        for word in inwords:
            if 'http://' not in word and 'https://' not in word:
                outwords.append(word)
        text=' '.join(outwords)

        # Step 2: Detect any phone numbers in the text
        for pattern, country in phone_patterns:
            match=re.search(pattern, text)
            if match:
                phone_number=match.group()

                # Skip numbers that are too short to be valid phone numbers
                if len(phone_number)>4:
                    return (phone_number, country)
            await asyncio.sleep(0)

        # Return None if no valid phone numbers are found
        return None

    # Embedded function to validate credit card numbers using Luhn's algorithm
    def ValidCC(card_number):
        # Remove any non-digit characters for validation purposes
        card_number=''.join(filter(str.isdigit, card_number))

        # Check for valid credit card lengths
        if len(card_number) not in [15, 16]:
            return False

        # Basic BIN check for common credit cards
        valid_bins=('4', '5', '34', '37', '6')  # Visa, MasterCard, AmEx, Discover
        if not card_number.startswith(valid_bins):
            return False

        # Luhn algorithm to verify credit card number
        checksum=0
        reverse_digits=card_number[::-1]
        for idx, digit in enumerate(reverse_digits):
            num=int(digit)
            # Double every second digit from the right
            if idx % 2==1:
                num *= 2
                if num>9:  # If doubling results in two digits, sum them
                    num -= 9
            checksum += num
        return checksum % 10==0

    # Regex patterns for various types of PII
    patterns={
        "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
        "Email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "Credit Card": r"\b(?:\d[ -]*?){13,16}\b",
        "IPv4 Address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "IPv6 Address": r"\b([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b",
        "EIN": r"\b\d{2}-\d{7}\b"
    }

    # Pattern to identify Discord mentions (e.g. <@396394433328971776>)
    discord_mention_pattern=r"<@\d{17,18}>"

    # Remove Discord mentions from sssthe text
    text_without_mentions=re.sub(discord_mention_pattern, "", text)

    # Check each PII pattern in the cleaned text
    for pii_type, pattern in patterns.items():
        match=re.search(pattern, text_without_mentions)
        if match:
            detected_value=match.group()

            # Special handling for Credit Card numbers. Ignore if not a valid
            # credit card based on the Luhn check and BIN

            if pii_type=="Credit Card" and not ValidCC(detected_value):
                continue

            return f"{pii_type}: {detected_value}"
        await asyncio.sleep(0)

        # Check phone numbers. This is a nasty process as local numbers
        # can cause false positives. AI is used to verify the REGEX is
        # accurate.

        match=await detect_phone_number(text)
        if match!=None:
            if "PIIClassifier" in bot:
                txt=f'REGEX matched: {match} CONFIRM: {text}'
                AImatch=await AIClassifier(gid,bot['PIIClassifier'],txt)
                if AImatch.lower()=='yes':
                    return f"AI/Phone Number: {match}"
                else:
                    return None

    # If no PII pattern was found
    return None

# The `MaintainTokenLimit` function is responsible for ensuring that the
# messages sent to the AI do not exceed a specific limit on the number of
# tokens used. Tokens are units of text that the AI processes, and each
# message can contain a varying number of tokens based on its length and
# complexity.  When users interact with the bot, this function checks how
# many tokens are currently being used in the conversation. If it finds
# that the total exceeds a predefined limit, it carefully removes older
# messages from the conversation history to make room for new ones. This
# way, it ensures that only relevant and recent information is kept while
# still allowing for meaningful interactions with users.

@function_trapper(None)
def MaintainTokenLimit(Tokens,orgmessages,max_tokens=128000,engine='openai',model="gpt-4o",encoding=None,HuggingFace=False):
    def count_tokens():
        # Calculate current tokens in the message list
        if engine=='openai':
            current_tokens=sum(len(enc.encode(message["content"])) for message in messages)
        elif engine=='huggingface':
            current_tokens=sum(len(enc(message["content"])["input_ids"]) for message in messages)
        elif engine=='cohere':
            current_tokens=sum(len(enc.tokenize(text=message["content"],model=model,offline=False).tokens) for message in messages)
        else:
            # Generic fall through. Anthropic, Perplexity do NOT have a
            # clean way of doing this... I've tried several. the 24 at the
            # end is what Anthropic calls overhead. They say 12, but as
            # wrong as the rest of this has been, the extra can not hurt.

            current_tokens=0
            for message in messages:
                if message['role']!='system':
                    current_tokens+=len(message['content'])+24
                elif engine!='anthropic':
                    current_tokens+=len(message['content'])+24
            current_tokens=int(current_tokens/4)

        return current_tokens

    # Early exit if we are not actually counting tokens.
    if max_tokens==0:
        return messages

    # Figure out which tokenizer to use.
    if engine=='openai':
        if encoding!=None:
            enc=tiktoken.get_encoding(encoding)
        else:
            enc=tiktoken.get_encoding(tiktoken.model.MODEL_TO_ENCODING[model])
    elif engine=='huggingface' or engine=='googleai':
        enc=AutoTokenizer.from_pretrained(model)
    elif engine=='cohere':
        enc=cohere.ClientV2(api_key=Tokens['Cohere'])

    # Make a separate working copy of the original messages.
    messages=orgmessages.copy()

    # Get a starting point
    current_tokens=count_tokens()
    old_tokens=current_tokens

    # While tokens exceed the limit, remove elements
    while current_tokens>max_tokens:
        for i in range(len(messages) - 1):
            if i<len(messages) - 1:
                if messages[i]['role'].lower()=="user" and messages[i+1]['role'].lower()=="assistant":
                    # Remove the pair (two items)
                    messages.pop(i)
                    messages.pop(i)
                    break
                elif messages[i]['role'].lower()=="user" and messages[i+1]['role'].lower()=="user":
                    # Remove only one item if two adjacent items are user/user
                    messages.pop(i)
                    break

        # Recalculate current tokens after removal
        current_tokens=count_tokens()
        # Check for the situation that we can't reduce the number of tokens.
        if old_tokens==current_tokens and current_tokens>max_tokens:
            print(f"{engine}/{model}: Token reductiion error. {current_tokens}>{max_tokens}")
            return None
        old_tokens=current_tokens

    return messages

# Get "steering" prompts, if there are any

# Steering files are a way of providing reinforcement to a pattern or paticular
# question/response designed to maintain the persona. Often times this may be used to
# enforce platform TOS/AUP.

# While we can dive into the nuances on unbiased AI material, we'll just skip to the
# finality: NOTHING IS UNBIASED. This will NEVER change simply because of how we learn,
# develop, and grow both as a family and societal structure. Bias is AUTOMATIC.

# The steering principles demonstrated here are much like we go through as children. The
# txt file will have the question repeated multiple times, with multiple acceptable
# responses. This practice is virtually identical to how we learn as children.

@function_trapper(None)
def GetSteering(bot,input_text):
    wordlist=GetWordList(StripPunctuation(input_text))
    if wordlist==None or wordlist==[]:
        return None

    SteerDir=f"{CompanionStorage}/{bot['BotName']}/Steering"

    for word in wordlist:
        if os.path.isdir(SteerDir+'/'+word):
            SteerDir+='/'+word
        elif os.path.isfile(SteerDir+'/'+word+'.txt'):
            prompts=ReadFile(SteerDir+'/'+word+'.txt').strip().split('\n')
            return prompts

    # No txt file found. No prompts available
    return None

# This function determines the appropriate configuration file for a companion bot
# based on whether the settings are for a specific channel or global and whether they
# are SFW (safe for work) or NSFW (not safe for work). It prioritizes NSFW
# channel-specific files, then SFW channel-specific files, followed by NSFW global
# files, and finally SFW global files. If none of these files exist, it falls back to
# the provided base filename to avoid potential errors in case the file is missing.
# This ensures the system can gracefully handle configuration scenarios without
# crashing.

@function_trapper(None)
def GetCompanionControlFile(basename,channel,nsfw):
    # .cfg may or may not exist. Perserve if it does.
    iscfg=basename.endswith(".cfg")
    new_basename=basename[:-4] if iscfg else basename
    cfg=".cfg" if iscfg else ""

    # NSFW channel version
    refname=f"{new_basename}.{channel}.nsfw"+cfg
    if nsfw and os.path.exists(refname):
        return refname

    # SFW channel version
    refname=f"{new_basename}.{channel}"+cfg
    if os.path.exists(refname):
        return refname

    # NSFW global version
    refname=f"{new_basename}.nsfw"+cfg
    if nsfw and os.path.exists(refname):
        return refname

    # SFW global version
    refname=f"{new_basename}"+cfg
    if nsfw and os.path.exists(refname):
        return refname

    # This is a real PITA to debug. Returning basename is just a nice way of
    # letting os.path.exists() deal with a missing file without having to test
    # for None everywhere. Returning None here will unleash chaos and be a
    # nightmare to find out this THIS one line can cause such nighmares.

    return basename

# The `GetCompanionPersona` function is responsible for determining and
# retrieving the specific personality or character traits that the bot will use
# when interacting with users in a particular Discord server.  When users send
# messages, it's important for the bot to respond in a way that fits its
# designated role or persona. This function checks the server's configuration
# settings to find out which persona should be used based on factors like the
# channel type and whether it’s a safe-for-work (SFW) or not-safe-for-work
# (NSFW) environment. It gathers all relevant information about how the bot
# should behave, including its name, response style, and any special rules it
# needs to follow.

@function_trapper(None)
def GetCompanionPersona(gid,channel,nsfw=False,Welcome=False):
    # Get the list of channels and the bot name that is allowed in a given channel
    cfg=f"{ConfigStorage}/{gid}/{gid}.cfg"
    if not os.path.exists(cfg):
        mkdir(f"{ConfigStorage}/{gid}")
        ErrorLog(f'NO configuration: {cfg}')
        return None

    try:
        Config=json.loads(jsonFilter(ReadFile(cfg)))
    except Exception as err:
        ErrorLog(f"{cfg} damaged: {sys.exc_info()[-1].tb_lineno}/{err}")
        return None

    if 'Channels' not in Config:
        Config['Channels']={}

    bot=Config.copy()

    # Welcome should really be Default. If more then one bot it listed, comma
    # separated, one one random, and vwerify that it has a welcome file.

    if Welcome==True:
        if 'Welcome' in Config:
            bot['BotName']=Config['Welcome']
        else:
            bot['BotName']=Config['Default']
        bot['Channel']=None
    else:
        Channels=Config['Channels']
        bot['Channel']=channel
        if channel in Channels:
            bot['BotName']=Channels[channel]
            bot['ResponseAllowed']='Yes'
        else:
            bot['BotName']=Config['Default']
            bot['ResponseAllowed']='No'

    # Base bot structure
    CompanionBotName=f"{CompanionStorage}/{bot['BotName']}/{bot['BotName']}"

    # System Role
    bot['System']=GetCompanionControlFile(f"{CompanionBotName}.system",channel,nsfw)

    # Persona file
    bot['Persona']=GetCompanionControlFile(f"{CompanionBotName}.persona",channel,nsfw)

    # EVERY channel can be dressed up.
    bot['Welcome']=GetCompanionControlFile(f"{CompanionBotName}.welcome",channel,nsfw)
    bot['Vulgarity']=GetCompanionControlFile(f"{CompanionBotName}.vulgarity",channel,nsfw)
    bot['ScamURLS']=GetCompanionControlFile(f"{CompanionBotName}.scamurls",channel,nsfw)
    bot['AutoFilter']=GetCompanionControlFile(f"{CompanionBotName}.autofilter",channel,nsfw)
    bot['AgeExploit']=GetCompanionControlFile(f"{CompanionBotName}.ageexploit",channel,nsfw)
    bot['PII']=GetCompanionControlFile(f"{CompanionBotName}.pii",channel,nsfw)
    bot['CIMS']=GetCompanionControlFile(f"{CompanionBotName}.cims",channel,nsfw)
    bot['TooMuchInformation']=GetCompanionControlFile(f"{CompanionBotName}.tmi",channel,nsfw)
    bot['Broken']=GetCompanionControlFile(f"{CompanionBotName}.broke",channel,nsfw)
    bot['URLBroken']=GetCompanionControlFile(f"{CompanionBotName}.urlbroke",channel,nsfw)
    bot['YTtags']=GetCompanionControlFile(f"{CompanionBotName}.yttags",channel,nsfw)
    bot['noYTtags']=GetCompanionControlFile(f"{CompanionBotName}.noyttags",channel,nsfw)

    # Load bot config file. Channel CFg always has priority.
    settings={}
    try:
        bcfg=GetCompanionControlFile(f"{ConfigStorage}/{gid}/{bot['BotName']}.cfg",channel,nsfw)
        if bcfg!=None:
            settings=json.loads(jsonFilter(ReadFile(bcfg)))
    except Exception as err:
        ErrorLog(f"{bcfg} damaged: {sys.exc_info()[-1].tb_lineno}/{err}")

    # Merge the persona settings into the controlling dictionary
    if settings!={}:
        bot|=settings

    # Run through some sanity checks.
    if 'AutoLogging' not in bot:
        bot['AutoLogging']='yes'
    if 'AutoModeration' not in bot:
        bot['AutoModeration']='yes'
    if 'PIIModeration' not in bot:
        bot['PIIModeration']='yes'
    if 'AllowBot' not in bot:
        bot['AllowBot']='no'
    if 'Engine' not in bot:
        bot['Engine']="openai"
    if 'Model' not in bot:
        bot['Model']="gpt-4o-mini"
    if 'freqpenalty' not in bot:
        bot['freqpenalty']=0.67
    else:
        if type(bot['freqpenalty'])!=float:
            bot['freqpenalty']=float(bot['freqpenalty'])
    if 'Temperature' not in bot:
        bot['Temperature']=0.37
    else:
        if type(bot['Temperature'])!=float:
            bot['Temperature']=float(bot['Temperature'])
    if 'AllowVulgarity' not in bot:
        bot['AllowVulgarity']='No'
    if 'MaxMemory' not in bot:
        bot['MaxMemory']=100
    else:
        if type(bot['MaxMemory'])!=int:
            bot['MaxMemory']=int(bot['MaxMemory'])

    BotLog(bot)

    # return the current bot
    return bot

# The `GetBabble` function is designed to manage the interaction between users
# and the AI within a Discord server. When a user sends a message to the bot,
# this function takes that message and prepares it for processing by the AI.
# Here's how it works: when a message is received, `GetBabble` gathers all
# relevant information, including who sent the message and which channel it was
# sent in. It then compiles this information along with any previous context or
# conversation history. This complete package is then sent to the AI for
# generating an appropriate response.

@function_trapper(None)
def GetBabble(message,text):
    # The "uid" and "channel" are used to load the persona and store the memory to
    # disk. At this point, we don't have any global variables.

    dataline=text.split('/')
    gid=message.guild.id
    uid=dataline[0]
    channel,cnsfw=dataline[1].split(':')
    nsfw=(cnsfw=='T')
    input_text=str(dataline[2:]).replace("'","\'").replace('"',"'")

    # Don't remember this request. does NOT bypass logging

    ForgetThisMessage=False
    if text.strip().startswith('%#>'):
        ForgetThisMessage=True
        input_text=input_text[3:].strip()

    # Load the persona and memory files
    # NSFW not allowed in threads directly, so find parent channel

    # Question: Do we take info of NSFW state or force verify? Currebt is
    # face value

    bot=None
    if isinstance(message.channel,discord.Thread):
        pchannel=str(message.channel.parent)
        bot=GetCompanionPersona(gid,pchannel,nsfw)   # message.channel.parent.nsfw
    else:
        bot=GetCompanionPersona(gid,channel,nsfw)

    persona=[]
    mList=[]

    # Read system role from system tag file
    # { "role": "system", "content": ""}

    if os.path.exists(bot['System']):
        buff=ReadFile(bot['System']).replace('\n','\\n').replace("'","\'").replace('"',"'").strip()
        fn=f"{MemoryStorage}/{gid}/{bot['BotName']}/{bot['BotName']}.{uid}.escore"
        buff=CalculateEmotionalScore(fn,gid,bot,buff,input_text)
        sysList=[ '{'+ f'"role": "system", "content": "{buff}"' +'}' ]
    else:
        sysList=[]

    # Read the persona file
    if os.path.exists(bot['Persona']):
        pfList=ReadFile(bot['Persona']).strip().split('\n')
    else:
        pfList=[]
    pList=sysList+pfList

    # Load memory files, if one exists.
    dn=f"{MemoryStorage}/{gid}/{bot['BotName']}"
    mkdir(dn)
    fn=f"{dn}/{bot['BotName']}.{uid}.{channel}.memory"
    if os.path.exists(fn):
        mList=ReadFile(fn).strip().split('\n')
        pList+=mList

    # Build the complete persona list

    for s in pList:
        try:
            persona.append(json.loads(s))
        except:
            ErrorLog(f"Broke: {sys.exc_info()[-1].tb_lineno}/{s}")

    # Look for a "steering" file. Should be last to ensurew its not chopped of.
    sList=GetSteering(bot,input_text)
    if sList!=None:
        pList+=sList

    # Add user input

    memU={ "role": "user", "content": input_text }
    persona.append(memU)

    # Process API for the request

    el=list(bot['Engine'].split(','))       # Engine list
    ec=len(el)                              # Engine list length
    tl=list(bot['MaxTokens'].split(','))    # Max Tokens list
    mt=len(tl)                              # Max Tokens list length
    # Encoding alwayys takes priority over modem
    if 'Encoding' in bot:
        ml=list(bot['Encoding'].split(','))     # Encoding list
        mc=len(ml)                              # Encoding list length
    else:
        ml=list(bot['Model'].split(','))        # Model list
        mc=len(ml)                              # Model list length

    # The number of models MUST equal the number of engines. 1 model per engine

    if ec!=mc!=mt:
        ErrorLog(f"Broke GB ((models/Encoding)!=engines!=MaxTokens): {sys.exc_info()[-1].tb_lineno}/{err}")
        return PickRandomResponse(bot['Broken'])

    # Run through the engins/models until we have a response.

    response=None
    ecounter=0
    while response==None and ecounter<ec:
        cbot=copy.deepcopy(bot)             # Make a copy
        cbot['Engine']=el[ecounter]
        cbot['MaxTokens']=int(tl[ecounter])
        # Encoding or Model
        if 'Encoding' in cbot:
            cbot['Encoding']=ml[ecounter]
        else:
            cbot['Model']=ml[ecounter]

        startTime=time.time()
        response=GetAIResponse(gid,persona,cbot)
        endTime=time.time()
        AppendFile(f'{LoggingStorage}/{gid}.timing',f"{datetime.datetime.fromtimestamp(startTime).strftime('%Y-%m-%d %H:%M:%S')} {cbot['Engine']} {cbot['Model']} {endTime-startTime:.6f}\n")

        if response==None:
            ecounter+=1
        else:
            break

    # check to see if we got a response. If not, don't save the
    # memory, just return.

    if response==None or response=='':
        return PickRandomResponse(bot['Broken'])

    # Save "memory" to disk

    memA={ "role": "assistant", "content": response }

    mList.append(json.dumps(memU))
    mList.append(json.dumps(memA))

    # Keep memory at a limited amount. The *2 is because we are saving user and AI
    # responses.

    if bot['MaxMemory']>0 and memA['content']!=None and not ForgetThisMessage:
        if len(mList)>(bot['MaxMemory']*2):
            mList=mList[2:]

        fn=f"{dn}/{bot['BotName']}.{uid}.{channel}.memory"
        fh=open(fn,'w')
        for i in mList:
            fh.write(i+'\n')
        fh.close()

    # Return the AI response
    return response

# The `HandleOneMessage` function is designed to take care of individual
# messages sent to the bot in a Discord server. When a user sends a message,
# this function steps in to manage the entire process of understanding and
# responding to that message.  Here's how it works: when a message is received,
# the function first gathers all necessary details, such as who sent the
# message and which channel it was sent in. It then checks if there are any
# specific rules or settings that need to be applied based on the context (like
# whether it's a safe-for-work environment). After that, it prepares everything
# needed for the AI to generate an appropriate response.

@function_timer
@function_trapper(None)
async def HandleOneMessage(request):
    with concurrent.futures.ThreadPoolExecutor() as pool:
        input_text=request['input']
        guild=client.get_guild(request['gid'])
        channel=await guild.fetch_channel(request['cid'])
        message=await channel.fetch_message(request['mid'])

        uid=str(message.author.id)
        author=str(message.author.mention)
        channel=str(message.channel)

        # NSFW not allowed in threads, so find parent channel
        bot=None
        if isinstance(message.channel,discord.Thread):
            pchannel=message.channel.parent
            bot=GetCompanionPersona(guild.id,str(pchannel),pchannel.nsfw)
            nsfw=str(pchannel.nsfw)[0]
            # WTAF? Really? bots have to join a thread...
            if not message.channel.me:
                await message.channel.join()
        else:
            bot=GetCompanionPersona(guild.id,str(message.channel),message.channel.nsfw)
            nsfw=str(message.channel.nsfw)[0]
        if bot==None:
            return

        print('U',guild.id,nsfw,uid,message.author,message.channel,len(message.content))

        # Handle any vulgarity
        if bot['AutoModeration'].lower()!='no' \
        and os.path.exists(bot['Vulgarity']) \
        and bot['AllowVulgarity'].lower()=='no' \
        and not nsfw=='T':
            if bool(pc.predict([ input_text ]))==True:
                await ModeratorNotify(bot,message.guild,f"{message.author.name}/{message.author.id} chastized for vulgarity in {message.channel.name}")
                await send_response(bot,message,PickRandomResponse(bot['Vulgarity']),delete=57)
                try: # delete the offending message
                    await message.delete()
                except:
                    pass
                return
            else:
                istr=f"{uid}/{channel}:{nsfw}/{input_text}"
                response=await client.loop.run_in_executor(pool,GetBabble,message,istr)
        else:
            istr=f"{uid}/{channel}:{nsfw}/{input_text}"
            response=await client.loop.run_in_executor(pool,GetBabble,message,istr)

        print('B',guild.id,client.user.id,bot['BotName'],message.channel,len(response))

        # Check to see if we actually got a response
        if response!=None and response.lower().strip()!="none":
            # Handle webhooks for response
            await send_response(bot,message,response)
        else:
            # Communication with AI failed. Put message back in queue
            if ResponseLock.acquire(timeout=ResponseTimeout):
                msg={}
                msg['gid']=guild.id
                msg['cid']=message.channel.id
                msg['mid']=message.id
                msg['input']=input_text
                PutNextRequest(guild.id,msg)
                ResponseLock.release()
            else:
                ErrorLog("Lock failed Reput Message")

# The `GetNextRequest` function is designed to retrieve the next request from a specific
# Discord server's list of messages that need to be processed by the AI.  When users
# interact with the bot and send messages, those messages are collected in a queue so
# that they can be handled one at a time. This function looks at this queue and pulls
# out the first request that is waiting to be addressed. By doing this, it ensures that
# each message is processed in order, allowing the AI to respond appropriately and
# maintain smooth communication.

@function_trapper(None)
def GetNextRequest(gid):
    rname=f"{MemoryStorage}/{gid}/requests.txt"

    if not os.path.exists(rname):
        return None

    # Read request list for a specific server
    request_list=ReadFile(rname).strip().split('\n')
    # Get first request
    try:
        request=json.loads(request_list[0])
    except Exception as err:
        ErrorLog(f"Broken request: {sys.exc_info()[-1].tb_lineno}/{err}")
        return None

    # Write the rest of the list back to disc. This is the file version of
    # popping the first item.

    if (len(request_list)-1)>0:
        fh=open(rname,'w')
        for i in range(1,len(request_list)):
            fh.write(request_list[i]+'\n')
        fh.close()
    else:
        os.remove(rname)

    return request

# The `PutNextRequest` function is responsible for adding a new request to a specific
# Discord server's list of messages that need to be processed by the AI.  When users
# send messages to the bot, those messages may require thoughtful responses from the AI.
# This function takes each new message and places it at the end of the queue, ensuring
# that it will be addressed in turn after any previous requests. By doing this, it helps
# manage how and when each message is handled, allowing for organized communication.

def PutNextRequest(gid,msg):
    rname=f"{MemoryStorage}/{gid}/requests.txt"
    s=json.dumps(msg)+'\n'
    AppendFile(rname,s)

###
### AI handlers (Optimized)
###

# This group of functions is designed to retrieve AI-generated responses
# from various platforms using APIs. Each function interfaces with a
# different AI service, including OpenAI, Anthropic, Hugging Face,
# TogetherAI, Cohere, Ollama, and Perplexity. The functions send input
# messages, along with parameters such as temperature and frequency
# penalty, to the respective service and receive a response. The responses
# are then processed and returned as text, often with additional details
# logged for transparency. These functions allow for flexibility in using
# multiple AI models, enabling seamless integration with different AI
# providers based on the user's preference or specific use case.

@function_trapper(None)
def GetOpenAI(apikey,messages,model,freqpenalty,temperature,timeout):
    clientAI=openai.OpenAI(api_key=apikey)
    completion=clientAI.chat.completions.create(
            model=model,
            frequency_penalty=freqpenalty,
            temperature=temperature,
            messages=messages,
            timeout=timeout
        )
    clientAI.close()
    response=completion.choices[0].message.content.strip()
    RawLog(f"OpenAI/{model}: {str(completion)}")
    return response

# Special note: meta-llama/llama-3.1-405b-instruct:free can cause errors by not
# returning a response. function_trapper DOES it job well, but it does looks like a
# program error. When using the free models, ALWAYS have multiple. Free means BUSY
# and a high probability is the model not responding.

@function_trapper(None)
def GetOpenRouter(apikey,messages,model,freqpenalty,temperature,timeout):
    clientAI=openai.OpenAI(api_key=apikey,base_url="https://openrouter.ai/api/v1")
    completion=clientAI.chat.completions.create(
            model=model,
            frequency_penalty=freqpenalty,
            temperature=temperature,
            messages=messages,
            timeout=timeout
        )
    clientAI.close()
    try:
        response=completion.choices[0].message.content.strip()
    except Exception as err:
        return None
    RawLog(f"OpenRouter/{model}: {str(completion)}")
    return response

@function_trapper(None)
def GetAnthropic(apikey,messages,model,freqpenalty,temperature,timeout):
    clientAI=anthropic.Anthropic(api_key=apikey,timeout=timeout)
    completion=clientAI.messages.create(
            system=messages[0]['content'],
            model=model,
            max_tokens=4096,
            temperature=temperature,
            messages=messages[1:],
            stream=False
        )
    clientAI.close()
    response=completion.content[0].text.strip()
    RawLog(f"Anthropic/{model}: {str(completion)}")
    return response

@function_trapper(None)
def GetHuggingFace(apikey,messages,model,freqpenalty,temperature,timeout):
    clientAI=InferenceClient(token=apikey,timeout=timeout)
    completion=clientAI.chat.completions.create(
            model=model,
            frequency_penalty=freqpenalty,
            temperature=temperature,
            messages=messages,
            stream=False
        )
    stop=completion.choices[0].finish_reason
    response=completion.choices[0].message.content.strip()
    RawLog(f"HuggingFace/{model}: {str(completion)}")
    return response,stop

@function_trapper(None)
def GetTogetherAI(apikey,messages,model,freqpenalty,temperature,timeout):
    clientAI=together.Together(api_key=apikey, timeout=timeout)
    completion=clientAI.chat.completions.create(
            model=model,
            frequency_penalty=freqpenalty,
            temperature=temperature,
            messages=messages,
            stream=False
        )
    response=completion.choices[0].message.content.strip()
    RawLog(f"TogetherAI/{model}: {str(completion)}")
    return response

@function_trapper(None)
def GetCohere(apikey,messages,model,freqpenalty,temperature,timeout):
    clientAI=cohere.ClientV2(api_key=apikey, timeout=timeout)
    completion=clientAI.chat(
            model=model,
            frequency_penalty=freqpenalty,
            temperature=temperature,
            messages=messages,
            safety_mode="NONE"
        )
    response=completion.message.content[0].text.strip()
    RawLog(f"Cohere/{model}: {str(completion)}")
    return response

@function_trapper(None)
def GetOllama(apikey,messages,model,freqpenalty,temperature,timeout,seed=0,mt=2048):
    options={
            "temperature": temperature,
            "frequency_penalty": freqpenalty,
            "seed": seed,
            "num_ctx": mt
        }
    clientAI=ollama.Client(timeout=timeout)
    completion=clientAI.chat(
            stream=False,
            model=model,
            options=options,
            messages=messages
        )
    response=completion['message']['content'].strip()
    RawLog(f"Ollama/{model}: {str(completion)}")
    return response

@function_trapper(None)
def GetPerplexity(apikey,messages,model,freqpenalty,temperature,timeout):
    # Prepare the payload for the request
    payload={
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

    # Perplexity URL
    PerplexityURL="https://api.perplexity.ai/chat/completions"

    # Set up headers including authorization
    headers={
            "Authorization": f"Bearer {apikey}",
            "Content-Type": "application/json"
        }

    # Make the POST request to the Perplexity API
    response=requests.post(PerplexityURL, json=payload, headers=headers,timeout=timeout)

    # Check if the request was successful
    if response.status_code==200:
        completion=response.json()

    response=completion["choices"][0]["message"]["content"].strip()

    # If there are citations in the choices text portion, append
    # them to the response. This is not neccessary, but it does look
    # nice and adds to the bot's presence.

    IsCitations=any(re.search(r'\[\d+\]', choice.get("message", {}).get("content", "")) for choice in completion.get("choices", []))
    if IsCitations:
        response+="\n\n"+"\n".join(f"<{url}>" for url in completion['citations'])
    RawLog(f"Perplexity/{model}: {str(completion)}")
    return response

# The `GetAIResponse` function is responsible for communicating with the
# AI to generate thoughtful replies based on user messages. When a user
# sends a message to the bot, this function takes all relevant
# information—like the context of the conversation and any specific
# instructions—and sends it to the AI service.  Here's how it works: once
# the necessary details are gathered, this function makes a request to the
# appropriate AI provider (such as OpenAI or Hugging Face) using their
# API. It specifies parameters like which model to use and how creative or
# focused the response should be. After sending this request, it waits for
# a reply from the AI.

@function_trapper(None)
def GetAIResponse(gid,persona,bot):
    print(gid,bot.get('Model'), bot.get('Encoding'))
    provider=bot.get('Engine').lower()

    # HuggingFace uses mutiple responses...
    hfresponses=[]

    # Default connection timeout
    tout=bot.get('Timeout', 60)
    mt=bot.get('MaxTokens', 2048 if provider=='ollama' else 4096)
    model=bot.get('Model')
    encoding=bot.get('Encoding')
    seed=bot.get('Seed', 0)

    # Provider-specific handling
    Tokens=ReadTokens(gid)

    # Adjust persona based on token limit
    WorkingPersona=MaintainTokenLimit(Tokens, persona, max_tokens=mt, engine=provider, model=model, encoding=encoding, HuggingFace=(provider != 'openai'))
    if WorkingPersona is None:
        return PickRandomResponse(bot['TooMuchInformation'])

    if provider=='openai':
       response=GetOpenAI(Tokens['OpenAI'],WorkingPersona,model,bot['freqpenalty'],bot['Temperature'],tout)
    elif provider=='openrouter':
       response=GetOpenRouter(Tokens['OpenRouter'],WorkingPersona,model,bot['freqpenalty'],bot['Temperature'],tout)
    elif provider=='anthropic':
       response=GetAnthropic(Tokens['Anthropic'],WorkingPersona,model,bot['freqpenalty'],bot['Temperature'],tout)
    elif provider=='togetherai':
        response=GetTogetherAI(Tokens['TogetherAI'],WorkingPersona,model,bot['freqpenalty'],bot['Temperature'],tout)
    elif provider=='cohere':
        response=GetCohere(Tokens['Cohere'],WorkingPersona,model,bot['freqpenalty'],bot['Temperature'],tout)
    elif provider=='ollama':
       response=GetOllama(None,WorkingPersona,model,bot['freqpenalty'],bot['Temperature'],tout,seed=seed,mt=mt)
    elif provider=='perplexity':
      response=GetPerplexity(Tokens['Perplexity'],WorkingPersona,model,bot['freqpenalty'],bot['Temperature'],tout)
    elif provider=='huggingface':
        # HuggingFace uses fragmentation for completion methods...
        # Access is free for 1000 requests per day. 1 response could
        # take 8 or more requests to the API.
        while True:
            resp,stop=GetHuggingFace(Tokens['HuggingFace'],WorkingPersona,model,bot['freqpenalty'],bot['Temperature'],tout)
            hfresponses.append(resp)

            # Emulate user typing continue. Count tokens as well...
            WorkingPersona.append({"role":"assistant", "content":resp})
            WorkingPersona.append({"role":"user", "content":"Continue"})
            WorkingPersona=MaintainTokenLimit(Tokens, WorkingPersona, max_tokens=mt, engine=provider, model=model, encoding=encoding, HuggingFace=(provider != 'openai'))
            if WorkingPersona is None:
                return PickRandomResponse(bot['TooMuchInformation'])

            # if finish reason is length, response is fragmented.
            print("HuggingFace fragment:",stop,len(resp))
            if stop!='length' or len(resp)==0:
                break
        response=' '.join(hfresponses).strip()
    # Engine not recognized.
    else:
        return None

    return response

###
### Special features
###

# The `AnagramSolver` function is designed to help users find all possible words that
# can be created by rearranging a set of letters. When a user provides a string of
# letters, this function analyzes those letters and searches through a dictionary of
# valid words to identify which ones can be formed.  Here's how it works: the function
# takes the input letters and generates various combinations and permutations. It then
# checks each combination against a list of known words to see if they match any valid
# entries. The results are organized by word length, allowing users to see which words
# can be created from their given letters.

@function_trapper(None)
def AnagramSolver(fromletters):
    def load_dictionary(file_path):
        # Load dictionary words from a file and return them as a set.
        with open(file_path, 'r') as f:
            words=set(word.strip().lower() for word in f.readlines())
        return words

    def find_valid_words_by_length(letters, dictionary):
        # Find all valid words from combinations and permutations of the input letters
        # grouped by length.

        valid_words={}

        # Generate combinations of letters from 3 to the length of the input
        for length in range(3, len(letters) + 1):
            for combo in itertools.combinations(letters, length):
                # For each combination, generate all permutations
                for perm in itertools.permutations(combo):
                    word=''.join(perm)
                    if word in dictionary:
                        if length not in valid_words:
                            valid_words[length]=set()
                        valid_words[length].add(word)
        # Sort each length's word list alphabetically
        for length in valid_words:
            valid_words[length]=sorted(valid_words[length])
        return valid_words

    # Load letters from the command line argument
    letters=fromletters.lower()

    # Load dictionary from the dictionary.txt file
    dictionary=load_dictionary(AnagramWordList)

    # Find valid words from the provided letters, grouped by length
    valid_words_by_length=find_valid_words_by_length(letters, dictionary)

    # Sorting the dictionary by word length in descending order and printing results
    wstr=''
    for length in sorted(valid_words_by_length.keys(), reverse=True):
        wstr+=f"**Words of length {length}**:\n"
        wstr+=' '.join(valid_words_by_length[length])+'\n\n'
    return wstr

# Decode has symbols

@function_trapper(None)
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

# The `yttags2text` function extracts tags from a YouTube video by
# analyzing its URL to find the video ID. It then uses YouTube's API to
# fetch details about the video, including its tags. If tags are available,
# it returns them as a simple list. If the video can't be found or has no
# tags, it returns a placeholder message. This process ensures the tags are
# easily accessible from any valid YouTube link.

@function_trapper('{[(*VNF*)]}')
def yttags2text(gid,url):
    def extract_video_id(url):
        # Match either a youtu.be or youtube.com URL to extract the video ID
        youtube_regex=r"(?:youtu\.be\/|youtube\.com\/(?:.*v=|.*\/|.*v\/|.*embed\/|.*shorts\/))([a-zA-Z0-9_-]{11})"
        match=re.search(youtube_regex, url)

        if match:
            return match.group(1)
        else:
            return None

    def get_video_tags(video_id):
        # Fetch video details including tags
        try:
            request=youtube.videos().list(
                part="snippet",
                id=video_id
            )
        except Exception as err:
            ErrorLog(f"Broke yttags: {sys.exc_info()[-1].tb_lineno}/{err}")
            return '{[(*VNF*)]}'

        response=request.execute()

        if "items" in response and len(response["items"])>0:
            video_snippet=response["items"][0]["snippet"]
            if "tags" in video_snippet:
                tags=video_snippet["tags"]
                return tags
            else:
                return None
        else:
            return '{[(*VNF*)]}'

    # Create YouTube Object
    Tokens=ReadTokens(gid)
    youtube=build('youtube', 'v3', developerKey=Tokens['YouTube'])

    # Retrieve and display tags
    tags=get_video_tags(extract_video_id(url))

    if isinstance(tags, list):
        return '\n'.join(tags)
    return tags

# The `youtube2text` function takes a YouTube video link, extracts its ID,
# and fetches its transcript. It combines the transcript into a readable
# format and returns it as a simple text summary starting with "Video
# Transcript:".

@function_trapper(None)
def youtube2text(video_url):
    # Extract the video ID from the URL
    #video_id=video_url.split('v=')[1]
    video_id=re.search(r'(v=|be/|embed/|v/|youtu\.be/|\/videos\/|\/shorts\/|\/watch\?v=|\/watch\?si=|\/watch\?.*?&v=)([a-zA-Z0-9_-]{11})',video_url).group(2)

    # Fetch the transcript using the YouTubeTranscriptApi
    transcript_list=youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id)

    # Use the TextFormatter to convert the transcript into plain text
    transcript_text='\n'.join(line['text'] for line in transcript_list)

    return 'Video Transcript: '+transcript_text

# The `PDF2Text` function processes a PDF file and extracts its text
# content. It reads the PDF from a given buffer, retrieves the text from
# all pages, and combines it into a single string prefixed with "PDF
# Content:".

@function_trapper(None)
def PDF2Text(pdf_buffer):
    with pdfplumber.open(io.BytesIO(pdf_buffer)) as pdf:
        text=""
        for page in pdf.pages:
            text+=page.extract_text()
        return 'PDF Content: '+text

# Call ScrapingAnt service to fetch web page

@function_trapper(None)
def ScrapingAnt(gid,url):
    Tokens=ReadTokens(gid)
    if 'ScrapingAnt' not in Tokens:
        return None

    print("Ant:",url)

    try:
        client = Ant.ScrapingAntClient(token=Tokens['ScrapingAnt'])
        result = client.general_request(url)
    except Exception as err:
        print(f"Ant: {err}")
        return None
    return result.content

# The `html2text` function is used to fetch and convert the content of a
# web page into plain text. First, it sets a user agent to mimic a browser
# request to the given URL. If the URL points to a YouTube video, it
# retrieves the video's transcript using the `youtube2text` function. For
# other types of pages, it makes an HTTP request to fetch the HTML content.
# The function handles errors gracefully, such as when a page is not found
# or if there is an issue with the URL. It checks if the content is a PDF
# and converts it to text if it is. Then, it processes the HTML by removing
# the head section, script, and style elements, and strips out other
# unnecessary HTML tags. The result is a cleaned-up, plain-text version of
# the web page, with extra whitespace removed. The function prints the
# length of the content fetched and returns it as a readable string.

@function_trapper(None)
def html2text(gid,url):
    # Set the user agent
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    request=urllib.request.Request(url, headers=headers)

    print("Fetch:",url)

    # Video transcript?
    if 'youtube.com/watch' in url or 'youtu.be/' in url:
        input_text=youtube2text(url)
        return input_text

    # Not a YouTube transcript, Fetch the HTML content from the URL

    html=None
    try:
        with urllib.request.urlopen(request,timeout=60) as response:
            html=response.read()
    except Exception as err:
        html=None

    if not html:
        html=ScrapingAnt(gid,url)
        if not html:
            return None
        # Convert to bytes
        html=html.encode('utf-8',errors='ignore')

    # Check for PDF signature
    if html[:5]=='%PDF-':
        text=PDF2Text(html).strip()
        print("PDF:",len(text),url)
        return text

    # Decoding MUST be done AFTER pdf test
    html=DecodeHashCodes(html.decode('utf-8',errors='ignore'))

    # Remove the entire head section
    html=re.sub(r'<head.*?>.*?</head>', '', html, flags=re.DOTALL)

    # Remove script and style elements
    html=re.sub(r'<(script|style).*?>.*?</\1>', '', html, flags=re.DOTALL)

    # Reduce <a> elements to their text content
    html=re.sub(r'<a[^>]*>(.*?)</a>', r'\1', html, flags=re.DOTALL)

    # Remove all other HTML tags
    text=re.sub(r'<[^>]+>', '', html)

    # Remove extra whitespace
    text=re.sub(r'\s+', ' ', text).strip()

    print("URL:",len(text),url)

    return 'Web Page Content: '+text

###
### Discord support functions
###

# The `DisectMessage` function is designed to capture and log detailed
# information about messages in a Discord server. It collects data such as
# the message's content, author, channel, and timestamp, as well as any
# mentions, reactions, attachments, or embeds. Additionally, it logs any
# special features like stickers, references to other messages, and
# interactive components like buttons or menus. The function ensures that
# no two instances run at the same time by using a lock mechanism, and it
# handles errors gracefully if any details are unavailable. This makes it a
# comprehensive tool for tracking and auditing messages, helping to monitor
# and manage communication within a Discord server.

@function_trapper(None)
def DisectMessage(event,message):
    if DisectLock.acquire(timeout=DisectTimeout):
        # Set up convience variables
        gid=message.guild.id
        channel=str(message.channel)
        uid=str(message.author.id)
        author=message.author
        member=message.guild.get_member(author.id) if message.guild else None
        nickname=member.nick if member and member.nick else author.name

        try:
            # Checking different channel types with isinstance
            if isinstance(message.channel, discord.TextChannel):
                insttype="Text Channel"
            elif isinstance(message.channel, discord.VoiceChannel):
                insttype="Voice Channel"
            elif isinstance(message.channel, discord.Thread):
                insttype="Thread"
            elif isinstance(message.channel, discord.DMChannel):
                insttype="Direct Message"
            elif isinstance(message.channel, discord.CategoryChannel):
                insttype="Category Channel"
            else:
                insttype="Unknown Channel"

            WriteLog(gid,uid,channel,f"Event trigger: {event}")
            WriteLog(gid,uid,channel,f"Message: {message.id}/{message.type}/{insttype}")
            WriteLog(gid,uid,channel,f"Message Timestamp: {message.created_at}/{message.edited_at if message.edited_at else 'Not Edited'}")
            WriteLog(gid,uid,channel,f"Message Pinned: {message.pinned}")
            WriteLog(gid,uid,channel,f"Message Author: {message.author.name}#{message.author.discriminator}/{nickname}/{author.display_name}/{message.author.id} Bot: {message.author.bot}")
            WriteLog(gid,uid,channel,f"Message Channel: {message.channel.name}/{message.channel.id}")
            WriteLog(gid,uid,channel,f"Message Guild: {message.guild.name if message.guild else 'DM'}/{message.guild.id if message.guild else 'DM'}")
            # Check if the message was sent via a webhook
            if message.webhook_id:
                WriteLog(gid,uid,channel,f"Message sent via Webhook ID: {message.webhook_id}")
            # List the users mentioned, if any
            if message.mentions:
                WriteLog(gid,uid,channel,f"Message Mentions: {[str(user) for user in message.mentions]}")
            if message.role_mentions:
                WriteLog(gid,uid,channel,f"Message Mentioned Roles: {[role.name for role in message.role_mentions]}")
            if message.channel_mentions:
                WriteLog(gid,uid,channel,f"Message Mentioned Channels: {[channel.name for channel in message.channel_mentions]}")
            if str(message.content).strip()!='':
                WriteLog(gid,uid,channel,f"Message Content: {message.content}")
            else:
                WriteLog(gid,uid,channel,f"Message Content: Empty content field")
            if message.reactions:
                WriteLog(gid,uid,channel,f"Message Reactions: {[(reaction.emoji, reaction.count) for reaction in message.reactions]}")

            # Log sticker information
            if message.stickers:
                WriteLog(gid,uid, channel, f"Message Stickers: {[{'name': sticker.name, 'id': sticker.id} for sticker in message.stickers]}")

            # Log reference information (for replies)
            if message.reference:
                ref=message.reference
                WriteLog(gid,uid, channel, f"Message is a Reply to: {ref.message_id} in Channel: {ref.channel_id} of Guild: {ref.guild_id}")

            # Log details about each embed
            if message.embeds:
                WriteLog(gid,uid,channel,f"Message Embeds: {len(message.embeds)} embeds")
                for index, embed in enumerate(message.embeds):
                    WriteLog(gid,uid, channel, f"Embed {index + 1} Title: {embed.title}")
                    WriteLog(gid,uid, channel, f"Embed {index + 1} Type: {embed.type}")
                    WriteLog(gid,uid, channel, f"Embed {index + 1} Description: {embed.description}")
                    WriteLog(gid,uid, channel, f"Embed {index + 1} URL: {embed.url}")
                    WriteLog(gid,uid, channel, f"Embed {index + 1} Timestamp: {embed.timestamp}")
                    WriteLog(gid,uid, channel, f"Embed {index + 1} Color: {embed.color}")
                    WriteLog(gid,uid, channel, f"Embed {index + 1} Footer: {embed.footer.text if embed.footer else 'None'}")
                    WriteLog(gid,uid, channel, f"Embed {index + 1} Image: {embed.image.url if embed.image else 'None'}")
                    WriteLog(gid,uid, channel, f"Embed {index + 1} Thumbnail: {embed.thumbnail.url if embed.thumbnail else 'None'}")
                    WriteLog(gid,uid, channel, f"Embed {index + 1} Author: {embed.author.name if embed.author else 'None'}")
                    WriteLog(gid,uid, channel, f"Embed {index + 1} Fields: {[{'name': field.name, 'value': field.value} for field in embed.fields]}")

            # Log detailed information about each attachment
            if message.attachments:
                WriteLog(gid,uid,channel,f"Message Attachments: {[attachment.url for attachment in message.attachments]}")
                for index, attachment in enumerate(message.attachments):
                    WriteLog(gid,uid, channel, f"Attachment {index + 1} Filename: {attachment.filename}")
                    WriteLog(gid,uid, channel, f"Attachment {index + 1} Size: {attachment.size} bytes")
                    WriteLog(gid,uid, channel, f"Attachment {index + 1} URL: {attachment.url}")
                    WriteLog(gid,uid, channel, f"Attachment {index + 1} Proxy URL: {attachment.proxy_url}")
                    WriteLog(gid,uid, channel, f"Attachment {index + 1} Height: {attachment.height if attachment.height else 'N/A'}")
                    WriteLog(gid,uid, channel, f"Attachment {index + 1} Width: {attachment.width if attachment.width else 'N/A'}")

            # Log message components (if any)
            if message.components:
                WriteLog(gid,uid, channel, f"Message Components: {[{'type': component.type, 'custom_id': component.custom_id} for component in message.components]}")
            WriteLog(gid,uid,channel,f"{'-'*80}")
        except AttributeError as e:
            WriteLog(gid,uid,channel,f"Error accessing message attributes: {e}")
        DisectLock.release()

# This function handles sending a response via a webhook in Discord,
# including the possibility of auto-deleting messages after a set time. It
# first checks if the bot is operating in a specific channel or system
# channel, and retrieves existing webhooks from that channel. It then
# ensures any existing "Companion Temporary Webhook" is deleted before
# creating a new one. The response, which may include text and an optional
# embed, is sent via the webhook. If the response exceeds 1900 characters,
# it's broken up into smaller parts. The function also queues messages for
# deletion after a specified time, ensuring that the deletion lock is
# respected. Once the message is sent and queued for deletion (if
# applicable), the webhook is deleted.

@function_trapper(None)
async def send_response(bot,message,response,embed=None,delete=None,member=None):
    global DeleteList
    whmsg=[]

    if bot['Channel']==None:
        webhooks=await member.guild.system_channel.webhooks()
    else:
        # If its a thread, get the parent channel
        pchannel=message.channel
        if isinstance(message.channel,discord.Thread):
            pchannel=message.channel.parent
        webhooks=await pchannel.webhooks()

    # Delete all webhooks with the name "Companion Temporary Webhook"
    for webhook in webhooks:
        if webhook.name=='Companion Temporary Webhook':
            await webhook.delete()

    threadID=None
    # Create a new webhook
    if bot['Channel']==None:
        syschannel=member.guild.system_channel
        webhook=await syschannel.create_webhook(name='Companion Temporary Webhook')
        author=None
    else:
        # Handle thread issues, get parent channel
        pchannel=message.channel
        if isinstance(message.channel,discord.Thread):
            pchannel=message.channel.parent
        webhook=await pchannel.create_webhook(name='Companion Temporary Webhook')
        # Get the name of the person this message is going to
        author=str(message.author.mention)
        if isinstance(message.channel,discord.Thread):
            threadID=message.channel # Actual thread ID

    # If the message is less then 1900 characters, just send it with a reply.
    if embed!=None:
        if author!=None:
            x1=f"{author}"
        else:
            x1=''
        if threadID:
            wm=await webhook.send(content=x1,embed=embed,username=bot['BotName'],avatar_url=bot['Avatar'],thread=threadID,wait=True)
        else:
            wm=await webhook.send(content=x1,embed=embed,username=bot['BotName'],avatar_url=bot['Avatar'],wait=True)
        whmsg.append(wm)
        await asyncio.sleep(1.1)
    elif len(response)<=1900:
        if author!=None:
            x1=f"{author} {response}"
        else:
            x1=f"{response}"
        # sending with and without threads must be separate
        if threadID:
            wm=await webhook.send(content=x1,username=bot['BotName'],avatar_url=bot['Avatar'],thread=threadID,wait=True)
        else:
            wm=await webhook.send(content=x1,username=bot['BotName'],avatar_url=bot['Avatar'],wait=True)
        whmsg.append(wm)
        await asyncio.sleep(1.1)
    else:

        # Break this up into multiple messages. Discord does NOT allow
        # direct reply with multiple message parts.

        x1=f"{author} {response}"
        l=len(x1)
        while l>1900:
            # We need to deal with the possibility that a \n doesn't exist in the input data.
            pmax=1900
            # Look for new line first
            p=x1.rfind('\n',0,pmax)
            if p==-1:
                # Look for a period  Separate at a sentence
                p=x1.rfind('.',0,pmax)
                if p==-1:
                    # Look for a space  Separate at a word
                    p=x1.rfind(' ',0,pmax)
                    if p==-1:
                        # Brute split
                        pmax=1900
            if len(x1[:p])>0:
                if threadID:
                    wm=await webhook.send(content=x1[:p].strip(),username=bot['BotName'],avatar_url=bot['Avatar'],thread=threadID,wait=True)
                else:
                    wm=await webhook.send(content=x1[:p].strip(),username=bot['BotName'],avatar_url=bot['Avatar'],wait=True)
                whmsg.append(wm)
                await asyncio.sleep(1.1)
            if x1[p]=='.' or x1[p]==' ':
                p+=1
            x1=x1[p:].strip()
            l=len(x1)
        if l>0:
            if threadID:
                wm=await webhook.send(content=x1.strip(),username=bot['BotName'],avatar_url=bot['Avatar'],thread=threadID,wait=True)
            else:
                wm=await webhook.send(content=x1.strip(),username=bot['BotName'],avatar_url=bot['Avatar'],wait=True)
                await asyncio.sleep(1.1)
            whmsg.append(wm)

    # Queue autodelete messages. Responses can be multiple messages.
    if delete!=None:
        if DeleteLock.acquire(timeout=DeleteTimeout):
            for whm in whmsg:
                DeleteList.append({"gid": whm.guild.id,"cid":whm.channel.id,"mid":whm.id,"Expires":whm.created_at.timestamp()+delete } )
            DeleteLock.release()
        else:
            ErrorLog("Lock failed SR autodelete")
    # Delete the webhook
    await webhook.delete()

# This function checks if a "ModerationArea" is specified in the bot's
# settings. If it exists, the function iterates through the guild's
# channels to find a text channel matching the name of the
# "ModerationArea." Once the correct channel is found, it sends the
# provided text message to that channel. The function stops once the
# message is sent, ensuring that only one notification is made.

@function_trapper(None)
async def ModeratorNotify(bot,guild,text):
    # If there is a moderator area, send a message to it.
    if 'ModerationArea' in bot:
        for channel in guild.channels:
            if isinstance(channel,discord.TextChannel) and channel.name==bot['ModerationArea']:
                await channel.send(text)
                break

# This function ensures that the server has a proper "owner" role and a
# secure "companion-administration" channel for server management. First,
# it checks if the "owner" role exists, and if not, it creates one with
# specific permissions and assigns it to the server owner. Next, the
# function checks for the existence of a "companion-administration"
# channel. If the channel doesn’t exist, it creates the channel with
# restricted permissions for most users, allowing only the owner role to
# access and manage it. If the channel already exists, it ensures the
# security settings are correct. The function returns the channel object
# for further use.

@function_trapper(None)
async def VerifyCompanionAdministration(guild):
    # Create the owner role if not present
    orole=discord.utils.get(guild.roles,name='owner')
    if not orole:
        # create the owner role
        orole=await guild.create_role(name='owner', \
            permissions=discord.Permissions(read_messages=True,send_messages=True), \
            mentionable=False,color=discord.Color(0xFF0000))

        # assign it to thew owner
        if orole not in guild.owner.roles:
            await guild.owner.add_roles(orole)

        # Push it to the highest position
        # await guild.edit_role_positions(positions={orole: len(guild.roles)-1})
    # else:
        # Push it to the highest position
        # if orole!=guild.roles[-1]:
        #     await guild.edit_role_positions(positions={orole: len(guild.roles)-1})

    # Check for the 'companion-administration' channel
    channel=discord.utils.get(guild.text_channels, name='companion-administration')

    # Set up default security
    overwrites={ guild.default_role: discord.PermissionOverwrite( view_channel=False,
                    send_messages=False,read_messages=False,read_message_history=False,
                    mention_everyone=False,add_reactions=False,attach_files=False,
                    send_tts_messages=False),
                 orole: discord.PermissionOverwrite(read_messages=True,read_message_history=True,
                    send_messages=True) }

    # If the channel does not exist, create it
    if not channel:
        if orole:
            # Create the channel and set permissions
            channel=await guild.create_text_channel('companion-administration', \
                overwrites=overwrites, position=len(guild.channels), \
                topic='This channel is for Companion administration.')
        else:
            # Owner role does not exist, should never happen.
            return None
    else:
        # Force channel to proper security settings
        channel.edit(overwrites=overwrites)
    return channel

# Verify all required permissions

@function_trapper
def VerifyGuildPermissions(guild):
    # List of non-voice-related permissions
    non_voice_permissions = [
        "create_instant_invite", "kick_members", "ban_members", "administrator",
        "manage_channels", "manage_guild", "add_reactions", "view_audit_log",
        "view_channel", "manage_roles", "manage_permissions", "manage_webhooks",
        "manage_emojis_and_stickers", "send_messages", "send_tts_messages",
        "manage_messages", "embed_links", "attach_files", "read_message_history",
        "mention_everyone", "manage_threads", "use_embedded_activities",
        "send_messages_in_threads", "use_application_commands", "manage_events"
    ]

    # Get the bot's current guild permissions
    bot_permissions = guild.me.guild_permissions

    # Find missing permissions
    missing_permissions = [perm for perm in non_voice_permissions if not getattr(bot_permissions, perm)]

    # Print missing permissions if any
    if missing_permissions:
        print(f"{guild.id} Missing permissions:")
        for perm in missing_permissions:
            print(f"- {perm}")
        return False  # Not all permissions are enabled

    return True  # All permissions are enabled

# This function checks the security setup of a Discord server to ensure
# it’s well-protected and highlights any weak points. It verifies if an
# "owner" role exists, has the highest permissions, and is assigned to the
# server owner. It examines key settings, such as strict account
# verification for new members, explicit content filtering, two-factor
# authentication, and restrictions on the `@everyone` role to prevent spam
# or abuse. If issues are found, it sends detailed recommendations to an
# admin channel, explaining what needs to be fixed and why. If everything
# is secure, it reports a successful audit, and it can run automatically
# for ongoing safety monitoring.

@function_trapper(None)
async def SecurityAudit(guild=None,message=None,ShowResults=False,auto=False):
    # failsafe catch
    if guild==None and message==None:
        return

    # Make sure we have a guild structure
    if not guild and message:
        guild=message.guild

    # Create the CompanionAdministration area (if not exist) and get the channel
    admin=await VerifyCompanionAdministration(guild)

    PermChk=VerifyGuildPermissions(guild)

    # Start with the automatic setting. Results will be forced if audit fails
    FailedAudit=False
    AuditOwnerRole=False
    IsHighestPos=False
    IsOwnerInRole=False
    GuildVerification=False
    ExplicitContent=False
    MFAlevel=False
    IsEveryoneMention=False
    IsEveryoneExternalApps=False

    orole=discord.utils.get(guild.roles,name='owner')
    if orole:
        AuditOwnerRole=True
        hrp=max(role.position for role in guild.roles)  # Get the highest role position
        if orole.position==hrp:
            IsHighestPos=True
        else:
            FailedAudit=True

        urole=discord.utils.get(guild.owner.roles,name='owner')
        if urole:
            IsOwnerInRole=True
        else:
            FailedAudit=True
    else:
        FailedAudit=True

    if str(guild.verification_level.name)=='highest':
        GuildVerification=True
    else:
        FailedAudit=True

    if str(guild.explicit_content_filter)=='all_members':
        ExplicitContent=True
    else:
        FailedAudit=True

    if str(guild.mfa_level)=='MFALevel.require_2fa':
        MFAlevel=True
    else:
        FailedAudit=True

    # Check permissions for @everyone role
    if not guild.default_role.permissions.mention_everyone:
        IsEveryoneMention=True
    else:
        FailedAudit=True

    # Check permissions for @everyone external APPs
    if not guild.default_role.permissions.use_embedded_activities:
        IsEveryoneExternalApps=True
    else:
        FailedAudit=True

    # Report the results
    if ShowResults or FailedAudit:
        await admin.send(f"Guild: {guild.name} ({guild.id})")
        await admin.send(f"Owner: {guild.owner} ({guild.owner.id})")
        if not PermChk:
            await admin.send(f"This guild does NOT have the proper permissions set to function.")
        if not AuditOwnerRole:
            await admin.send(f"The `owner` role does not exist. A dedicated guild owner role is vital for securing control, ensuring only trusted hands hold top permissions. This role acts as the ultimate safeguard against unauthorized changes, breaches, and ensures accountability in managing server integrity.")
        if not IsHighestPos:
            await admin.send(f"The `owner` role does NOT have the highet position in the role list. Please visit the [Discord Role Management](https://support.discord.com/hc/en-us/articles/214836687-Role-Management-101) for more details.")
        if not IsOwnerInRole:
            await admin.send(f"{guild.owner} is NOT in the `owner` role.")
        if not GuildVerification:
            await admin.send(f"this guild is NOT protected with the highest verification level.  Please visit the [Discord Verification Levels](https://support.discord.com/hc/en-us/articles/216679607-Verification-Levels) for more details.")
        if not ExplicitContent:
            await admin.send(f"Sensitive content filter is NOT set to the hight level. Please visit the [Sensitive Content Filter](https://support.discord.com/hc/en-us/articles/18210995019671-Discord-Sensitive-Content-Filters) for more details.")
        if not MFAlevel:
            await admin.send(f"This guild is NOT protected by two factor authentication. Please visit the [Discord Multifactor Authentication](https://support.discord.com/hc/en-us/articles/219576828-Setting-up-Multi-Factor-Authentication) for more details.")
        if not IsEveryoneMention:
            await admin.send(f"Allowing the `@everyone` role to ping everyone opens the door to spam and raid abuse, as any member could trigger mass notifications, disrupting user experience and overwhelming the server. This permission should always be restricted to prevent chaos and maintain a controlled, respectful communication environment. Please visit [Discord Role Management](https://support.discord.com/hc/en-us/articles/214836687-Role-Management-101) for more details.")
        if not IsEveryoneExternalApps:
            await admin.send(f"Allowing the `Use External Apps` permission for the `@everyone` role opens the door for malicious users to exploit embedded activities, such as inviting members to inappropriate or harmful third-party apps. This can be a vector for server raids, as attackers can coordinate disruptions, share harmful content, or lure members into unsafe interactions, undermining server security and trust.")

        if ShowResults:
            await admin.send(f"Current Members: {guild.member_count}")
        if FailedAudit:
            await admin.send(f"**This server has FAILED the security audit.** Please correct the above issues as quickly as possible.")
            if auto:
                await admin.send(f"This audit was performed as a part of Companion's automated maintenance. You will continue to receive these messages as long as the above issues remain uncorrected.")
            await admin.send(f"Thank you.")
        else:
            if ShowResults:
                await admin.send(f"**This server has PASSED the security audit.**")

# This function safeguards a Discord server by identifying and addressing
# cases where a new member attempts to impersonate the server owner. It
# compares the username and display name of the incoming member with those
# of the owner, and if a match is detected, it logs the incident, notifies
# moderators via a configured companion bot (if available), and promptly
# kicks the impersonator from the server with a clear reason. By
# automatically enforcing these measures, the function helps maintain the
# server’s integrity, ensuring a secure and trustworthy environment for its
# members.

@function_trapper(False)
async def ImposterAmoungUs(guild, member):
    # Retrieve the "owner" role and members
    owner_role=discord.utils.get(guild.roles, name="owner")
    owner_members=owner_role.members if owner_role else [guild.owner]

    # Standardize the new member's username and display name for comparison
    member_name=member.name.lower()
    member_nick=member.display_name.lower()

    # Check if the new member has the same username or display name as any "owner" role member
    for owner in owner_members:
        owner_name=owner.name.lower()
        owner_nick=owner.display_name.lower()

        if member != owner and (member_name==owner_name or member_nick==owner_nick):
            # Log and notify about impersonation
            txt=f"{member}/{member.id}/{member.display_name} kicked for impersonating an owner."
            ErrorLog(txt)
            bot=GetCompanionPersona(member.guild.id, None, Welcome=True)
            if bot is not None:
                await ModeratorNotify(bot, member.guild, txt)

            # Kick the impersonator
            await member.kick(reason="Impersonating a server owner")
            return True
    return False

# This function acts as a bypass for regular system measures, granting special
# permissions to **trusted** users, roles, or channels listed in a whitelist. It
# checks if a user’s ID, their role name, or the channel name matches an entry in
# the bot’s predefined whitelist. If a match is found, it allows the action without
# enforcing standard restrictions. This ensures trusted individuals or channels can
# operate freely, even when other controls are in place.

def CheckWhitelist(bot,whitelist,message=None,user=None):
    if message==None and author==None:
        return False

    if user==None:
        author=message.author
    else:
        author=user

    # Check whitelist
    if whitelist not in bot:
        return False

    wList=bot[whitelist].split(',')
    for uc in wList:
        uc=uc.lower().strip()
        # Is this a whitelisted user ID
        if uc[0]=='!':
            if uc[1:]==str(author.id):
                return True
        # Is this a whitelisted user role.
        if uc[0]=='@':
            for role in author.roles:
                if role.name==uc[1:]:
                    return True
            return False
        # Is this a white listed channel
        if uc[0]=='#' and message!=None:
            if uc[1:]==message.channel.name.lower().strip():
                return True

    return False

# The `IsPIIDetected` function is an asynchronous handler that checks for
# personally identifiable information (PII) in a message sent in a Discord
# server. It first verifies if PII moderation is enabled by checking a bot
# configuration. If a whitelist is provided (`PIIWhitelist`), it checks
# whether the message sender or the channel matches any whitelisted user or
# channel names. If the sender or channel is whitelisted, the function
# skips the PII check. If not, the function uses the `DetectPII` function
# to scan the message content for sensitive information like names,
# addresses, or other private details. If PII is detected, the function
# notifies the server moderators about the violation, including the
# author's name, ID, channel, and the content of the message. If the
# message contains PII, it sends a predefined response (from the
# `PickRandomResponse` function), deletes the message, and prevents further
# action from the bot, unless the sender is a bot. The function ensures
# that any potential violation is swiftly dealt with while respecting the
# settings for whitelisted users and channels.

@function_trapper(False)
async def IsPIIDetected(bot,message):
    if bot['PIIModeration'].lower()!='no' and os.path.exists(bot['PII'])==True:
        if CheckWhitelist(bot,'PIIWhitelist',message):
            return False

        HasPII=await DetectPII(message.guild.id,bot,message.content)
        if HasPII:
            await ModeratorNotify(bot,message.guild,f"PII detected: {message.author.name}/{message.author.id} in {message.channel.name}, {HasPII}")
            await ModeratorNotify(bot,message.guild,f"{message.content}")
            author=str(message.author.mention)
            # If its a bot, it doesn't deserve a response
            if not message.author.bot:
                await send_response(bot,message,PickRandomResponse(bot['PII']),delete=300)
            await message.delete()
            return True

    return False

###
### Background Tasks
###

# This function conducts a routine automated security audit for all the
# servers the bot is a part of, running every 23 hours. For each server
# (`guild`), it invokes a `SecurityAudit` function to check for potential
# security vulnerabilities or issues, with specific parameters to
# customize the audit process. The use of `await asyncio.sleep(0)` ensures
# smooth operation without blocking other asynchronous tasks. This helps
# maintain server security and ensures compliance with any predefined
# security protocols.

@tasks.loop(hours=23)
@function_trapper
async def AutomatedSecurityAudit():
    for guild in client.guilds:
        await SecurityAudit(guild,None,False,True)
        await asyncio.sleep(0)

# This function performs routine maintenance to manage memory files for
# servers, ensuring they don’t exceed retention limits. It operates on a
# 23-hour loop, reviewing configuration files for each server to determine
# the maximum allowable age for memory files, defined in days and
# converted to seconds. It then scans the memory file directory,
# identifies files older than the specified limit, and deletes them. The
# process includes error handling for damaged configuration files and
# utilizes asynchronous operations (`asyncio.sleep(0)`) to maintain
# responsiveness during execution. This keeps server memory storage
# optimized and prevents excessive accumulation of outdated data.

@tasks.loop(hours=17)
@function_trapper
async def MemoryMaintenance():
    # Get server CFg files
    cfg_files=[]
    for dirpath, _, filenames in os.walk(ConfigStorage):
        for file in filenames:
            if file.endswith('.cfg'):
                cfg_files.append(os.path.join(dirpath, file))

    # Read server CFG file and get MaxMemory
    for cfg in cfg_files:
        try:
            Config=json.loads(jsonFilter(ReadFile(cfg)))
            await asyncio.sleep(0)
        except Exception as err:
            ErrorLog(f"{cfg} damaged: {sys.exc_info()[-1].tb_lineno}/{err}")
            continue

        if 'MaxMemory' not in Config:
            continue

        # Get how long to keep old memory files in seconds
        MaxMemory=float(Config['MaxMemory'])*86400
        sid=cfg.split('/')[5].split('.')[0]
        dn=f"{MemoryStorage}/{sid}"

        # Ignore cfg files that aren't guild ids
        if not os.path.exists(dn):
            continue

        # Get list of .memory files for this server

        mfiles=[]
        for dirpath, _, filenames in os.walk(dn):
            for file in filenames:
                if file.endswith('.memory') or file.endswith('.escore'):
                    mfiles.append(os.path.join(dirpath, file))

        # Now check the memory files for age. If the file is OLDER then
        # MaxMemory, delete it.

        ct=time.time()
        for mf in mfiles:
            factor=1
            lmt=os.path.getmtime(mf)
            if mf.endswith('.escore'):
                factor=5
            if ct-lmt>(MaxMemory*factor):
                os.remove(mf)
            await asyncio.sleep(0)

# Handle autodelete messages. It is important to consider that when this
# is executed, the original message may not exist. We have to fetch
# message from the guild, channel, and message IDs.

# Optime this similar to the active_join strategy.

@tasks.loop(seconds=3)
@function_trapper
async def autodelete_messages():
    global DeleteList

    if DeleteLock.acquire(timeout=DeleteTimeout):
        now=time.time()
        if DeleteList:
            for msg in list(DeleteList):
                if now>msg['Expires']:
                    guild=client.get_guild(msg['gid'])              # Guild
                    channel=guild.get_channel(msg['cid'])           # Channel
                    message=await channel.fetch_message(msg['mid']) # Message
                    DeleteList.remove(msg)
                    try:
                        await message.delete()
                    except Exception as err:
                        # Something broke, most likely message already deleted.
                        pass
        DeleteLock.release()
    else:
        ErrorLog("Lock failed ADM")

# This function manages a circular queue of guilds in a thread-safe manner,
# ensuring orderly rotation and access. By acquiring a global lock
# (`GuildQueueLock`) within a defined timeout, it extracts the first guild
# in the queue, moves it to the end, and then releases the lock to allow
# other processes access. If the lock cannot be acquired within the
# timeout, the function safely exits and returns `None`. This mechanism
# facilitates balanced and sequential processing of guild-related tasks
# while avoiding conflicts or race conditions in a multi-threaded
# environment.

# Adapt this technique to channels, to prevent a busy channel from monopolizing
# resources.

@function_trapper(None)
def RotateGuildQueue():
    global GuildQueueLock
    global GuildQueue

    # Add the guild to the circular guild queue
    if GuildQueueLock.acquire(timeout=GuildQueueTimeout):
        top=GuildQueue.popleft()
        GuildQueue.append(top)
        GuildQueueLock.release()
        return top
    return None

# This asynchronous function, running every X seconds, manages response
# data processing across multiple guilds in a controlled and efficient
# manner. It rotates through a global queue of guilds using a thread-safe
# mechanism to ensure fair access. For each guild, it checks if processing
# ("babbling") is already locked, skipping it if busy. If available, it
# attempts to retrieve the next request in a thread-safe way. When a
# request is found, the function ensures that only one AI-related task per
# guild is handled at a time using a per-guild lock. It processes the
# request through `HandleOneMessage`, gracefully handling exceptions by
# reinserting failed requests back into the queue. The system leverages
# multiple locking mechanisms (`BabbleLock`, `ResponseLock`,
# `GuildQueueLock`) to maintain robust concurrency control while balancing
# workloads among guilds.

@tasks.loop(seconds=3)
@function_trapper
async def update_response_data():
    global BabbleLock
    global ResponseLock
    global GuildQueueLock
    global GuildQueue

    guild=RotateGuildQueue()
    if guild==None:
        ErrorLog("Guild rotation failed.")
        return

    # Check to see is the guild is available to babble
    if guild.id in BabbleLock and BabbleLock[guild.id].locked():
        return

###> Add chanel rotation per guild. Rotate channel queue.

    # Pull the next request

    request=None
    if ResponseLock.acquire(timeout=ResponseTimeout):
        request=GetNextRequest(guild.id)
        ResponseLock.release()

    # Only 1 AI request at a time

    if request!=None:
        # Create guild lock for babbling
        if guild.id not in BabbleLock:
            BabbleLock[guild.id]=threading.Lock()

        if BabbleLock[guild.id].acquire(timeout=BabbleTimeout):
            try:
                await HandleOneMessage(request)
            except Exception as err:
                # It broke, try to put the request back in the queue
                if ResponseLock.acquire(timeout=ResponseTimeout):
                    PutNextRequest(guild.id,request)
                    ResponseLock.release()
                ErrorLog(f"Broke: {sys.exc_info()[-1].tb_lineno}/{str(err)}")
            BabbleLock[guild.id].release()
        else:
            # Couldn't get the lock, try to put the request back in the queue
            if ResponseLock.acquire(timeout=ResponseTimeout):
                PutNextRequest(guild.id,request)
                ResponseLock.release()

# The `track_ActiveUsers` function, running every X seconds, manages and
# tracks active users across channels and guilds by sweeping through two
# main data structures: `ActiveUsers` and `ActiveJoins`. It checks each
# user's activity in channels, and if the time since their last recorded
# activity exceeds the `SlowwModeCooldown`, it reduces their activity
# factor. If the factor drops below 1, the user is removed from the
# channel’s active list; otherwise, the timestamp is updated. Similarly,
# for users in the `ActiveJoins` list, if the elapsed time since their
# join exceeds the cooldown, they are removed. This process ensures that
# user activity is efficiently tracked and cleaned up, maintaining an
# accurate state while respecting cooldowns for both channels and guilds.

@tasks.loop(seconds=60)
@function_trapper
async def track_ActiveUsers():
    global ActiveUsers
    global ActiveJoins

    current_time=time.time()
    # Sweep every channel
    for ac in list(ActiveUsers):
        # Sweep users in a channel
        for au in list(ActiveUsers[ac]):
            # Check time added againt expiration
            if (current_time-au[1])>SlowwModeCooldown:
                # reduce factor
                au[2]-=1
                if au[2]<1:
                    ActiveUsers[ac].remove(au)
                else:
                    au[1]=time.time()

    # Sweep all guilds
    for ag in list(ActiveJoins):
        # Sweep all users in join list
        for au in list(ActiveJoins[ag]):
            if (current_time-au[1])>SlowwModeCooldown:
                ActiveJoins[ag].remove(au)

###
### Discord event functions
###

# Doesn't exist in API
"""
@client.event
@function_trapper
async def on_member_kick(guild, member):
    txt=f"{member}/{member.id}/{member.display_name} kicked."
    ErrorLog(txt)
    bot=GetCompanionPersona(guild.id, None, Welcome=True)
    if bot is not None:
        await ModeratorNotify(bot, guild, txt)
"""

@client.event
@function_trapper
async def on_member_ban(guild, member):
    txt=f"{member}/{member.id}/{member.display_name} banned."
    ErrorLog(txt)
    bot=GetCompanionPersona(guild.id, None, Welcome=True)
    if bot is not None:
        await ModeratorNotify(bot, guild, txt)

@client.event
@function_trapper
async def on_member_unban(guild, member):
    txt=f"{member}/{member.id}/{member.display_name} unbanned."
    ErrorLog(txt)
    bot=GetCompanionPersona(guild.id, None, Welcome=True)
    if bot is not None:
        await ModeratorNotify(bot, guild, txt)

# The `on_message_edit` event handles edited messages in Discord, checking
# for potential moderation issues such as leetspeak attempts, vulgarity, and
# malicious edits aimed at extracting personal information like age. Upon
# detecting an edit, it first verifies that the content has indeed changed
# before proceeding. It then checks if the message is in a thread and
# adjusts accordingly. If the message involves a bot persona, it logs the
# changes and proceeds with moderation. The function scans the edited
# message for specific "leet" words that might indicate an attempt to bypass
# filters or ask for personal details like age. Additionally, it checks for
# vulgar language, comparing the message content with a predictive model. If
# vulgarity is found and the bot is set to block it, the message is deleted,
# and the user is notified. If leetspeak is detected, the bot notifies
# moderators with details of the edit, and an embedded message is created
# for transparency. One of the more insidious attacks the bot counters
# involves an attacker initially asking an innocent question, like "how many
# sides to an octagon?" The victim may respond "8," and then the attacker
# edits the message to read, "How old are you?" or "What is your age?" The
# attacker takes a screenshot of the edited message, which could be used to
# falsely accuse the victim of violating Discord's age restrictions, risking
# a permanent ban. This malicious tactic exploits the fact that Discord's
# age policy is strictly enforced. A major vulnerability in this system
# exists when a message is posted before the bot is loaded and then edited
# afterward; the bot will not receive the edit notification, creating a
# loophole that only Discord can fix. To combat this, the bot aims to delete
# the original message, preventing such malicious actions. If the message
# passes all checks, no action is taken.

@client.event
@function_trapper
async def on_message_edit(before, after):
    # Leet list deritives for trying to get someone's age.

    lside=['ask','how','is','are','your','you','when','whens','what','whats','wut','wuts','was','tell','ur','u','r']
    rside=['over','old','young','under','teen','tween','tweenie','born','date','year','yr','age','birth','birthed','birthdate','birthday','bday','bd','born']

    # Search for word in list
    def CheckWordList(side,sampleText):
        Found=False
        for w in range(len(side)):
            if side[w] in sampleText:
                Found=True
                break
        return Found,side[w]

    # Don't do any processing if the content between before and after are
    # identical.

    if after.content==before.content:
        return

    # If this is a thread, get the parent channel
    pchannel=after.channel
    nsfw=None
    if isinstance(after.channel,discord.Thread):
        pchannel=after.channel.parent
        nsfw=after.channel.parent.nsfw
    else:
        nsfw=after.channel.nsfw

    channel=str(pchannel)
    uid=str(after.author.id)
    bot=GetCompanionPersona(after.guild.id,channel,nsfw)
    if bot==None:
        return

    # Log everything
    if bot['AutoLogging'].lower()!='no':
        DisectMessage("Message edited (before)",before)
        DisectMessage("Message edited (after)",after)

    # Manage automated moderation
    if bot['AutoModeration'].lower()=='no':
        return

    if CheckWhitelist(bot,'AgeLEETWhitelist',after):
        return

    # Build leet lists

    leftside=BuildLeetList(lside)
    rightside=BuildLeetList(rside)

    sampleText=StripPunctuation(after.content.lower())

    leftFound,leftWord=CheckWordList(leftside,sampleText)
    rightFound,rightWord=CheckWordList(rightside,sampleText)

    # NEED a global moderation switch
    # Check for vulgarity in the edited response

    # This could be a problem at the global level of a server, where
    # partial moderation may be desired, vs an absolute approach.

    if bot['AutoModeration'].lower()!='no' \
    and os.path.exists(bot['Vulgarity']) \
    and bot['AllowVulgarity'].lower()!='yes' \
    and not nsfw:
        if bool(pc.predict([ after.content ]))==True:
            await ModeratorNotify(bot,after.guild,f"{after.author.name}/{after.author.id} chastized for vulgarity in {after.channel.name}")
            await send_response(bot,after,PickRandomResponse(bot['Vulgarity']),delete=57)
            try: # delete the offending message
                await after.delete()
            except:
                pass
            return

    if leftFound and rightFound:
        ageMatch=await AIClassifier(after.guild.id,bot['AgeLEETClassifier'],after.content)
        if ageMatch.lower()=='no':
            return

        await ModeratorNotify(bot,after.guild,f"LEET words/Malicious edit possibility: {after.author.name}/{after.author.id} in {after.channel.name} matching {leftWord}/{rightWord}")
        # This seems to be a better way to ruin the attacker's plan
        embed=discord.Embed(
            title='Message edited',
            description=f'UID: {uid}\nAuthor: {after.author}\n\nBefore edit:\n\n{before.content}\n\nAfter edit:\n\n{after.content}\n\n',
            color=discord.Color.red() )
#        try: # delete the edited message
#            await after.delete()
#        except:
#            pass
        await send_response(bot,after,None,embed=embed)
        return

# The `on_message_delete` event is triggered when a message is deleted in a
# Discord channel. It first determines which bot persona is responsible for
# handling the message by checking the channel, user ID, and the message
# content. If a bot persona is found for the given guild and channel, it
# proceeds to log the deleted message, provided that automatic logging is
# enabled in the bot's configuration. The message is dissected and logged
# for audit purposes, allowing administrators or the bot itself to track
# deleted messages for transparency and moderation purposes. If no relevant
# bot persona is found, no action is taken.

@client.event
@function_trapper
async def on_message_delete(message):
    # Figure out which persona is calling the shots.
    channel=str(message.channel)
    uid=str(message.author.id)
    bot=GetCompanionPersona(message.guild.id,channel,message,message.channel.nsfw)
    if bot==None:
        return

    # Log everything
    if bot['AutoLogging'].lower()!='no':
        DisectMessage("Deleted message",message)

# The `on_member_update` event is triggered when a member's profile
# information, such as their username, nickname, or roles, is updated. It
# compares the values of the member's name, nickname, and roles before and
# after the update to detect any changes. The function includes an
# impersonation detection mechanism, calling the `ImposterAmongUs` function to
# check if the member's profile resembles that of a server owner or a prominent
# figure in the community. If impersonation is detected, further processing is
# halted. Additionally, when roles are added or removed, the bot notifies the
# moderators about the changes and provides a list of all the roles the member
# holds, ensuring the moderators are aware of any updates to the member's
# permissions.

@client.event
@function_trapper
async def on_member_update(before, after):
    # Impersonation detection
    if await ImposterAmoungUs(after.guild,after):
        return

    # Check if the roles have changed
    if before.roles != after.roles:
        bot=GetCompanionPersona(after.guild.id,None,Welcome=True)
        if bot==None:
            return

        added_roles=[role for role in after.roles if role not in before.roles]
        removed_roles=[role for role in before.roles if role not in after.roles]

        if added_roles:
            for role in added_roles:
                await ModeratorNotify(bot,after.guild,f"{after.name} was given the role: {role.name}")

        if removed_roles:
            for role in removed_roles:
                await ModeratorNotify(bot,after.guild,f"{after.name} lost the role: {role.name}")

        # Print all roles that the user has after the update
        role_names=', '.join([role.name for role in after.roles])
        await ModeratorNotify(bot,after.guild,f"{after.name} now has the following roles: {role_names}")

# The `on_member_join` event is triggered whenever a new member joins a
# guild. It tracks new member joins by recording the member's ID and the
# current time in the `ActiveJoins` dictionary for the respective guild.
# If a companion bot is set for the guild (with the `Welcome=True` flag),
# it checks whether the bot is available and logs a welcome message if
# `AutoLogging` is enabled. Additionally, the event includes an
# impersonation detection check using the `ImposterAmoungUs` function. If
# the bot detects impersonation, it terminates further processing. If there
# is a moderator area, it sends a notification about the new member
# joining. Finally, if a welcome message exists for the bot, it sends a
# personalized welcome message to the system channel, replacing
# `{username}` with the new member's mention.

@client.event
@function_trapper
async def on_member_join(member):
    global ActiveJoins

    # Track new member joins
    key=member.guild.id
    if key not in ActiveJoins:
        ActiveJoins[key]=[]
    if member.id not in ActiveJoins[key]:
        ut=[member.id,time.time()]
        ActiveJoins[key].append(ut)

    # Welcome forces the default bot.
    bot=GetCompanionPersona(member.guild.id,None,Welcome=True)
    if bot==None:
        return

    if bot['AutoLogging'].lower()!='no':
        ErrorLog(f"OMJ: {member}/{member.id}/{member.display_name}")

    # Impersonation detection
    if await ImposterAmoungUs(member.guild,member):
        return

    # If there is a moderator area, send a message to it.
    name=member.name
    if member.nick:
        name=member.nick
    await ModeratorNotify(bot,member.guild,f"{name}/{member}/{member.id}/{member.display_name} joined.")

    if os.path.exists(bot['Welcome']):
        # Figure out which persona is calling the shots.
        response=PickRandomResponse(bot['Welcome']).replace('{username}',f'**{member.mention}**')
        # A message of None will automatically refer to the system channel
        await send_response(bot,None,response,member=member)

# The `on_member_remove` event is triggered when a member leaves a guild.
# It checks if a companion bot is set for the guild (with the
# `Welcome=True` flag) and proceeds if the bot is available. If
# `AutoLogging` is enabled, it logs the departure of the member. The event
# also sends a notification to the moderator area of the guild, informing
# about the member's departure, using the `ModeratorNotify` function. This
# helps ensure that the moderator team is kept updated about any member
# leaving the server.

@client.event
@function_trapper
async def on_member_remove(member):
    # Welcome forces the default bot.
    bot=GetCompanionPersona(member.guild.id,None,Welcome=True)
    if bot==None:
        return

    if bot['AutoLogging'].lower()!='no':
        ErrorLog(f"OMR: {member}")

    # If there is a moderator area, send a message to it.
    name=member.name
    if member.nick:
        name=member.nick
    await ModeratorNotify(bot,member.guild,f"{name}/{member}/{member.id}/{member.display_name} left.")

# The `on_typing` event is triggered when a user begins typing in a text
# channel. This method is used to manage user activity by adjusting slow
# mode settings based on typing behavior. It first checks if the typing
# event is occurring in a direct message or thread and ensures it operates
# only in regular channels. The code tracks user activity by assigning a
# multiplier (`joins`) to factor in the number of recent member joins in
# the guild. This helps adjust the expected number of typing users in a
# channel based on the server size.

#The primary function of this event is to detect potential raid-like
#activity by analyzing the number of typing users in a channel. If the
#typing count exceeds a certain threshold (based on the server's size and
#channel distribution), slow mode is applied to prevent spam. The slow mode
#duration is dynamically adjusted based on the number of typing users and
#the expected user count for that channel. If the number of typing users is
#significantly higher than expected, the bot logs a potential raid attempt
#and sets a more aggressive slow mode duration.

#Additionally, the event includes a cooldown mechanism that prevents
#multiple slow mode adjustments in a short period, ensuring that changes
#are made only once every 5 minutes per channel.

@client.event
@function_trapper
async def on_typing(channel, user, when):
    global ActiveUsers
    global ActiveJoins

    # if direct message, ignore
    if isinstance(channel,discord.DMChannel):
        return

    # If this is a thread, get the parent channel
    pchannel=channel
    if isinstance(channel,discord.Thread):
        pchannel=channel.parent

    # Track active member joins
    joins=1
    if pchannel.guild.id in ActiveJoins:
        joins=len(ActiveJoins[channel.guild.id])

    # joins will be used a a multiplier so is the threshold is not met, then
    # a multiplier of 1 is used is keep the method simple.

    if joins<=int(len(pchannel.guild.members)*0.01):
        joins=1

    # Create a unique key for the channel using guild and channel IDs
    key=f"{pchannel.guild.id}.{pchannel.id}"

    # When this function gets called, someone was typing. Add them to
    # the channel tracking list.

    if key not in ActiveUsers:
        ActiveUsers[key]=[]

    found=False
    for u in ActiveUsers[key]:
        if u[0]==user.id:
            # Reset the timer
            u[1]=time.time()
            u[2]+=1*joins
            found=True

    if not found:
        # User ID, and the time they were typing, factor
        # The factor is used as a decrementer to prevent manipulation
        ut=[user.id,time.time(),joins]
        ActiveUsers[key].append(ut)

    # Calculate the number of typing users in the channel
    typing_count=len(ActiveUsers[key])

    # Check if the cooldown has expired. Slowdown can only be adjust
    # ONCE every 5 minutes per channel.

    current_time=time.time()
    last_change=LastSlowmodeChange.get(key, 0)
    if current_time - last_change<SlowwModeCooldown:
        return  # Skip the adjustment process if still in cooldown

    # Calculate expected users
    server=channel.guild

    # Theory: 1% of all active users throughout the server should be
    # active normally. Assuming the distribution of users will be
    # spread out over the number of channels, gives us an expected
    # number of users per channel. This is a fallacy, but it is a
    # reasonable starting point to build the theory on. Possible
    # expansions could be actually messuring user activity per
    # channel, but to get something very basic, I felt this was
    # reasonable enough for most applications given that I am using
    # only 3 secords per user as the slowdown rate, unless the number
    # of user is above the expected amount. This is a primitive
    # anti-raid method.

    expected_users=int(max(1, round(len(server.members) * 0.01 / len(server.channels))))
    if expected_users<1:
        expected_users=1

    # Determine slow mode duration
    if typing_count>2 * expected_users:  # Over threshold
        bot=GetCompanionPersona(server.id,None,Welcome=True)
        await ModeratorNotify(bot,server,f"Under potential raid attack, {joins} joins, {typing_count} active users>{expected_users} expected users")
        slow_mode_duration=SlowModeMultiplier * typing_count*10*joins
    elif typing_count>expected_users:
        slow_mode_duration=SlowModeMultiplier * typing_count*joins
    else:
        slow_mode_duration=0

    # Apply slow mode
    await pchannel.edit(slowmode=slow_mode_duration)
    LastSlowmodeChange[key]=current_time  # Update the last change time
    print(f"Slowmode {server.id}/{channel.name}: {slow_mode_duration} seconds, {typing_count} active, {expected_users} expected")

# At the heart of the bot is its core function, which revolves around
# processing and responding to messages within a Discord server. When a
# message is received, the bot first examines who sent it and confirms that
# it wasn’t sent by itself, ensuring it only interacts with users. Once
# this is established, the bot determines which persona it should adopt
# based on the server settings. This allows the bot to be flexible and
# respond in different ways depending on the environment it’s in. For
# example, it might be more formal in some servers and more casual in
# others.

# After identifying the appropriate persona, the bot processes the content
# of the message. It looks for key words or phrases to understand the
# intent of the message. If the message is a command or question, the bot
# will trigger the corresponding response or action. This could range from
# providing an answer to a query to executing a special function like
# checking the status of the server or deleting harmful content. The bot’s
# responses are always carefully crafted to be contextually appropriate,
# ensuring that it communicates in a way that matches the tone and setting
# of the conversation.

# The function also includes checks for harmful content, like spam or
# malicious links. If a message contains something that could disrupt the
# conversation or harm the server, the bot can take immediate action, such
# as deleting the message or issuing a warning. This ensures that the
# environment stays safe and free from unwanted disruptions. Additionally,
# the bot is programmed to detect when users are engaging in private
# messages and will politely remind them that it only interacts within the
# server, maintaining clear boundaries for its interactions.

# Ultimately, this core function allows the bot to continuously monitor and
# interact with the flow of conversation in the server. It ensures that the
# bot remains responsive and adaptive, delivering personalized messages
# while keeping the space safe and organized. By focusing on this core
# task, the bot can maintain a smooth and engaging experience for users,
# adjusting its behavior as needed to meet the specific needs of each
# server.

@client.event
@function_trapper
async def on_message(message):
    global ResponseLock
    global GuildQueueLock
    global GuildQueue
    global ActiveJoins

    try:
        key=message.guild.id
        if key not in ActiveJoins:
            ActiveJoins[key]=[]
        if message.author.id not in ActiveJoins[key]:
            ut=[message.author.id,time.time()]
            ActiveJoins[key].append(ut)

        # Ignore messages from the bot itself. This does NOT work with webhooks,
        # so We need to check for that too.

        if message.author==client.user:
            return

        # Handle direct messages
        if isinstance(message.channel,discord.DMChannel):
            await message.channel.send(f'You have messaged the Companion AI chatbot/moderation. This bot functions ONLY within the limits of a Discord server and does NOT support interactions via DMs. Thank you.')
            return

        # Figure out which persona is calling the shots.
        guild=message.guild
        # Add the guild to the circular guild queue, if not already in it.
        if guild.id not in GuildQueue and GuildQueueLock.acquire(timeout=GuildQueueTimeout):
            GuildQueue.append(guild)
            GuildQueueLock.release()

        channel=str(message.channel)
        uid=str(message.author.id)

        # Owner role information. This will be used to verify bot commands.
        orole=discord.utils.get(guild.roles,name='owner')
        # Bots/webhooks will breaks this... safe way to make sure webhook can
        # never be registered as owner
        if not message.author.bot:
            mrole=orole and orole in message.author.roles
        else:
            mrole=None

        # Handle auto publish
        if message.channel.type==discord.ChannelType.news:
            await message.publish()

        # NSFW not allowed in threads, so find parent channel
        bot=None
        nsfw=False
        if isinstance(message.channel,discord.Thread):
            pchannel=str(message.channel.parent)
            nsfw=message.channel.parent.nsfw
            bot=GetCompanionPersona(message.guild.id,pchannel,nsfw)
            # WTAF? Really? bots have to join a thread...
            if not message.channel.me:
                await message.channel.join()
        else:
            nsfw=message.channel.nsfw
            bot=GetCompanionPersona(message.guild.id,channel,nsfw)
        if bot==None:
            return

        # Log everything
        if bot['AutoLogging'].lower()!='no':
            DisectMessage("Received message",message)

        # Now that we have a bot name, we can check for webhooks and make sure
        # they are not my own.

        if message.webhook_id and message.author.name==bot['BotName']:
            return

        # Moderation section
        if bot['AutoModeration'].lower()!='no':
            # MUST BE FIRST!
            # Imposter among us no more!

            if await ImposterAmoungUs(message.guild,message.author):
                await message.delete()
                return

            # Check for input that is a number only
            if os.path.exists(bot['AgeExploit'])==True and NumberOnly(message.content):
                await ModeratorNotify(bot,message.guild,f"AgeExploit detected: {message.author.name}/{message.author.id} in {message.channel.name}")
                author=str(message.author.mention)
                # If its a bot, it doesn't deserve a response
                if not message.author.bot:
                    await send_response(bot,message,PickRandomResponse(bot['AgeExploit']),delete=300)
                await message.delete()
                return

            # Check if message has any PII
            if await IsPIIDetected(bot,message):
                return

            # This is really the only absolute exception to BOT responsing...
            # Check for scam links and delete them.

            if os.path.exists(CompanionScamURLS)==True and os.path.exists(bot['ScamURLS'])==True and '://' in message.content:
                if CheckMessageURLs(message.guild.id,message.content):
                    if not message.author.bot:
                        await send_response(bot,message,PickRandomResponse(bot['ScamURLS']),delete=57)
                    await message.delete()
                    return

            if os.path.exists(CompanionAutoFilter)==True and os.path.exists(bot['AutoFilter'])==True:
                autofilter=ReadFile2List(CompanionAutoFilter)
                for text in autofilter:
                    if text in message.content:
                        author=str(message.author.mention)
                        # If its a bot, it doesn't deserve a response
                        if not message.author.bot:
                            await send_response(bot,message,PickRandomResponse(bot['AutoFilter']),delete=57)
                        await message.delete()
                        return

            # Run CIMS
            if os.path.exists(bot['CIMS'])==True and 'CIMSClassifier' in bot:
                # CIMS will return true if message was deleted.
                if await CheckCIMS(message.guild.id,bot,message,nsfw=nsfw):
                    return

        # Don't respond to other bots.
        if message.author.bot and bot['AllowBot'].lower()!='yes':
            return

        # User commands section
        # Allow the user to erase their own stored conversation

        if str(message.content).strip().startswith('%Forget'):
            await message.delete()
            dn=f"{MemoryStorage}/{guild.id}/{bot['BotName']}"
            mkdir(dn)
            fn=f"{dn}/{bot['BotName']}.{uid}.{channel}.memory"
            if os.path.exists(fn):
                os.remove(fn)
                await send_response(bot,message,"Conversation forgotten",delete=57)
            return

        # Only guild owner/Owner role allowed to use advanced commands
        if mrole:
            if str(message.content).strip().startswith('%SecurityAudit'):
                await message.delete()
                await SecurityAudit(guild,message,True)
                return

            if str(message.content).strip().startswith('%CheckBot'):
                member=message.guild.get_member(client.user.id) # Get the bot's member object in the guild
                # Check if the bot is a member of the channel
                if member in message.channel.members and bot['ResponseAllowed'].lower()=='yes':
                    await send_response(bot,message,"Allowed",delete=57)
                else:
                    await send_response(bot,message,"Not Allowed",delete=57)
                await message.delete()
                return

            if str(message.content).strip().startswith('%PurgeRequests'):
                # Give the AI the message
                if ResponseLock.acquire(timeout=ResponseTimeout):
                    rname=f"{MemoryStorage}/{gid}/requests.txt"
                    if os.path.exists(rname):
                        os.remove(rname)
                        msg=f"Rrequests purged"
                    else:
                        msg=f"Request list already empty"
                    ResponseLock.release()
                    await send_response(bot,message,msg,delete=57)
                else:
                    ErrorLog("PurgeRequest Lock failed")
                return

        # If we have a bot, then we can converse here.

        # Check to see if the message is a replay to the bot, or a mention or a
        # public message, specifically that the user used the reply feature of the
        # APP, or the @ and bot name, if talking to the bot. This convoluted
        # approach is needed because all bot replies are via webhooks. Webhooks
        # have different user IDs then the bot.

        # All of this is NECCESSARY if we want the ability to server multiple
        # personas, each with its own avatar. Discord does NOT allow multiple
        # avatars per a single user (bot.user) without changing EVERY avatar in
        # EVERY channel. Using webhooks is the only viable option to acheive
        # multiple AI personas in an imersive methodology.

        botReference=False
        if message.reference is not None and message.reference.message_id is not None:
            refmsg=await message.channel.fetch_message(message.reference.message_id)
            # ID won't work here because everything is sent via webhook
            if (refmsg.author.name==client.user.name or refmsg.author.name==bot['BotName']):
                botReference=True

        publicMsg=message.reference==None and len(message.mentions)==0 and len(message.role_mentions)==0 and len(message.channel_mentions)==0
        botAnswer=(publicMsg or botReference or client.user in message.mentions)

        # Verify that the bot is no talking to itself. Webhooks rotate
        # constantly and when bot injection is used, is is very possible
        # to create a loop. These checks make sure that doesn't happen.

        if bot['ResponseAllowed'].lower()=='yes' and bot['Channel']!=None and botAnswer and message.author.name.split('#')[0]!=bot['BotName']:
            input_text=message.content.strip()

            # If a trigger file exists, check to see if one on the trigger words are in the user message.
            # Also if trigger file exists, and message is directed to bot.
            trigger=f"{CompanionStorage}/{bot['BotName']}/{bot['BotName']}.{channel}.trigger"
            if os.path.exists(trigger):
                # If message is directed to bot, override trigger
                if client.user in message.mentions or (message.reference and message.reference.resolved.author.id==client.user.id):
                    pass
                else:
                    wfound=False
                    twords=ReadFile2List(trigger,ForceLower=True)
                    inwords=StripPunctuation(input_text.replace('  ',' ')).split(' ')
                    while '' in inwords:
                        inwords.remove('')
                    # Search the list word by word
                    for w in inwords:
                        if w.lower() in twords:
                            wfound=True
                            break
                    # A trigger word was not found, don't continue.
                    if wfound==False:
                        return

            # Anagram solver... how the hell did I end up don the rabbit hole? Really?

            if os.path.exists(AnagramWordList) and input_text.lower().strip().startswith('%anagramsolver'):
                if CheckWhitelist(bot,'AllowAnagramSolver',message):
                    letters=input_text[14:].strip().lower()
                    input_text=AnagramSolver(letters)
                    await send_response(bot,message,input_text)
                    return
                else:
# Write response for "That action is not allowed here... Self deleting
                    await message.delete()
                    return

            # Read tags from YouTune video
            if os.path.exists(bot['YTtags']) and os.path.exists(bot['noYTtags']) \
            and input_text.lower().strip().startswith('%yttags'):
                if CheckWhitelist(bot,'AllowYTTags',message):
                    # Web/URL reference
                    url=input_text[7:].strip()
                    input_text=yttags2text(guild.id,url)
                    if input_text==None:
                        await send_response(bot,message,PickRandomResponse(bot['noYTtags']))
                    elif input_text=='{[(*VNF*)]}':
                        await send_response(bot,message,PickRandomResponse(bot['URLBroken']))
                    else:
                        await send_response(bot,message,f"{PickRandomResponse(bot['YTtags'])}\n\n{input_text}")
                    return
                else:
# Write response for "That action is not allowed here... Self deleting
                    await message.delete()
                    return

            # if the input text starts with "%http", replace it with the actual URL text
            if os.path.exists(bot['TooMuchInformation']) and input_text.lower().strip().startswith('%http'):
                if CheckWhitelist(bot,'AllowHTTP',message):
                    # Web/URL reference
                    url=input_text.replace(' ','')[1:]
                    input_text=html2text(message.guild.id,url)
                    if input_text==None:
                        await send_response(bot,message,PickRandomResponse(bot['URLBroken']))
                        return
                else:
# Write response for "That action is not allowed here... Self deleting
                    await message.delete()
                    return

            # Give the AI the message
            if ResponseLock.acquire(timeout=ResponseTimeout):
                msg={}
                msg['input']=input_text
                msg['gid']=guild.id
                msg['cid']=message.channel.id
                msg['mid']=message.id
                PutNextRequest(guild.id,msg)
                ResponseLock.release()
            else:
                ErrorLog("Message Lost: Lock failed OM")
    except discord.HTTPException as err:
        if err.code==429:  # Rate limit error
            retry_after=int(err.response.headers.get('X-RateLimit-Reset', 1))*2
            ErrorLog(f"Rate limit hit. Retrying after {retry_after} seconds.")
            await asyncio.sleep(retry_after)
            await on_message(message)  # Retry the request

# When the bot joins a new server (guild), this function logs the event and
# ensures the server is properly set up. It adds the new server to a queue,
# ensuring that no duplicates are added, and creates necessary directories
# for storing memory and log files specific to that server. Additionally, a
# security audit is triggered for the new server to ensure everything is
# properly configured and secure. This function helps to integrate the bot
# smoothly into the new environment, ensuring that all operational
# requirements are met from the start.

@client.event
@function_trapper
async def on_guild_join(guild):
    global GuildQueueLock
    global GuildQueue

    ErrorLog(f"Companion invited to new guild: {guild}/{guild.id}")
    # Add the guild to the circular guild queue
    if guild.id not in GuildQueue and GuildQueueLock.acquire(timeout=GuildQueueTimeout):
        GuildQueue.append(guild)
        GuildQueueLock.release()

    mkdir(f"{ConfigStorage}/{guild.id}")
    mkdir(f'{MemoryStorage}/{guild.id}')
    mkdir(f'{LoggingStorage}/{guild.id}')
    await SecurityAudit(guild,None,False,True)

# When the bot is removed from a server (guild), this function logs the
# event and ensures that the server is properly removed from the queue. It
# checks if the server exists in the queue, and if so, it safely removes it
# while ensuring proper synchronization with a lock. This function helps
# maintain an updated queue of active servers, ensuring that the bot only
# tracks relevant servers.

# TODO: purge all guild files.

@client.event
@function_trapper
async def on_guild_remove(guild):
    global GuildQueueLock
    global GuildQueue

    ErrorLog(f"Companion kicked out of guild: {guild}/{guild.id}")
    # Add the guild to the circular guild queue
    if guild.id in GuildQueue and GuildQueueLock.acquire(timeout=GuildQueueTimeout):
        GuildQueue.remove(guild)
        GuildQueueLock.release()

# When the bot is ready, this function initializes several tasks to ensure
# smooth operation across all servers it is connected to. It logs in, adds
# servers to a processing queue, creates necessary directories for each
# server, and checks that the bot has the required administrator
# permissions in each server. If any permissions are missing, a warning is
# logged. Then, the function starts a series of background tasks like
# updating response data, auto-deleting messages, tracking active users,
# and conducting security audits to maintain the bot’s performance and
# security. Finally, it prints a confirmation that the bot is fully
# operational and ready to serve.

@client.event
@function_trapper
async def on_ready():
    print(f'Logged in as {client.user}')

    # Print some fluff
    for guild in client.guilds:
        if not VerifyGuildPermissions(guild):
            print(f"{guild.id} does NOT have the proper permissions to function.")

        # Add the guild to the circular guild queue, if not already in it.
        if guild.id not in GuildQueue and GuildQueueLock.acquire(timeout=GuildQueueTimeout):
            GuildQueue.append(guild)
            GuildQueueLock.release()

        # Make sure the neccessary directories exist
        mkdir(f'{ConfigStorage}/{guild.id}')
        mkdir(f'{MemoryStorage}/{guild.id}')
        mkdir(f'{LoggingStorage}/{guild.id}')

        # Check if the bot's role has administrator permissions
        if not guild.me.guild_permissions.administrator:
            print(f"  Error: Companion does not have administrator privileges in {guild.name}.")

    # Start the task when the bot is ready
    update_response_data.start()
    autodelete_messages.start()
    track_ActiveUsers.start()
    MemoryMaintenance.start()
    AutomatedSecurityAudit.start()

    print("Ready to serve!")

###
### STARTUP: starts the bot with the corresponding token
###

@function_trapper
def main():
    print(f'Companion {Version}')
    mkdir(ConfigStorage)

    Tokens=ReadTokens()

    client.run(Tokens['Discord'],log_handler=None)

if __name__=='__main__':
    main()

###
### END OF PROGRAM
###
