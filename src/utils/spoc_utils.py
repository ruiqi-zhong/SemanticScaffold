import pandas as pd
import numpy as np
from onmt_dir.prepare_for_onmt import plain2onmt_tok, round_trip
from parse.lexer import tokenize
from parse.program import program_dir, comment_dir

SPLIT_SIGN = '\n######\n'
def diff_two_generations(program1_by_line, program2_by_line, comments=None, keys=('line1', 'line2')):
    result_str = '==========\n'
    if type(program1_by_line) == str:
        program1_by_line = program1_by_line.split('\n')
    if type(program2_by_line) == str:
        program2_by_line = program2_by_line.split('\n')
    if comments is None:
        comments = ['' for _ in range(len(program1_by_line))]
    line1_key, line2_key = keys
    for line_code1, line_code2, comment in zip(program1_by_line, program2_by_line, comments):
        if line_code1 != line_code2:
            result_str += SPLIT_SIGN
            result_str += line1_key + ':  ' + line_code1 + '\n'
            result_str += line2_key + ': ' + line_code2 + '\n'
            result_str += 'comment: ' + comment
            result_str += SPLIT_SIGN
    result_str += '==========\n'
    return result_str

def obtain_gold_program(f_name):
    src_file_path = program_dir + f_name + '.cc'
    with open(src_file_path, 'r') as in_file:
        program_str = in_file.read()
    program_by_line = [round_trip(c) for c in program_str.split('\n')]
    return program_by_line

def obtain_comments(f_name):
    comment_file_path = comment_dir + f_name + '.txt'
    with open(comment_file_path, 'r') as in_file:
        comments = in_file.read().split('\n')
    return comments

def get_rank_from_log(log_list, idx_based=False):
    if len(log_list) == 0:
        return float('inf')
    for idx, log in enumerate(log_list):
        if log['status'] == 'Passed':
            if idx_based:
                return idx
            else:
                return log['rank']
    return float('inf')


def annotate_type(psu, table):
    values = [plain2onmt_tok(t.value, t.kind) for t in tokenize(psu, new_line=False)
              if t.kind != 'whitespace']
    def get_type_from_table(v):
        if v not in table:
            return 'None'
        else:
            return str(table[v][0]).replace(' ', '_').replace('\'', '').replace('\"', '')
    result = ' '.join([(v + '￨' + get_type_from_table(v)) for v in values])
    return result

def softmax(arr):
    if len(arr) == 0:
        return []
    arr = np.array(arr)
    arr = arr - arr[0]
    e = np.e ** (-arr)
    return e / np.sum(e)

def normalize_scores_l(scores_l):
    return [normalize_scores(scores) for scores in scores_l]

def normalize_scores(scores):
    return [-np.log(x) for x in softmax(scores)]

def get_f_from_dir(f_dir):
    with open(f_dir, 'r') as in_file:
        s = in_file.read().strip().split('\n')
    return s

def kf_range(key):
    file_range = None
    if key == 'worker':
        file_range = get_f_from_dir('../spoc/spoc-testw.frange')
    elif key == 'problem':
        file_range = get_f_from_dir('../spoc/spoc-testp.frange')
    elif key == 'train':
        file_range = get_f_from_dir('../spoc/spoc-train.frange')
    elif key == 'infeasible':
        file_range = get_f_from_dir('../spoc/oracly_infeasible.frange')
    elif key == 'feasible':
        file_range = get_f_from_dir('../spoc/oracly_feasible.frange')
    elif key == 'all':
        file_range = None
    return file_range


def freeze_dict(d):
    return tuple(sorted(d.items()))

def freeze_config(info_dict, keys=None):
    result = []
    if keys is None:
        keys = set(info_dict.keys())
    for key in sorted(keys):
        val = info_dict.get(key)
        if type(val) == dict:
            result.append(((key, type(val)),  freeze_dict(val)))
        elif type(val) in (list, set):
            result.append(((key, type(val)), tuple(sorted(val))))
        else:
            result.append(((key, type(val)), val))
    return tuple(result)

def unfreeze_config(config):
    info_dict = {}
    for (key, class_type), val in config:
        if class_type in (list, set):
            info_dict[key] = set(val)
        elif class_type == dict:
            info_dict[key] = {a: b for a, b in val}
        else:
            info_dict[key] = val
    return info_dict

# take in a dataframe that contains a problem solution
# get the code string with or without comment
def get_code_str(problem, with_comment=True):
    s = ''
    indent, code, text = [problem[key].values for key in ['indent', 'code', 'text']]
    for i, c, t in zip(indent, code, text):
        if with_comment:
            t = '' if type(t) != str else ' # ' + str(t)
        else:
            t = ''
        s += '    ' * i + c + t + '\n'
    return s

def get_comment(problem, reveal_nan=False):
    comments = [str(v) for v in problem['text'].values]
    if reveal_nan:
        for idx, comment in enumerate(comments):
            if comment == 'nan':
                comments[idx] = problem['code'].values[idx]
    return '\n'.join(comments)

def get_indent(problem):
    return '\n'.join([str(v) for v in problem['indent'].values])

# verify that this constitutes a real problem solution
def verify_problem_df(problem_df):
    l = problem_df['line'].values
    consistent_keys = ['subid', 'workerid', 'probid']
    
    # consistent keys are identifiers for a problem solution
    for key in consistent_keys:
        if len(set(problem_df[key])) != 1:
            return False
    
    # check if the line number is consistent
    for idx, e in enumerate(l):
        if e != idx:
            return False
    return True

# obtain all the problem df grouped by annotated submissions
def get_all_problem_df(csv_dir='../spoc/spoc-train.tsv'):
    raw_df = pd.read_csv(csv_dir, sep='\t')
    df_by_problems = raw_df.groupby(['subid', 'probid', 'workerid'])
    return df_by_problems

# verify whether every problem has consistent line numbers
def verify_all():
    df_by_problems = get_all_problem_df()
    for name, problem_df in df_by_problems:
        if not verify_problem_df(problem_df):
            return False
    return True