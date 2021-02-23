"""
Parser for pdf2video script file syntax.
Author: T. Junttila
License: The MIT License
"""

from abc import ABC, abstractmethod
import re
import sys

class AST(ABC):
    """Base class for abstract syntax tree nodes."""

    @abstractmethod
    def to_ssml(self, neural):
        """Get the SSML representation of the sub-tree."""

    @abstractmethod
    def to_words(self):
        """Get the plain words representation of the sub-tree."""

    @abstractmethod
    def to_sub(self):
        """Get the sub-titles representation of the sub-tree."""

class ASTWord(AST):
    """An AST node for a word."""
    def __init__(self, text):
        super().__init__()
        self.text = text
    def to_ssml(self, neural):
        return self.text
    def to_words(self):
        return [self.text]
    def to_sub(self):
        return self.text

class ASTBreak(AST):
    """An AST node for a break."""
    def __init__(self, time):
        self.time = time
    def to_ssml(self, neural):
        return '<break time="'+str(self.time*100)+'ms" />'
    def to_words(self):
        return []
    def to_sub(self):
        return ''

class ASTDelim(AST):
    """An AST node for a delimiter."""
    def __init__(self, text):
        self.text = text
    def to_ssml(self, neural):
        return self.text
    def to_words(self):
        return []
    def to_sub(self):
        return self.text

class ASTSpace(AST):
    """An AST node for a white space."""
    def __init__(self):
        pass
    def to_ssml(self, neural):
        return ' '
    def to_words(self):
        return []
    def to_sub(self):
        return ' '

class ASTEmph(AST):
    """An AST node for emphasized text."""
    def __init__(self, children):
        self.children = children
    def to_ssml(self, neural):
        children_ssml = "".join([child.to_ssml(neural) for child in self.children])
        if neural:
            return '<prosody rate="90%" volume="loud">'+children_ssml+'</prosody>'
        return '<prosody pitch="high" volume="loud">'+children_ssml+'</prosody>'
    def to_words(self):
        result = []
        for child in self.children:
            result += child.to_words()
        return result
    def to_sub(self):
        return "".join([child.to_sub() for child in self.children])

class ASTPhoneme(AST):
    """An AST node for text read with phonemes."""
    def __init__(self, text, xsampa):
        self.text = text
        self.xsampa = xsampa
    def to_ssml(self, neural):
        return f'<phoneme alphabet="x-sampa" ph="{self.xsampa}">{self.text}</phoneme>'
    def to_words(self):
        return re.split(r'\s+', self.text.strip())
    def to_sub(self):
        return self.text

class ASTSub(AST):
    """An AST node for text with different sub-title representation."""
    def __init__(self, children, subtitles):
        self.children = children
        self.subtitles = subtitles
    def to_ssml(self, neural):
        children_ssml = [child.to_ssml(neural) for child in self.children]
        return "".join(children_ssml)
    def to_words(self):
        result = []
        for child in self.children:
            result += child.to_words()
        return result
    def to_sub(self):
        return self.subtitles

class ASTSlow(AST):
    """An AST node for text read slowly."""
    def __init__(self, children):
        self.children = children
    def to_ssml(self, neural):
        children_ssml = "".join([child.to_ssml(neural) for child in self.children])
        return '<prosody rate="80%">'+children_ssml+'</prosody>'
    def to_words(self):
        result = []
        for child in self.children:
            result += child.to_words()
        return result
    def to_sub(self):
        return "".join([child.to_sub() for child in self.children])

class ASTLow(AST):
    """An AST node for text read in low pitch."""
    def __init__(self, children):
        self.children = children
    def to_ssml(self, neural):
        children_ssml = "".join([child.to_ssml(neural) for child in self.children])
        if neural:
            # prosody pitch not yet in neural TTS, make it slightly slower
            return '<prosody rate="80%">'+children_ssml+'</prosody>'
        return '<prosody pitch="low">'+children_ssml+'</prosody>'
    def to_words(self):
        result = []
        for child in self.children:
            result += child.to_words()
        return result
    def to_sub(self):
        return "".join([child.to_sub() for child in self.children])

class ASTHigh(AST):
    """An AST node for text read in high pitch."""
    def __init__(self, children):
        self.children = children
    def to_ssml(self, neural):
        children_ssml = "".join([child.to_ssml(neural) for child in self.children])
        if neural:
            # prosody pitch not yet in neural TTS, make it slightly faster
            return '<prosody rate="120%">'+children_ssml+'</prosody>'
        return '<prosody pitch="high">'+children_ssml+'</prosody>'
    def to_words(self):
        result = []
        for child in self.children:
            result += child.to_words()
        return result
    def to_sub(self):
        return "".join([child.to_sub() for child in self.children])

