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

import sys
import os
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
import together
import cohere
import huggingface_hub
import anthropic
from transformers import AutoTokenizer
from googleapiclient.discovery import build
import google.generativeai as genai

import DecoratorFunctions as DF
import CoreFunctions as CF
import FileFunctions as FF

PersonaConfig="/home/JackrabbitAI/Personas"

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

    def __init__(self,engine,model,maxtokens,encoding=None,persona=None,user=None,userhome=None,maxmem=100,freqpenalty=0.73,temperature=0.31,seed=0,timeout=300,reset=False,save=True,timing=True,isolation=False,retry=7,retrytimeout=37,maxrespsize=0,maxrespretry=7,maxrespretrytimeout=37):
        self.engine=engine.lower()  # AI engine for a memory item (token count)
        self.model=model            # AI model being used
        self.maxtokens=maxtokens    # Maximum number of tokens allowed for a given model
        self.encoding=encoding
        self.MaxMemory=maxmem
        self.freqpenalty=freqpenalty
        self.temperature=temperature
        self.seed=seed
        self.timeout=timeout        # Timeout for connection to take place
        self.timing=timing          # Are we timing the AI api call?
        self.persona=persona        # the AI persona
        self.completion=None
        self.response=None
        self.reset=reset            # Do we reset the memory before the AI functionality?
        self.save=save              # Do we save any memory at all?
        self.isolation=isolation    # Are we wanting an isolated response (No memory?)
        self.maxretries=retry       # Number of times to retry a request
        self.retrytimeout=retrytimeout # Sleep between retries
        self.maxrespsize=maxrespsize # Some models are prone to "dictionary dumps", reject any response larger then this. 0=no rejection
        self.maxrespretry=maxrespretry # Number of time to retry size rejection
        self.maxrespretrytimeout=maxrespretrytimeout # Number of seconds to wait between retries
        self.Memory=[]

        if self.engine=='openai' and self.encoding==None:
            if 'gpt-4o' in self.model:
                self.encoding="o200k_base"
            else:
                self.encoding="cl100k_base"

        self.SetStorage(user,userhome)

    # Change the engine

    def SetEngine(self,engine):
        self.engine=engine.lower()
        if self.engine=='openai':
            if 'gpt-4o' in self.model:
                self.encoding="o200k_base"
            else:
                self.encoding="cl100k_base"

    # Change the model

    def SetModel(self,model):
        self.model=model

    # Change the maximum number of tokens

    def SetModel(self,maxtokens):
        self.maxtokens=maxtokens

    # Change the encoding

    def SetEncoding(self,encoding):
        self.encoding=encoding

    def FreqPenalty(self,freqpenalty):
        self.freqpenalty=freqpenalty

    def Temperature(self,temperture):
        self.temperature=temperature

    def Timeout(self,timeout):
        self.timeout=timeout

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
        # Set user and userhome
        self.user=user
        self.userhome=userhome

        # if $HOME is not defined
        self.MemoryLocation=f"/home/JackrabbitAI/Memory/NoUser.memory"
        self.TimingLocation=f"/home/JackrabbitAI/Memory/NoUser.timing"

        # Check userhome. This overrides the entire user system,
        # setting the default directory to the program.

        if userhome!=None:
            self.MemoryLocation=f"{userhome}/{os.path.basename(CF.RunningName)}.memory"
            self.TimingLocation=f"{userhome}/{os.path.basename(CF.RunningName)}.timing"
            return

        # Figure out where to store the memory files
        if user==None:
            home=os.environ.get('HOME')
            if home:
                self.MemoryLocation=f"{home}/.JackrabbitAI/Memory/{os.path.basename(CF.RunningName)}.memory"
                self.TimingLocation=f"{home}/.JackrabbitAI/Memory/{os.path.basename(CF.RunningName)}.timing"
        else:
            # ADD: storage location
            self.MemoryLocation=f"/home/JackrabbitAI/Memory/{user}.memory"
            self.TimingLocation=f"/home/JackrabbitAI/Memory/{user}.timing"
        FF.mkdir(os.path.dirname(self.MemoryLocation))

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

    def Put(self,role,data):
        self.Memory.append({ "role":role,"content":data,
            "engine":self.engine,
            "model":self.model,
            "encoding":self.encoding,
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
            return sum(message['tokens'] for message in self.Memory)

        # Make a separate working copy of the original messages.
        messages=self.Memory.copy()

        # Get a starting point
        current_tokens=count_tokens()
        old_tokens=current_tokens

        # While tokens exceed the limit, remove elements
        while current_tokens>self.maxtokens:
            for i in range(len(messages)-1):
                if i<len(messages)-1:
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

    # The `JumpTable` function is a method that appears to be part of a class,
    # responsible for handling requests to various AI engines. It takes in
    # several parameters, including `messages`, `engine`, `model`,
    # `freqpenalty`, `temperature`, `timeout`, and optional parameters `seed`
    # and `mt`. The function reads tokens from a file, then uses a series of
    # if-elif statements to determine which AI engine to interact with based on
    # the value of the `engine` parameter. Depending on the engine, it calls a
    # corresponding method (e.g. `GetOpenAI`, `GetTogetherAI`, etc.) to
    # retrieve a response and completion, handling exceptions by setting the
    # response and completion to None if an error occurs. If the engine is not
    # recognized, it also sets the response and completion to None.

    @DF.function_trapper(None)
    def JumpTable(self,messages,engine,model,freqpenalty,temperature,timeout,seed=0,mt=2048):
        # Read tokens
        Tokens=FF.ReadTokens(userhome=self.userhome)

        try:
            if self.engine=='openai':
                self.response,self.completion=self.GetOpenAI(Tokens['OpenAI'],messages,self.model,self.freqpenalty,self.temperature,self.timeout)
            elif self.engine=='googleai':
               self.response,self.completion=self.GetGoogleAI(Tokens['GoogleAI'],messages,self.model,self.freqpenalty,self.temperature,self.timeout)
            elif self.engine=='xai':
               self.response,self.completion=self.GetxAI(Tokens['xAI'],messages,self.model,self.freqpenalty,self.temperature,self.timeout)
            elif self.engine=='cohere':
                self.response,self.completion=self.GetCohere(Tokens['Cohere'],messages,self.model,self.freqpenalty,self.temperature,self.timeout)
            elif self.engine=='togetherai':
                self.response,self.completion=self.GetTogetherAI(Tokens['TogetherAI'],messages,self.model,self.freqpenalty,self.temperature,self.timeout)
            elif self.engine=='ollama':
                self.response,self.completion=self.GetOllama(Tokens['Ollama'],messages,self.model,self.freqpenalty,self.temperature,self.timeout,seed=self.seed,mt=mt)
            elif self.engine=='openrouter':
               self.response,self.completion=self.GetOpenRouter(Tokens['OpenRouter'],messages,self.model,self.freqpenalty,self.temperature,self.timeout)
            elif self.engine=='anthropic':
               self.response,self.completion=self.GetAnthropic(Tokens['Anthropic'],messages,self.model,self.freqpenalty,self.temperature,self.timeout)
            elif self.engine=='perplexity':
                self.response,self.completion=self.GetPerplexity(Tokens['Perplexity'],messages,self.model,self.freqpenalty,self.temperature,self.timeout)
            elif self.engine=='huggingface':
                self.response,self.completion=self.GetHuggingFace(Tokens['HuggingFace'],messages,self.model,self.freqpenalty,self.temperature,self.timeout)
            # Engine not recognized.
            else:
                self.response=None
                self.completion=None
        except Exception as err:
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

#    @DF.function_trapper(None)
    def Response(self,input):
        # Reset the memory if needed

        if self.reset:
            self.Reset()

        # Load the system role only ONCE

        if self.persona.lower()!="none" and self.Memory==None:
            SystemRole=self.GetPersona(self.persona)
            self.Put("system", SystemRole)

        # Read any existing memory if not in isolation
        if not self.isolation:
            self.Read()

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
        while self.response==None:
            self.JumpTable(wm,self.engine,self.model,self.freqpenalty,self.temperature,self.timeout,seed=self.seed,mt=self.maxtokens)

            # main retry level
            if self.response==None:
                time.sleep(self.retrytimeout)
                msr=0   # Reset the size counter
                if rc<self.maxretries:
                    rc+=1
                else:
                    break

            # Response size limitation check
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

        # if response is empty exit early, don't save empty response.

        if self.response==None:
            return None

        # Add the new response to AI memory
        self.Put("assistant",self.response)

        # Update and add the raw response
        self.UpdateLast("result",str(self.completion))

        # Save to disk
        if self.save and not self.isolation:
            self.Write()

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

    @DF.function_trapper(None)
    def GetOpenAI(self,apikey,messages,model,freqpenalty,temperature,timeout):
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
        response=completion.choices[0].message.content.strip()
        return response,completion

    @DF.function_trapper(None)
    def GetGoogleAI(self,apikey,messages,model,freqpenalty,temperature,timeout,openai=False):
        # Sub functions
        def PrepareGeminiHistory(messages):
            # (Conversion function remains the same)
            gemini_messages = []
            system_instruction = None
            for message in messages:
                role = message.get("role")
                content = message.get("content")
                if role == "system":
                    system_instruction = content
                elif role == "user":
                    gemini_messages.append({"role": "user", "parts": [content]})
                elif role == "assistant":
                    gemini_messages.append({"role": "model", "parts": [content]})
            return system_instruction, gemini_messages

        # function code

        safety_settings=[
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]

        if openai==True:
            # Works exceptionally well but does not allow disabiling the safety settings
            clientAI=openai.OpenAI(api_key=apikey,base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

            try:
                completion=clientAI.chat.completions.create(
                        model=model,
                        frequency_penalty=freqpenalty,
                        temperature=temperature,
                        messages=messages,
                        timeout=timeout
                    )
            except:
                completion=clientAI.chat.completions.create(
                        model=model,
                        temperature=temperature,
                        messages=messages,
                        timeout=timeout
                    )
            clientAI.close()
            response=completion.choices[0].message.content.strip()
            return response,completion
        else:
            # Use Gemini native code
            sysmsg,history=PrepareGeminiHistory(messages)
            if sysmsg==None:
                sysmsg="You are a helpful assistant"

            if model=='gemini-2.5-flash-lite':
                gencfg=genai.GenerationConfig(temperature=temperature)
            else:
                gencfg=genai.GenerationConfig(temperature=temperature,frequency_penalty=freqpenalty)

            genai.configure(api_key=apikey)
            model = genai.GenerativeModel(
                model_name=model,
                system_instruction=sysmsg,
                safety_settings=safety_settings,
                generation_config=gencfg)
            chat=model.start_chat(history=history)

            prompt=history[-1]['parts'][0]
            completion=chat.send_message(prompt)
            response=completion.text
            return response,completion

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
    #    stop=completion.choices[0].finish_reason
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
        if response.status_code==200:
            completion=response.json()

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

    @DF.function_trapper(None)
    def GetPersona(basename,channel=None,nsfw=False):
        if channel:
            # NSFW channel version
            refname=f"{PersonaConfig}/{basename}/{basename}.{channel}.system.nsfw"
            if nsfw and os.path.exists(refname):
                return FF.ReadFile(refname).replace('\n','\\n').replace("'","\'").replace('"',"'").strip()

            # SFW channel version
            refname=f"{PersonaConfig}/{basename}/{basename}.{channel}.system"
            if os.path.exists(refname):
                return FF.ReadFile(refname).replace('\n','\\n').replace("'","\'").replace('"',"'").strip()

        # NSFW global version
        refname=f"{PersonaConfig}/{basename}/{basename}.system.nsfw"
        if nsfw and os.path.exists(refname):
            return FF.ReadFile(refname).replace('\n','\\n').replace("'","\'").replace('"',"'").strip()

        # SFW global version
        refname=f"{PersonaConfig}/{basename}/{basename}.system"
        if os.path.exists(refname):
            return FF.ReadFile(refname).replace('\n','\\n').replace("'","\'").replace('"',"'").strip()

        return None
