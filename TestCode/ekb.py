import sys
import os

# Expert Knowledge Base (EKB)
# Pre-ASK style knowledge base using the filesystem as a directory trie.
# Input is reduced to keywords, each keyword becomes a directory level.
# The final keyword points to a .txt file containing the answer.
#
# Example:
#   "How do I cook an egg?" -> keywords: ['how', 'cook', 'egg']
#   File path: /home/JackrabbitAI/ExpertKnowledgeBase/english/how/cook/egg.txt

class ExpertKnowledgeBase:
    def __init__(self,base=None,kbpath=None):
        # Words that add no value to the search query.
        # Articles, pronouns, prepositions, auxiliary verbs, etc.
        # Question words (how, what, when, where, why) are NOT stop words
        # because they define the context of the query.
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
                'very'}

        # Synonym reduction: maps complex words to simple equivalents.
        # Applied after depluralization to normalize vocabulary.
        self.REDUCE = {
            'acquire': 'get', 'obtain': 'get', 'procure': 'get', 'attain': 'get',
            'purchase': 'buy', 'procure': 'buy',
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

        # Default location and language of the knowledge base
        self.LANG='english'
        self.BASE=base if base is not None else '/home/JackrabbitAI/ExpertKnowledgeBase'
        self.kbpath=kbpath if kbpath is not None else None

    def SetLocation(self, path):
        # Set or override the base directory for the knowledge base
        self.BASE=path

    def Reduce(self, text):
        # Turn a natural language query into a list of keywords.
        # Steps:
        #   1. Lowercase everything
        #   2. Strip non-alpha characters
        #   3. Remove stop words (words with no search value)
        #   4. Depluralize: -ies -> -y, -ing -> strip, -s -> strip
        #   5. Synonym reduction: map to simplest equivalent word
        words = []
        for w in text.lower().split():
            # Keep only letters, strip punctuation
            w = ''.join(c for c in w if c.isalpha())
            # Skip empty or stop words
            if not w or w in self.STOP:
                continue
            # Depluralize in order of specificity
            if w.endswith('ies') and len(w) > 3:    # berries -> berry
                w = w[:-3] + 'y'
            elif w.endswith('ing') and len(w) > 3:  # cooking -> cook
                w = w[:-3]
            elif w.endswith('s') and len(w) > 1:    # eggs -> egg
                w = w[:-1]
            # Synonym reduction: map to simplest equivalent
            if w in self.REDUCE:
                w = self.REDUCE[w]
            words.append(w)
        return words

    def Search(self, query):
        # Reduce the query to keywords
        keywords = self.Reduce(query)

        # Build the file path from keywords.
        # Language is the root level, then keywords as directories.
        # os.path.join takes each directory as a separate argument.
        # The * operator unpacks the list into separate arguments.
        # Example: keywords = ['how', 'cook', 'egg']
        #          os.path.join(BASE, LANG, 'how', 'cook', 'egg')
        #          -> /home/JackrabbitAI/ExpertKnowledgeBase/english/how/cook/egg
        self.kbpath = os.path.join(self.BASE, self.LANG, *keywords)

        # Check if the answer file exists, return its contents or None
        if os.path.isfile(self.kbpath + '.txt'):
            with open(self.kbpath + '.txt') as f:
                return f.read().strip()
        return None

    def Update(self, answer):
        # Create the directory path if it does not exist
        os.makedirs(os.path.dirname(self.kbpath), exist_ok=True)
        # Write the answer to the .txt file
        with open(self.kbpath + '.txt', 'w') as f:
            f.write(answer)

def TestTheEKB():
    ekb = ExpertKnowledgeBase()

    # Set an answer: search establishes the path, update writes it
    ekb.Search('How do I cook an egg?')

    ekb.Search('What is the best way to learn python?')

    # Retrieve answers
    print(ekb.Search('How do I cook an egg?'))
    print(ekb.Search('What is the best way to learn python?'))

    # Synonym reduction in action
    print(ekb.Reduce('How do I acquire a python?'))
    print(ekb.Reduce('How do I purchase eggs?'))
    print(ekb.Reduce('How do I commence cooking?'))

    print(ekb.Search('How do I fly a kite?'))  # Returns None, no answer stored

if __name__ == '__main__':
    TestTheEKB()
