# Author: T. Junttila
# License: The MIT License

import re

class AST:
    def __init__(self):
        pass
    def to_ssml(self, neural):
        assert False
    def to_words(self):
        assert False
    def to_sub(self):
        assert False
class ASTWord(AST):
    def __init__(self, text):
        self.text = text
    def to_ssml(self, neural):
        return self.text
    def to_words(self):
        return [self.text]
    def to_sub(self):
        return self.text
class ASTBreak(AST):
    def __init__(self, time):
        self.time = time
    def to_ssml(self, neural):
        return '<break time="'+str(self.time*100)+'ms" />'
    def to_words(self):
        return []
    def to_sub(self):
        return ''
class ASTDelim(AST):
    def __init__(self, text):
        self.text = text
    def to_ssml(self, neural):
        return self.text
    def to_words(self):
        return []
    def to_sub(self):
        return self.text
class ASTSpace(AST):
    def __init__(self):
        pass
    def to_ssml(self, neural):
        return ' '
    def to_words(self):
        return []
    def to_sub(self):
        return ' '
class ASTEmph(AST):
    def __init__(self, children):
        self.children = children
    def to_ssml(self, neural):
        children_ssml = "".join([child.to_ssml(neural) for child in self.children])
        if neural:
            return '<prosody rate="90%" volume="loud">'+children_ssml+'</prosody>'
        else:
            return '<prosody pitch="high" volume="loud">'+children_ssml+'</prosody>'
    def to_words(self):
        result = []
        for child in self.children: result += child.to_words()
        return result
    def to_sub(self):
        return "".join([child.to_sub() for child in self.children])
class ASTPhoneme(AST):
    def __init__(self, text, xsampa):
        self.text = text
        self.xsampa = xsampa
    def to_ssml(self, neural):
        return f'<phoneme alphabet="x-sampa" ph="{self.xsampa}">{self.text}</phoneme>'
    def to_words(self):
        return re.split('\s+', self.text.strip())
    def to_sub(self):
        return self.text
class ASTSub(AST):
    def __init__(self, children, subtitles):
        self.children = children
        self.subtitles = subtitles
    def to_ssml(self, neural):
        children_ssml = [child.to_ssml(neural) for child in self.children]
        return "".join(children_ssml)
    def to_words(self):
        result = []
        for child in self.children: result += child.to_words()
        return result
    def to_sub(self):
        return self.subtitles
class ASTSlow(AST):
    def __init__(self, children):
        self.children = children
    def to_ssml(self, neural):
        children_ssml = "".join([child.to_ssml(neural) for child in self.children])
        return '<prosody rate="80%">'+children_ssml+'</prosody>'
    def to_words(self):
        result = []
        for child in self.children: result += child.to_words()
        return result
    def to_sub(self):
        return "".join([child.to_sub() for child in self.children])
class ASTLow(AST):
    def __init__(self, children):
        self.children = children
    def to_ssml(self, neural):
        children_ssml = "".join([child.to_ssml(neural) for child in self.children])
        if neural:
            # prosody pitch not yet in neural TTS, make it slightly slower
            return '<prosody rate="80%">'+children_ssml+'</prosody>'
        else:
            return '<prosody pitch="low">'+children_ssml+'</prosody>'
    def to_words(self):
        result = []
        for child in self.children: result += child.to_words()
        return result
    def to_sub(self):
        return "".join([child.to_sub() for child in self.children])
class ASTHigh(AST):
    def __init__(self, children):
        self.children = children
    def to_ssml(self, neural):
        children_ssml = "".join([child.to_ssml(neural) for child in self.children])
        if neural:
            # prosody pitch not yet in neural TTS, make it slightly faster
            return '<prosody rate="120%">'+children_ssml+'</prosody>'
        else:
            return '<prosody pitch="high">'+children_ssml+'</prosody>'
    def to_words(self):
        result = []
        for child in self.children: result += child.to_words()
        return result
    def to_sub(self):
        return "".join([child.to_sub() for child in self.children])
