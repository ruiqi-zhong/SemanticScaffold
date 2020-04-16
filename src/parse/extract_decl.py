from collections import namedtuple
FuncArg = namedtuple('FuncArg', ['name', 'type'])

numerical_order = ['bool', 'short', 'size_t', 'char', 'int', 'long', 'long long', 'float', 'double']
numerical_order = {s: i for i, s in enumerate(numerical_order)}
numerical_types = ['bool', 'short', 'size_t', 'char', 'int', 'long', 'long long', 'float', 'double']
integer_num = {'bool', 'short', 'size_t', 'char', 'int', 'long', 'long long'}

class TypeError(Exception):
    pass

def is_numerical(simple_type):
    return simple_type.data_type in numerical_types and simple_type.depth == 0

def is_int(simple_type):
    return simple_type.data_type in integer_num and simple_type.depth == 0

def is_string(simple_type):
    return (simple_type.data_type == 'string' and simple_type.depth == 0 and not simple_type.is_iter) \
                or (simple_type.data_type == 'char' and simple_type.depth <= 1)

def is_type(simple_type, s):
    return simple_type.data_type == s and simple_type.depth == 0

# ignore these cases
def is_generic(t):
    if isinstance(t, SimpleType) and t.data_type == 'generic':
        return True
    if isinstance(t, FuncType) and t.return_type.data_type == 'generic':
        return True
    return False
    
def get_min_cast(args):
    for t in numerical_types:
        for arg in args:
            if arg.data_type == t:
                result = SimpleType(t)
    return result

def valid_casting(arg, enc):
    # if the expected type is void and
    # the encountered type is None (which means void)
    # then it is a valid casting

    if arg.data_type == 'void' and enc is None:
        return True
    if len(arg.args) != len(enc.args):
        return False
    for aarg, aenc in zip(arg.args, enc.args):
        if not valid_casting(aarg, aenc):
            return False
    if arg.depth == enc.depth and arg.data_type == enc.data_type and arg.is_iter == enc.is_iter:
        return True
    if is_string(arg) and is_string(enc):
        return True
    if is_numerical(arg) != is_numerical(enc):
        raise TypeError('Casting Error')
    if is_numerical(arg):
        if is_int(arg) and not is_int(enc):
            return False
        else:
            return True
    if arg.depth != enc.depth or arg.data_type != enc.data_type or arg.is_iter != enc.is_iter:
        return False
    return True

def simplified_primitives(s):
    if s == 'unsigned' or s == 'int64_t':
        return 'int'
    tokens = s.split(' ')
    if tokens[-1] == 'double':
        return 'double'
    if tokens[0] in ('signed', 'unsigned'):
        tokens = tokens[1:]
    if len(tokens) > 1 and tokens[-1] == 'int':
        tokens = tokens[:-1]
    result = ' '.join(tokens)
    return result
    
class SimpleType:
    
    def __init__(self, data_type, const=False, static=False, is_iter=False, args=[], depth=0):
        
        self.data_type = simplified_primitives(data_type)
        self.is_iter = is_iter
        self.const, self.static = const, static
        self.args = args
        self.depth = depth
    
    @classmethod
    def from_decl_bracket_args(cls, decl, bracket_args):
        args = [cls.from_decl_bracket_args(arg, []) for arg in decl.args]
        return SimpleType(decl.data_type, decl.const, decl.static, decl.is_iter, args, len(bracket_args))
    
    def __repr__(self):
        result = ''
        if self.static:
            result += 'static '
        if self.const:
            result += 'const '
        result += self.data_type.__repr__() + ' '
        if len(self.args) != 0:
            result += '< '
            for arg in self.args:
                result += arg.__repr__()
            result += ' > '
        if self.is_iter:
            result += '::iterator '
        result += '%d ' % self.depth
        return result
    
    def get_type(self):
        return self

class CompositeTypeConstructorError(TypeError):
    pass
    
class CompositeType:
    
    def __init__(self, types):
        self.types = types
    
    def add_type(self, another_type):
        self.types.append(another_type)

    def get_type(self):
        return self.types[0]
    
    @classmethod
    def from_type(cls, some_type):
        if isinstance(some_type, cls):
            types = some_type.types
            return cls(types)
        elif isinstance(some_type, SimpleType):
            return cls([some_type])
        else:
            raise CompositeTypeConstructorError('type %s not understood by the constructor.' % (type(some_type).__name__))
    
    def __repr__(self):
        result = '( ' + ', '.join([t.__repr__() for t in self.types]) + ')'
        return result

