#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Jackrabit AI
# 2024-2025 Copyright © Robert APM Darin
# All rights reserved unconditionally.

# This Python code defines a sophisticated system for managing interactions
# with various AI models, focusing on memory management, tokenization, and
# communication with multiple AI services. The core of the system is the
# `Agent` class, which acts as a centralized manager for AI interactions,
# handling memory storage, token limits, and responses from different AI
# engines.

# The `Agent` class is initialized with parameters that configure its behavior,
# such as the AI engine, model, token limits, and memory settings. It includes
# methods to set and adjust these parameters, ensuring flexibility in how the
# AI is used. The class also manages storage locations for memory and timing
# data, adapting to user-specific or default directories based on provided
# inputs.

# Memory management is a key feature, with methods to read, write, reset, and
# maintain memory within token limits. The system stores conversation history
# in a structured format, including metadata like the engine, model, and token
# count for each message. It ensures that memory stays within a specified limit
# by removing older messages when necessary, prioritizing recent and relevant
# interactions.

# The code includes a `JumpTable` method that acts as a dispatcher, routing
# requests to the appropriate AI service based on the specified engine. It
# supports a wide range of AI providers, including OpenAI, Cohere, Anthropic,
# and others, each with its own method for generating responses. This modular
# approach allows for easy integration of new AI services in the future.

# The `Response` method is central to the system's functionality, handling user
# input, memory updates, and interactions with the AI. It manages the entire
# lifecycle of a request, from adding user input to memory, maintaining token
# limits, sending requests to the AI, and storing the response. The method also
# includes timing and logging features to track performance.

# Tokenization is handled by the `GetTokenCount` method, which calculates the
# number of tokens in a message based on the engine and model. This is crucial
# for managing costs and ensuring compatibility with different AI services, as
# each has its own tokenization method.

# Overall, this code provides a robust framework for building AI-powered
# applications, offering memory persistence, token management, and seamless
# integration with multiple AI engines. It is designed to be adaptable,
# efficient, and capable of handling complex conversational workflows while
# maintaining a clear and organized structure.

# IMPORTANT: This library was designed with the thought process of FORKING to
# control resource management. There are too many known issues with Python for
# threading to be considered stable.

import sys
import os
os.environ["TOGETHER_NO_BANNER"]="1"
import pwd
import io
import copy
import itertools
import functools
import inspect
import traceback
import requests
import datetime
import time
import random
import json
import string
import re
import tiktoken
import openai
import ollama
import cohere
import huggingface_hub
import anthropic
from transformers import AutoTokenizer
from googleapiclient.discovery import build
import google.genai
import google.genai.types
import together

import DecoratorFunctions as DF
import CoreFunctions as CF
import FileFunctions as FF
import EKBFunctions as EKB

# Verify that JackrabbitDLM is loaded and running.
JRDLM=False
if os.path.exists('/home/JackrabbitDLM/DLMLocker.py'):
    try:
        sys.path.append('/home/JackrabbitDLM')
        import DLMLocker as DLM
        fw1=DLM.Locker("LockerTest",Timeout=10,Retry=0)
        if fw1.IsDLM():
            JRDLM=True
    except:
        pass

TOGETHER_NO_BANNER=1

# A class makes sense here because of the limited scope of the memory and the
# neccessity of tracking it as a separation of functionality. The idealization of
# memory for the AI has potential for encapulated growth for various management
# structures that could potentially mirror human memory. Memory cound theoritical be
# compartmentalized by topic, for example.

# Each memory item must record the engine ad model to get a proper token count.

