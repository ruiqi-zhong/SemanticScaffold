from utils.multi_best_pq import Multipq
from utils.spoc_utils import kf_range
from evals.gold_judge import Judge
from onmt_dir.prepare_for_onmt import round_trip
from parse.program import Program_generator
import os
from argparse import ArgumentParser
from search_util.structured_search import search_structured_groups
from parse.misc import braces_acceptable
import time
from typing import Tuple, List, Callable, Dict, Any
import pickle as pkl

translate_dir = '../spoc/pre_trans/'
search_options = {'base', 'syntax', 'semantics'}

verbose = True

# a map from the program id
# to translations, scores,
# where translation is a list (length = number of lines in a program) of list (length = number of candidates) of strings
# (in other words, L x C in the notation of the paper)
# and scores is of the same dimension and each float is the negative log of the probability of a translation
# the translations are precomputed and we used OpenNMT to obtain the translations
def translation_map(f_name: str) -> Tuple[List[List[str]], List[List[float]]]:
    return pkl.load(open('../spoc/pre_trans/' + f_name, 'rb'))


def search(translation_map: Callable[[str], Tuple[List[List[str]], List[List[float]]]],  # see documentation above, generate code pieces and scores
           program_dict: Dict[str, Any],  # a dictionary that contains information needed for a program, including pseudo code, indent, etc
           result_dir: str,  # the directory to dump the results
           budget: int,  # budget B
           search_opt: str,  # the constraint we use for searching,
           structure_beam_size: int = 50,  # beam width W for the search
           structure_topk: int = 20,  # the top K scaffolds we use for the search
           regular: bool = False  # whether to use hierarchical or regular beam search
           ):
    # load program information
    f_name, indent = program_dict['f_name'], program_dict['indent']
    program_length = len(indent)

    # evaluation requires running on a lot of testcases and is time consuming
    # we memoize all the evaluation results and save it on the disk
    memo_dir = '../spoc/eval_memo/' + f_name
    memo = {}
    if os.path.exists(memo_dir):
        memo = pkl.load(open(memo_dir, 'rb'))

    # the id of the problem (for testcases) is the substring after the 1st -
    pid = f_name.split('-')[1]

    # the path we are dumping the search results and statistics
    search_result_dir = result_dir + f_name + '.pkl'
    search_stats_result_dir = result_dir + f_name + '.stats'

    # if the result path already exists, return
    # else dump a lock to indicate that currently this process is working on it
    if os.path.exists(search_result_dir):
        return
    pkl.dump('working', open(search_result_dir, 'wb'))
    if verbose:
        print('searching for file %s.' % f_name)

    # check whether the gold program can pass the constraint
    gold_sents_l, gold_scores_l = [[round_trip(c)] for c in program_dict['program_by_line']], [[0] for _ in range(program_length)]
    gold_groups = search_structured_groups(gold_sents_l, gold_scores_l, search_opt, indent)['groups']
    if gold_groups is not None:
        gold_passed = True
    else:
        gold_passed = False

    # load the translation
    translations = translation_map(f_name)
    sents_l, scores_l = translations

    # search the scaffold
    if not regular:
        search_info = search_structured_groups(sents_l, scores_l, search_opt, indent,
                                               beam_size=structure_beam_size, top_k=structure_topk)
    else:
        search_info = search_structured_groups(sents_l, scores_l, search_opt, indent,
                                               beam_size=budget * 2, top_k=budget, use_code=True)
    # if regular beam search
    # groups is a list of full candidate programs
    # if hierarchical beam search
    # group is a list, each element represent a scaffold,
    # where each scaffold is Tuple[List[List[str]], List[List[float]], float], the first two element
    # the same return type as translations, the third element is the score of a scaffold
    # every translation within the same scaffold has the same configuration for each line.
    groups = search_info['groups']

    if groups is None:
        pkl.dump([], open(search_result_dir, 'wb'))
        return []

    # next_code returns an iterator that generates the next candidate
    if regular:
        def next_code():
            idx = 0
            while True:
                if idx < len(groups):
                    yield groups[idx]
                    idx += 1
                else:
                    yield None
    else:
        def next_code():
            mpq = Multipq(groups)
            while True:
                yield mpq.pop()

    cur_idx = 0
    return_val = []
    code_iter = next_code()
    while cur_idx < budget:
        code = next(code_iter)
        if code is None:
            break
        # check whether a piece of code has been evaluated in the history
        # if yes, then directly load the result and hence avoid computation
        if memo.get(code) is None:
            # if the braces do not match (e.g. more '{' than '}' in the program), then reject directly
            if braces_acceptable(code):
                j = Judge(problem_id=pid, judge_type='all', eager=True, judge_id=f_name + str(cur_idx))
                result = j.judge_program_str(code)
                return_val.append({'rank': cur_idx, 'code': code, 'status': result['Status'], 'gold_pass': gold_passed})
                memo[code] = result['Status']
            else:
                return_val.append({'rank': cur_idx, 'code': code, 'status': 'braces rejected', 'gold_pass': gold_passed})
        else:
            return_val.append({'rank': cur_idx, 'code': code, 'status': memo[code], 'gold_pass': gold_passed})
        if code in memo and memo[code] == 'Passed':
            break

        cur_idx += 1

    #  dump the search results and the memo
    pkl.dump(return_val, open(search_result_dir, 'wb'))
    pkl.dump(search_info, open(search_stats_result_dir, 'wb'))
    pkl.dump(memo, open(memo_dir, 'wb'))
    return return_val


