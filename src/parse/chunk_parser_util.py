def filter_space(tokens):
    return [t for t in tokens if type(t).__name__ != 'Token' or t.kind != 'whitespace']


def match_tokens(source, target, start):
    for idx in range(len(target)):
        if start + idx >= len(source) or target[idx] != source[start + idx].value:
            return None
    return start + len(target) - 1

class ArgParseError(Exception):
    pass

primitive_types = [
    "void",
    
    "short int",
    "short",
    "unsigned short int",
    "signed short int",
    
    "int",
    "unsigned int",
    "signed int",
    
    "long int",
    "long",
    "unsigned long int",
    "unsigned long",
    "signed long int",
    "signed long",

    "long long int",
    "long long",
    "unsigned long long int",
    "unsigned long long",
    "signed long long int",
    "signed long long",
    "long long unsigned",
    
    "char",
    "unsigned char",
    "signed char",
    
    "float",
    "double",
    "long double",
    "wchar_t",
    "bool",
    "string",
    "int long long",
    "ulong long",
    
    "unsigned",
    "size_t",
    "FILE",
    
    "istream",
    "ostream",
    "ofstream",
    "istringstream",
    "stringstream",
    "ifstream",
    "int64_t"
    
]

data_structures = {
    'vector': 1,
    'pair': 2,
    'map': 2,
    'set': 1,
    'queue': 1,
    'stack': 1,
    'list': 1,
    "priority_queue": 1
}
primitive_types = sorted([t.split(' ') for t in primitive_types], key=lambda x: -len(x))

class VarType:
    
    def __init__(self, static, const, data_type, is_iter, num_pointers=0):
        self.static, self.const, self.data_type = static, const, data_type
        self.is_iter = is_iter
        self.num_pointers = num_pointers
        self.args = []
    
    def __repr__(self):
        result = ''
        result += 'static ' if self.static else ''
        result += 'const ' if self.const else ''
        result += self.data_type
        if len(self.args) == 0:
            return result
        result += '<'
        for idx, arg in enumerate(self.args):
            result += arg.__repr__()
            if idx + 1 != len(self.args):
                result += ','
        result += '>'
        if self.is_iter:
            result += '::iterator '
        return result
                      
def match_decl_type(tokens, start=0):
    cur = start
    if start >= len(tokens):
        return None
    if tokens[cur].kind == 'in-quote':
        return None
    static, const = False, False
    token = tokens[cur]
    # checking whether static and/or const
    if token.value == 'static':
        static = True
        cur += 1
        token = tokens[cur]

    if token.value == 'const':
        const = True
        cur += 1
        token = tokens[cur]

    if token.value == 'inline':
        cur += 1
        token = tokens[cur]

    is_iter = False
    for p in primitive_types:
        end = match_tokens(tokens, p, cur)
        if end is not None:
            if end + 1 < len(tokens) and tokens[end + 1].value == 'const':
                const = True
                end += 1
            return VarType(static, const, ' '.join(p), is_iter), end
        
    num_args = data_structures.get(token.value)
    if num_args is None:
        return None
    if tokens[cur + 1].value != '<':
        raise ArgParseError
    args = []
    cur += 2
    for _ in range(num_args):
        arg, end = match_decl_type(tokens, start=cur)
        cur = end + 1
        args.append(arg)
        if _ + 1 != num_args:
            if tokens[cur].value != ',':
                raise TypeError
            cur += 1
    # special handling of consecutive ">"
    if tokens[cur].value == '>>':
        tokens[cur].value = '>'
        tokens.insert(cur, tokens[cur])
    if tokens[cur].value != '>':
        raise ArgParseError
    
    # extend if ::iterator is a suffix
    if tokens[cur + 1].value == '::':
        cur += 2
        if tokens[cur].value != 'iterator':
            raise ArgParseError
        is_iter = True
    v = VarType(static, const, token.value, is_iter)
    v.args = args
    return v, cur


class Quote:
    
    def __init__(self, nodes):
        self.nodes = nodes
        for node in nodes:
            assert type(node).__name__ == 'Token' and node.kind == 'in-quote'
    
    def __repr__(self):
        return "".join([n.value for n in self.nodes])



class Args:
    
    def __init__(self, tokens):
        cur = 0
        self.args = []
        tokens = filter_space(tokens)
        include_name = None
        while cur < len(tokens):
            decl_cur = match_decl_type(tokens, start=cur)
            if decl_cur is None:
                raise ArgParseError
            decl, cur = decl_cur
            if (cur + 1 < len(tokens)) and tokens[cur + 1].value == '&':
                cur += 1
                address = True
            else:
                address = False

            pointer = 0
            while (cur + 1 < len(tokens)) and tokens[cur + 1].value == '*':
                cur += 1
                pointer += 1
            if include_name is None:
                include_name = (cur + 1 < len(tokens)) and tokens[cur + 1].kind == 'identifier'
            if include_name:
                cur += 1
                arg_name = tokens[cur]
            else:
                arg_name = 'no-arg-name'
            
            arr = 0
            while cur + 1 < len(tokens) and tokens[cur + 1].value == '[':
                next_close_bracket = cur + 2
                arr += 1
                while tokens[next_close_bracket].value != ']':
                    next_close_bracket += 1
                cur = next_close_bracket
            
            default_arg_expr = None
            if (cur + 1 < len(tokens)) and tokens[cur + 1].value == '=':
                default_arg_start = cur + 2
                end = default_arg_start
                while (end < len(tokens) and (tokens[end].value != ',' or tokens[end].kind != 'operator')):
                    end += 1
                from parse.chunk_parser import parse_chunk
                default_arg_expr = parse_chunk(tokens[default_arg_start:end])
                cur = end - 1
            
            self.args.append((decl, address, arg_name, arr, default_arg_expr, pointer))
            if cur != len(tokens) - 1:
                cur += 1
                if tokens[cur].value != ',':
                    raise ArgParseError
            cur += 1
    
    def __repr__(self):
        result = ','.join([str(x) for x in self.args])
        return result

def match_return(tokens):
    if tokens[0].value == 'return' and tokens[0].kind != 'in-quote':
        return True, 1
    else:
        return False, 0