class ASTSayAs(AST):
    """An AST node for text read as letters."""
    def __init__(self, letters):
        self.letters = letters
    def to_ssml(self, neural):
        return '<say-as interpret-as="characters">'+self.letters+'</say-as>'
    def to_words(self):
        return re.split(r'\s+', self.letters.strip())
    def to_sub(self):
        return self.letters


def parse_to_ast(string, err_linenum = None):
    """Parse the script text string into a sequence of AST nodes."""
    i = 0
    string_length = len(string)
    def read_until(chars):
        nonlocal i
        tmp = i
        while i < string_length and string[i] not in chars:
            i += 1
        return string[tmp:i]
    def err(msg):
        linenum_text = '' if err_linenum is None else f'On line {err_linenum}: '
        print(linenum_text+msg)
        sys.exit(1)
        #assert False, msg
    result = []
    while i < string_length:
        if string[i] == '#':
            if string[i:i+4] == '#sub':
                match = re.match(
                    '^#sub(.)(?P<text>((?!\1).)*?)\\1(?P<sub>((?!\1).)+?)\\1',
                    string[i:])
                if match is None:
                    err(f'Malformed #sub "{string[i:]}"')
                result.append(ASTSub(parse_to_ast(match['text']), match['sub']))
                i += len(match.group(0))
                continue
            if string[i:i+5] == '#slow':
                match = re.match('^#slow(.)(?P<text>((?!\1).)+?)\\1', string[i:])
                if match is None:
                    err(f'Malformed #slow "{string[i:]}"')
                result.append(ASTSlow(parse_to_ast(match['text'])))
                i += len(match.group(0))
                continue
            if string[i:i+4] == '#low':
                match = re.match('^#low(.)(?P<text>((?!\1).)+?)\\1', string[i:])
                if match is None:
                    err(f'Malformed #low "{string[i:]}"')
                result.append(ASTLow(parse_to_ast(match['text'])))
                i += len(match.group(0))
                continue
            if string[i:i+5] == '#high':
                match = re.match('^#high(.)(?P<text>((?!\1).)+?)\\1', string[i:])
                if match is None:
                    err(f'Malformed #high "{string[i:]}"')
                result.append(ASTHigh(parse_to_ast(match['text'])))
                i += len(match.group(0))
                continue
            if string[i:i+3] == '#ph':
                match = re.match(
                    '^#ph(.)(?P<text>((?!\1).)+?)\\1(?P<ph>((?!\1).)+?)\\1',
                    string[i:])
                if match is None:
                    err(f'Malformed #ph "{string[i:]}"')
                result.append(ASTPhoneme(match['text'], match['ph']))
                i += len(match.group(0))
                continue
            # Break #10
            match = re.match(r'^#(?P<time>\d+)', string[i:])
            if match:
                result.append(ASTBreak(int(match['time'])))
                i += len(match.group(0))
                continue
            err(f'Unrecognized script command "{string[i:]}"')
        elif string[i] == '*':
            match = re.match(r'^\*(?P<text>[^\*]+)\*', string[i:])
            if match is None:
                err(f'Malformed emphasis "{string[i:]}"')
            result.append(ASTEmph(parse_to_ast(match['text'])))
            i += len(match.group(0))
        elif string[i] == '@':
            match = re.match(r'^@(?P<text>[^@]+)@', string[i:])
            if match is None:
                err(f'Malformed say-as "{string[i:]}"')
            result.append(ASTSayAs(match['text']))
            i += len(match.group(0))
        else:
            match = re.match(r'^\s+', string[i:])
            if match:
                result.append(ASTSpace())
                i += len(match.group(0))
                continue
            # Negative numbers are words
            match = re.match(r'^-\d+', string[i:])
            if match:
                result.append(ASTWord(match.group(0)))
                i += len(match.group(0))
                continue
            # Delimiters
            match = re.match('^[-.,:;!?"]', string[i:])
            if match:
                result.append(ASTDelim(match.group(0)))
                i += len(match.group(0))
                continue
            word = read_until([' ','\t','#','*','@','"','.',',',':',';','!','?'])
            result.append(ASTWord(word))
    return result

def parse(string, neural):
    """Parse a script text line."""
    ast = parse_to_ast(string)
    ssml = "".join([node.to_ssml(neural) for node in ast])
    words = []
    for node in ast:
        words += node.to_words()
    sub = "".join([node.to_sub() for node in ast])
    return (ssml, words, sub)
