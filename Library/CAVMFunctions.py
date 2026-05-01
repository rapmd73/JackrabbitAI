#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Jackrabit AI
# 2024-2026 Copyright © Robert APM Darin
# All rights reserved unconditionally.

# Context-Aware Versioned Memory

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib

import CoreFunctions as CF
import FileFunctions as FF

class ContextAwareVersionedMemory:
    """
    Versioned Context-Aware Memory.

    A chain represents a coherent topic/concept across multiple exchanges.
    Each Update() creates a new version within the chain; previous versions remain intact.
    The chain's current state is always its latest version.
    """

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

    # ========== Tokenization & helpers ==========

    def WordTokens(self, text):
        words = []
        for w in str(text).lower().split():
            w = ''.join(c for c in w if c.isalnum())
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

    def Tokenize(self, text):
        return Counter(self.WordTokens(text))

    @staticmethod
    def Hash(text):
        import hashlib
        return hashlib.sha256(str(text).encode('utf-8')).hexdigest()

    @staticmethod
    def CosineLike(counter_a, counter_b):
        if not counter_a or not counter_b:
            return 0.0
        intersection = sum(counter_a[k] * counter_b.get(k, 0) for k in counter_a)
        norm_a = sum(v*v for v in counter_a.values()) ** 0.5
        norm_b = sum(v*v for v in counter_b.values()) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return intersection / (norm_a * norm_b)

    # ========== Profile persistence ==========
    
    def GetProfiles(self):
        if self.profiles is None:
            self.profiles = self.LoadProfiles(self.base)
        return self.profiles

    def MarkProfilesDirty(self):
        self.dirty = True

    def PersistProfilesIfDirty(self):
        if self.dirty:
            self.SaveProfiles(self.base, self.profiles)
            self.dormant_chains = self.LoadDormant(self.base)
            self.dirty = False

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

    def SaveDormant(self, base=None):
        base = base or self.base
        path = os.path.join(base, 'dormant.db')
        lines = []
        for cid in sorted(self.dormant_chains):
            lines.append(f"{cid}")
        FF.WriteFile(path, '\n'.join(lines) + '\n')

    # ========== Decay & Expiry ==========
    
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

    # ========== Chain operations ==========

    def GetChainCount(self):
        profiles = self.GetProfiles()
        self.dormant_chains = self.LoadDormant(self.base)
        active = [cid for cid in profiles if cid not in self.dormant_chains]
        return len(active)

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

    def GetProfile(self, chain_id):
        profiles = self.GetProfiles()
        return profiles.get(str(chain_id))

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

    # ========== Core API ==========

    def Update(self, content=None, input=None, response=None, contexts=None):
        """
        Create a new version within a chain.
        Chain identity is determined by similarity to existing chains' LATEST versions.
        If similar chain found → append version to that chain.
        Else → create new chain (version 1).
        Returns (chain_id, version_number).
        """
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

    def Search(self, query, limit=3, version=None):
        """
        Search for chains relevant to the query.
        By default, scores against the latest version of each active chain.
        Returns list of (score, chain_id, version_index, top_tokens) tuples, sorted descending.
        """
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

    def TopTokens(self, counter, n=None):
        if n is None:
            n = self.CONTEXT_COUNT_DEFAULT
        if n <= 0:
            return []
        most = counter.most_common(n)
        return [tok for tok, _ in most]

    # Convenience: human-readable history
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
