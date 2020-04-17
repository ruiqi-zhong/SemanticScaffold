from utils.spoc_utils import get_all_problem_df, get_code_str, get_comment, get_indent
from evals.gold_judge import prepare_judge_folder
import os

data_dir = '../spoc/data/'

def write_for_problem(problem_df, out_dir_name):
    # write code into the data directory
    code_str = get_code_str(problem_df, with_comment=False)
    src_cc = data_dir + 'programs/' + out_dir_name + '.cc'
    with open(src_cc, 'w') as out_file:
        out_file.write(code_str)

    # write comment into the data directory
    comment_str = get_comment(problem_df)
    comment_file = data_dir + 'comments/' + out_dir_name + '.txt'
    with open(comment_file, 'w') as out_file:
        out_file.write(comment_str)

    # write comments where line with nan is revealed into the data directory
    nan_revealed_str = get_comment(problem_df, reveal_nan=True)
    nan_revealed_file = data_dir + 'comments_revealed/' + out_dir_name + '.txt'
    with open(nan_revealed_file, 'w') as out_file:
        out_file.write(nan_revealed_str)

    # write indentation into the data directory
    indent_str = get_indent(problem_df)
    indent_file = data_dir + 'indent/' + out_dir_name + '.txt'
    with open(indent_file, 'w') as out_file:
        out_file.write(indent_str)

def write_all(csv_dir):
    df_by_problems = get_all_problem_df(csv_dir)
    idx = 0
    f_range = set()
    for name, problem_df in df_by_problems:
        idx += 1
        out_dir_name = '-'.join([str(x) for x in name])
        print('writing for %s' % out_dir_name)
        write_for_problem(problem_df, out_dir_name)
        f_range.add(out_dir_name)
    return f_range

if __name__ == '__main__':
    os.mkdir('../spoc/eval_memo/')
    os.mkdir('../spoc/onmt/')
    os.mkdir('../spoc/search_results/')

    os.system('wget https://sumith1896.github.io/spoc/data/spoc.zip')
    os.system('mv spoc.zip ../spoc/')
    os.system('unzip ../spoc/spoc.zip -d ../spoc/')
    os.system('rm ../spoc/spoc.zip')
    os.system('mv ../spoc/train/spoc-train.tsv ../spoc/')
    os.system('mv ../spoc/test/*.tsv ../spoc/')

    print('preparing judge folder')
    prepare_judge_folder()
    os.mkdir(data_dir)

    for name in ['indent', 'programs', 'comments_revealed', 'comments']:
        os.mkdir(os.path.join(data_dir, name))

    print('expanding and writing data ...')
    for csv_dir in ['../spoc/spoc-testp', '../spoc/spoc-testw', '../spoc/spoc-train']:
        f_range = write_all(csv_dir + '.tsv')
        with open(csv_dir + '.frange', 'w') as out_file:
            for f in f_range:
                out_file.write(f + '\n')
