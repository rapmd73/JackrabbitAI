#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Jackrabit AI
# 2024-2025 Copyright © Robert APM Darin
# All rights reserved unconditionally.

# Expert Knowledge Base (EKB)
# Pre-ASK style knowledge base using the filesystem as a directory trie.
# Manual population, sliding window search, returns all matching knowledge.
#
# Example:
#   "How do I cook an egg?" -> keywords: ['how', 'cook', 'egg']
#   File path: /tmp/Expert/english/how/cook/egg.txt

import sys
import os

sys.path.append('/home/JackrabbitAI/Library')

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Jackrabit AI
# 2024-2025 Copyright © Robert APM Darin
# All rights reserved unconditionally.

import sys
import os

import DecoratorFunctions as DF
import CoreFunctions as CF
import FileFunctions as FF

class ExpertKnowledgeBase:
    def __init__(self, Base=None):
        # Stop words (no search value)
        self.STOP = {'a','an','the','is','are','was','were','be','been','being',
                'have','has','had','do','does','did','will','would','shall',
                'should','may','might','must','can','could','i','you','he',
                'she','it','we','they','me','him','her','us','them','my',
                'your','his','its','our','their','this','that','these','those',
                'if','then','else','for','and','nor','but','or','yet','so',
                'to','of','in','on','at','by','with','from','up','about',
                'into','through','during','before','after','above','below',
                'between','under','again','further','once','here','there',
                'all','each','every','both','few','more','most','other',
                'some','such','no','not','only','own','same','than','too',
                'very','as',
                # Common verbs with no search value
                'said','say','says','told','tell','tells','asked','ask','asks',
                'went','go','goes','come','comes','came','get','gets','got',
                'make','makes','made','know','knows','knew','think','thinks','thought',
                'take','takes','took','see','sees','saw','want','wants','wanted',
                'use','uses','used','find','finds','found','give','gives','gave',
                'put','puts','keep','keeps','kept','let','lets','begin','begins','began',
                'show','shows','showed','hear','hears','heard','play','plays','played',
                'run','runs','ran','move','moves','moved','live','lives','lived',
                'believe','believes','believed','bring','brings','brought',
                'happen','happens','happened','write','writes','wrote',
                'provide','provides','provided','sit','sits','sat',
                'stand','stands','stood','lose','loses','lost',
                'pay','pays','paid','meet','meets','met',
                'include','includes','included','continue','continues','continued',
                'set','sets','learn','learns','learned','change','changes','changed',
                'lead','leads','led','understand','understands','understood',
                'watch','watches','watched','follow','follows','followed',
                'stop','stops','stopped','create','creates','created',
                'speak','speaks','spoke','read','reads','allow','allows','allowed',
                'add','adds','added','spend','spends','spent','grow','grows','grew',
                'open','opens','opened','walk','walks','walked','win','wins','won',
                'offer','offers','offered','remember','remembers','remembered',
                'love','loves','loved','consider','considers','considered',
                'appear','appears','appeared','buy','buys','bought',
                'wait','waits','waited','serve','serves','served',
                'die','dies','died','send','sends','sent','expect','expects','expected',
                'build','builds','built','stay','stays','stayed',
                'fall','falls','fell','cut','cuts','reach','reaches','reached',
                'kill','kills','killed','remain','remains','remained'}

        # Synonym reduction
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

        # Configuration
        self.LANG = 'english'
        self.BASE=Base if Base is not None else '/home/JackrabbitAI/ExpertKnowledgeBase'
        FF.mkdir(self.BASE)

    def SetLocation(self, path):
        # Set or override the base directory for the knowledge base
        self.BASE=path

    def Reduce(self, text):
        # Turn text into keywords
        words = []
        for w in text.lower().split():
            w = ''.join(c for c in w if c.isalpha())
            if not w or w in self.STOP:
                continue
            if w.endswith('ies') and len(w) > 3:
                w = w[:-3] + 'y'
            elif w.endswith('ing') and len(w) > 3:
                w = w[:-3]
            elif w.endswith('s') and len(w) > 1:
                w = w[:-1]
            if w in self.REDUCE:
                w = self.REDUCE[w]
            words.append(w)
        return words

    def Search(self, text):
        # Search with sliding window, return ALL matching knowledge as a list
        # Start at 10 words, work backwards (more words = more specific)
        keywords = self.Reduce(text)

        if len(keywords) < 2:
            return None

        # Collect all matches (avoid duplicates)
        matches = []
        tried = set()

        # Start at 10 words (or max available), work backwards to 2
        max_window = min(10, len(keywords))

        for window_size in range(max_window, 1, -1):
            for i in range(len(keywords) - window_size + 1):
                window = tuple(keywords[i:i + window_size])

                if window in tried:
                    continue
                tried.add(window)

                # Try all sub-sequences of this window
                for start in range(len(window)):
                    for end in range(len(window), start, -1):
                        subseq = window[start:end]
                        if len(subseq) < 2:
                            continue

                        path = os.path.join(self.BASE, self.LANG, *subseq)
                        if os.path.exists(path+'.txt'):
                            content=FF.ReadFile(path+'.txt')
                            if content and content not in matches:
                                matches.append(content)

        if not matches:
            return None

        return matches