class ASTSayAs(AST):
    def __init__(self, letters):
        self.letters = letters
    def to_ssml(self, neural):
        return '<say-as interpret-as="characters">'+self.letters+'</say-as>'
    def to_words(self):
        return re.split('\s+', self.letters.strip())
    def to_sub(self):
        return self.letters


def parse_(string):
    i = 0
    n = len(string)
    def read_until(chars):
        nonlocal i
        tmp = i
        while i < n and string[i] not in chars:
            i += 1
        return string[tmp:i]
    def err(msg):
        assert False, msg
    result = []
    while i < n:
        if string[i] == '#':
            if string[i:i+4] == '#sub':
                m = re.match('^#sub(.)(?P<text>((?!\1).)*?)\\1(?P<sub>((?!\1).)+?)\\1', string[i:])
                if m == None:
                    err(f'Malformed #sub "{string[i:]}"')
                t = parse_(m['text'])
                result.append(ASTSub(t, m['sub']))
                i += len(m.group(0))
                continue
            if string[i:i+5] == '#slow':
                m = re.match('^#slow(.)(?P<text>((?!\1).)+?)\\1', string[i:])
                if m == None:
                    err(f'Malformed #slow "{string[i:]}"')
                t = parse_(m['text'])
                result.append(ASTSlow(t))
                i += len(m.group(0))
                continue
            if string[i:i+4] == '#low':
                m = re.match('^#low(.)(?P<text>((?!\1).)+?)\\1', string[i:])
                if m == None:
                    err(f'Malformed #low "{string[i:]}"')
                t = parse_(m['text'])
                result.append(ASTLow(t))
                i += len(m.group(0))
                continue
            if string[i:i+5] == '#high':
                m = re.match('^#high(.)(?P<text>((?!\1).)+?)\\1', string[i:])
                if m == None:
                    err(f'Malformed #high "{string[i:]}"')
                t = parse_(m['text'])
                result.append(ASTHigh(t))
                i += len(m.group(0))
                continue
            if string[i:i+3] == '#ph':
                m = re.match('^#ph(.)(?P<text>((?!\1).)+?)\\1(?P<ph>((?!\1).)+?)\\1', string[i:])
                if m == None:
                    err(f'Malformed #ph "{string[i:]}"')
                result.append(ASTPhoneme(m['text'], m['ph']))
                i += len(m.group(0))
                continue
            # Break #10
            m = re.match('^#(?P<time>\d+)', string[i:])
            if m != None:
                result.append(ASTBreak(int(m['time'])))
                i += len(m.group(0))
                continue
            err(f'Unrecognized command "{string[i:]}"')
        elif string[i] == '*':
            m = re.match('^\*(?P<text>[^\*]+)\*', string[i:])
            if m == None:
                err(f'Malformed emphasis "{string[i:]}"')
            t = parse_(m['text'])
            result.append(ASTEmph(t))
            i += len(m.group(0))
        elif string[i] == '@':
            m = re.match('^@(?P<text>[^@]+)@', string[i:])
            if m == None:
                err(f'Malformed say-ass "{string[i:]}"')
            result.append(ASTSayAs(m['text']))
            i += len(m.group(0))
        else:
            m = re.match('^\s+', string[i:])
            if m != None:
                result.append(ASTSpace())
                i += len(m.group(0))
                continue
            # Negative numbers are words
            m = re.match('^-\d+', string[i:])
            if m != None:
                result.append(ASTWord(m.group(0)))
                i += len(m.group(0))
                continue
            # Delimiters
            m = re.match('^[-.,:;!?"]', string[i:])
            if m != None:
                result.append(ASTDelim(m.group(0)))
                i += len(m.group(0))
                continue
            word = read_until([' ','\t','#','*','@','"','.',',',':',';','!','?'])
            result.append(ASTWord(word))
    return result

def parse(string, neural):
    ast = parse_(string)
    ssml = "".join([node.to_ssml(neural) for node in ast])
    words = []
    for node in ast:
        words += node.to_words()
    sub = "".join([node.to_sub() for node in ast])
    return (ssml, words, sub)