class Agent:

    # This function, `__init__`, is a constructor method that initializes an
    # object with various parameters related to AI engine configuration and
    # functionality. It takes in numerous parameters, including the AI engine,
    # model, maximum tokens, encoding, persona, user information, memory
    # settings, and timing controls. The function sets these parameters as
    # instance variables and performs some basic validation and default value
    # assignments, such as setting the encoding to a specific value if the
    # engine is 'openai' and no encoding is provided. Additionally, it calls a
    # separate method `SetStorage` to configure storage settings based on user
    # information. The initialized object appears to be designed to manage
    # interactions with an AI API, controlling aspects such as memory usage,
    # response timing, and isolation.

    # RateLimit is 2 seconds

    def __init__(self,engine,model,maxtokens,encoding=None,persona=None,user=None,userhome=None,usertokens=None,maxmem=100,freqpenalty=0.73,temperature=0.31,seed=0,timeout=300,maxmodelexpire=900,reset=False,save=True,timing=True,isolation=False,retry=7,retrytimeout=37,maxrespsize=0,maxrespretry=7,maxrespretrytimeout=37,UseOpenAI=False,UseRateLimit=True,RateLimitWait=2000,UseEKB=True):
        self.PersonaConfig="/home/JackrabbitAI/Personas"

        self.SystemRoleDefault= \
            "You are a capable, practical assistant who helps users think, write, analyze, plan, and solve problems across many domains. Your job is to be clear, accurate, adaptable, and genuinely useful. Focus on the user's real goal, not just the literal wording of the request. When the request is slightly ambiguous, make a reasonable interpretation and help immediately. If a wrong assumption would materially affect correctness, ask one brief clarifying question instead of proceeding.\n\n"+ \
            "Give direct answers first and put the most useful information up front. Be concise by default while still being complete. Expand when the task is complex or when the user wants more depth. Write in natural, clear, specific language. Be professional, calm, and respectful. Avoid stiff, generic, theatrical, sarcastic, flattering, or condescending phrasing. Never use em dashes.\n\n"+ \
            "Be cooperative and solution-oriented. Do not be rude, combative, dismissive, smug, or needlessly corrective. Do not lecture the user. Do not flatter the user or agree just to be agreeable. If the user is mistaken, correct the issue plainly and tactfully, then continue with the most helpful answer you can provide. If an idea is weak, incomplete, or likely to fail, explain why in practical terms and suggest a better approach.\n\n"+ \
            "Be accurate and intellectually honest at all times. Do not claim certainty when certainty is not justified. If something is unclear, missing, or uncertain, say so plainly and provide the best qualified answer you can. Distinguish between what is known, what is likely, and what is speculative. Do not invent facts, sources, outcomes, or experiences.\n\n"+ \
            "Prioritize truth, clarity, and usefulness. Help the user make progress. Do not nitpick minor issues or turn small mistakes into long corrections. When a brief warning or correction is needed, keep it brief and continue with the most useful response. Follow the user's constraints closely, but do not reinforce false claims or bad reasoning. Correct important errors calmly and briefly.\n\n"+ \
            "Adapt your approach to the task. For writing, help with ideation, structure, drafting, rewriting, tone, clarity, and editing. For analysis, break the problem into parts, explain the key reasoning, and highlight assumptions, tradeoffs, and risks. For planning and decision-making, turn vague goals into concrete options, steps, and recommendations. For technical questions, be precise, explicit, and grounded in actual behavior and constraints.\n\n"+ \
            "Structure responses so they are easy to read and immediately usable. Start with the answer, recommendation, or output the user needs. Use paragraphs by default, and use lists when they improve clarity, especially for steps, comparisons, or grouped information. Keep explanations proportional to the difficulty of the task. Provide examples, alternatives, or next steps when they help the user apply the answer quickly.\n\n"+ \
            "Think carefully before responding, but do not dump long hidden reasoning or verbose process unless it is useful. Present concise rationale, key steps, or short explanations that help the user understand the result. If the request is underspecified, make the best reasonable assumption and state it briefly. If that would likely mislead the user, ask one short clarifying question instead. If user constraints conflict, prioritize correctness and explicitly note the conflict.\n\n"+ \
            "If there are several valid approaches, present the best one first, then mention strong alternatives briefly. Avoid robotic phrasing, empty praise, canned politeness, and repetitive disclaimers. Ensure outputs are directly usable and, when applicable, include simple verification steps or examples so results can be tested. Your goal is to be a useful, intelligent counterpart: clear, grounded, honest, effective, and respectful."

        self.AIJumpTable = {
            'openai': self.GetOpenAI,
            'mistral': self.GetMistral,
            'googleai': self.GetGoogleAI,
            'xai': self.GetxAI,
            'cohere': self.GetCohere,
            'togetherai': self.GetTogetherAI,
            'nvidia': self.GetNVidia,
            'ollama': self.GetOllama,
            'openrouter': self.GetOpenRouter,
            'anthropic': self.GetAnthropic,
            'perplexity': self.GetPerplexity,
            'huggingface': self.GetHuggingFace }
        self.AITokenMap = {
            'openai': 'OpenAI',
            'mistral': 'Mistral',
            'googleai': 'GoogleAI',
            'xai': 'xAI',
            'cohere': 'Cohere',
            'togetherai': 'TogetherAI',
            'nvidia': 'NVidia',
            'ollama': 'Ollama',
            'openrouter': 'OpenRouter',
            'anthropic': 'Anthropic',
            'perplexity': 'Perplexity',
            'huggingface': 'HuggingFace' }

        self.UseEKB=UseEKB          # Using the EKB
        self.AIError=False          # Error in the AI engine, breaks retry
        self.user=None              # User name
        self.userhome=None          # User home directory
        self.MemoryLocation=None    # Memory files location
        self.TimingLocation=None    # Timing file location
        self.usertokens=usertokens  # explicit path to tokens. OVERIDE user area
        self.UseOpenAI=UseOpenAI    # Use OpenAI libraries when available
        self.engine=engine.lower()  # AI engine for a memory item (token count)
        self.model=model            # AI model being used
        self.maxtokens=maxtokens    # Maximum number of tokens allowed for a given model
        self.encoding=encoding
        self.MaxModelExpire=maxmodelexpire
        self.MaxMemory=maxmem
        self.freqpenalty=freqpenalty
        self.temperature=temperature
        self.seed=seed
        self.timeout=timeout        # Timeout for connection to take place
        self.timing=timing          # Are we timing the AI api call?
        self.persona=persona        # the AI persona
        self.nsfw=False             # Loaded a NSFW persona
        self.completion=None        # The total return payload
        self.response=None          # The response
        self.stop=None              # The stop reason for the request
        self.reset=reset            # Do we reset the memory before the AI functionality?
        self.save=save              # Do we save any memory at all?
        self.isolation=isolation    # Are we wanting an isolated response (No memory?)
        self.maxretries=retry       # Number of times to retry a request
        self.retrytimeout=retrytimeout # Sleep between retries
        self.maxrespsize=maxrespsize # Some models are prone to "dictionary dumps", reject any response larger then this. 0=no rejection
        self.maxrespretry=maxrespretry # Number of time to retry size rejection
        self.maxrespretrytimeout=maxrespretrytimeout # Number of seconds to wait between retries
        self.UseRateLimit=UseRateLimit and JRDLM    # Use rate limits only in JRDLM is available
        self.RateLimitWait=RateLimitWait
        self.Limiter=None
        self.ModelLock=None         # None by default for condirional testing
        self.discordChannel=None    # No discord channel
        self.allowNSFW=False        # nsfw roles are NOT allowed
        self.Memory=[]

        if self.engine=='openai' and self.encoding==None:
            if 'gpt-4o' in self.model:
                self.encoding="o200k_base"
            else:
                self.encoding="cl100k_base"

        if self.UseRateLimit:
            ln=f"RateLimiter.{self.engine}.{self.model}"
            self.Limiter=DLM.Locker(ln,ID=ln)

        # Set user information

        self.SetStorage(user,userhome)

        # Model lock needs to be brutal to ensure each model layer is aggressively
        # protected. The limit is set be a standard of the LONGEST response I have
        # seen. (15 minutes for each API)

        if JRDLM:
            ln=f"Response.{self.engine}.{self.model}"
            if self.user:
                ln=f"Response.{self.engine}.{self.model}.{self.user}"
            elif self.userhome:
                ln=f"Response.{self.engine}.{self.model}.{self.userhome}"
            elif self.MemoryLocation:
                ln=f"Response.{self.engine}.{self.model}.{self.MemoryLocation}"
            self.ModelLock=DLM.Locker(ln,ID=ln)

    # Set rate limits. The wait is in MILLISECONDS

    def SetRateLimit(self,UseRateLimit=False,RateLimitWait=1000):
        self.UseRateLimit=UseRateLimit
        self.RateLimitWait=RateLimitWait

    # Rate limit locking using DLM. The wait is in MILLISECONDS

    # Forced Wait forces the waiting period. With NVidia, and similar, you don't
    # need to wait beyoud the locking process, ie NVidia allows a request for their
    # free models of 1.5 seconds between API calls. This can be accomplished
    # WITHOUT a forced wait AFTER the lock has been performed. If this function is
    # called twice, it waits for the lock ti expire, creating the effect needed
    # without extra delay.

    def EnforceRatelimit(self, ForcedWait=False):
        if self.UseRateLimit:
            expire=self.RateLimitWait/1000
            while self.Limiter.Lock(expire=expire)!='locked':
                CF.ElasticSleep(expire)
            if ForcedWait:
                CF.ElasticSleep(expire)
                self.Limiter.Unlock()

    # Set discord channel and NSFW allowance

    def Discord(channel,nssw):
        self.discordChannel=channel
        self.allowNSFW=nsfw

    # Set the Persona Config location

    def SetPersonaConfig(pcfg):
        self.PersonaConfig=pcfg

    # Change the engine

    def SetEngine(self,engine):
        self.engine=engine.lower()
        if self.engine=='openai':
            if 'gpt-4o' in self.model:
                self.encoding="o200k_base"
            else:
                self.encoding="cl100k_base"

    # Change the model. This is the model name, like gpt=4o-mini or gpt-5-chat-latest

    def SetModel(self,model):
        self.model=model

    # Change the maximum number of tokens

    def SetTokens(self,maxtokens):
        self.maxtokens=maxtokens

    # Change the encoding, like o200k_base. OpenAI os the only one that uses
    # this so far.

    def SetEncoding(self,encoding):
        self.encoding=encoding

    # Frequency Penality

    def FreqPenalty(self,freqpenalty):
        self.freqpenalty=freqpenalty

    # Temperature

    def Temperature(self,temperature):
        self.temperature=temperature

    # How long to hold the connection before failing out

    def Timeout(self,timeout):
        self.timeout=timeout

    # Set the memory and timing locations separately

    def SetMemory(self,memory=None,timing=None):
        if memory is not None:
            self.MemoryLocation=f"{memory}/{os.path.basename(CF.RunningName)}.memory"
        if timing is not None:
            self.TimingLocation=timing
        else:
            self.TimingLocation=f"{memory}/{os.path.basename(CF.RunningName)}.timing"
        FF.mkdir(os.path.dirname(self.MemoryLocation))

    # The `SetStorage` function is a method that sets the storage locations for
    # memory and timing files within an object. It takes two optional
    # parameters, `user` and `userhome`, which determine the directory where
    # these files are stored. If `userhome` is provided, it overrides the
    # default user system and sets the storage location to a directory within
    # the specified path. Otherwise, the function checks if a `HOME`
    # environment variable is defined and uses it to construct the storage
    # path; if not, or if a `user` is specified, it defaults to a predefined
    # directory structure under `/home/JackrabbitAI/Memory`. The function
    # ensures the parent directory of the storage location exists by creating
    # it if necessary using `FF.mkdir`.

    def SetStorage(self,user=None,userhome=None):
        # Check userhome. This overrides the entire user system,
        # setting the default directory to the program.

        if user is None and userhome is not None:
            self.user=user
            self.userhome=userhome
            self.MemoryLocation=f"{userhome}/{os.path.basename(CF.RunningName)}.memory"
            self.TimingLocation=f"{userhome}/{os.path.basename(CF.RunningName)}.timing"
            FF.mkdir(os.path.dirname(self.MemoryLocation))
            return

        # Get the $USER environment

        if not user:
            user=os.environ.get('USER')

        # Set user and userhome
        self.user=user
        self.userhome=os.environ.get('HOME')

        # Figure out where to store the memory files
        if self.userhome is None and self.user is not None:
            try:
                self.userhome=pwd.getpwnam(self.user).pw_dir
            except:
                self.userhome=None

            if self.userhome:
                self.MemoryLocation=f"{self.userhome}/.JackrabbitAI/Memory/{os.path.basename(CF.RunningName)}.memory"
                self.TimingLocation=f"{self.userhome}/.JackrabbitAI/Memory/{os.path.basename(CF.RunningName)}.timing"
                FF.mkdir(os.path.dirname(self.MemoryLocation))
                return

        # if user and userhome are NOT defined
        self.MemoryLocation=f"/home/JackrabbitAI/Memory/NoUser.memory"
        self.TimingLocation=f"/home/JackrabbitAI/Memory/NoUser.timing"

    # Reset AI memory and erase file.

    def Reset(self):
        self.Memory=[]
        if os.path.exists(self.MemoryLocation):
            os.remove(self.MemoryLocation)

    # Memory might also contain emotional scores or token counts. Return only
    # role/content

    def Get(self):
        mem=[]
        for item in self.Memory:
            memdata={}
            memdata['role']=item['role']
            memdata['content']=item['content']
            mem.append(memdata)

        return mem

    # Put a memory element into the AI memory data

    def Put(self,role,data,reset=False):
        if reset:
            self.Memory=[]

        self.Memory.append({ "role":role,"content":data,
            "engine":self.engine,"model":self.model,"encoding":self.encoding,
            "tokens":self.GetTokenCount(data) })

    def UpdateLast(self,role,data):
        self.Memory[-1][role]=data

    # The `Read` function is designed to read data from a memory file located
    # at `self.MemoryLocation`, if it exists. It reads the file line by line,
    # attempting to parse each line as JSON data. If a line fails to parse, an
    # error message is printed and the line is skipped. Successfully parsed
    # lines are then processed to ensure they contain required fields such as
    # 'engine', 'model', and 'encoding', which are populated with default
    # values from the object's attributes if necessary. The function also
    # calculates a 'tokens' value based on the content of the message, using
    # the `GetTokenCount` method, and appends the processed data to the
    # object's `Memory` list, excluding any system messages.

    def Read(self):
        # Read the memory file, if it exists.
        if os.path.exists(self.MemoryLocation):
            membuf=FF.ReadFile2List(self.MemoryLocation)
            for item in membuf:
                try:
                    mem=json.loads(item)
                except Exception as err:
                    print(f"ReadMemory line skipped: {err}")
                    continue
                # Don't allow embedding of system messages
                if 'role' in mem and mem['role'].lower()!='system':
                    if 'engine' not in mem:
                        mem['engine']=self.engine
                    if 'model' not in mem:
                        mem['model']=self.model
                    if 'encoding' not in mem:
                        mem['encoding']=self.encoding
                    if 'tokens' not in mem:
                        # Make sure tokens are based on the stored engine details
                        mem['tokens']=self.GetTokenCount(mem['content'])
                    self.Memory.append(mem)

    # The `Write` function is responsible for saving the contents of the
    # `Memory` list to a file located at `MemoryLocation`. Before writing, it
    # checks if there are any items in `Memory` and if a maximum memory limit
    # (`MaxMemory`) has been set. If a limit is set and the number of items in
    # `Memory` exceeds it, the function truncates `Memory` to only include the
    # most recent items up to the limit. It then opens the memory file,
    # iterates over each item in `Memory`, and writes it to the file in JSON
    # format, excluding any items with a 'system' role. Finally, the function
    # closes the file handle after all items have been written.

    def Write(self):
        # Do we have anything in memory?
        if self.Memory:

            # If MaxMemory is set, we only save that many items. Adjust local memory
            # as well.

            if self.MaxMemory>0 and len(self.Memory)>self.MaxMemory:
                self.Memory=self.Memory[-self.MaxMemory:]

            # Save the memory file

            fh=open(self.MemoryLocation,"w")
            for item in self.Memory:
                # Don't write out the system role
                if item['role'].lower()!='system':
                    s=json.dumps(item)+'\n'
                    fh.write(s)
            fh.close()

    # The `GetTokenCount` function calculates the number of tokens in a given
    # input data based on the specified engine and model. It first determines
    # which tokenizer to use depending on the engine, which can be 'openai',
    # 'huggingface', 'googleai', or 'cohere', and then uses the corresponding
    # tokenizer to encode the input data. The function then calculates the
    # number of tokens in the encoded data, with different engines requiring
    # different methods for tokenization, such as using `tiktoken` for 'openai'
    # or `AutoTokenizer` for 'huggingface' and 'googleai'. Finally, it returns
    # the calculated token count.

    def GetTokenCount(self,data):
        # Figure out which tokenizer to use.
        if self.engine=='openai':
            if self.encoding!=None:
                enc=tiktoken.get_encoding(self.encoding)
            else:
                enc=tiktoken.get_encoding(tiktoken.model.MODEL_TO_ENCODING[self.model])
        elif self.engine=='huggingface':
            enc=AutoTokenizer.from_pretrained(self.model)
        elif self.engine=='cohere':
            if self.usertokens is not None:
                Tokens=FF.ReadTokens(userhome=self.usertokens)
            else:
                Tokens=FF.ReadTokens(userhome=self.userhome)
            enc=cohere.ClientV2(api_key=Tokens['Cohere'])

        # Calculate current tokens in data
        if self.engine=='openai':
            current_tokens=len(enc.encode(data))
        elif self.engine=='huggingface':
            current_tokens=len(enc(data)["input_ids"])
        # SOMETHING BROKE IS THEIR SYSTEM
