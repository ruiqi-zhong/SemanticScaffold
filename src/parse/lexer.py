if __name__ == '__main__':
    import sys
    sys.path.append('./')

import collections
import re
from parse.str_util import split_keep_space, cmp_sub


Token = collections.namedtuple("Token", ["kind", "value", "offset", "program_token_id"])

def filter_space(tokens):
    return [t for t in tokens if type(t).__name__ != 'Token' or t.kind != 'whitespace']

def join_tokens(tokens):
    rep = ''.join([t.value + ' ' if t.kind not in ('in-quote', 'in-char', 'start-quote', 'start-char') else t.value for t in tokens])
    return rep.strip()

class Token:
    
    def __init__(self, kind, value, offset):
        self.kind, self.value, self.offset = kind, value, offset
    
    def set_pid(self, pid):
        self.program_token_id = pid
        self.start, self.end = pid, pid
    
    def set_program(self, program):
        self.program = program
    
    def set_lid(self, lid):
        self.line_id = lid
        
    def __repr__(self):
        return self.value#str(vars(self))

operators = [
    ">>=",
    "<<=",
    "+=",
    "-=",
    "*=",
    "/=",
    "%=",
    "&=",
    "|=",
    "^=",
    "<<",
    ">>",
    "++",
    "--",
    "->",
    "&&",
    "||",
    "==",
    "!=",
    "<=",
    ">=",
    "::",
    "<",
    ">",
    "+",
    "-",
    "*",
    "/",
    "%",
    "=",
    "!",
    "~",
    "&",
    "|",
    "^",
    ".",
    ",",
    "?",
    ":",
    "#",
    "sizeof\b",
    "new\b",
    "delete\b"
]

operators = [
    ">>=",
    "<<=",
    "+=",
    "-=",
    "*=",
    "/=",
    "%=",
    "&=",
    "|=",
    "^=",
    "<<",
    ">>",
    "++",
    "--",
    "->",
    "&&",
    "||",
    "==",
    "!=",
    "<=",
    ">=",
    "::",
    "<",
    ">",
    "+",
    "-",
    "*",
    "/",
    "%",
    "=",
    "!",
    "~",
    "&",
    "|",
    "^",
    ".",
    ",",
    "?",
    ":",
    "#"
]

word_op = [
    r"sizeof\b",
    r"new\b",
    r"delete\b"
]

specification = [
    ("whitespace", r"\s+"),
    ("operator", "|".join([re.escape(operator) for operator in operators] + word_op)),
    ("identifier", r"[a-zA-Z_$][a-zA-Z0-9_]*"),
    ("LL", r"\d+(LL|ll)"),
    ("hexa", r"0x[a-f0-9]+"),
    ("scientific", r"\d+(\.\d*)?(e|E)(-|\+)?\d+"),
    ("number", r"\d+(\.\d*)?"),
    ("string", r'"(\\.|[^\\"])*"'),
    ("character", r"'(\\.|[^\\'])'"),
    ("open_curly", re.escape("{")),
    ("close_curly", re.escape("}")),
    ("open_paren", re.escape("(")),
    ("close_paren", re.escape(")")),
    ("open_square", re.escape("[")),
    ("close_square", re.escape("]")),
    ("semicolon", re.escape(";")),
]

regex = "|".join(
    "(?P<{}>{})".format(kind, pattern) for kind, pattern in specification)

def post_process(token):
    if token.kind != 'in-quote':
        if token.value == 'and':
            token.kind = 'operator'
            token.value = '&&'
        if token.value == 'or':
            token.kind = 'operator'
            token.value = '||'


class TokenizationError(Exception):
    pass


def tokenize(code, fill_program_id=False, new_line=True):
    index = 0
    tokens = []
    offset = 0
    for match in re.finditer(regex, code):
        kind = match.lastgroup
        value = match.group()
        index = match.end()
        if kind == 'string':
            # split the strings into quotes and in-quotes
            tokens.append(Token('start-quote', '\"', offset))
            segs = split_keep_space(value[1:-1], offset + 1)
            for val, idx in segs:
                tokens.append(Token('in-quote', val, idx))
            tokens.append(Token('end-quote', '\"', index - 1))
        elif kind == 'character':
            tokens.append(Token('start-char', value[0], offset))
            tokens.append(Token('in-char', value[1:-1], offset + 1))
            tokens.append(Token('end-char', value[-1], index - 1))
        else:
            t = Token(kind, value, offset)
            post_process(t)
            tokens.append(t)
        offset = index

    if index != len(code):
        # raise TokenizationError('Cannot parse %s' % code)
        pass

    for token in tokens:
        if not cmp_sub(token.value, code, token.offset):
            # print(tokens)
            # raise TokenizationError('Cannot parse %s' % code)
            pass
        
    if new_line:
        tokens.append(Token('whitespace', '\n', offset))
    if fill_program_id:
        for pid, token in enumerate(tokens):
            token.program_token_id = pid
            token.start, token.end = pid, pid

    return tokens


def main():
    tokens = tokenize("int main(){ x[0] = 1; *y = 1; &a= 1; newM new a[1]; 2 <= 1; 1e-9; sizeof int; \"hello world!\\n\" }")
    print([(t.value, t.kind) for t in tokens])


if __name__ == "__main__":
    main()