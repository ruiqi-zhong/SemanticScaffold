import sys
sys.path.append('./')

from onmt_dir.prepare_for_onmt import round_trip
from parse.lexer import tokenize, filter_space, join_tokens
import re
from collections import namedtuple, OrderedDict

debug = False
foroneline = re.compile('for\s*\(.+\)\s*\{.+;\s*\}')

Atom = namedtuple('Atom', ['name', 'f', 'optional'])
trivial_code = {'', ';', '}', '{'}

def split_by_semicolon(code):
    tokens = filter_space(tokenize(code, new_line=False))
    semi_idxes = [idx for idx, token in enumerate(tokens) if token.kind == "semicolon"]
    semi_idxes = [-1] + semi_idxes + [len(tokens)]
    segments = [join_tokens(tokens[semi_idxes[i] + 1: semi_idxes[i + 1]]) for i in range(len(semi_idxes) - 1)]
    return segments

class parse_single_line_exception(Exception):
    pass

def line_well_formed_brace(code):
    tokens = filter_space(tokenize(code, new_line=False))
    start, end = 0, len(tokens)
    if len(tokens) == 0:
        return True
    if tokens[0].kind == 'close_curly':
        start += 1
    if tokens[-1].kind == 'open_curly':
        end -= 1
    count = 0
    for token in tokens[start:end]:
        if token.kind == 'open_curly':
            count += 1
        elif token.kind == 'close_curly':
            count -= 1
        if count < 0:
            return False
    if count != 0:
        return False
    return True

def clean_braces(start_idx, tokens):
    resulting_tokens = None
    if tokens[start_idx].kind == 'open_curly':
        end_idx, content = find_matching_close(start_idx, tokens, 'curly')
        if end_idx != len(tokens):
            return None
        else:
            resulting_tokens = tokens[start_idx + 1: end_idx - 1]
    if resulting_tokens is None:
        resulting_tokens = tokens[start_idx:]
    if len(resulting_tokens) == 0:
        return ''
    if resulting_tokens[-1].kind == 'semicolon':
        del resulting_tokens[-1]
    returned_val = join_tokens(resulting_tokens)
    return returned_val

def end_w_open_curly(tokens):
    return len(tokens) != 0 and tokens[-1].kind == 'open_curly'

def start_w_close_curly(tokens):
    return len(tokens) != 0 and tokens[0].kind == 'close_curly'

def find_matching_close(start_idx, tokens, paren_type):
    paren_start_idx, paren_end_idx, content = start_idx, None, None
    stack_depth = 1
    for idx in range(paren_start_idx + 1, len(tokens)):
        if tokens[idx].kind == 'open_' + paren_type:
            stack_depth += 1
        elif tokens[idx].kind == 'close_' + paren_type:
            stack_depth -= 1
        if stack_depth == 0:
            paren_end_idx = idx + 1
            content = join_tokens(tokens[start_idx + 1: paren_end_idx - 1])
            break
    return paren_end_idx, content

def match_paren(start_idx, tokens):
    return find_matching_close(start_idx, tokens, 'paren')

def match_curly(start_idx, tokens):
    return find_matching_close(start_idx, tokens, 'curly')

def match_token_(start_idx, tokens, token_val):
    token = tokens[start_idx]
    if token.kind not in ('in-quote', 'in-char'):
        if token.value == token_val:
            return start_idx + 1, token.value
    return None, None

def get_match_token(token_val):
    def f(start_idx, tokens):
        return match_token_(start_idx, tokens, token_val)
    return f

def match_kind_(start_idx, tokens, kind):
    token = tokens[start_idx]
    if token.kind == kind:
        return start_idx + 1, token.value
    return None, None

def get_match_kind(kind):
    def f(start_idx, tokens):
        return match_kind_(start_idx, tokens, kind)
    return f

def get_trailing(start_idx, tokens):
    return len(tokens), clean_braces(start_idx, tokens)

def parse_gen(code, grammar):
    tokens = filter_space(tokenize(round_trip(code), new_line=False))
    result = OrderedDict()
    result['code'] = code
    result['start_w_close_curly'] = start_w_close_curly(tokens)
    result['end_w_open_curly'] = end_w_open_curly(tokens)
    cur_idx = 0
    if tokens[-1].value == ';':
        tokens = tokens[:-1]
    for atom in grammar:
        if cur_idx >= len(tokens):
            next_idx, content = None, None
        else:
            next_idx, content = atom.f(cur_idx, tokens)
        if next_idx is None and not atom.optional:
            raise parse_single_line_exception('Error parsing atom %s, which is required' % atom.name)
        result[atom.name] = content
        if next_idx is not None:
            cur_idx = next_idx
    if 'stmt' in result:
        result['new_scope'] = result['stmt'] is None
    else:
        result['new_scope'] = False
    return result

ifline_grammar = [
    Atom('extra closing curly', get_match_kind('close_curly'), True),
    Atom('else', get_match_token('else'), True),
    Atom('if', get_match_token('if'), False),
    Atom('predicate_stmt', match_paren, True),
    Atom('stmt', get_trailing, True)
]
def parse_ifline(code):
    result = parse_gen(code, ifline_grammar)
    return result