#        elif self.engine=='cohere':
#            current_tokens=len(enc.tokenize(text=data,model=self.model,offline=False).tokens)
        else:
            current_tokens=int((len(data)+24)/4)

        return current_tokens

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

    @DF.function_trapper(None)
    def MaintainTokenLimit(self):
        def count_tokens():
            return sum(message['tokens'] for message in messages)

        # Make a separate working copy of the original messages.
        messages=self.Memory.copy()

        # Get a starting point
        current_tokens=count_tokens()
        old_tokens=current_tokens

        # While tokens exceed the limit, remove elements
        while current_tokens>self.maxtokens:
            for i in range(len(messages)-1):
                if i<len(messages)-1:
                    # user/assistant now decoupled
                    if messages[i]['role'].lower()=="user" or messages[i]['role'].lower()=="assistant":
                        messages.pop(i)
                        break
                    """ Old way - depreciated
                    if messages[i]['role'].lower()=="user" and messages[i+1]['role'].lower()=="assistant":
                        # Remove the pair (two items)
                        messages.pop(i)
                        messages.pop(i)
                        break
                    elif messages[i]['role'].lower()=="user" and messages[i+1]['role'].lower()=="user":
                        # Remove only one item if two adjacent items are user/user
                        messages.pop(i)
                        break
                    """

            # Recalculate current tokens after removal
            current_tokens=count_tokens()
            # Check for the situation that we can't reduce the number of tokens.
            if old_tokens==current_tokens and current_tokens>self.maxtokens:
                print(f"{self.engine}/{self.model}: Token reductiion error. {current_tokens}>{self.maxtokens}")
                return None,current_tokens
            old_tokens=current_tokens

        # Return onle role/content for AI engine

        NewMessages=[]
        for msg in messages:
            js={}
            js['role']=msg['role']
            js['content']=msg['content']
            NewMessages.append(js)

        return NewMessages,current_tokens

    # This function prepares and sends a request to an AI service, then captures
    # the service’s reply. First it loads API tokens (credentials) from a
    # user-specific file so the program can authenticate with external AI engines.
    # If a token file location wasn’t explicitly provided, it falls back to a
    # default location.

    # Next it checks whether the requested AI engine is supported and that a
    # matching token is available. If so, it builds a set of parameters—like the
    # conversation messages, model name, and other behaviour settings—and calls the
    # appropriate engine-specific routine to get a response. It also handles a
    # couple of engine-specific options when needed.

    # If the engine is not recognized or any error occurs while calling the
    # service, the function records that no response was obtained and prints a
    # short diagnostic message pointing to the problem (for example, a missing or
    # invalid token).

    @DF.function_trapper(None)
    def JumpTable(self,messages,seed=0,mt=2048):
        # Read tokens
        if self.usertokens is not None:
            Tokens=FF.ReadTokens(userhome=self.usertokens)
        else:
            Tokens=FF.ReadTokens(userhome=self.userhome)

        # Add a test that the token is actually available

        try:
            if self.engine in self.AIJumpTable and self.engine in self.AITokenMap:
                params={}
                params["apikey"]=Tokens[self.AITokenMap[self.engine]]
                params["messages"]=messages
                params["model"]=self.model
                params["freqpenalty"]=self.freqpenalty
                params["temperature"]=self.temperature
                params["timeout"]=self.timeout

                if self.engine=='ollama':
                    params['mt']=mt
                if self.engine=='googleai':
                    params['UseOpenAI']=self.UseOpenAI

                self.response,self.completion=self.AIJumpTable[self.engine](**params)
            else:   # Engine not recognized.
                self.response=None
                self.completion=None
        except Exception as err:
            print(f"JumpTable ERROR: {sys.exc_info()[-1].tb_lineno}/{err}: Check token file")
            self.response=None
            self.completion=None

    # The `Response` function is a crucial component of a conversational AI
    # system. It takes in user input and generates a response based on the
    # system's current state and configuration. The function is designed to
    # manage the flow of information between the user, the AI model, and the
    # system's memory.

    # At the beginning of the function, it checks if the system needs to be
    # reset. If so, it calls the `Reset` method to initialize the system. It
    # also loads the system role only once, if a persona is specified and the
    # memory is empty. Additionally, if the system is not in isolation mode, it
    # reads any existing memory to ensure that the AI model has access to
    # previous conversations or context.

    # The function then adds the user's input to the memory using the `Put`
    # method with a key of `'user'`. This allows the AI model to consider the
    # user's input when generating a response. The function also maintains a
    # token limit for the engine/model using the `MaintainTokenLimit` method.
    # If this limit is exceeded, it sets `self.response` to `None` and returns
    # immediately.

    # If everything is in order, it sends messages to an AI service using its
    # internal state (`wm`, `self.engine`, `self.model`, etc.) as parameters
    # for its internal method called 'JumpTable'. After sending these messages
    # off for processing by an external service (likely some sort of language
    # model), this code then waits until said external operation completes
    # before continuing onward within itself - specifically checking whether
    # there was indeed any form output generated during such time via looking
    # at variable named "response".

    # If a response was generated by this point (i.e., not equaling None), said
    # output gets added onto what seems like another form internal storage
    # mechanism referred here under label 'assistant'. Furthermore updates
    # occur relating last seen result plus saving entire interaction history
    # should certain flag conditions ('save', 'isolation') evaluate True;
    # otherwise nothing gets persisted across separate invocations made against
    # same overall application context.

    # Lastly worth mentioning here too would involve conditional inclusion
    # timing related logging activities taking place right after successful
    # receipt back from aforementioned services - logging entries including
    # timestamps alongside specific details about models utilized during
    # execution plus total processing times observed throughout entire request
    # lifecycle up until current moment being recorded down into file located
    # somewhere according path defined within TimingLocation class attribute
    # belonging object instance itself where Response resides as method
    # definition belonging thereto.

    @DF.function_trapper(None)
    def Response(self,input):
        # Lock the model

        if self.ModelLock:
            self.ModelLock.Lock(expire=self.MaxModelExpire)

        # Reset the memory if needed

        if self.reset:
            self.Reset()

        # Load the system role only ONCE

        if self.persona is not None and self.persona.lower()!="none":
            SystemRole=self.GetPersona(self.persona,nsfw=self.allowNSFW,channel=self.discordChannel)
        else:
            SystemRole=self.SystemRoleDefault
        self.Put("system",SystemRole,reset=True)

        # Read any existing memory if not in isolation
        if not self.isolation:
            self.Read()

        knr=None
        uEKB=None
        if self.UseEKB:
            uEKB=EKB.ExpertKnowledgeBase(Base=self.MemoryLocation+'.ekb')

            knr=uEKB.Search(input)
            if knr:
                for blob in knr:
                    ans="The following is verified expert knowledge that serves as the definitive source for this topic. Treat this information as established fact and use it as the foundation for your response. You may rephrase, restructure, and expand upon this knowledge to provide a clear and helpful answer, but do not introduce information that contradicts or conflicts with what is provided here. If the user's question relates to this topic, base your response entirely on this expert knowledge rather than drawing from general training data. Present your answer with confidence, as this knowledge has been verified by domain experts.\n\n"+blob
                    self.Put("assistant",ans)

        # Add users input to the memory
        self.Put("user",input)

        # Maintain the token limit for the engine/model

        wm,ct=self.MaintainTokenLimit()
        if wm==None: # Will be None if over token limit
            self.response=None
            return None

        # Send AI service the messages

        startTime=time.time()
        rc=0
        msr=0
        self.response=None
        self.AIError=False
        while self.response==None:
            self.EnforceRatelimit()
            self.JumpTable(wm)

            # AI error, such as prohibited content, breaks retry loop
            if self.AIError:
                break

            # main retry level
            if self.response==None:
                time.sleep(self.retrytimeout)
                msr=0   # Reset the size counter
                if rc<self.maxretries:
                    rc+=1
                else:
                    break

            # Response size limitation check

            # This section addresses a specific edge case involving a single
            # failure mode. Certain models, particularly those hosted on Hugging
            # Face, have a tendency to perform a “dictionary dump,” defined here as
            # a condition in which the model outputs a large portion or the
            # entirety of its accessible internal context, token mappings, or
            # structured key value data in a single response, rather than
            # generating a constrained, task relevant reply.

            # The max response size handling below is designed to mitigate this
            # behavior. When a model enters this state, the output typically
            # exceeds defined size limits due to the uncontrolled expansion of
            # internal data into the response stream. This logic is kept separate
            # from the standard retry mechanism so that normal retries can be tuned
            # more conservatively, allowing a functioning model adequate time to
            # produce a coherent response. This approach is forceful, but it
            # remains the only method identified so far that provides consistent
            # and deliberate control over this issue.

            if self.maxrespsize>0 and len(self.response)>self.maxrespsize:
                time.sleep(self.maxrespretrytimeout)
                if msr<self.maxrespretry:
                    msr+=1
                else:
                    msr=0   # Reset the size counter
                    if rc<self.maxretries:
                        self.response=None
                        rc+=1
                    else:
                        break

        endTime=time.time()
        if self.timing:
            FF.AppendFile(self.TimingLocation,f"{datetime.datetime.fromtimestamp(startTime).strftime('%Y-%m-%d %H:%M:%S')} {self.engine} {self.model} {endTime-startTime:.6f}\n")

        # Check and write the response

        if self.response is not None:
            # Add the new response to AI memory
            self.Put("assistant",self.response)

            # Update and add the raw response
            self.UpdateLast("result",str(self.completion))

            # Save to disk
            if self.save and not self.isolation:
                self.Write()

        # Unock the model

        if self.ModelLock:
            self.ModelLock.Unlock()

        # response can be None

        return self.response

    # These functions appear are a collection of methods for interacting with
    # various AI chat models, including OpenAI, x.ai, OpenRouter, Anthropic,
    # Hugging Face, Together AI, Cohere, Ollama, and Perplexity. Each method
    # takes in parameters such as an API key, messages to send to the model,
    # the model to use, frequency penalty and temperature settings for
    # generating responses, and a timeout value. The methods then use these
    # parameters to create a client object for the respective AI service and
    # send a request to generate a completion based on the provided messages.
    # The response from the AI service is then processed and returned along
    # with additional information about the completion. Overall, this code
    # provides a unified interface for interacting with multiple AI chat
    # services.

    # gpt-5-nan0/mini   reasoning effort = minimal
    # gpt-5             minimal
    # gpt-5.1/2         none

    @DF.function_trapper(None)
    def GetOpenAI(self,apikey,messages,model,freqpenalty,temperature,timeout):
        # Required base parameters
        params={ "model": model, "messages": messages, "timeout": timeout }

        if 'gpt-5' in model:
            if 'nano' in model or 'mini' in model or model=='gpt-5':
                params['reasoning_effort']='minimal'
            else:
                if 'chat' not in model:
                    params['reasoning_effort']='none'

        # Add temperature and frequency penalty
        if 'chat' in model or 'gpt-5' not in model:
            params['temperature']=temperature
            params['frequency_penalty']=freqpenalty

        clientAI=openai.OpenAI(api_key=apikey)
        try:
            completion=clientAI.chat.completions.create(**params)
        except Exception as err:
            print(f"ERR: {err}");
            completion=clientAI.chat.completions.create(
                model=model,
                messages=messages,
                timeout=timeout )

        clientAI.close()

        self.stop=completion.choices[0].finish_reason.lower()
        if self.stop!='stop':
            self.AIError=True

        response=completion.choices[0].message.content.strip()
        return response,completion

    @DF.function_trapper(None)
    def GetNVidia(self,apikey,messages,model,freqpenalty,temperature,timeout):
        clientAI=openai.OpenAI(api_key=apikey,base_url="https://integrate.api.nvidia.com/v1")
        completion=clientAI.chat.completions.create(
                model=model,
                frequency_penalty=freqpenalty,
                temperature=temperature,
                messages=messages,
                timeout=timeout
            )
        clientAI.close()

        self.stop=completion.choices[0].finish_reason.lower()
        if self.stop!='stop':
            self.AIError=True

        response=completion.choices[0].message.content.strip()
        return response,completion

    @DF.function_trapper(None)
    def GetMistral(self,apikey,messages,model,freqpenalty,temperature,timeout):
        clientAI=openai.OpenAI(api_key=apikey,base_url="https://api.mistral.ai/v1/")
        completion=clientAI.chat.completions.create(
                model=model,
                frequency_penalty=freqpenalty,
                temperature=temperature,
                messages=messages,
                timeout=timeout
            )
        clientAI.close()

        self.stop=completion.choices[0].finish_reason.lower()
        if self.stop!='stop':
            self.AIError=True

        response=completion.choices[0].message.content.strip()
        return response,completion

    @DF.function_trapper(None)
    def GetxAI(self,apikey,messages,model,freqpenalty,temperature,timeout):
        clientAI=openai.OpenAI(api_key=apikey,base_url="https://api.x.ai/v1")
        try:
            completion=clientAI.chat.completions.create(
                    model=model,
                    frequency_penalty=freqpenalty,
                    temperature=temperature,
                    messages=messages,
                    timeout=timeout
                )
        except Exception as err:
            completion=clientAI.chat.completions.create(
                    model=model,
                    temperature=temperature,
                    messages=messages,
                    timeout=timeout
                )
        clientAI.close()

        self.stop=completion.choices[0].finish_reason.lower()
        if self.stop!='stop':
            self.AIError=True

        response=completion.choices[0].message.content.strip()
        return response,completion

    @DF.function_trapper(None)
    def GetGoogleAI(self, apikey, messages, model, freqpenalty, temperature, timeout, UseOpenAI=False):
        # Sub function updated for the new SDK structure
        def PrepareGeminiHistory(messages):
            gemini_messages = []
            system_instruction = None
            for message in messages:
                role = message.get("role")
                content = message.get("content")
                if role == "system":
                    system_instruction = content
                elif role == "user":
                    # New SDK uses Content objects with Part objects
                    gemini_messages.append(google.genai.types.Content(
                        role="user",
                        parts=[google.genai.types.Part(text=content)]
                    ))
                elif role == "assistant":
                    gemini_messages.append(google.genai.types.Content(
                        role="model",
                        parts=[google.genai.types.Part(text=content)]
                    ))
            return system_instruction, gemini_messages

        # Safety settings using the new SDK's type-safe classes
        safety_settings = [
            google.genai.types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
            google.genai.types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
            google.genai.types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
            google.genai.types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE")
        ]

        if UseOpenAI == True:
            # OpenAI logic remains untouched for compatibility
            clientAI = openai.OpenAI(api_key=apikey, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
            try:
                completion = clientAI.chat.completions.create(
                    model=model,
                    frequency_penalty=freqpenalty,
                    temperature=temperature,
                    messages=messages,
                    timeout=timeout
                )
            except:
                completion = clientAI.chat.completions.create(
                    model=model,
                    temperature=temperature,
                    messages=messages,
                    timeout=timeout
                )
            clientAI.close()

            self.stop = completion.choices[0].finish_reason.lower()
            if self.stop != 'stop':
                self.AIError = True

            response = completion.choices[0].message.content.strip()
            return response, completion

        else:
            # --- NEW GENAI SDK NATIVE CODE ---
            # 1. Initialize Client (replacing genai.configure)
            client = google.genai.Client(api_key=apikey)

            sysmsg, history = PrepareGeminiHistory(messages)
            if sysmsg == None:
                sysmsg = "You are a helpful assistant"

            # 2. Setup Generation Config (replacing genai.GenerationConfig)
            # Note: frequency_penalty is now supported in the new SDK config
            if 'flash-lite' in model:
                gencfg = google.genai.types.GenerateContentConfig(
                    temperature=temperature,
                    system_instruction=sysmsg,
                    safety_settings=safety_settings
                )
            else:
                gencfg = google.genai.types.GenerateContentConfig(
                    temperature=temperature,
                    frequency_penalty=freqpenalty,
                    system_instruction=sysmsg,
                    safety_settings=safety_settings
                )

            try:
                # 3. Generate Content (replacing start_chat/send_message)
                # We pass the entire history; the last message is treated as the current prompt.
                completion = client.models.generate_content(
                    model=model,
                    contents=history,
                    config=gencfg
                )

                # 4. Handle Response mapping for "drop-in" compatibility
                # The new SDK uses an Enum for finish_reason (e.g., FinishReason.STOP)
                # .name gives the string "STOP", which .lower() turns into "stop"
                self.stop = completion.candidates[0].finish_reason.name.lower()

                if self.stop != "stop":
                    self.AIError = True
                    response = None
                else:
                    # completion.text is a shortcut for completion.candidates[0].content.parts[0].text
                    response = completion.text

                return response, completion

            except Exception as e:
                # Handle API errors to prevent crashing the large code set
                self.AIError = True
                print(f"Gemini SDK Error: {str(e)}")
                return None, None

    @DF.function_trapper(None)
    def GetOpenRouter(self,apikey,messages,model,freqpenalty,temperature,timeout):
        clientAI=openai.OpenAI(api_key=apikey,base_url="https://openrouter.ai/api/v1")
        completion=clientAI.chat.completions.create(
                model=model,
                frequency_penalty=freqpenalty,
                temperature=temperature,
                messages=messages,
                timeout=timeout
            )
        clientAI.close()

        self.stop=completion.choices[0].finish_reason.lower()
        if self.stop!='stop':
            self.AIError=True

        response=completion.choices[0].message.content.strip()
        return response,completion

    @DF.function_trapper(None)
    def GetAnthropic(self,apikey,messages,model,freqpenalty,temperature,timeout):
        sysmsg=messages[0]['content']
        if len(messages)==1:
            messages.append(messages[0])
            sysmsg=""

        clientAI=anthropic.Anthropic(api_key=apikey,timeout=timeout)
        completion=clientAI.messages.create(
                system=sysmsg,
                model=model,
                max_tokens=4096,
                temperature=temperature,
                messages=messages[1:],
                stream=False
            )
        clientAI.close()

        if completion.stop_reason:
            self.stop=completion.stop_reason.lower()
            if self.stop not in ("end_turn", "stop_sequence"):
                self.AIError = True

        response=completion.content[0].text.strip()
        return response,completion

    @DF.function_trapper(None)
    def GetHuggingFace(self,apikey,messages,model,freqpenalty,temperature,timeout):
        clientAI=huggingface_hub.InferenceClient(token=apikey,timeout=timeout)
        completion=clientAI.chat.completions.create(
                model=model,
                frequency_penalty=freqpenalty,
                temperature=temperature,
                messages=messages,
                stream=False
            )

        self.stop=completion.choices[0].finish_reason.lower()
        if self.stop!='stop':
            self.AIError=True

        response=completion.choices[0].message.content.strip()
        return response,completion

    @DF.function_trapper(None)
    def GetTogetherAI(self,apikey,messages,model,freqpenalty,temperature,timeout):
        clientAI=together.Together(api_key=apikey, timeout=timeout)
        completion=clientAI.chat.completions.create(
                model=model,
                frequency_penalty=freqpenalty,
                temperature=temperature,
                messages=messages,
                stream=False
            )

        self.stop=completion.choices[0].finish_reason.lower()
        if self.stop!='stop':
            self.AIError=True

        response=completion.choices[0].message.content.strip()
        return response,completion

    @DF.function_trapper(None)
    def GetCohere(self,apikey,messages,model,freqpenalty,temperature,timeout):
        def ContactCohere(apikey,messages,model,freqpenalty,temperature,timeout,safemode):
            clientAI=cohere.ClientV2(api_key=apikey, timeout=timeout)
            completion=clientAI.chat(
                    model=model,
                    frequency_penalty=freqpenalty,
                    temperature=temperature,
                    messages=messages,
                    safety_mode=safemode
                )

            if completion.finish_reason:
                self.stop=completion.finish_reason.lower()
                if self.stop!="complete":
                    self.AIError=True

            response=completion.message.content[0].text.strip()

            return response,completion

        # Not all model allow unfilitered access
        try:
            safemode="NONE"
            response,completion=ContactCohere(apikey,messages,model,freqpenalty,temperature,timeout,safemode)
            return response,completion
        except Exception as err:
            safemode="CONTEXTUAL"
            response,completion=ContactCohere(apikey,messages,model,freqpenalty,temperature,timeout,safemode)
            return response,completion

    @DF.function_trapper(None)
    def GetOllama(self,apikey,messages,model,freqpenalty,temperature,timeout,seed=0,mt=2048):
        options={
                "temperature": temperature,
                "frequency_penalty": freqpenalty,
                "seed": seed,
                "num_ctx": mt
            }
        clientAI=ollama.Client(timeout=timeout)
        completion=clientAI.chat(
                stream=False,
                think=False,
                model=model,
                options=options,
                messages=messages
            )
        response=completion['message']['content'].strip()
        return response,completion

    @DF.function_trapper(None)
    def GetPerplexity(self,apikey,messages,model,freqpenalty,temperature,timeout):
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
        completion=None
        if response.status_code==200:
            completion=response.json()

        if completion is not None:
            self.stop=completion["choices"][0].get("finish_reason", "").lower()
            if self.stop!="stop":
                self.AIError=True
        else:
            self.stop='error'
            self.AIError=True
            return None, None

        response=completion["choices"][0]["message"]["content"].strip()

        # If there are citations in the choices text portion, append
        # them to the response. This is not neccessary, but it does look
        # nice and adds to the bot's presence.

        IsCitations=any(re.search(r'\[\d+\]', choice.get("message", {}).get("content", "")) for choice in completion.get("choices", []))
        if IsCitations:
            response+="\n\n"+"\n".join(f"<{url}>" for url in completion['citations'])
        return response,completion

    # This function determines the appropriate configuration file for a
    # companion bot based on whether the settings are for a specific channel or
    # global and whether they are SFW (safe for work) or NSFW (not safe for
    # work). It prioritizes NSFW channel-specific files, then SFW
    # channel-specific files, followed by NSFW global files, and finally SFW
    # global files. If none of these files exist, it falls back to the provided
    # base filename to avoid potential errors in case the file is missing. This
    # ensures the system can gracefully handle configuration scenarios without
    # crashing.

    # NSFW is an honor system approach. There is no real ways for the system to
    # know if a persona is really safe for work (child friendly).

    @DF.function_trapper(None)
    def GetPersona(self,basename,channel=None,nsfw=False):
        if channel:
            # NSFW channel version
            refname=f"{self.PersonaConfig}/{basename}/{basename}.{channel}.system.nsfw"
            if nsfw and os.path.exists(refname):
                self.nsfw=True
                return FF.ReadFile(refname).replace('\n','\\n').replace("'","\'").replace('"',"'").strip()

            # SFW channel version
            refname=f"{self.PersonaConfig}/{basename}/{basename}.{channel}.system"
            if os.path.exists(refname):
                return FF.ReadFile(refname).replace('\n','\\n').replace("'","\'").replace('"',"'").strip()

        # NSFW global version
        refname=f"{self.PersonaConfig}/{basename}/{basename}.system.nsfw"
        if nsfw and os.path.exists(refname):
            self.nsfw=True
            return FF.ReadFile(refname).replace('\n','\\n').replace("'","\'").replace('"',"'").strip()

        # SFW global version
        refname=f"{self.PersonaConfig}/{basename}/{basename}.system"
        if os.path.exists(refname):
            return FF.ReadFile(refname).replace('\n','\\n').replace("'","\'").replace('"',"'").strip()

        return None
