casting_types = {'bool', 'short', 'size_t', 'char', 'int', 'long', 'long long', 'float', 'double', 'stringstream'}

class OpprecParseError(Exception):
    pass

def extract_id(n):
    result = set()
    if type(n).__name__ == 'Token':
        if n.kind == 'identifier':
            result.add(n.value)
    else:
        result |= n.get_identifiers()
    return result

class Binop:

    def __init__(self, left, op, right):
        self.left, self.op, self.right = left, op, right
        self.op_str = self.op if isinstance(self.op, str) else self.op.value

    def __repr__(self):
        return '(' + self.left.__repr__() + ' ' + self.op.__repr__() + ' ' + self.right.__repr__() + ')'

    def get_identifiers(self):
        all_ids = set()
        if self.op_str != 'cast':
            all_ids |= extract_id(self.left)
        if self.op_str not in ('.', '::', '->'):
            all_ids |= extract_id(self.right)
        return all_ids


class Unop:

    def __init__(self, op, e):
        self.op, self.e = op, e

    def __repr__(self):
        return '(' + self.e.__repr__() + ' , ' + self.op.__repr__() + ')'

    def get_identifiers(self):
        all_ids = extract_id(self.e)
        return all_ids

class Ternary:

    def __init__(self, op, a, b, c):
        self.op, self.a, self.b, self.c = op, a, b, c

    def __repr__(self):
        return '(' + self.a.__repr__() + '?' + self.b.__repr__() + ':' + self.c.__repr__() + ')'

    def get_identifiers(self):
        all_ids = extract_id(self.a) | extract_id(self.b) | extract_id(self.c)
        return all_ids


def is_op(node):
    return type(node).__name__ == 'Token' and node.kind == 'operator'


# each operator is "wrapped" by this class
# it contains information about: the raw string,
# when this operation can be applied
# and how it will change the tokens

# cond_change is a function that takes in nodes, an idx
# modifies the nodes if the condition is met
# and returns an idx of the current (newly generated) node
class Qual:

    def __init__(self, op_str, cond_change):
        self.op_str, self.cond_change = op_str, cond_change


def init_std_binary(s):
    def cond(nodes, idx):
        if idx <= 0 or idx >= len(nodes) - 1:
            return None
        node = nodes[idx]
        if is_op(node) and node.value == s and not (is_op(nodes[idx - 1]) or is_op(nodes[idx + 1])):
            new_node = Binop(*nodes[idx - 1:idx + 2])
            del nodes[idx - 1]
            del nodes[idx - 1]
            del nodes[idx - 1]
            nodes.insert(idx - 1, new_node)
            return idx - 1
        else:
            return None

    q = Qual(s, cond)
    return q


def init_std_unary(s, op_on_left, heuristic=False):
    def cond(nodes, idx):
        if op_on_left and idx >= len(nodes) - 1:
            return None
        if not op_on_left and idx <= 0:
            return None
        assert not heuristic or op_on_left

        node = nodes[idx]
        if is_op(node) and node.value == s:
            e = nodes[idx + 1] if op_on_left else nodes[idx - 1]
            if is_op(e):
                return None
            if heuristic and idx >= 1 and not is_op(nodes[idx - 1]):
                return None
            new_node = Unop(node, e)
            if op_on_left:
                del nodes[idx]
                del nodes[idx]
                nodes.insert(idx, new_node)
                return idx
            else:
                del nodes[idx - 1]
                del nodes[idx - 1]
                nodes.insert(idx - 1, new_node)
                return idx - 1
        return None

    q = Qual(s, cond)
    return q


QUAL_BY_PREC = [[] for _ in range(17)]

RAW_BIN_OPS = [
    ['::'],
    ['.', '->'],
    [],
    ['.*', '->*'],
    ['*', '/', '%'],
    ['+', '-'],
    ['<<', '>>'],
    ['<=>'],
    ['<', '<=', '>', '>='],
    ['==', '!='],
    ['&'],
    ['^'],
    ['|'],
    ['&&'],
    ['||'],
    ['=', '+=', '-=', '*=', '/=', '%=', '<<=', '>>=', '&=', '^=', '|='],
    [',']
]

