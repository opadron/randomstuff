
from copy import copy
from functools import wraps

import itertools as it

import re
import sys

class ReversibleIterator:
    def __init__(self, iterator):
        self.iterator = iter(iterator)
        self.state_stack = []
        self.push_back_buffer = []
        self.iterator_history = []
        self.iterator_history_index = 0

    def push(self):
        self.state_stack.append({
            'offset': self.iterator_history_index,
            'push_back_buffer': copy(self.push_back_buffer)
        })

    def apply(self, state=None):
        if state is None:
            state = self.state_stack[-1]

        self.push_back_buffer = state['push_back_buffer']
        self.iterator_history_index = state['offset']

    def pop(self):
        self.apply(self.state_stack.pop())

    def drop(self):
        self.state_stack.pop()
        self._clean_history()

    def put(self, obj):
        self.push_back_buffer.append(obj)

    def _clean_history(self):
        clear_history = (
            self.iterator_history_index >= len(self.iterator_history) and
            not self.state_stack
        )

        if clear_history:
            self.iterator_history = []
            self.iterator_history_index = 0

    def _next(self):
        if self.push_back_buffer:
            return self.push_back_buffer.pop()

        if self.iterator_history:
            result = None
            has_result = False
            if self.iterator_history_index < len(self.iterator_history):
                result = self.iterator_history[self.iterator_history_index]
                has_result = True
                self.iterator_history_index += 1

            if has_result:
                return result

        try:
            result = next(self.iterator)
        except StopIteration:
            return None

        if self.state_stack:
            self.iterator_history.append(result)
            self.iterator_history_index += 1

        return result

    def next(self):
        result = self._next()
        self._clean_history()
        return result

    def next_while(self, predicate, putcap=True):
        result = []
        while True:
            partial = self.next()
            if partial is not None and predicate(partial):
                result.append(partial)
            else:
                if putcap:
                    self.put(partial)
                break

        return result

    def next_until(self, predicate, putcap=True):
        return self.next_while((lambda partial: not predicate(partial)), putcap)

    def next_while_str(self, predicate, putcap=True):
        return ''.join(self.next_while(predicate, putcap))

    def next_until_str(self, predicate, putcap=True):
        return ''.join(self.next_until(predicate, putcap))

class Parser:
    def __init__(self, tokenizers):
        self.tokenizers = tokenizers
        self.stack = []
        self.state = {}
        self.restart = False

    def push(self, parser):
        self.stack.append(parser)
        self.restart = True

    def pop(self):
        self.stack.pop()
        self.restart = True

    def parse_next(self, stream):
        tokenizers = (self.stack[-1] if self.stack else self).tokenizers

        for tokenizer in tokenizers:
            if self.restart:
                self.restart = False
                return self.parse_next(stream)

            result = tokenizer(stream, self.state, self.push, self.pop)
            if result is not None:
                return result

    def _parse(self, stream):
        while True:
            yield self.parse_next(stream)

    def parse(self, stream):
        return ReversibleIterator(self._parse(stream))


def stream_wrapper(klass):
    def decorator(func):
        @wraps(func)
        def wrapper(_s_t_r_e_a_m_=None,
                    _s_t_a_t_e_=None,
                    _p_u_s_h_=None,
                    _p_o_p_=None,
                    **kwargs):
            if _s_t_a_t_e_ is None:
                _s_t_a_t_e_ = {}

            if _s_t_r_e_a_m_:
                return func(_s_t_r_e_a_m_, _s_t_a_t_e_, _p_u_s_h_, _p_o_p_)
            else:
                return klass(**kwargs)
        return wrapper
    return decorator

def auto_stream(func):
    @wraps(func)
    def wrapper(_s_t_r_e_a_m_, *args, **kwds):
        _s_t_r_e_a_m_.push()
        result = func(_s_t_r_e_a_m_, *args, **kwds)
        if result:
            _s_t_r_e_a_m_.drop()
        else:
            _s_t_r_e_a_m_.pop()
        return result
    return wrapper

def pusher(parser):
    def decorator(func):
        @wraps(func)
        def wrapper(_s_t_r_e_a_m_,
                    _s_t_a_t_e_,
                    _p_u_s_h_,
                    *args,
                    **kwds):
            result = func(_s_t_r_e_a_m_,
                          _s_t_a_t_e_,
                          _p_u_s_h_,
                          *args,
                          **kwds)
            if result is not None:
                _p_u_s_h_(parser)

            return result
        return wrapper
    return decorator

def popper(func):
    @wraps(func)
    def wrapper(_s_t_r_e_a_m_,
                _s_t_a_t_e_,
                _p_u_s_h_,
                _p_o_p_,
                *args,
                **kwds):
        result = func(_s_t_r_e_a_m_,
                      _s_t_a_t_e_,
                      _p_u_s_h_,
                      _p_o_p_,
                      *args,
                      **kwds)
        if result is not None:
            _p_o_p_()

        return result
    return wrapper

