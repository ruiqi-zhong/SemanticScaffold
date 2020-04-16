import pickle as pkl
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
from typing import Tuple, List

translate_dir = '../spoc/pre_trans/'
search_options = {'base', 'syntax', 'semantics', 'typed'}

verbose = True

def get_translation_map(model_dir):
    model_name = model_dir.split('/')[-1]
    # a map from the program id
    # to translations, scores,
    # where translation is a list (length = number of lines in a program) of list (length = number of candidates) of strings
    # (in other words, L x C in the notation of the paper)
    # and scores is of the same dimension and each float is the negative log of the probability of a translation
    # the translations are precomputed and we used OpenNMT to obtain the translations
    def load_translation(f_name: str) -> Tuple[List[List[str]], List[List[float]]]:
        translation_memo_path = translate_dir + model_name + '/' + f_name + '.pkl'
        translation = pkl.load(open(translation_memo_path, 'rb'))
        return translation
    return load_translation


def search(translation_map, program_dict, result_dir, budget, use_indent,
           search_opt, structure_beam_size=50, structure_topk=20, regular=False):
    f_name, indent = program_dict['f_name'], program_dict['indent']
    program_length = len(indent)
    if not use_indent:
        indent = None
    memo_dir = '../spoc/eval_memo/' + f_name
    memo = {}
    if os.path.exists(memo_dir):
        memo = pkl.load(open(memo_dir, 'rb'))

    pid = f_name.split('-')[1]

    model_result_dir = result_dir

    search_result_dir = model_result_dir + f_name + '.pkl'
    search_stats_result_dir = model_result_dir + f_name + '.stats'

    if os.path.exists(search_result_dir):
        return

    pkl.dump('working', open(search_result_dir, 'wb'))
    if verbose:
        print('searching for file %s.' % f_name)

    gold_sents_l, gold_scores_l = [[round_trip(c)] for c in program_dict['program_by_line']], [[0] for _ in range(program_length)]
    gold_groups = search_structured_groups(gold_sents_l, gold_scores_l, search_opt, indent)['groups']
    if gold_groups is not None:
        gold_passed = True
    else:
        gold_passed = False

    translations = translation_map(f_name)
    sents_l, scores_l = translations
    if not regular:
        search_info = search_structured_groups(sents_l, scores_l, search_opt, indent,
                                               beam_size=structure_beam_size, top_k=structure_topk)
    else:
        search_info = search_structured_groups(sents_l, scores_l, search_opt, indent,
                                               beam_size=budget * 2, top_k=budget, use_code=True)
    groups = search_info['groups']

    if groups is None:
        pkl.dump([], open(search_result_dir, 'wb'))
        return []

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
        if memo.get(code) is None:
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

    pkl.dump(return_val, open(search_result_dir, 'wb'))
    pkl.dump(search_info, open(search_stats_result_dir, 'wb'))
    return return_val

def get_args():
    parser = ArgumentParser()
    parser.add_argument('--regular', default=False, action='store_true')
    parser.add_argument('--model_dir', type=str)
    parser.add_argument('--result_dir', type=str)
    parser.add_argument('--target', type=str)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--budget', type=int, default=100)
    parser.add_argument('--search_opt', type=str)
    parser.add_argument('--use_indent', default=False, action='store_true')
    parser.add_argument('--structure_beam_size', type=int, default=50)
    parser.add_argument('--structure_topk', type=int, default=20)

    args = parser.parse_args()

    model_name = args.model_dir.split('/')[-1]

    if args.result_dir is None:
        model_result_dir = '../spoc/search_results/' + model_name + '-' + args.search_opt
        model_result_dir += 'hierarchical' if not args.regular else 'regular'
        if args.use_indent:
            model_result_dir += '-use_indent-'
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
    file_range = kf_range(args.target)

    seed = args.seed + int(1000000 * time.time()) % 1000000
    pg = Program_generator().program_generator(all_info=True, shuffle=True, file_range=file_range, seed=seed)
    translation_map = get_translation_map('../spoc/oldmodels/programscomments_onmt_step_200000.pt')

    assert args.search_opt in search_options

    for program_dict in pg:
        search(translation_map, program_dict, result_dir=args.result_dir, budget=args.budget,
               use_indent=args.use_indent, search_opt=args.search_opt,
               structure_beam_size=args.structure_beam_size,
               structure_topk=args.structure_topk, regular=args.regular)
