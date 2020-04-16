import sys
sys.path.append('./')

from onmt_dir.prepare_for_onmt import round_trip
from search_util.structured_search import search_structured_groups


def pseudo_compile_check(code, indent, search_opt):
    code_by_line = code.strip().split('\n')
    program_length = len(code_by_line)
    gold_sents_l, gold_scores_l = [[round_trip(c)] for c in code_by_line], [[0] for _ in range(program_length)]
    gold_groups = search_structured_groups(gold_sents_l, gold_scores_l, search_opt, indent)['groups']
    return gold_groups is not None
