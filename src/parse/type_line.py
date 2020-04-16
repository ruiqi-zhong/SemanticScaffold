import sys
sys.path.append('./')

from parse.single_line_expr import decompose_line, end_w_open_curly, start_w_close_curly, parse_single_line_exception
from parse.chunk_parser import parse_chunk, parse_func_header, ParseChunkError
from parse.lexer import tokenize
from onmt_dir.prepare_for_onmt import round_trip

debug = False

class LineSig:

    def __init__(self, line_code, typed=True):
        result = type_line(line_code)
        if result is not None:
            self.atoms_declared, self.atoms_used, self.prototype = result
        self.is_none = (result == None)
        self.typed = typed

    def __repr__(self):
        if self.is_none:
            return 'nonelinesig'
        s = '========== line sigature starts ==========\n'
        s += 'atoms declared \n'
        for key in sorted(self.atoms_declared.keys()):
            s += key.__repr__()
            if self.typed:
                s += ' ' + self.atoms_declared[key].__repr__()
            s += '\n'

        s += 'atoms used \n'
        for key in sorted(self.atoms_used):
            s += key + '\n'
        s += str(self.prototype) + '\n'
        s += '========== line sigature ends ==========\n'
        return s

    def __hash__(self):
        return hash(self.__repr__())

    def __eq__(self, other):
        if not isinstance(other, LineSig):
            return False
        if self.__repr__() == other.__repr__():
            return True
        return False

def adddepth2func(result, atoms_declared):
    atoms_declared[('func', result['func_decl'][0])] = result['func_decl'][1], 0
    for arg_name, arg_type in result['var_decl'].items():
        atoms_declared[('var_name', arg_name)] = arg_type, 1
    if result['is_prototype']:
        return result['func_decl'][0]

def addvar_decl2line(segment_info, atoms_declared, depth):
    for var_name, var_type in segment_info['var_decl'].items():
        atoms_declared[('var_name', var_name)] = var_type, depth

def parse_var_used(nodes, atoms_used, depth):
    for node in nodes:
        if type(node).__name__ == 'Token':
            if node.kind == 'identifier':
                atoms_used[node.value] = depth
        else:
            for identifier in node.get_identifiers():
                atoms_used[identifier] = depth

def get_cores(line_code):
    line_code = round_trip(line_code)
    try:
        tokens = tokenize(line_code)
        result = parse_func_header(tokens)
        return []
    except:
        result = decompose_line(line_code)
        cores = []
        for key in result:
            if 'stmt' in key:
                stmt, depth = result[key]
                stmt = tokenize(stmt)
                segment_info = parse_chunk(stmt)
                cores += segment_info['nodes']
        return cores


def type_line(line_code):
    line_code = round_trip(line_code)
    atoms_declared, atoms_used, prototype = {}, {}, None
    forest = []
    try:
        try:
            tokens = tokenize(line_code, new_line=False)
            result = parse_func_header(tokens)
            line_type = 'prototype' if result['is_prototype'] else 'function'
            prototype = adddepth2func(result, atoms_declared)
            sw_close_curly, ew_open_curly = start_w_close_curly(tokens), end_w_open_curly(tokens)
        except ParseChunkError:
            result = decompose_line(line_code)
            if result is None:
                return None
            line_type = result['line_type']
            sw_close_curly, ew_open_curly = result['start_w_close_curly'], result['end_w_open_curly']
            for key in result:
                if 'stmt' in key:
                    stmt, depth = result[key]
                    stmt = tokenize(stmt, new_line=False)
                    segment_info = parse_chunk(stmt)
                    addvar_decl2line(segment_info, atoms_declared, depth)
                    parse_var_used(segment_info['nodes'], atoms_used, depth)
                    forest += segment_info['nodes']

        return {
            # used for consider scope
            'line_type': line_type,
            'start_w_close_curly': sw_close_curly,
            'end_w_open_curly': ew_open_curly,
            'line_complete': len(line_code) > 0 and line_code[-1] in ('}', ';'),

            'atoms_declared': atoms_declared,
            'atoms_used': atoms_used,
            'prototype': prototype,

            'forest': forest,
            'code': line_code
        }
    except ParseChunkError:
        return None
