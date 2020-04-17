import sys
sys.path.append('./')
from parse.program import Program_generator
from parse.lexer import tokenize
from parse.program import data_dir
from tqdm import tqdm

citation_symbols = {'start-quote': '\"', 'start-char':'\'',
                    'end-quote': '\"', 'end-char': '\''}
WHITE_SPACE = '!WHITE_SPACE!'
NEXT_LINE = '!Next_LINE!'
debug = False
train_dir = '../spoc/onmt/'


# mapping from a token to a token for onmt
def plain2onmt_tok(val, kind):
    if '\n' in val:
        return NEXT_LINE
    if kind in citation_symbols:
        return kind
    if kind == 'in-quote' or kind == 'in-char':
        if ' ' in val:
            return WHITE_SPACE
        else:
            return val
    if kind != 'whitespace':
        return val
    return None


# mapping from translation format to a piece of code
def to_code(s):
    tokens = s.split(' ')
    saved_tks = []
    in_quote = False
    for t in tokens:
        if t in citation_symbols:
            saved_tks.append(citation_symbols[t])
            in_quote = t[:5] == 'start'
        elif t == NEXT_LINE:
            saved_tks.append('\n')
        elif t == WHITE_SPACE:
            saved_tks.append(' ')
        else:
            saved_tks.append(t)
        if not in_quote:
            saved_tks.append(' ')
    result = ''.join(saved_tks).strip()
    return result


def to_onmt(s):
    values = [plain2onmt_tok(t.value, t.kind) for t in tokenize(s, new_line=False) if t.kind != 'whitespace']
    result = ' '.join([v for v in values if v is not None])
    return result


def round_trip(c):
    s = to_onmt(c)
    c = to_code(s)
    return c


def train2onmt():
    with open('../spoc/spoc-train.frange', 'r') as in_file:
        s = in_file.read().strip()
    comment_key = sys.argv[1]
    assert comment_key in ('comments', 'nan_revealed')
    prefix = 'programs'
    program_dir = data_dir + prefix
    src_file = open(train_dir + prefix + comment_key + '_train.src', 'w')
    tgt_file = open(train_dir + prefix + comment_key + '_train.tgt', 'w')
    orig_code = open(train_dir + prefix + comment_key + '_train.orig', 'w')
    f_range = s.split('\n')
    pg = Program_generator(program_dir=program_dir + '/').program_generator(all_info=True, file_range=f_range)
    for idx, program_dict in tqdm(enumerate(pg), total=len(f_range)):
        codes, comments = program_dict['program_str'].strip().split('\n'), program_dict[comment_key]
        if len(codes) != len(comments):
            raise Exception('line of code does not match comments!')
        for code, comment in zip(codes, comments):
            train_src_toks, train_tgt_toks = to_onmt(comment), to_onmt(code)
            round_trip = to_code(train_tgt_toks)
            src_file.write(train_src_toks + '\n')
            tgt_file.write(train_tgt_toks + '\n')
            orig_code.write(round_trip + '\n')
    src_file.close()
    tgt_file.close()
    orig_code.close()


if __name__ == '__main__':
    train2onmt()