def substring_parser(substring):
    def decorator(func):
        @wraps(func)
        def wrapper(_s_t_r_e_a_m_, _s_t_a_t_e_, *args, **kwds):
            has_result = bool(substring)
            for char in substring:
                has_result = (has_result and _s_t_r_e_a_m_.next() == char)
                if not has_result:
                    break

            _s_t_a_t_e_['substring'] = (substring if has_result else None)
            return func(_s_t_r_e_a_m_, _s_t_a_t_e_, *args, **kwds)
        return wrapper
    return decorator

class Token:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __str__(self):
        return '{}: {}'.format(self.__class__.__name__, str(self.__dict__))

def identity(stream, state, push, pop):
    return stream.next()

class CarriageReturn(Token): pass
@stream_wrapper(CarriageReturn)
@auto_stream
@substring_parser('\r')
def carriage_return(stream, state, push, pop):
    return (carriage_return() if state['substring'] else None)

# class NewLine(Token): pass
# @stream_wrapper(NewLine)
# @auto_stream
# @substring_parser('\n')
# def newline(stream, state, push, pop):
#     token = state['substring']
#     if token:
#         has_carriage_return = bool(carriage_return(stream, state, push, pop))
#         if has_carriage_return:
#             stream.next() # eat the '\r'
# 
#         return newline(carriage_return=has_carriage_return)
# 
#     return None

class Space(Token): pass
@stream_wrapper(Space)
@auto_stream
@substring_parser(' ')
def space(stream, state, push, pop):
    return (space() if state['substring'] else None)

class PythonLine(Token): pass
@stream_wrapper(PythonLine)
def python_line(stream, state, push, pop):
    text = stream.next_until_str((lambda c: c is None or c == '\n'))
    return (python_line(text=text) if text else None)

class Identifier(Token): pass
ord_a = ord('a')
ord_z = ord('z')
ord_A = ord('A')
ord_Z = ord('Z')
ord_0 = ord('0')
ord_9 = ord('9')
ord__ = ord('_')
@stream_wrapper(Identifier)
@auto_stream
def identifier(stream, state, push, pop):
    predicate = lambda ord_c: (
        (ord_a <= ord_c and ord_c <= ord_z) or
        (ord_A <= ord_c and ord_c <= ord_Z) or
        ord_c == ord__
    )

    text = stream.next_while_str((lambda c: predicate(ord(c))))
    ord_t0 = (ord(text[0]) if text else None)
    return (
        identifier(text=text)
        if text and not (ord_0 <= ord_t0 and ord_t0 <= ord_9)
        else None
    )

class Colon(Token): pass
@stream_wrapper(Colon)
@auto_stream
@substring_parser(':')
def colon(stream, state, push, pop):
    return (colon() if state['substring'] else None)

def keyword_parser(keyword, klass):
    @stream_wrapper(klass)
    @auto_stream
    @substring_parser(keyword)
    def keyword_func(stream, state, push, pop):
        token = state['substring']
        if token:
            stream.push()
            id = identifier(stream, state, push, pop)
            stream.pop()
            return (klass() if not id else None)
        return None
    return keyword_func

class ParserKeyword(Token): pass

class Filename(Token): pass
class NewLine(Token): pass
@stream_wrapper(Filename)
def filename(stream, state, push, pop):
    if 'f' in state:
        result = '\r'
        while result == '\r':
            result = state['f'].read(1)

        if result:
            if result == '\n':
                result = NewLine()
            return result

        del state['f']

    fname = stream.next()

    if fname:
        state['f'] = open(fname)
        return filename(text=fname)

    return None

class Character(Token): pass
@stream_wrapper(Character)
@auto_stream
def character(stream, state, push, pop):
    c = stream.next()

    if isinstance(c, Filename):
        state['filename'] = c.text
        state['line_number'] = 1
        state['column_number'] = 1

        return None

    if isinstance(c, NewLine):
        state['line_number'] += 1
        state['column_number'] = 1

        return None

    result = None
    if c is not None:
        result = character(
            c=c, line=state['line_number'], column=state['column_number'])

        state['column_number'] += 1

    return result

class String(Token):
    def __str__(self):
        return ''.join((
            'STR ', '(', self.char, ') ',
            '[', ' '.join(str(t) for t in self.tokens), ']'))