elseline_grammar = [
    Atom('extra closing curly', get_match_kind('close_curly'), True),
    Atom('else', get_match_token('else'), False),
    Atom('stmt', get_trailing, True)
]
def parse_elseline(code):
    result = parse_gen(code, elseline_grammar)
    return result

forline_grammar = [
    Atom('for', get_match_token('for'), False),
    Atom('for_control', match_paren, True),
    Atom('stmt', get_trailing, True)
]
def parse_forline(code):
    for_parse = parse_gen(code, forline_grammar)
    result = OrderedDict()
    for_control = for_parse['for_control']
    triplet = split_by_semicolon(for_control)
    if len(triplet) == 3:
        result['for_init_stmt'], result['for_cond_stmt'], result['for_increment_stmt'] = triplet
    else:
        result['for_init_stmt'], result['for_iter_stmt'] = for_control.split(':')
    for key in ['stmt', 'new_scope', 'start_w_close_curly', 'end_w_open_curly']:
        result[key] = for_parse[key]
    return result

whileline_grammar = [
    Atom('extra closing curly', get_match_kind('close_curly'), True),
    Atom('while', get_match_token('while'), False),
    Atom('while_cond_stmt', match_paren, True),
    Atom('stmt', get_trailing, True)
]
def parse_whileline(code):
    result = parse_gen(code, whileline_grammar)
    if result['start_w_close_curly']:
        result['new_scope'] = False
    return result

doline_grammar = [
    Atom('do', get_match_token('do'), False),
    Atom('stmt', get_trailing, True)
]
def parse_doline(code):
    return parse_gen(code, doline_grammar)

line_grammar = [
    Atom('line_stmt', get_trailing, False)
]
def parse_simpleline(code):
    return parse_gen(code, line_grammar)

def parse_dowhile(code):
    while_idx = code.index('while')
    do_part, while_part = code[:while_idx], code[while_idx:]
    do_result = parse_doline(do_part)
    while_result = parse_whileline(while_part)
    result = OrderedDict()
    for key in do_result:
        result[key] = do_result[key]
    for key in while_result:
        result[key] = while_result[key]

    tokens = filter_space(tokenize(round_trip(code), new_line=False))
    result['code'] = code
    result['start_w_close_curly'] = start_w_close_curly(tokens)
    result['end_w_open_curly'] = end_w_open_curly(tokens)
    result['new_scope'] = False
    return result

def has_key_word(code, kword):
    tokens = tokenize(code)
    for t in tokens:
        if t.value == kword and t.kind != 'in-quote':
            return True
    return False

# all the statements in the decomposed results
# operate at a deeper level of symbol table
def post_process_decomposition(result, depth_added):
    returned_val = OrderedDict()
    for key in result:
        if 'stmt' in key:
            if result[key] is not None and result[key] not in trivial_code:
                returned_val[key] = result[key], depth_added
        else:
            returned_val[key] = result[key]
    return returned_val

def return_result_for_trivial_code(code):
    tokens = filter_space(tokenize(round_trip(code), new_line=False))
    result = OrderedDict()
    result['code'] = code
    result['start_w_close_curly'] = start_w_close_curly(tokens)
    result['end_w_open_curly'] = end_w_open_curly(tokens)
    result['new_scope'] = result['end_w_open_curly']
    if code == '{':
        result['line_type'] = 'open_curly_only'
    elif code == '}':
        result['line_type'] = 'close_curly_only'
    elif code == '':
        result['line_type'] = 'empty'
    elif code == ';':
        result['line_type'] = 'line'
    return result

def return_result_for_line_marker(code):
    tokens = filter_space(tokenize(round_trip(code), new_line=False))
    result = OrderedDict()
    result['code'] = code
    result['start_w_close_curly'] = start_w_close_curly(tokens)
    result['end_w_open_curly'] = end_w_open_curly(tokens)
    result['new_scope'] = result['end_w_open_curly']
    result['line_type'] = 'marker'
    return result

def decompose_line(code):
    if not line_well_formed_brace(code):
        return None
    code = round_trip(code)
    if code in trivial_code:
        return return_result_for_trivial_code(code)
    if code[-1] == ':':
        return return_result_for_line_marker(code)

    result = None
    has_do, has_while, has_if, has_for, has_else = [has_key_word(code, kword) for kword in ['do', 'while', 'if', 'for', 'else']]
    if has_if:
        result = parse_ifline(code)
        result['line_type'] = 'if' if not has_else else 'else if'
    elif has_else:
        result = parse_elseline(code)
        result['line_type'] = 'else'
    elif has_while and not has_do:
        result = parse_whileline(code)
        result['line_type'] = 'while'
    elif has_for:
        result = parse_forline(code)
        result['line_type'] = 'for'
    elif has_do and not has_while:
        result = parse_doline(code)
        result['line_type'] = 'do'
    elif has_do and has_while:
        result = parse_dowhile(code)
        result['line_type'] = 'dowhile'
    if result is not None:
        result = post_process_decomposition(result, 1)
    else:
        result = parse_simpleline(code)
        result = post_process_decomposition(result, 0)
        result['line_type'] = 'line'

    if result is not None and debug:
        for key in result:
            if 'stmt' in key:
                print(key, result[key])
        input()
    return result
