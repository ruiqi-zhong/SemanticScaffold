import sys
sys.path.append('./')

from parse.lexer import tokenize, filter_space
from collections import defaultdict
from parse.program import Program_generator

def extract_extra_braces(c):
    tokens = filter_space(tokenize(c, new_line=False))
    extra_close_curly, extra_open_curly, goto_stmt = False, False, False
    if len(tokens) >= 1 and tokens[-1].kind == 'operator' and tokens[-1].value == ':':
        goto_stmt = True
    elif len(tokens) >= 2 and tokens[-2].kind == 'operator' and tokens[-2].value == ':' \
        and (tokens[-1].kind == 'semicolon' and tokens[-1].value == ';'):
        goto_stmt = True
    if goto_stmt:
        return extra_close_curly, extra_open_curly, goto_stmt

    stack = []
    num_tokens = len(tokens)
    for idx, t in enumerate(tokens):
        kind = t.kind
        if kind == 'open_curly':
            stack.append((idx, kind))
        elif kind == 'close_curly':
            if len(stack) != 0 and stack[-1][1] == 'open_curly':
                del stack[-1]
            else:
                stack.append((idx, kind))

    for idx, kind in stack:
        if (kind == 'close_curly' and idx != 0) or (kind == 'open_curly' and idx != num_tokens - 1):
            return None
        if kind == 'close_curly':
            extra_close_curly = True
        if kind == 'open_curly':
            extra_open_curly = True
    return extra_close_curly, extra_open_curly, goto_stmt

def check_braces(code_by_line, indent):
    code_by_indent = defaultdict(list)
    for c, i in zip(code_by_line, indent):
        code_by_indent[int(i)].append(c)

    for i in code_by_indent:
        same_level_code = code_by_indent[i]
        brace_info = [extract_extra_braces(c) for c in same_level_code]
        brace_info = [info for info in brace_info if not info[2]]
        if brace_info[0][0] or brace_info[-1][1]:
            return False
        print(len(brace_info))
        for idx in range(len(brace_info) - 1):
            if brace_info[idx][1] != brace_info[idx + 1][0]:
                return False
    return True

def braces_acceptable(program_str):
    tokens = filter_space(tokenize(program_str, new_line=False))
    counter = 0
    for t in tokens:
        if t.kind == 'open_curly':
            counter += 1
        elif t.kind == 'close_curly':
            counter -= 1
        if counter < 0:
            return False
    return counter == 0