def get_args():
    parser = ArgumentParser()
    parser.add_argument('--regular', default=False, action='store_true',
                        help='default is hierarchical beam search, use this flag for regular beam search.')
    parser.add_argument('--result_dir', type=str,
                        help='the directory where you want to save all the evaluation results. '
                             'a directory with informative name will be automatically created in ../spoc/search_results/ if empty.')
    parser.add_argument('--target', type=str,
                        help='the dataset split for evaluation, worker/problem.')
    parser.add_argument('--seed', type=int, default=0,
                        help='we randomly decide the order of evaluation.')
    parser.add_argument('--budget', type=int, default=100,
                        help='budget B in the paper.')
    parser.add_argument('--search_opt', type=str,
                        help='the constraint we are using for the search. '
                             'base for no constraint, '
                             'syntax for Syntactic constraint, '
                             'semantics for SymTable constraint. ')
    parser.add_argument('--structure_beam_size', type=int, default=50,
                        help='the beam size we use to search the scaffold. '
                             'denoted by W in the paper.')
    parser.add_argument('--structure_topk', type=int, default=20,
                        help='the top k scaffold we keep for the subsequent search. '
                             'denoted by K in the paper. ')

    args = parser.parse_args()

    if args.result_dir is None:
        model_result_dir = '../spoc/search_results/' + args.search_opt + '-'
        model_result_dir += 'hierarchical' if not args.regular else 'regular'
        if not args.regular:
            model_result_dir += 'structure_beam_size%d' % args.structure_beam_size
            model_result_dir += 'structure_topk%d' % args.structure_topk
        model_result_dir += 'budget%d' % args.budget
        model_result_dir += '/'
        if not os.path.exists(model_result_dir):
            os.mkdir(model_result_dir)
        args.result_dir = model_result_dir
    return args

if __name__ == '__main__':
    args = get_args()
    print(args)

    # file range contains all the program id we want to evaluate
    file_range = kf_range(args.target)

    # sometimes we are running several processes and we use randomness & time difference
    # to avoid potential interference between processes
    seed = args.seed + int(1000000 * time.time()) % 1000000

    # an iterator that yields program_dict, which is a dictionary that contains information about a program
    pg = Program_generator().program_generator(all_info=True, shuffle=True, file_range=file_range, seed=seed)

    assert args.search_opt in search_options

    for program_dict in pg:
        search(translation_map, program_dict, result_dir=args.result_dir, budget=args.budget,
               search_opt=args.search_opt,
               structure_beam_size=args.structure_beam_size,
               structure_topk=args.structure_topk, regular=args.regular)
