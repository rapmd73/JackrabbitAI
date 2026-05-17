#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Jackrabit AI
# 2024-2026 Copyright © Robert APM Darin
# All rights reserved unconditionally.

# Context-Aware Versioned Memory

import sys
sys.path.append('/home/GitHub/JackrabbitDLM')
import os
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib

import CoreFunctions as CF
import FileFunctions as FF

import DLMLocker as DLM

class ContextAwareVersionedMemory:
    # Purpose:
    # Initializes a new ContextAwareVersionedMemory instance with configurable parameters for memory management behavior.
    #
    # Explanation for Beginners:
    # When you create a new CAVM object, this method sets up all the internal configurations that control how the memory system works. Think of it as setting the rules for how your memory system will behave - how similar conversations need to be to be grouped together, how long to remember things, how quickly old memories fade, etc.
    #
    # Technical Details:
    # This constructor sets up:
    # - Stop words list: Common words like "the", "is", "and" that are filtered out during processing
    # - Word reduction mapping: Normalizes words to their base forms (e.g., "running" -> "run")
    # - Configuration parameters that control memory behavior:
    #   * ProfileDecay: How much older memories fade in influence (0.95 = 5% fading per update)
    #   * MinTokensPerMemory: Minimum meaningful content needed to store a memory (2 tokens)
    #   * SimilarityThreshold: How similar conversations need to be to be grouped (0.43 = 43% similarity)
    #   * DormantDays/HardDeleteDays: When to archive/delete inactive memories
    #   * ContextCountDefault: How many key terms to store as a summary of each memory chain
    #   * Base: Where to save memory data on disk
    # - Creates the storage directory if it doesn't exist
    # - Loads any previously dormant chain identifiers
    #
    # Parameters:
    # - ProfileDecay (float, default 0.95): Decay factor for older versions in a chain. Values closer to 1.0 mean slower fading; values closer to 0.0 mean faster fading.
    # - MinTokensPerMemory (int, default 2): Minimum number of meaningful tokens required to create a memory entry. Prevents storing meaningless fragments.
    # - SimilarityThreshold (float, default 0.43): Minimum similarity score (0.0 to 1.0) required for a new exchange to be considered part of an existing chain.
    # - DormantDays (int, default 30): Number of days of inactivity after which a chain is considered dormant.
    # - HardDeleteDays (int, default 90): Number of days of inactivity after which a chain is permanently deleted.
    # - ContextCountDefault (int, default 23): Number of top tokens to extract and store as a summary/context for each chain.
    # - Base (str, default '/home/JackrabbitAI/Memory/CAVM'): Filesystem path where chain data will be persisted.
    #
    # Usage Example:
    # ```python
    # # Create a CAVM instance with default settings
    # cavm = ContextAwareVersionedMemory()
    #
    # # Create a CAVM instance with custom settings for a specific use case
    # cavm_custom = ContextAwareVersionedMemory(
    #     ProfileDecay=0.90,    # Faster fading of old memories
    #     SimilarityThreshold=0.5, # Require higher similarity to group conversations
    #     DormantDays=7,        # Consider chains dormant after just one week
    #     Base='/tmp/my_cavm_data' # Store data in a custom location
    # )
    # ```
    #
    # Important Notes:
    # - The constructor does not immediately load all chain data into memory for efficiency - data is loaded on-demand when needed
    # - All file paths are automatically created if they don't exist
    # - The stop words list and word reduction mappings are designed for English language processing

    def __init__(self,
                 ProfileDecay=0.95,           # decay factor for old versions (optional visual ageing)
                 MinTokensPerMemory=2,
                 SimilarityThreshold=0.43,    # for chain matching (topic identity)
                 DormantDays=30,
                 HardDeleteDays=90,
                 ContextCountDefault=23,
                 Base='/home/JackrabbitAI/Memory/CAVM'):

        self.STOP_WORDS = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'shall',
            'should', 'may', 'might', 'must', 'can', 'could', 'i', 'you', 'he',
            'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my',
            'your', 'his', 'its', 'our', 'their', 'this', 'that', 'these', 'those',
            'if', 'then', 'else', 'for', 'and', 'nor', 'but', 'or', 'yet', 'so',
            'to', 'of', 'in', 'on', 'at', 'by', 'with', 'from', 'up', 'about',
            'into', 'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'under', 'again', 'further', 'once', 'here', 'there', 'all',
            'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some',
            'such', 'no', 'not', 'only', 'own', 'same', 'than', 'too', 'very',
            'as', 'said', 'say', 'says', 'told', 'tell', 'tells', 'asked', 'ask',
            'asks', 'went', 'go', 'goes', 'come', 'comes', 'came', 'get', 'gets',
            'got', 'make', 'makes', 'made', 'know', 'knows', 'knew', 'think',
            'thinks', 'thought', 'take', 'takes', 'took', 'see', 'sees', 'saw',
            'want', 'wants', 'wanted', 'use', 'uses', 'used', 'find', 'finds',
            'found', 'give', 'gives', 'gave', 'put', 'puts', 'keep', 'keeps',
            'kept', 'let', 'lets', 'begin', 'begins', 'began', 'show', 'shows',
            'showed', 'hear', 'hears', 'heard', 'play', 'plays', 'played', 'run',
            'runs', 'ran', 'move', 'moves', 'moved', 'live', 'lives', 'lived',
            'believe', 'believes', 'believed', 'bring', 'brings', 'brought',
            'happen', 'happens', 'happened', 'write', 'writes', 'wrote', 'provide',
            'provides', 'provided', 'sit', 'sits', 'sat', 'stand', 'stands',
            'stood', 'lose', 'loses', 'lost', 'pay', 'pays', 'paid', 'meet',
            'meets', 'met', 'include', 'includes', 'included', 'continue',
            'continues', 'continued', 'set', 'sets', 'learn', 'learns', 'learned',
            'change', 'changes', 'changed', 'lead', 'leads', 'led', 'understand',
            'understands', 'understood', 'watch', 'watches', 'watched', 'follow',
            'follows', 'followed', 'stop', 'stops', 'stopped', 'create', 'creates',
            'created', 'speak', 'speaks', 'spoke', 'read', 'reads', 'allow',
            'allows', 'allowed', 'add', 'adds', 'added', 'spend', 'spends',
            'spent', 'grow', 'grows', 'grew', 'open', 'opens', 'opened', 'walk',
            'walks', 'walked', 'win', 'wins', 'won', 'offer', 'offers', 'offered',
            'remember', 'remembers', 'remembered', 'love', 'loves', 'loved',
            'consider', 'considers', 'considered', 'appear', 'appears', 'appeared',
            'buy', 'buys', 'bought', 'wait', 'waits', 'waited', 'serve', 'serves',
            'served', 'die', 'dies', 'died', 'send', 'sends', 'sent', 'expect',
            'expects', 'expected', 'build', 'builds', 'built', 'stay', 'stays',
            'stayed', 'fall', 'falls', 'fell', 'cut', 'cuts', 'reach', 'reaches',
            'reached', 'kill', 'kills', 'killed', 'remain', 'remains', 'remained'
        }
        self.REDUCE = {
            'acquire': 'get', 'obtain': 'get', 'procure': 'get', 'attain': 'get',
            'purchase': 'buy',
            'commence': 'start', 'begin': 'start', 'initiate': 'start',
            'terminate': 'end', 'finish': 'end', 'conclude': 'end', 'cease': 'end',
            'assist': 'help', 'aid': 'help', 'support': 'help',
            'inform': 'tell', 'notify': 'tell', 'advise': 'tell',
            'inquire': 'ask', 'question': 'ask',
            'utilize': 'use', 'employ': 'use',
            'endeavor': 'try', 'attempt': 'try',
            'comprehend': 'understand', 'grasp': 'understand',
            'demonstrate': 'show', 'display': 'show', 'exhibit': 'show',
            'construct': 'build', 'create': 'build', 'assemble': 'build',
            'destroy': 'break', 'demolish': 'break', 'ruin': 'break',
            'remove': 'delete', 'erase': 'delete', 'eliminate': 'delete',
            'insert': 'add', 'include': 'add', 'append': 'add',
            'discover': 'find', 'locate': 'find',
            'examine': 'check', 'inspect': 'check', 'verify': 'check',
            'select': 'pick', 'choose': 'pick',
            'require': 'need',
            'desire': 'want', 'wish': 'want',
            'repair': 'fix', 'mend': 'fix', 'restore': 'fix',
            'connect': 'link', 'join': 'link', 'attach': 'link',
            'disconnect': 'unlink', 'detach': 'unlink',
            'separate': 'split', 'divide': 'split',
            'combine': 'merge', 'unite': 'merge',
            'transfer': 'move', 'relocate': 'move', 'shift': 'move',
            'remain': 'stay', 'persist': 'stay',
            'depart': 'leave', 'exit': 'leave',
            'arrive': 'come', 'reach': 'come',
            'prior': 'before', 'previous': 'before',
            'subsequent': 'after', 'following': 'after',
            'sufficient': 'enough', 'adequate': 'enough',
            'complete': 'full', 'entire': 'full',
            'additional': 'more', 'extra': 'more',
            'numerous': 'many', 'several': 'many',
            'small': 'little', 'tiny': 'little',
            'large': 'big', 'huge': 'big', 'enormous': 'big',
            'rapid': 'fast', 'quick': 'fast', 'swift': 'fast',
            'difficult': 'hard', 'tough': 'hard',
            'simple': 'easy', 'effortless': 'easy',
            'incorrect': 'wrong', 'mistaken': 'wrong',
            'correct': 'right', 'accurate': 'right',
            'identical': 'same', 'equal': 'same',
            'distinct': 'other', 'different': 'other',
            'essential': 'need', 'necessary': 'need', 'vital': 'need',
            'superior': 'better', 'improved': 'better',
            'inferior': 'worse',
            'maximum': 'most', 'greatest': 'most',
            'minimum': 'least', 'smallest': 'least',
            'immediately': 'now', 'instantly': 'now',
            'previously': 'ago', 'formerly': 'ago',
            'subsequently': 'later', 'afterward': 'later',
            'presently': 'now', 'currently': 'now',
            'occasionally': 'sometimes', 'periodically': 'sometimes',
            'never': 'not', 'seldom': 'rarely',
            'always': 'ever', 'forever': 'ever',
            'perhaps': 'maybe', 'possibly': 'maybe',
            'certainly': 'yes', 'definitely': 'yes', 'surely': 'yes',
        }
        self.UseReduce = True

        self.PROFILE_DECAY = ProfileDecay
        self.MIN_TOKENS_PER_MEMORY = MinTokensPerMemory
        self.SIMILARITY_THRESHOLD = SimilarityThreshold
        self.DORMANT_DAYS = DormantDays
        self.HARD_DELETE_DAYS = HardDeleteDays
        self.CONTEXT_COUNT_DEFAULT = ContextCountDefault

        self.base = Base if Base is not None else '/home/JackrabbitAI/Memory/CAVM'
        self.profiles = None      # loaded on demand
        self.dirty = False
        FF.mkdir(self.base)
        self.dormant_chains = self.LoadDormant()

    # LockManager Decorator Documentation
    # 
    # Purpose:
    # Provides thread-safe access to CAVM methods by implementing distributed locking using JackrabbitDLM (DLM).
    # 
    # Explanation for Beginners:
    # Imagine multiple parts of your program trying to read or write to the same memory system at the same time. Without coordination, this could lead to corrupted data or unexpected behavior. The LockManager decorator acts like a traffic cop, ensuring that only one part of the program can access the memory system at any given moment. When a method finishes its work, it releases the lock so another part can proceed.
    # 
    # Technical Details:
    # This decorator wraps public methods of the ContextAwareVersionedMemory class to ensure exclusive access during execution. It:
    # 1. Creates a DLM.Locker instance tied to the CAVM base directory
    # 2. Acquires the lock with a 10-second expiration and 7 retry attempts
    # 3. Executes the wrapped method
    # 4. Releases the lock in a finally block to ensure it always happens, even if an exception occurs
    # 5. Uses DLM recursion counting to handle nested calls safely
    # 
    # The lock identifier is the CAVM base directory itself, ensuring all instances pointing to the same base directory coordinate with each other.
    # 
    # Usage:
    # This decorator is applied automatically to all public methods that access shared state (profiles, dormant chains, etc.). Developers don't need to apply it manually - it's built into the class design.
    # 
    # Example of what it does conceptually:
    # ```
    # def LockManager(func):
    #     def wrapper(self, *args, **kwargs):
    #         # Acquire lock (wait if another process holds it)
    #         lock = DLM.Locker(self.base, ID=self.base, Timeout=10, Retry=7)
    #         lock.Lock(expire=10)
    #         try:
    #             # Execute the actual method while holding the lock
    #             return func(self, *args, **kwargs)
    #         finally:
    #             # Always release the lock when done
    #             lock.Unlock()
    #     return wrapper
    # ```
    # 
    # Important Notes:
    # - The lock uses the CAVM base directory as its ID, meaning all CAVM instances pointing to the same base directory will coordinate their access
    # - The timeout and retry values are hardcoded (10 seconds expiry, 7 retries) - these are not configurable through the decorator
    # - This decorator is essential for preventing race conditions in multi-process or multi-threaded environments
    # - The lock is reentrant, meaning the same thread/process can acquire it multiple times without deadlocking

    def LockManager(func):
        def wrapper(self, *args, **kwargs):
            own=DLM.Locker(self.base,ID=self.base,Timeout=10,Retry=7)
            own.Lock(expire=10)          # DLM recursion count +1 (or TTL reset)
            try:
                return func(self, *args, **kwargs)
            finally:
                own.Unlock()             # DLM recursion count -1 (releases at 0)
        return wrapper

    # WordTokens Method Documentation
    # 
    # Purpose:
    # Converts raw text into a list of meaningful tokens by applying linguistic preprocessing steps including case normalization, punctuation removal, stop word filtering, stemming, and word reduction.
    # 
    # Explanation for Beginners:
    # Before the system can compare conversations for similarity, it needs to break down the text into its important parts. This method takes a sentence or paragraph and extracts the meaningful words while ignoring common words that don't carry much meaning (like "the", "is", "and"). It also simplifies words to their base forms so that "running", "runs", and "ran" are all treated as the same concept ("run").
    # 
    # Technical Details:
    # The WordTokens method performs these operations on input text:
    # 1. Converts to lowercase for case-insensitive comparison
    # 2. Splits on whitespace to get individual words
    # 3. Removes all non-alphanumeric characters (punctuation, special characters)
    # 4. Filters out stop words (extensive list of common English words)
    # 5. Applies stemming rules:
    #    - Words ending in 'ies' (like "tries") become 'y' (-> "try")
    #    - Words ending in 'ing' (like "running") lose the 'ing' (-> "run")
    #    - Words ending in 's' (like "cats") lose the 's' (-> "cat") - but only if longer than 1 character
    # 6. Applies word reduction mapping if enabled (e.g., "acquire" -> "get", "demonstrate" -> "show")
    # 7. Returns the processed list of meaningful tokens
    # 
    # Parameters:
    # - text (str): The input text to be tokenized
    # 
    # Returns:
    # - list: A list of processed string tokens representing the meaningful content of the input
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # tokens = cavm.WordTokens("The quick brown fox jumps over the lazy dog's bone.")
    # # Returns: ['quick', 'brown', 'fox', 'jump', 'over', 'lazi', 'dog', 'bon']
    # # Note: "the" removed (stop word), "jumps" -> "jump", "lazy" -> "lazi", "dog's" -> "dog", "bone." -> "bon"
    # ```
    # 
    # Important Notes:
    # - The method is designed primarily for English language processing
    # - Empty strings or strings containing only stop words will return an empty list
    # - The stemming rules are simple suffix removals and may not produce linguistically correct stems in all cases
    # - The word reduction mapping (REDUCE dictionary) helps normalize synonyms and variations
    # - This method is called internally by Tokenize() and is not typically called directly by external code

    def WordTokens(self, text):
        words = []
        for w in str(text).lower().split():
            w = ''.join(c for c in w if c.isalpha())    #isalnum
            if not w or w in self.STOP_WORDS:
                continue
            if w.endswith('ies') and len(w) > 3:
                w = w[:-3] + 'y'
            elif w.endswith('ing') and len(w) > 3:
                w = w[:-3]
            elif w.endswith('s') and len(w) > 1:
                w = w[:-1]
            if self.UseReduce and hasattr(self, 'REDUCE') and w in self.REDUCE:
                w = self.REDUCE[w]
            words.append(w)
        return words

    # Tokenize Method Documentation
    # 
    # Purpose:
    # Converts text into a Counter object (dictionary-like structure) that counts the frequency of each meaningful token after linguistic preprocessing.
    # 
    # Explanation for Beginners:
    # While WordTokens gives you a list of important words, Tokenize takes it a step further by counting how many times each word appears. This creates a numerical representation of the text that can be compared mathematically with other texts. Think of it as creating a fingerprint of the text's content where common words have higher counts.
    # 
    # Technical Details:
    # The Tokenize method:
    # 1. Calls WordTokens() to get a list of processed meaningful tokens
    # 2. Uses collections.Counter to count occurrences of each token
    # 3. Returns the Counter object where keys are tokens and values are their frequencies
    # 
    # This numerical representation enables mathematical comparison methods like cosine similarity to quantify how similar two pieces of text are in terms of their meaningful content.
    # 
    # Parameters:
    # - text (str): The input text to be tokenized and counted
    # 
    # Returns:
    # - Counter: A collections.Counter object mapping each token to its frequency count
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # counter = cavm.Tokenize("The cat chased the cat and the dog chased the cat.")
    # # Returns: Counter({'cat': 3, 'chased': 2, 'dog': 1})
    # # Note: "the" removed as stop word, words counted by frequency
    # ```
    # 
    # Important Notes:
    # - Returns a Counter object, not a plain dictionary - but behaves like a dictionary for most purposes
    # - Empty input or input with only stop words returns an empty Counter
    # - This method is typically called internally by other methods like Update() and Search()
    # - The Counter enables mathematical operations like dot product and normalization needed for similarity calculations

    def Tokenize(self, text):
        return Counter(self.WordTokens(text))

    # Hash Method Documentation
    # 
    # Purpose:
    # Generates a unique SHA-256 hash identifier for a given text string, used to create chain identifiers for new topical chains in CAVM.
    # 
    # Explanation for Beginners:
    # When CAVM encounters a conversation exchange that doesn't match any existing topical chain, it needs to create a new chain for this topic. To do this reliably, it creates a unique "fingerprint" or ID for the exchange content. This Hash method generates that fingerprint using a standard cryptographic algorithm (SHA-256) that produces the same ID for identical content and different IDs for different content, with extremely low chance of collisions (two different texts producing the same ID).
    # 
    # Technical Details:
    # The Hash method:
    # 1. Takes any input text and converts it to a string
    # 2. Encodes the string as UTF-8 bytes
    # 3. Applies the SHA-256 cryptographic hash function
    # 4. Returns the resulting hash as a hexadecimal string (64 characters)
    # 
    # This hash serves as the chain_id for new chains, ensuring that identical content always produces the same chain ID while different content produces different IDs with negligible collision probability.
    # 
    # Parameters:
    # - text (any): The input to be hashed (will be converted to string)
    # 
    # Returns:
    # - str: A 64-character hexadecimal string representing the SHA-256 hash of the input
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # hash1 = cavm.Hash("What is the capital of France?")
    # hash2 = cavm.Hash("What is the capital of France?")
    # hash3 = cavm.Hash("What is the capital of Germany?")
    # # hash1 == hash2 (same input)
    # # hash1 != hash3 (different input, extremely unlikely to collide)
    # ```
    # 
    # Important Notes:
    # - The hash is deterministic: same input always produces same output
    # - Designed for distributing chains uniformly across the hash space
    # - Not cryptographically secure for security purposes (not needed here) but excellent for creating unique identifiers
    # - The hash is used as the chain_id in the storage system (chain_profiles.db)
    # - Changing even one character in the input produces a completely different hash (avalanche effect)

    def Hash(self,text):
        return hashlib.sha256(str(text).encode('utf-8')).hexdigest()

    # CosineLike Method Documentation
    # 
    # Purpose:
    # Calculates a similarity score between two token counters using a cosine-like measure, quantifying how semantically similar two pieces of text are based on their meaningful word content.
    # 
    # Explanation for Beginners:
    # Imagine representing each piece of text as a point in a multi-dimensional space where each dimension corresponds to a unique word, and the value along that dimension represents how many times that word appears. The cosine similarity measures the angle between these two points - if they point in similar directions (small angle), the texts are similar; if they point in very different directions (large angle), the texts are dissimilar. This method implements a variation of this concept specifically for CAVM's needs.
    # 
    # Technical Details:
    # The CosineLike method computes similarity between two Counter objects (token frequency distributions):
    # 1. Calculates the dot product (intersection) of the two counters: sum of (count_in_a * count_in_b) for all tokens in a
    # 2. Computes the magnitude (norm) of each counter: sqrt(sum of count^2 for all tokens)
    # 3. Returns the dot product divided by the product of magnitudes
    # 4. Handles edge cases where one or both counters are empty (returns 0.0)
    # 
    # This is essentially the cosine similarity formula, which ranges from 0.0 (no similarity) to 1.0 (identical token distributions), though in practice with text data it rarely reaches exactly 1.0 unless the texts are identical after processing.
    # 
    # Parameters:
    # - counter_a (Counter): First token frequency distribution
    # - counter_b (Counter): Second token frequency distribution
    # 
    # Returns:
    # - float: Similarity score between 0.0 and 1.0, where higher values indicate greater similarity
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # text1 = "The quick brown fox jumps over the lazy dog"
    # text2 = "A fast brown fox leaps above a sleepy dog"
    # counter1 = cavm.Tokenize(text1)  # {'quick':1, 'brown':1, 'fox':1, 'jump':1, 'over':1, 'lazi':1, 'dog':1}
    # counter2 = cavm.Tokenize(text2)  # {'fast':1, 'brown':1, 'fox':1, 'leap':1, 'above':1, 'sleepy':1, 'dog':1}
    # similarity = cavm.CosineLike(counter1, counter2)
    # # Returns a value between 0.0 and 1.0 representing semantic similarity
    # # In this case, would be moderately high due to shared words: brown, fox, dog
    # ```
    # 
    # Important Notes:
    # - Returns 0.0 if either counter is empty (no meaningful tokens)
    # - The method is symmetric: CosineLike(a,b) == CosineLike(b,a)
    # - This similarity measure is used throughout CAVM to:
    #   * Determine if a new exchange belongs to an existing chain (Update method)
    #   * Rank chains by relevance to a query (Search method)
    # - The score is not a probability or percentage, but a relative measure of similarity
    # - Works best when comparing texts of similar length and topical focus

    def CosineLike(self,counter_a, counter_b):
        if not counter_a or not counter_b:
            return 0.0
        intersection = sum(counter_a[k] * counter_b.get(k, 0) for k in counter_a)
        norm_a = sum(v*v for v in counter_a.values()) ** 0.5
        norm_b = sum(v*v for v in counter_b.values()) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return intersection / (norm_a * norm_b)

    # GetProfile Method Documentation
    # 
    # Purpose:
    # Retrieves the profile for a specific chain by its chain_id.
    # 
    # Explanation for Beginners:
    # Each chain in CAVM has a profile that contains all of its versions (the exchanges about that topic) and metadata like when it was last updated. This method allows you to look up the complete profile for a particular chain if you know its chain_id.
    # 
    # Technical Details:
    # This method:
    # - Calls GetProfiles() to ensure the profiles dictionary is loaded
    # - Looks up the chain_id (converted to string) in the profiles dictionary
    # - Returns the profile dictionary if found, or None if not found
    # - The method is decorated with @LockManager to ensure thread-safe access
    # 
    # Parameters:
    # - chain_id (any): The identifier of the chain to retrieve (will be converted to string)
    # 
    # Returns:
    # - dict or None: The profile dictionary for the chain if found, otherwise None.
    #   The profile dictionary contains:
    #   - chain_id: The chain's identifier
    #   - versions: A list of version dictionaries (each representing an exchange)
    #   - last_updated: Timestamp of the most recent version
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # # Add a conversation to create a chain
    # chain_id, version_num = cavm.Update(input="Hello", response="Hi there!")
    # # Later, retrieve the full profile for that chain
    # profile = cavm.GetProfile(chain_id)
    # # profile contains the chain's complete data if successful
    # ```
    # 
    # Important Notes:
    # - The chain_id is converted to string for lookup consistency
    # - Returns None if the chain_id does not exist in profiles
    # - The method does not automatically load dormant chains separately; it uses the existing profiles dictionary
    # - The @LockManager decorator ensures safe concurrent access
    # - The profile returned is the actual internal dictionary; modifying it directly will affect internal state (use with caution)

    @LockManager
    def GetProfiles(self):
        if self.profiles is None:
            self.profiles = self.LoadProfiles(self.base)
        return self.profiles

    # MarkProfilesDirty Method Documentation
    # 
    # Purpose:
    # Marks the internal profiles dictionary as dirty (modified), indicating that changes need to be persisted to disk.
    # 
    # Explanation for Beginners:
    # When the CAVM system makes changes to its memory chains (like adding a new version or updating a chain), it doesn't immediately write those changes to disk for performance reasons. Instead, it sets a flag saying "the memory has been changed and needs to be saved later." This method sets that flag. The actual saving to disk happens later when the system is idle or when explicitly requested, preventing excessive disk writes during active use.
    # 
    # Technical Details:
    # This method simply sets self.dirty = True. The dirty flag is checked by PersistProfilesIfDirty() which, when called, will save the profiles to disk if the flag is true and then reset the flag. This allows multiple modifications to be batched into a single disk write operation.
    # 
    # Parameters:
    # - None
    # 
    # Returns:
    # - None
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # # After making changes to profiles (e.g., via Update), the system internally calls this method
    # # You typically won't call this directly unless you're extending the class
    # cavm.MarkProfilesDirty()
    # # Later, PersistProfilesIfDirty() will save the changes to disk
    # ```
    # 
    # Important Notes:
    # - This method is called internally by methods that modify profiles (like Update, ExpireChains, etc.)
    # - External code should not need to call this method directly under normal usage
    # - The dirty flag is part of a lazy persistence strategy to improve performance
    # - The method is decorated with @LockManager to ensure thread-safe modification of the flag

    @LockManager
    def MarkProfilesDirty(self):
        self.dirty = True

    # PersistProfilesIfDirty Method Documentation
    # 
    # Purpose:
    # Saves the chain profiles to disk if they have been marked as dirty (modified), then resets the dirty flag.
    # 
    # Explanation for Beginners:
    # When the CAVM system makes changes to its memory (like adding new conversations), it doesn't write every change to disk immediately because that would be slow. Instead, it keeps track that changes have been made (by setting a dirty flag) and then saves all the changes at once when appropriate. This method checks if there are unsaved changes and, if so, writes them to the storage file and clears the flag.
    # 
    # Technical Details:
    # This method:
    # - Checks if self.dirty is True
    # - If true, calls SaveProfiles() to write self.profiles to chain_profiles.db
    # - Reloads the dormant chains set from dormant.db (to pick up any changes made during expiration)
    # - Sets self.dirty = False
    # - The method is decorated with @LockManager to ensure thread-safe execution
    # 
    # Parameters:
    # - None
    # 
    # Returns:
    # - None
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # # After performing operations that modify profiles (like Update), the system internally may call this method
    # # You typically won't call this directly unless you're extending the class or managing persistence manually
    # cavm.PersistProfilesIfDirty()  # Will save if dirty, do nothing if not
    # ```
    # 
    # Important Notes:
    # - This method is called internally by the Update method after modifications
    # - External code generally does not need to call this method directly
    # - The method is part of a lazy persistence strategy to batch disk writes and improve performance
    # - The @LockManager decorator ensures safe concurrent access
    # - If an error occurs during saving, it is silently caught and ignored (as per the SaveProfiles implementation)

    @LockManager
    def PersistProfilesIfDirty(self):
        if self.dirty:
            self.SaveProfiles(self.base, self.profiles)
            self.dormant_chains = self.LoadDormant(self.base)
            self.dirty = False

    # LoadProfiles Method Documentation
    # 
    # Purpose:
    # Loads chain profiles from the persistent storage file (chain_profiles.db) into memory.
    # 
    # Explanation for Beginners:
    # Imagine the CAVM system has a notebook where it keeps records of all topical conversations (chains). This method is like opening that notebook and reading the contents into the computer's working memory so the system can quickly access and search through the conversations. If the notebook doesn't exist yet (first time running), it returns an empty collection.
    # 
    # Technical Details:
    # This method:
    # - Constructs the path to chain_profiles.db in the base directory
    # - If the file doesn't exist, returns an empty dictionary
    # - Reads the file line by line (each line is a JSON object representing a chain profile)
    # - For each line, parses the JSON and converts the 'tokens' field from a plain dictionary back to a Counter object (since JSON doesn't preserve Counter type)
    # - Stores the profile in a dictionary keyed by chain_id
    # - Returns the dictionary of profiles
    # - Any malformed lines are skipped (to prevent corruption from breaking the entire load)
    # - The method is decorated with @LockManager to ensure thread-safe file reading
    # 
    # Parameters:
    # - base (str): The base directory where chain_profiles.db is located (defaults to self.base if not provided)
    # 
    # Returns:
    # - dict: A dictionary mapping chain_id strings to profile objects (each containing chain_id, versions list, and last_updated timestamp)
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # # This method is typically called internally by GetProfiles()
    # profiles = cavm.LoadProfiles(cavm.base)
    # # profiles is a dict like: {'chain_id_1': {'chain_id': 'chain_id_1', 'versions': [ ... ], 'last_updated': '2024-01-01T12:00:00Z'}, ...}
    # ```
    # 
    # Important Notes:
    # - This method is called by GetProfiles() to lazy-load profiles on first access
    # - The @LockManager decorator ensures safe concurrent access to the file
    # - Profiles are loaded only once per instance (unless manually reset) because GetProfiles caches them in self.profiles
    # - The method handles file not found and malformed JSON gracefully by returning what it can
    # - Each version in the versions list has its 'tokens' field converted from dict to Counter for proper similarity calculations

    @LockManager
    def LoadProfiles(self, base):
        path = os.path.join(base, 'chain_profiles.db')
        profiles = {}
        if not os.path.exists(path):
            return profiles
        try:
            raw = FF.ReadFile(path)
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    cid = obj.get('chain_id')
                    if cid:
                        # Reconstruct versions list with real Counters
                        versions = []
                        for vdata in obj.get('versions', []):
                            vdata['tokens'] = Counter(vdata.get('tokens', {}))
                            versions.append(vdata)
                        obj['versions'] = versions
                        profiles[cid] = obj
                except Exception:
                    continue
        except Exception:
            pass
        return profiles

    # SaveProfiles Method Documentation
    # 
    # Purpose:
    # Saves the chain profiles dictionary to the persistent storage file (chain_profiles.db).
    # 
    # Explanation for Beginners:
    # After the CAVM system has made changes to its memory chains (like adding new versions or updating chains), this method writes all the current chain data to a file on disk so that the information is not lost when the program stops. It converts the internal data structures (including Counter objects for token counts) into a format that can be stored as plain text (JSON) and writes each chain as a separate line in the file.
    # 
    # Technical Details:
    # This method:
    # - Constructs the path to chain_profiles.db in the base directory
    # - Iterates over each profile in the profiles dictionary
    # - For each profile, creates a copy and converts the 'tokens' field in each version from a Counter object to a plain dictionary (since JSON serialization doesn't handle Counter)
    # - Serializes each profile to a JSON string
    # - Writes all JSON strings to the file, one per line, followed by a newline
    # - The method is decorated with @LockManager to ensure thread-safe file writing
    # 
    # Parameters:
    # - base (str): The base directory where chain_profiles.db is located (defaults to self.base if not provided)
    # - profiles (dict): The dictionary of chain profiles to save (typically self.profiles)
    # 
    # Returns:
    # - None
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # # After making changes to cavm.profiles (e.g., via Update), the system internally calls this method
    # # You typically won't call this directly unless you're extending the class or managing persistence manually
    # cavm.SaveProfiles(cavm.base, cavm.profiles)
    # ```
    # 
    # Important Notes:
    # - This method is called by PersistProfilesIfDirty() when the dirty flag is set
    # - The @LockManager decorator ensures safe concurrent access to the file
    # - Each line in the file is a complete JSON object representing a chain profile
    # - The method does not handle exceptions (they are silently ignored) - this is by design to avoid crashing the persistence process
    # - The file is overwritten completely each time this method is called
    # - The tokens in each version are converted from Counter to dict for JSON serialization, and then back to Counter when loaded

    @LockManager
    def SaveProfiles(self, base, profiles):
        path = os.path.join(base, 'chain_profiles.db')
        lines = []
        for profile in profiles.values():
            obj = dict(profile)
            # Convert Counters to plain dicts for JSON
            versions_serial = []
            for v in profile.get('versions', []):
                v_copy = dict(v)
                v_copy['tokens'] = dict(v.get('tokens', {}))
                versions_serial.append(v_copy)
            obj['versions'] = versions_serial
            lines.append(json.dumps(obj, ensure_ascii=False))
        FF.WriteFile(path, '\n'.join(lines) + '\n')

    # LoadDormant Method Documentation
    # 
    # Purpose:
    # Loads the set of dormant chain identifiers from the persistent storage file (dormant.db).
    # 
    # Explanation for Beginners:
    # When a chain hasn't been used for a certain period (DormantDays), it is marked as dormant to save resources. This method reads the list of dormant chain IDs from disk so the system knows which chains are currently inactive. Think of it as checking the archive box to see which conversations have been moved to long-term storage.
    # 
    # Technical Details:
    # This method:
    # - Constructs the path to dormant.db in the base directory (or provided base)
    # - If the file doesn't exist, returns an empty set
    # - Reads the file line by line (each line contains a chain ID, optionally followed by a tab and timestamp)
    # - Extracts the chain ID (first part before tab) from each line
    # - Returns a set of these chain IDs
    # - The method is decorated with @LockManager to ensure thread-safe file reading
    # 
    # Parameters:
    # - base (str, optional): The base directory where dormant.db is located. If not provided, uses self.base.
    # 
    # Returns:
    # - set: A set of chain_id strings representing dormant chains
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # dormant_chains = cavm.LoadDormant()
    # # dormant_chains is a set like: {'chain_id_1', 'chain_id_2', ...}
    # ```
    # 
    # Important Notes:
    # - This method is called by GetProfiles(), Update(), Search(), and other methods to check if a chain is dormant
    # - The @LockManager decorator ensures safe concurrent access to the file
    # - The file format is one chain ID per line (with optional tab-separated timestamp, though only the ID is used)
    # - Returns an empty set if the file doesn't exist or is empty
    # - The method does not handle exceptions (they are silently ignored) - this is by design to avoid breaking the sleep/wake cycle

    @LockManager
    def LoadDormant(self, base=None):
        base = base or self.base
        path = os.path.join(base, 'dormant.db')
        if not os.path.exists(path):
            return set()
        chains = set()
        try:
            for line in FF.ReadFile(path).splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split('\t')
                chains.add(parts[0])
        except Exception:
            pass
        return chains

    @LockManager
    def SaveDormant(self, base=None):
        base = base or self.base
        path = os.path.join(base, 'dormant.db')
        lines = []
        for cid in sorted(self.dormant_chains):
            lines.append(f"{cid}")
        FF.WriteFile(path, '\n'.join(lines) + '\n')

    # DecayVersions Method Documentation
    # 
    # Purpose:
    # Applies a decay multiplier to the token counts of all versions in a chain except the most recent one, reducing the influence of older versions over time.
    # 
    # Explanation for Beginners:
    # As a chain gets newer versions, the older versions become less relevant. This method implements a form of "forgetting" where the importance of older exchanges in a chain gradually fades. It does this by multiplying the count of each token in older versions by a decay factor (like 0.95, meaning each token keeps 95% of its weight per update). The most recent version is left unchanged to preserve the current state of the topic.
    # 
    # Technical Details:
    # This method:
    # - Takes a list of version dictionaries (each version has a 'tokens' field which is a Counter)
    # - For every version except the last one in the list:
    #   * Creates a new Counter
    #   * For each token in the version's tokens, multiplies the count by self.PROFILE_DECAY
    #   * Replaces the version's tokens with the new decayed Counter
    # - The most recent version (the last in the list) is left untouched
    # - The method is decorated with @LockManager to ensure thread-safe execution
    # 
    # Parameters:
    # - versions (list): A list of version dictionaries, ordered from oldest to newest (as stored in the chain)
    # 
    # Returns:
    # - None (modifies the versions list in place)
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # # Assume we have a chain with 3 versions [v1, v2, v3] where v3 is the latest
    # cavm.DecayVersions([v1, v2, v3])
    # # After this call, v1 and v2 have their token counts multiplied by PROFILE_DECAY, v3 unchanged
    # ```
    # 
    # Important Notes:
    # - This method is called by Update() before appending a new version to a chain
    # - The decay factor (PROFILE_DECAY) is set during initialization (default 0.95)
    # - The method modifies the versions list in place; it does not return a new list
    # - If the versions list is empty or has only one element, the method does nothing
    # - The decay is applied to the raw token counts, which may result in fractional counts (since Counter can hold floats)

    @LockManager
    def DecayVersions(self, versions):
        """Apply decay multiplier to token counts in all versions except the most recent."""
        if not versions:
            return
        # Keep latest version undecayed; decay older ones
        for v in versions[:-1]:
            new_tokens = Counter()
            for token, count in v['tokens'].items():
                new_tokens[token] = count * self.PROFILE_DECAY
            v['tokens'] = new_tokens

    # ExpireChains Method Documentation
    # 
    # Purpose:
    # Identifies and handles chains that have been inactive for extended periods, marking them as dormant or permanently deleting them based on configured time thresholds.
    # 
    # Explanation for Beginners:
    # Over time, some topics in the conversation memory may become inactive and no longer relevant. This method periodically checks all chains and applies two policies:
    # 1. Chains inactive for longer than HardDeleteDays (default 90 days) are permanently deleted to free up space
    # 2. Chains inactive for longer than DormantDays (default 30 days) but less than HardDeleteDays are marked as dormant (archived) to save active memory resources
    # This helps the system focus on relevant, recent conversations while preserving older ones for potential future reference and cleaning up truly obsolete data.
    # 
    # Technical Details:
    # This method:
    # - Takes the current profiles dictionary and base directory as input
    # - Calculates the current time in UTC
    # - Defines two cutoff times:
    #   * cutoff_hard: now minus HARD_DELETE_DAYS
    #   * cutoff_dormant: now minus DORMANT_DAYS
    # - Iterates through each chain in profiles:
    #   * Parses the chain's last_updated timestamp
    #   * Calculates age in days since last update
    #   * If age > HARD_DELETE_DAYS: marks chain for deletion
    #   * Else if age > DORMANT_DAYS: adds chain to new_dormant set
    # - Deletes all marked chains from the profiles dictionary
    # - Updates the dormant.db file:
    #   * Reads existing dormant chains
    #   * Combines with new_dormant set
    #   * Removes any chains that were deleted
    #   * Writes the updated set back to dormant.db
    # - The method is decorated with @LockManager to ensure thread-safe execution
    # 
    # Parameters:
    # - profiles (dict): The dictionary of chain profiles to examine and modify
    # - base (str, optional): The base directory where storage files are located. If not provided, uses self.base.
    # 
    # Returns:
    # - list: A list of chain_id strings that were permanently deleted
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # # This method is typically called internally by Update() before adding new versions
    # profiles = cavm.GetProfiles()
    # deleted_chains = cavm.ExpireChains(profiles, cavm.base)
    # # deleted_chains contains the IDs of chains that were permanently removed
    # # The profiles dictionary has been modified in-place (deleted chains removed)
    # # The dormant.db file has been updated to reflect newly dormant chains
    # ```
    # 
    # Important Notes:
    # - This method modifies the profiles dictionary in-place by deleting expired chains
    # - It updates the dormant.db file to reflect the new set of dormant chains
    # - The method is called by Update() to ensure memory hygiene before adding new content
    # - Time calculations use UTC timezone for consistency
    # - If a chain's last_updated timestamp cannot be parsed, it is treated as current time (age 0 days)
    # - The method handles file reading/writing errors gracefully by continuing with what it can

    @LockManager
    def ExpireChains(self, profiles, base):
        base = base or self.base
        now = datetime.now(timezone.utc)
        cutoff_hard = now - timedelta(days=self.HARD_DELETE_DAYS)
        cutoff_dormant = now - timedelta(days=self.DORMANT_DAYS)
        to_delete = []
        new_dormant = set()
        for cid, p in profiles.items():
            try:
                last = datetime.fromisoformat(p.get('last_updated'))
            except Exception:
                last = now
            age_days = (now - last).total_seconds() / 86400
            if age_days > self.HARD_DELETE_DAYS:
                to_delete.append(cid)
            elif age_days > self.DORMANT_DAYS:
                new_dormant.add(cid)
        for cid in to_delete:
            del profiles[cid]
        # Update dormant.db
        dormant_path = os.path.join(base, 'dormant.db')
        existing = set()
        if os.path.exists(dormant_path):
            try:
                for line in FF.ReadFile(dormant_path).splitlines():
                    line = line.strip()
                    if line:
                        existing.add(line.split('\t')[0])
            except Exception:
                pass
        updated = (existing | new_dormant) - set(to_delete)
        lines = [f"{cid}" for cid in sorted(updated)]
        FF.WriteFile(dormant_path, '\n'.join(lines) + '\n')
        return to_delete

    # GetChainCount Method Documentation
    # 
    # Purpose:
    # Returns the number of active (non-dormant) chains in the memory system.
    # 
    # Explanation for Beginners:
    # Not all chains in CAVM are actively used. Some become dormant after a period of inactivity. This method tells you how many chains are currently active and participating in the memory system - the ones that are still being updated and searched against. Dormant chains are excluded from this count as they are effectively archived.
    # 
    # Technical Details:
    # This method:
    # - Retrieves all profiles from storage via GetProfiles()
    # - Loads the current set of dormant chain IDs via LoadDormant()
    # - Counts how many profile IDs are NOT in the dormant set
    # - Returns this count as the number of active chains
    # - The method is decorated with @LockManager to ensure thread-safe execution
    # 
    # Parameters:
    # - None
    # 
    # Returns:
    # - int: The number of active chains (chains not marked as dormant)
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # # Add some conversations to create chains
    # cavm.Update(input="Hello", response="Hi!")
    # cavm.Update(input="What is AI?", response="AI is artificial intelligence")
    # # Check how many active chains we have
    # active_count = cavm.GetChainCount()
    # # Returns the number of chains that are currently active (not dormant)
    # ```
    # 
    # Important Notes:
    # - This method excludes dormant chains from the count
    # - Dormant chains are those that have been inactive for longer than DormantDays but less than HardDeleteDays
    # - The count represents chains that are eligible for new updates and search results
    # - The method is called internally by other methods that need to know the active chain count
    # - Both GetProfiles() and LoadDormant() are called, each of which is thread-safe due to their own @LockManager decorators

    @LockManager
    def GetChainCount(self):
        profiles = self.GetProfiles()
        self.dormant_chains = self.LoadDormant(self.base)
        active = [cid for cid in profiles if cid not in self.dormant_chains]
        return len(active)

    # GetChainLabels Method Documentation
    # 
    # Purpose:
    # Generates human-readable labels for each chain by extracting the top tokens from the latest version of each chain.
    # 
    # Explanation for Beginners:
    # Each chain in CAVM represents a topic of conversation. To make it easier to understand what a chain is about without reading all its content, this method creates a short label consisting of the most important words from the most recent exchange in that chain. Think of it as creating a quick summary or tag for each topic.
    # 
    # Technical Details:
    # This method:
    # - Retrieves all chain profiles via GetProfiles()
    # - For each chain, gets its list of versions
    # - If the chain has at least one version, takes the latest version (last in the list)
    # - Extracts the tokens Counter from that version
    # - Uses TopTokens() to get the N most frequent tokens (default 23)
    # - Joins those tokens with spaces to form a label string
    # - If a chain has no versions, labels it as '(no versions)'
    # - Returns a dictionary mapping chain_id to its label string
    # - The method is decorated with @LockManager to ensure thread-safe execution
    # 
    # Parameters:
    # - None
    # 
    # Returns:
    # - dict: A dictionary mapping chain_id strings to label strings (space-separated top tokens)
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # # Add some conversations
    # cavm.Update(input="What is the capital of France?", response="The capital of France is Paris.")
    # cavm.Update(input="I like apples", response="Apples are healthy")
    # # Get labels for all chains
    # labels = cavm.GetChainLabels()
    # # Returns something like: {'chain_id_1': 'capital france paris', 'chain_id_2': 'apple healthy'}
    # ```
    # 
    # Important Notes:
    # - The label is based only on the latest version of each chain, not the entire history
    # - The number of tokens in the label is controlled by ContextCountDefault (default 23)
    # - Chains with no versions get the label '(no versions)'
    # - The method does not include dormant chains differently; it labels all chains present in profiles
    # - The @LockManager decorator ensures safe concurrent access

    @LockManager
    def GetChainLabels(self):
        profiles = self.GetProfiles()
        labels = {}
        for cid, p in profiles.items():
            versions = p.get('versions', [])
            if versions:
                latest = versions[-1]
                tokens = latest.get('tokens', {})
                top = self.TopTokens(tokens, self.CONTEXT_COUNT_DEFAULT)
                labels[cid] = ' '.join(top) if top else '(empty)'
            else:
                labels[cid] = '(no versions)'
        return labels

    # GetProfile Method Documentation
    # 
    # Purpose:
    # Retrieves the profile for a specific chain by its chain_id.
    # 
    # Explanation for Beginners:
    # Each chain in CAVM has a profile that contains all of its versions (the exchanges about that topic) and metadata like when it was last updated. This method allows you to look up the complete profile for a particular chain if you know its chain_id.
    # 
    # Technical Details:
    # This method:
    # - Calls GetProfiles() to ensure the profiles dictionary is loaded
    # - Looks up the chain_id (converted to string) in the profiles dictionary
    # - Returns the profile dictionary if found, or None if not found
    # - The method is decorated with @LockManager to ensure thread-safe access
    # 
    # Parameters:
    # - chain_id (any): The identifier of the chain to retrieve (will be converted to string)
    # 
    # Returns:
    # - dict or None: The profile dictionary for the chain if found, otherwise None.
    #   The profile dictionary contains:
    #   - chain_id: The chain's identifier
    #   - versions: A list of version dictionaries (each representing an exchange)
    #   - last_updated: Timestamp of the most recent version
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # # Add a conversation to create a chain
    # chain_id, version_num = cavm.Update(input="Hello", response="Hi there!")
    # # Later, retrieve the full profile for that chain
    # profile = cavm.GetProfile(chain_id)
    # # profile contains the chain's complete data if successful
    # ```
    # 
    # Important Notes:
    # - The chain_id is converted to string for lookup consistency
    # - Returns None if the chain_id does not exist in profiles
    # - The method does not automatically load dormant chains separately; it uses the existing profiles dictionary
    # - The @LockManager decorator ensures safe concurrent access
    # - The profile returned is the actual internal dictionary; modifying it directly will affect internal state (use with caution)

    @LockManager
    def GetProfile(self, chain_id):
        profiles = self.GetProfiles()
        return profiles.get(str(chain_id))

    # GetVersion Method Documentation
    # 
    # Purpose:
    # Retrieves a specific version of a chain by its chain_id and version number, with flexible indexing options.
    # 
    # Explanation for Beginners:
    # Each chain in CAVM contains multiple versions, where each version represents an exchange (input and response) about that topic. Versions are numbered starting from 1 for the first exchange. This method allows you to access a specific version by its number, or use special indexing to get the latest version or count backwards from the latest (like getting the second-most recent version).
    # 
    # Technical Details:
    # This method:
    # - Retrieves the chain profile using GetProfile(chain_id)
    # - If the profile doesn't exist or has no versions, returns None
    # - Gets the list of versions for the chain
    # - Handles the version parameter with three possible interpretations:
    #   * version=None (default): returns the latest version (last in the list)
    #   * version < 0: treats as negative index from the end (-1 = latest, -2 = second-latest, etc.)
    #   * version > 0: treats as 1-based index from the beginning (1 = first version, 2 = second, etc.)
    # - Returns the version dictionary if the index is valid, otherwise returns None
    # - The method is decorated with @LockManager to ensure thread-safe access
    # 
    # Parameters:
    # - chain_id (any): The identifier of the chain (will be converted to string)
    # - version (int or None, optional): The version number to retrieve:
    #   * None or omitted: returns the latest version
    #   * Negative integer: counts backwards from the latest (-1 = latest, -2 = second-latest, etc.)
    #   * Positive integer: 1-based index from the beginning (1 = first version)
    # 
    # Returns:
    # - dict or None: The version dictionary if found and valid, otherwise None.
    #   Each version dictionary contains:
    #   - input: The user's input for this exchange
    #   - response: The AI's response for this exchange
    #   - tokens: Counter of meaningful tokens from the combined input/response
    #   - last_updated: Timestamp when this version was created
    #   - contexts: Dictionary of context information
    #   - v: The version number (1-based index)
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # # Add several exchanges about the same topic
    # cavm.Update(input="What is Python?", response="Python is a programming language")
    # cavm.Update(input="How do I install it?", response="Use pip install python")
    # cavm.Update(input="What are lists?", response="Lists are ordered collections")
    # # Get the latest version (3rd exchange)
    # latest = cavm.GetVersion(chain_id)  # Returns the 3rd version
    # # Get the first version
    # first = cavm.GetVersion(chain_id, 1)  # Returns the 1st version
    # # Get the second-latest version
    # second_latest = cavm.GetVersion(chain_id, -2)  # Returns the 2nd version
    # ```
    # 
    # Important Notes:
    # - Version numbering starts at 1 for the first version in a chain
    # - Negative indices follow Python's negative indexing convention: -1 is last element, -2 is second-to-last, etc.
    # - If the requested version index is out of bounds, the method returns None
    # - The method does not automatically create versions; it only retrieves existing ones
    # - The @LockManager decorator ensures safe concurrent access
    # - The version dictionary returned is the actual internal dictionary; modifying it directly will affect internal state (use with caution)

    @LockManager
    def GetVersion(self, chain_id, version=None):
        """Get a specific version of a chain. version=None => latest."""
        profile = self.GetProfile(chain_id)
        if not profile:
            return None
        versions = profile.get('versions', [])
        if not versions:
            return None
        if version is None:
            return versions[-1]
        if version < 0:
            # negative index from end: -1 = latest, -2 = second-latest
            idx = len(versions) + version
            if 0 <= idx < len(versions):
                return versions[idx]
            return None
        if 1 <= version <= len(versions):
            return versions[version - 1]
        return None

    # Reset Method Documentation
    # 
    # Purpose:
    # Completely clears all chain data from the memory system by deleting the storage files and resetting internal state.
    # 
    # Explanation for Beginners:
    # Sometimes you might want to start fresh with a clean memory system, removing all previously learned conversations and chains. This method does exactly that - it deletes all stored chain data from disk and resets the internal memory structures to their initial empty state.
    # 
    # Technical Details:
    # This method:
    # - Deletes the two storage files: chain_profiles.db and dormant.db from the base directory
    # - Resets self.profiles to an empty dictionary
    # - Resets self.dormant_chains to an empty set
    # - Resets self.dirty flag to False
    # - The method is decorated with @LockManager to ensure thread-safe execution
    # - Note: Only these two files are deleted because they are the only ones currently used by the system
    # 
    # Parameters:
    # - None
    # 
    # Returns:
    # - None
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # # Add some conversations and create chains
    # cavm.Update(input="Hello", response="Hi!")
    # # Later, to start completely fresh:
    # cavm.Reset()
    # # All chains and their history are now deleted
    # # The system is back to its initial state as if newly created
    # ```
    # 
    # Important Notes:
    # - This method permanently deletes all stored chain data - use with caution
    # - It only deletes chain_profiles.db and dormant.db (the current storage files)
    # - If other files exist in the base directory, they are not touched
    # - After calling Reset(), the system will behave as if it was just instantiated
    # - The @LockManager decorator ensures safe concurrent access during the reset operation
    # - This method is useful for testing or when you want to clear all learned memory

    @LockManager
    def Reset(self):
        base = self.base
        for fn in ['chain_profiles.db', 'dormant.db']:   # only these two exist now
            try:
                os.remove(os.path.join(base, fn))
            except Exception:
                pass
        self.profiles = {}
        self.dormant_chains = set()
        self.dirty = False

    # Update Method Documentation
    # 
    # Purpose:
    # Adds a new exchange (input/response pair) to the memory system, either by appending it to an existing topically-related chain or by creating a new chain for the topic.
    # 
    # Explanation for Beginners:
    # This is the main method you use to add new conversations to the CAVM memory system. When you provide an input (what the user said) and a response (what the AI said), the system determines whether this exchange belongs to an existing topic of conversation or starts a new one. It does this by comparing the meaningful content of the exchange to the most recent exchange in each existing chain. If it finds a sufficiently similar chain, it adds the exchange as a new version to that chain. If not, it creates a brand new chain for this topic.
    # 
    # Technical Details:
    # The Update method performs these steps:
    # 1. Combines the provided content, input, and response parameters into a single string
    # 2. Tokenizes the combined string to extract meaningful tokens (using WordTokens and Tokenize)
    # 3. Checks if the token count meets the minimum threshold (MinTokensPerMemory)
    # 4. Loads current profiles and dormant chains from storage
    # 5. Calls ExpireChains() to clean up old/dormant chains
    # 6. Compares the tokenized exchange against the LATEST version of each active chain using CosineLike similarity
    # 7. Finds the chain with the highest similarity score
    # 8. If the best score is below SimilarityThreshold OR no chains exist:
    #    * Creates a new chain with a chain_id based on the hash of the combined content
    #    * Sets this as version 1 of the new chain
    # 9. If a sufficiently similar chain is found:
    #    * Applies decay to older versions in that chain (via DecayVersions)
    #    * Appends the exchange as a new version with an incremented version number
    # 10. Marks profiles as dirty and persists changes to disk
    # 11. Returns the chain_id and version number of the newly added/existing chain
    # 
    # The method is decorated with @LockManager to ensure thread-safe execution.
    # 
    # Parameters:
    # - content (any, optional): Additional content to include in the memory (will be converted to string)
    # - input (any, optional): The user's input for this exchange (will be converted to string)
    # - response (any, optional): The AI's response for this exchange (will be converted to string)
    # - contexts (dict, optional): Custom context information to store with this version. If not provided, defaults to a dictionary with a 'default' key containing the top tokens from the exchange.
    # 
    # Returns:
    # - tuple: (chain_id_str, version_number) where:
    #   - chain_id_str (str): The unique identifier for the chain (SHA-256 hash of the content for new chains, or existing chain ID)
    #   - version_number (int): The version number of this exchange within the chain (1 for new chains, incremented for existing chains)
    #   Returns (None, 0) if the combined content has fewer tokens than MinTokensPerMemory
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # # First exchange - creates a new chain
    # chain_id, version = cavm.Update(
    #     input="What is the capital of France?",
    #     response="The capital of France is Paris."
    # )
    # # Returns something like: ('a1b2c3d4...', 1)
    # 
    # # Second exchange on same topic - adds to existing chain
    # chain_id, version = cavm.Update(
    #     input="What about Germany?",
    #     response="The capital of Germany is Berlin.",
    #     content="We were discussing European capitals"
    # )
    # # Returns the same chain_id but with version=2
    # 
    # # Exchange on different topic - creates new chain
    # chain_id2, version2 = cavm.Update(
    #     input="How do I bake a cake?",
    #     response="You need flour, sugar, eggs, and butter."
    # )
    # # Returns a different chain_id and version=1
    # ```
    # 
    # Important Notes:
    # - The method combines content, input, and response (if provided) into a single string for processing
    # - At least one of content, input, or response should be provided to generate meaningful tokens
    # - The SimilarityThreshold (default 0.43) determines how similar an exchange needs to be to join an existing chain
    # - Before adding a new version to an existing chain, older versions in that chain undergo decay (reducing their influence)
    # - The method automatically handles memory hygiene by calling ExpireChains() before processing
    # - All changes are persisted to disk via the lazy persistence mechanism (dirty flag + PersistProfilesIfDirty)
    # - The @LockManager decorator ensures safe concurrent access to the memory system

    @LockManager
    def Update(self, content=None, input=None, response=None, contexts=None):
        parts = []
        if content is not None: parts.append(str(content))
        if input is not None: parts.append(str(input))
        if response is not None: parts.append(str(response))
        combined = '\n'.join(parts)

        token_ctr = self.Tokenize(combined)
        if sum(token_ctr.values()) < self.MIN_TOKENS_PER_MEMORY:
            return None, 0

        profiles = self.GetProfiles()
        self.dormant_chains = self.LoadDormant(self.base)
        self.ExpireChains(profiles, self.base)

        # Find best-matching active chain by scoring against its LATEST version
        scores = {}
        for cid, p in profiles.items():
            if cid in self.dormant_chains:
                continue
            versions = p.get('versions', [])
            if not versions:
                continue
            latest = versions[-1]
            score = self.CosineLike(token_ctr, latest['tokens'])
            if score > 0:
                scores[cid] = score

        best_cid, best_score = (max(scores.items(), key=lambda x: x[1]) if scores else (None, 0.0))

        now_iso = datetime.now(timezone.utc).isoformat()
        version = {
            'input': input,
            'response': response,
            'tokens': token_ctr,
            'last_updated': now_iso,
            'contexts': contexts if contexts is not None else {
                'default': self.TopTokens(token_ctr, self.CONTEXT_COUNT_DEFAULT)
            }
        }

        if best_cid is None or best_score < self.SIMILARITY_THRESHOLD:
            # New chain — version 1
            chain_id_str = self.Hash(combined)
            version['v'] = 1
            profiles[chain_id_str] = {
                'chain_id': chain_id_str,
                'versions': [version],
                'last_updated': now_iso
            }
            new_version = 1
        else:
            # Append to existing chain
            profile = profiles[best_cid]
            # Decay older versions before adding fresh one
            self.DecayVersions(profile['versions'])
            version_index = len(profile['versions']) + 1
            version['v'] = version_index
            profile['versions'].append(version)
            profile['last_updated'] = now_iso
            chain_id_str = best_cid
            new_version = version_index

        # Enforce per-chain version cap
        profile = profiles[chain_id_str]
        self.MarkProfilesDirty()
        self.PersistProfilesIfDirty()
        return chain_id_str, new_version

    # Search Method Documentation
    # 
    # Purpose:
    # Searches for chains relevant to a given query by comparing the query against specified versions of chains and returning the most similar matches.
    # 
    # Explanation for Beginners:
    # Sometimes you want to find what the AI remembers about a particular topic. This method allows you to search through all the stored conversations (chains) to find those that are most relevant to your query. It works by comparing your query to the exchanges in each chain and ranking them by similarity. You can specify whether to search against the latest version of each chain, a specific version number, or count backwards from the latest.
    # 
    # Technical Details:
    # The Search method:
    # 1. Tokenizes the query string to extract meaningful tokens
    # 2. Returns an empty list if the query has no meaningful tokens
    # 3. Loads current profiles and dormant chains from storage
    # 4. For each active chain (not in dormant set):
    #    * Gets the list of versions for the chain
    #    * Selects which version to score against based on the version parameter:
    #      - None or omitted: latest version (last in list)
    #      - Negative integer: counts backwards from latest (-1 = latest, -2 = second-latest, etc.)
    #      - Positive integer: 1-based index from beginning (1 = first version)
    #    * If the selected version index is valid, calculates similarity between query tokens and version tokens using CosineLike
    #    * If similarity > 0, gets the top tokens from that version as a summary
    #    * Appends a tuple of (score, chain_id, version_index, top_tokens) to the results list
    # 5. Sorts the results by score in descending order (highest similarity first)
    # 6. Returns the top 'limit' results (default 3)
    # - The method is decorated with @LockManager to ensure thread-safe execution
    # 
    # Parameters:
    # - query (str): The text to search for (will be tokenized)
    # - limit (int, optional): Maximum number of results to return (default 3)
    # - version (int or None, optional): Which version of each chain to score against:
    #   * None or omitted: latest version
    #   * Negative integer: counts backwards from latest (-1 = latest, -2 = second-latest, etc.)
    #   * Positive integer: 1-based index from beginning (1 = first version)
    # 
    # Returns:
    # - list: A list of tuples, each containing:
    #   - score (float): Similarity score between 0.0 and 1.0 (higher = more similar)
    #   - chain_id (str): The identifier of the matching chain
    #   - version_index (int): The version number of the chain that matched (1-based)
    #   - top_tokens (list): The top ContextCountDefault tokens from the matching version (as a summary)
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # # Add some conversations about different topics
    # cavm.Update(input="What is Python?", response="Python is a programming language")
    # cavm.Update(input="I like apples", response="Apples are healthy fruit")
    # cavm.Update(input="How do I make coffee?", response="Use a coffee maker or French press")
    # # Search for programming-related memories
    # results = cavm.Search("Tell me about coding languages")
    # # Returns something like: [(0.65, 'chain_id_1', 1, ['python', 'program', 'language'])]
    # # Search for food-related memories, checking the second version if it exists
    # results = cavm.Search("I'm hungry", version=-1)  # Latest version
    # # Returns something like: [(0.48, 'chain_id_2', 1, ['apple', 'healthy', 'fruit']), (0.42, 'chain_id_3', 1, ['coffee', 'maker', 'press'])]
    # ```
    # 
    # Important Notes:
    # - The search is case-insensitive and ignores stop words (like "the", "is", "and") due to the tokenization process
    # - Only returns chains with a similarity score > 0.0
    # - Results are sorted by similarity score in descending order (most relevant first)
    # - The version parameter allows you to search against specific historical versions of chains, not just the latest
    # - If a chain doesn't have enough versions for the requested version index, it is skipped
    # - The @LockManager decorator ensures safe concurrent access
    # - This method does not modify the memory system; it is read-only

    @LockManager
    def Search(self, query, limit=3, version=None):
        query_ctr = self.Tokenize(query)
        if not query_ctr:
            return []
        profiles = self.GetProfiles()
        if not profiles:
            return []
        dormant = self.LoadDormant(self.base)
        scores = []
        for cid, prof in profiles.items():
            if cid in dormant:
                continue
            versions = prof.get('versions', [])
            if not versions:
                continue
            # Select version to score
            if version is None:
                vdata = versions[-1]   # latest
                v_idx = len(versions)
            elif version < 0:
                idx = len(versions) + version
                if 0 <= idx < len(versions):
                    vdata = versions[idx]
                    v_idx = idx + 1
                else:
                    continue
            elif 1 <= version <= len(versions):
                vdata = versions[version - 1]
                v_idx = version
            else:
                continue
            score = self.CosineLike(query_ctr, vdata['tokens'])
            if score > 0:
                top = self.TopTokens(vdata['tokens'], self.CONTEXT_COUNT_DEFAULT)
                scores.append((score, cid, v_idx, top))
        scores.sort(key=lambda x: x[0], reverse=True)
        return scores[:limit]

    # TopTokens Method Documentation
    # 
    # Purpose:
    # Extracts the N most frequent tokens from a token counter, returning them as a list of strings.
    # 
    # Explanation for Beginners:
    # When you have a collection of words with their frequencies (like what comes out of the Tokenize method), this method helps you find the most important or common words. It's like creating a summary of the key topics by picking the words that appear most frequently.
    # 
    # Technical Details:
    # This method:
    # - Takes a Counter object (token frequency distribution) and an optional count N
    # - If N is not provided, uses self.CONTEXT_COUNT_DEFAULT (default 23)
    # - If N is less than or equal to 0, returns an empty list
    # - Uses the Counter's most_common() method to get the top N tokens by frequency
    # - Extracts just the token strings (ignoring the counts) and returns them as a list
    # - This is a direct method (not decorated with @LockManager) as it only processes data passed to it
    # 
    # Parameters:
    # - counter (Counter): A collections.Counter object mapping tokens to their frequencies
    # - n (int, optional): The number of top tokens to return. If not provided, uses CONTEXT_COUNT_DEFAULT.
    # 
    # Returns:
    # - list: A list of strings containing the top N tokens ordered by frequency (highest first)
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # # Create a token counter from some text
    # counter = cavm.Tokenize("The quick brown fox jumps over the lazy dog. The fox was quick and brown.")
    # # counter might be: {'quick': 2, 'brown': 2, 'fox': 2, 'jump': 1, 'over': 1, 'lazi': 1, 'dog': 1}
    # # Get the top 3 tokens
    # top_tokens = cavm.TopTokens(counter, 3)
    # # Returns: ['quick', 'brown', 'fox'] (or similar order depending on how Counter breaks ties)
    # ```
    # 
    # Important Notes:
    # - The method returns only the token strings, not their frequencies
    # - If there are ties in frequency, the order is determined by Python's Counter implementation (which is generally insertion order for equal counts)
    # - If n is greater than the number of unique tokens, returns all tokens ordered by frequency
    # - This method is used internally by GetChainLabels, Update, Search, and GetHistory to create summaries
    # - The default value (CONTEXT_COUNT_DEFAULT) controls how many tokens are used for chain labels and context summaries

    def TopTokens(self, counter, n=None):
        if n is None:
            n = self.CONTEXT_COUNT_DEFAULT
        if n <= 0:
            return []
        most = counter.most_common(n)
        return [tok for tok, _ in most]

    # GetHistory Method Documentation
    # 
    # Purpose:
    # Returns a human-readable summary of all versions in a chain, showing key information about each exchange.
    # 
    # Explanation for Beginners:
    # This method provides a way to look at the complete history of a chain (topic) in an easy-to-read format. For each version (exchange) in the chain, it shows the version number, snippets of the input and response, timestamp, token count, and the top tokens from that exchange. Think of it as getting a detailed log of all conversations about a particular topic.
    # 
    # Technical Details:
    # This method:
    # - Retrieves the chain profile using GetProfile(chain_id)
    # - If the profile doesn't exist, returns an empty list
    # - Iterates through each version in the chain's versions list
    # - For each version, creates a summary dictionary containing:
    #   * version: The version number (1-based index)
    #   * input_snippet: First 60 characters of the input (or empty if none) followed by '...' if truncated
    #   * response_snippet: First 60 characters of the response (or empty if none) followed by '...' if truncated
    #   * timestamp: When this version was created
    #   * token_count: Total number of tokens in this version
    #   * top_tokens: The top 10 tokens from this version (by frequency)
    # - Returns the list of version summaries
    # - The method is decorated with @LockManager to ensure thread-safe access
    # 
    # Parameters:
    # - chain_id (any): The identifier of the chain to retrieve history for (will be converted to string)
    # 
    # Returns:
    # - list: A list of dictionaries, each representing a version in the chain with the fields described above.
    #   Returns an empty list if the chain_id doesn't exist or has no versions.
    # 
    # Usage Example:
    # ```python
    # cavm = ContextAwareVersionedMemory()
    # # Add several exchanges about the same topic
    # cavm.Update(input="What is Python?", response="Python is a programming language")
    # cavm.Update(input="How do I install it?", response="Use pip install python")
    # cavm.Update(input="What are lists?", response="Lists are ordered collections")
    # # Get the history for this chain
    # history = cavm.GetHistory(chain_id)
    # # Returns a list like:
    # # [
    # #   {
    # #     'version': 1,
    # #     'input_snippet': 'What is Python?',
    # #     'response_snippet': 'Python is a programming language',
    # #     'timestamp': '2024-01-01T12:00:00Z',
    # #     'token_count': 5,
    # #     'top_tokens': ['python', 'program', 'language']
    # #   },
    # #   {
    # #     'version': 2,
    # #     'input_snippet': 'How do I install it?',
    # #     'response_snippet': 'Use pip install python',
    # #     'timestamp': '2024-01-01T12:05:00Z',
    # #     'token_count': 6,
    # #     'top_tokens': ['install', 'pip', 'python']
    # #   },
    # #   ...
    # # ]
    # ```
    # 
    # Important Notes:
    # - Snippets are truncated to 60 characters with '...' added if truncated
    # - If input or response is None/empty, the snippet will be an empty string
    # - Token count is the sum of all token frequencies in the version's tokens Counter
    # - Top tokens shows the 10 most frequent tokens from that specific version
    # - The method does not include version metadata like 'v' in the history (it's redundant with the version field)
    # - The @LockManager decorator ensures safe concurrent access

    @LockManager
    def GetHistory(self, chain_id):
        """Return list of version summaries for the chain."""
        profile = self.GetProfile(chain_id)
        if not profile:
            return []
        history = []
        for v in profile['versions']:
            history.append({
                'version': v['v'],
                'input_snippet': (v.get('input','')[:60] + '...') if v.get('input') else '',
                'response_snippet': (v.get('response','')[:60] + '...') if v.get('response') else '',
                'timestamp': v.get('last_updated'),
                'token_count': sum(v['tokens'].values()),
                'top_tokens': self.TopTokens(v['tokens'], 10)
            })
        return history
