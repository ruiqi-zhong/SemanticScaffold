if __name__ == '__main__':
    import sys
    sys.path.append('./')


from parse.op_prec_parser import op_prec_parse, OpprecParseError, extract_id
from parse.chunk_parser_util import filter_space, match_decl_type, match_return, Quote, Args, ArgParseError
from parse.extract_decl import extract_arg_chunk, FuncType, extract_decl_from_c_p


class ParseChunkError(Exception):
    pass

def extract_func_header_arg(tokens):
    open_paren_idx, close_paren_idx = None, None
    for idx, t in enumerate(tokens):
        if t.kind == 'open_paren':
            if open_paren_idx is not None:
                raise ParseChunkError('Function header has two open parenthesis')
            open_paren_idx = idx
        if t.kind == 'close_paren':
            if close_paren_idx is not None:
                raise ParseChunkError('Function header has two open parenthesis')
            close_paren_idx = idx
    if open_paren_idx is None or close_paren_idx is None:
        return None, None, None
    header, args = tokens[:open_paren_idx], tokens[open_paren_idx + 1: close_paren_idx]
    prototype = False
    if close_paren_idx + 1 < len(tokens) and tokens[close_paren_idx + 1].value == ';':
        prototype = True
    return header, args, prototype

class ParenExpr:
    
    def __init__(self, paren_type):
        self.paren_type = paren_type
        self.nodes = []
    
    def complete(self):
        if self.paren_type != 'chunk_expr':
            if pair[self.nodes[0].kind] != self.nodes[-1].kind:
                raise ParseChunkError
        self.parse_op()
    
    def parse_op(self):
        self.is_type = False
        # get the "node" of the expression
        if self.paren_type != 'chunk_expr':
            node = self.nodes[1:-1]
        else:
            node = self.nodes
            
        if len(node) == 0:
            self.node = []
            return
        
        if self.paren_type == 'start-quote':
            self.node = Quote(node)
            return
            
        # check whether the node is a C-type casting
        try:
            r = match_decl_type(filter_space(node))
        except:
            r = None
        if r is not None and r[1] == len(filter_space(node)) - 1:
            self.is_type = True
            self.node = r[0]
            return
        try:
            # use the operator precedence parser
            self.node = op_prec_parse(filter_space(node))
        except OpprecParseError:
            raise ParseChunkError
        
    @classmethod
    def construct_paren(cls, tokens):
        stack = [cls('chunk_expr')]
        for t in tokens:
            # openning a new parenthensis
            if t.kind in pair:
                new_t = cls(t.kind)
                stack[-1].nodes.append(new_t)
                stack.append(new_t)
            stack[-1].nodes.append(t)
            # complete the rightmost parenthensis
            if t.kind == pair[stack[-1].paren_type]:
                stack[-1].complete()
                del stack[-1]
        if len(stack) != 1:
            raise ParseChunkError
        result = stack[0]
        result.complete()
        return result

    def get_identifiers(self):
        result = set()
        if self.node is not None and type(self.node).__name__ not in ('Quote', 'VarType'):
            for node in self.node:
                result |= extract_id(node)
        return result


    def __repr__(self):
        if not hasattr(self, 'node'):
            return '$' + ''.join([t.__repr__() for t in self.nodes]) + '$'
        return self.node.__repr__()


pair = {
    "start-quote":"end-quote",
    "start-char":"end-char",
    "open_curly":"close_curly",
    "open_square":"close_square",
    "open_paren":"close_paren",
    "chunk_expr":"chunk_expr"
}
        
        
def parse_expr(tokens):
    paren_expr_trees = ParenExpr.construct_paren(tokens)
    return paren_expr_trees

def parse_func_header(tokens):
    tokens = filter_space(tokens)
    result = {
        'var_decl': {}
    }
    if len(tokens) == 0:
        raise ParseChunkError
    if tokens[-1].value == '{':
        del tokens[-1]
    header_tokens, arg_tokens, prototype = extract_func_header_arg(tokens)
    if header_tokens is None:
        raise ParseChunkError('Cannot parse out header, arg')
    result['is_prototype'] = prototype
    try:
        args, op_args = extract_arg_chunk(Args(arg_tokens))
        r = match_decl_type(filter_space(header_tokens))
        if r is None:
            raise ParseChunkError('Function header does not declare return type')
        return_type, idx = r
        if len(header_tokens) != idx + 2:
            raise ParseChunkError('Function header has name length longer than 2')
        func_name, func_type = header_tokens[idx + 1].value, FuncType(return_type, args, op_args=op_args)
        result['func_decl'] = (func_name, func_type)
        for arg in func_type.args + func_type.op_args:
            result['var_decl'][arg.name] = arg.type
    except ArgParseError:
        raise ParseChunkError
    return result

def parse_chunk(tokens):
    tokens = filter_space(tokens)
    result = {
        'tokens': tokens,
        'nodes': [],
        'var_decl': {},
        'func_decl': None,
    }

    returning, idx = match_return(tokens)
    result['returning'] = returning
    tokens = tokens[idx:]
    try:
        r = match_decl_type(tokens)
    except:
        r = None

    if r is None:
        node = parse_expr(tokens).node
        if isinstance(node, list):
            result['nodes'] += node
    else:
        decl, idx = r
        exclude_decl_nodes = parse_expr(tokens[idx + 1:])
        if tokens[idx + 1].kind == 'open_paren':
            new_nodes = parse_expr(tokens)
        else:
            new_nodes = exclude_decl_nodes
        result['nodes'] += new_nodes.node
        for node in exclude_decl_nodes.node:
            var_decls = extract_decl_from_c_p(node, decl)
            for var_name in var_decls:
                result['var_decl'][var_name] = var_decls[var_name]
    return result