for prec in range(17):
    QUAL_BY_PREC[prec].extend([init_std_binary(op) for op in RAW_BIN_OPS[prec]])

RAW_2_LEFT_OPS = ['++', '--', '!', '~', 'sizeof', 'new', 'delete']
QUAL_BY_PREC[2].extend([init_std_unary(op, op_on_left=True) for op in RAW_2_LEFT_OPS])
HEUR_2_LEFT = ['+', '-', '*', '&']
QUAL_BY_PREC[2].extend([init_std_unary(op, op_on_left=True, heuristic=True) for op in HEUR_2_LEFT])
RAW_1_RIGHT_OPS = ['++', '--']
QUAL_BY_PREC[1].extend([init_std_unary(op, op_on_left=False) for op in RAW_1_RIGHT_OPS])


def paren_call_cond(nodes, idx, paren_type, name):
    if idx >= 1 and type(nodes[idx]).__name__ == 'ParenExpr' and nodes[idx].paren_type == paren_type and not is_op(
            nodes[idx - 1]) and not nodes[idx].is_type and not (
            type(nodes[idx - 1]).__name__ == 'ParenExpr' and nodes[idx - 1].is_type):
        new_node = Binop(nodes[idx - 1], name, nodes[idx])
        del nodes[idx - 1]
        del nodes[idx - 1]
        nodes.insert(idx - 1, new_node)
        return idx - 1
    return None


QUAL_FUNC = Qual('call', lambda x, y: paren_call_cond(x, y, 'open_paren', 'call'))
QUAL_SQUARE = Qual('square', lambda x, y: paren_call_cond(x, y, 'open_square', 'square'))
QUAL_BY_PREC[1].append(QUAL_FUNC)
QUAL_BY_PREC[1].append(QUAL_SQUARE)


def cast_cond(nodes, idx):
    if idx >= 1 and type(nodes[idx - 1]).__name__ == 'ParenExpr' and nodes[idx - 1].is_type and not is_op(nodes[idx]):
        new_node = Binop(nodes[idx - 1], 'cast', nodes[idx])
        del nodes[idx - 1]
        del nodes[idx - 1]
        nodes.insert(idx - 1, new_node)
        return idx - 1
    return None
QUAL_CAST = Qual('cast', cast_cond)
QUAL_BY_PREC[2].append(QUAL_CAST)


def ternary(nodes, idx):
    if idx > len(nodes) - 4 or idx == 0:
        return None
    node = nodes[idx]
    if (is_op(node) and is_op(nodes[idx + 2])
            and node.value == '?'
            and nodes[idx + 2].value == ':'
            and not is_op(nodes[idx - 1]) and not is_op(nodes[idx + 1]) and not is_op(nodes[idx + 3])):
        new_node = Ternary('ternary', nodes[idx - 1], nodes[idx + 1], nodes[idx + 3])
        for _ in range(5):
            del nodes[idx - 1]
        nodes.insert(idx - 1, new_node)
        return idx - 1
    else:
        return None


QUAL_TERN = Qual('ternary', ternary)
QUAL_BY_PREC[15].append(QUAL_TERN)

prec2assoc = [1] * 17
prec2assoc[2] = -1
prec2assoc[15] = -1


# return an executable tree over the nodes
def op_prec_parse(tokens):
    nodes = tokens[:]
    for prec, assoc in enumerate(prec2assoc):
        QUALs = QUAL_BY_PREC[prec]
        cur = 0 if assoc == 1 else len(nodes) - 1
        while cur >= 0:
            if cur >= len(nodes):
                break
            for qual in QUALs:
                new_node_idx = qual.cond_change(nodes, cur)
                if new_node_idx is not None:
                    cur = new_node_idx
                    break
            cur += assoc
    return nodes