class EscapeSequence(Token): pass
@stream_wrapper(String)
@auto_stream
def string(stream, state, push, pop):
    c = stream.next()
    if isinstance(c, Character) and c.c in '"\'`':
        tokens = []
        head = c
        escape = None

        while True:
            c = stream.next()
            if escape == 'x':
                c2 = stream.next()
                if (
                        isinstance(c, Character) and
                        isinstance(c2, Chaacter) and (
                        (ord('a') <= ord(c.c) and ord(c.c) <= ord('f')) or
                        (ord('A') <= ord(c.c) and ord(c.c) <= ord('F')) or
                        (ord('0') <= ord(c.c) and ord(c.c) <= ord('9'))) and (
                        (ord('a') <= ord(c2.c) and ord(c2.c) <= ord('f')) or
                        (ord('A') <= ord(c2.c) and ord(c2.c) <= ord('F')) or
                        (ord('0') <= ord(c2.c) and ord(c2.c) <= ord('9')))):
                    tokens.append(EscapeSequence(
                            text=''.join(('x', c.c, c2.c))))
                    escape = None
                else:
                    raise Error('Invalid escape sequence')
            elif escape == 'u':
                c2 = stream.next()
                c3 = stream.next()
                c4 = stream.next()
                if (
                        isinstance(c, Character) and
                        isinstance(c2, Chaacter) and
                        isinstance(c3, Chaacter) and
                        isinstance(c4, Chaacter) and (
                        (ord('a') <= ord(c.c) and ord(c.c) <= ord('f')) or
                        (ord('A') <= ord(c.c) and ord(c.c) <= ord('F')) or
                        (ord('0') <= ord(c.c) and ord(c.c) <= ord('9'))) and (
                        (ord('a') <= ord(c2.c) and ord(c2.c) <= ord('f')) or
                        (ord('A') <= ord(c2.c) and ord(c2.c) <= ord('F')) or
                        (ord('0') <= ord(c2.c) and ord(c2.c) <= ord('9'))) and (
                        (ord('a') <= ord(c3.c) and ord(c3.c) <= ord('f')) or
                        (ord('A') <= ord(c3.c) and ord(c3.c) <= ord('F')) or
                        (ord('0') <= ord(c3.c) and ord(c3.c) <= ord('9'))) and (
                        (ord('a') <= ord(c4.c) and ord(c4.c) <= ord('f')) or
                        (ord('A') <= ord(c4.c) and ord(c4.c) <= ord('F')) or
                        (ord('0') <= ord(c4.c) and ord(c4.c) <= ord('9')))):
                    tokens.append(EscapeSequence(
                            text=''.join(('u', c.c, c2.c, c3.c, c4.c))))
                    escape = None
                else:
                    raise Error('Invalid escape sequence')
            else:
                if isinstance(c, Character):
                    if c.c == head.c:
                        return String(
                                column=head.column,
                                line=head.line,
                                char=head.c,
                                tokens=tokens)
                    elif c.c == '\\':
                        c2 = stream.next()
                        if isinstance(c2, Character):
                            if c2.c in 'abfnrtv\\' or c2.c == head.c:
                                tokens.append(EscapeSequence(text=c2.c))
                            elif c2.c == 'x' or c2.c == 'u':
                                escape = c2.c
                            else:
                                raise Error('Invalid escape sequence')
                        else:
                            raise Error('Invalid escape sequence')
                    else:
                        tokens.append(c)
                else:
                    tokens.append(c)

    return None

class Indent(Token): pass
@stream_wrapper(Indent)
@auto_stream
def indent(stream, state, push, pop):
    state['indent_enabled'] = state.get('indent_enabled', True)
    indent_enabled = state['indent_enabled']

    c = stream.next()

    if indent_enabled:
        predicate = lambda x: isinstance(x, Character) and x.c == ' '
        if predicate(c) and (c.column - 1)%4 == 0:
            stream.push()
            if (
                predicate(stream.next()) and
                predicate(stream.next()) and
                predicate(stream.next())
            ):
                stream.drop()
                return Indent(column=c.column)
            else:
                stream.pop()

    state['indent_enabled'] = isinstance(c, NewLine)
    return None

FilenameParser = Parser([filename])
CharacterParser = Parser([character, identity])
StringParser = Parser([string, identity])
IndentParser = Parser([indent, identity])

streams = [ReversibleIterator(('sample.txt',))]
streams.append(FilenameParser.parse(streams[-1]))
streams.append(CharacterParser.parse(streams[-1]))
streams.append(StringParser.parse(streams[-1]))
# streams.append(IndentParser.parse(streams[-1]))

## ParserKeywordSubParser = Parser([
##     space,
##     newline,
##     identifier,
##     popper(colon)
## ])
## 
## MainParser = Parser([
##     space,
##     newline,
##     pusher(ParserKeywordSubParser)(keyword_parser('parser', ParserKeyword)),
##     python_line
## ])
## 
## S = ReversibleIterator(it.chain.from_iterable(
##     iter(line) for line in it.takewhile(lambda line: line, sys.stdin)
## ))
## 
## S2 = MainParser.parse(S)

while True:
    token = streams[-1].next()
    if token is None: break
    print('[' + str(token) + ']')