class FuncType:
    
    def __init__(self, return_decl, args, type_check=None, op_args=[]):
        self.args = args
        for arg in self.args:
            if not isinstance(arg, FuncArg):
                raise TypeError
        
        if len(self.args) == 1 and self.args[0].type.data_type == 'void':
            self.args = []
        
        self.op_args = op_args
        self.return_type = SimpleType.from_decl_bracket_args(return_decl, [])
        if type_check is not None:
            self.type_check = type_check
        else:
            self.initialize_type_check()
    
    def initialize_type_check(self):
        def f(encountered):
            if len(self.args) > len(encountered):
                raise TypeError
            for arg, enc in zip(self.args, encountered[:len(self.args)]):
                if not valid_casting(arg.type, enc):
                    raise TypeError
            if len(encountered) > len(self.args):
                for arg, enc in zip(self.op_args[len(self.args):], encountered[len(self.args):]):
                    if not valid_casting(arg.type, enc):
                        raise TypeError
            return self.return_type
        self.type_check = f
    
    def set_args(self, args, op_args=[]):
        if len(self.args) == 1 and self.args[0].type.data_type == 'void':
            self.args = []
        self.op_args = op_args
        self.args = args
        self.initialize_type_check()
        
    
    def __repr__(self):
        result = ''
        result += self.return_type.__repr__()
        result += '('
        result += ','.join([a.__repr__() for a in self.args])
        result += ')'
        return result

# parse a sub_part of the declaration (seperated by comma already)
def parse_comma_sub(right):
    # throw away the assignment
    if type(right).__name__ == 'Binop' and type(right.op).__name__ == 'Token' and right.op.value == '=':
        target = right.left
    else:
        target = right
    bracket_args = []
    while type(target).__name__ == 'Unop' and target.op.value == '*':
        target = target.e
        bracket_args.append(None)
        
    # parsing all the trailing brackets
    while type(target).__name__ == 'Binop' and target.op == 'square':
        square_paren = target.right
        target = target.left
        #if square_paren.node is None:
        bracket_args = [None] + bracket_args

    # special handling of initializing an object (e.g. a vector)
    if type(target).__name__ == 'Binop' and target.op == 'call':
        target = target.left

    if type(target).__name__ == 'ParenExpr':
        if len(target.node) == 0 or type(target.node[0]).__name__ != 'Token':
            return None, None
        arg_name = target.node[0].value
    elif type(target).__name__ == 'Token' and target.kind == 'identifier':
        arg_name = target.value
    else:
        arg_name, bracket_args = None, None
    return arg_name, bracket_args

def extract_func_header(c_p):
    return_type = c_p['decl']
    function_name = c_p['node'].nodes[0].value
    return return_type, function_name

def extract_arg_chunk(node):
    args, op_args = [], []
    for arg in node.args:
        param_name = arg[2].value if type(arg[2]) != str else arg[2]

        simple_arg = FuncArg(param_name, SimpleType.from_decl_bracket_args(arg[0], [None] * (arg[3] + arg[5])))
        if arg[4] is None:
            args.append(simple_arg)
        else:
            op_args.append(simple_arg)
    return args, op_args

# extract information from (function_header_chunk, arg_chunk)
def extract_func_info_from_header_arg(function_header_chunk, arg_chunk=None):
    args, op_args = extract_arg_chunk(arg_chunk.c_p if arg_chunk is not None else None)
    return_type, function_name = extract_func_header(function_header_chunk.c_p)
    return function_name, FuncType(return_type, args, op_args=op_args)

def extract_decl_from_c_p(node, decl):
    result_dict = {}
    if decl is None:
        return result_dict
    while type(node).__name__ == 'Binop' and type(node.op).__name__ == 'Token' and node.op.value == ',':
        # parsing every segments (that might contain declaration) seperated by ','
        left, right = node.left, node.right
        node = left
        arg_name, bracket_args = parse_comma_sub(right)
        if arg_name is not None:
            result_dict[arg_name] = SimpleType.from_decl_bracket_args(decl, bracket_args)
    # parse the leftmost declaration
    arg_name, bracket_args = parse_comma_sub(node)
    if arg_name is not None:
        result_dict[arg_name] = SimpleType.from_decl_bracket_args(decl, bracket_args)
    return result_dict