import pickle as pkl
from argparse import ArgumentParser
import os
from collections import defaultdict
from utils.spoc_utils import kf_range

def get_f_from_dir(f_dir):
    with open(f_dir, 'r') as in_file:
        s = in_file.read().strip().split('\n')
    return s

def get_args():
    parser = ArgumentParser()
    parser.add_argument('--result_dir')
    parser.add_argument('--opt')
    args = parser.parse_args()
    return args

def subset_result(result_dir, f_names):
    result, num_rejects, f_name2result, f_name2gold = [], defaultdict(int), {}, {}
    num_searches, num_compile_errors = 0, 0
    num_no_candidates = 0
    for f_name in f_names:
        search_result_dir = result_dir + f_name + '.pkl'
        if not os.path.exists(search_result_dir):
            result.append('not finished')
            # print(f_name, 'not finished.')
        else:
            d = pkl.load(open(search_result_dir, 'rb'))
            if type(d) == str:
                # print(f_name, d)
                result.append('not finished')
                continue
            elif type(d) == list:
                if len(d) > 0 and 'gold_pass' in d[0]:
                    f_name2gold[f_name] = d[0]['gold_pass']
                passed = False
                if len(d) == 0:
                    num_no_candidates += 1
                for _ in d:
                    num_searches += 1
                    if _['status'] == 'Passed':
                        result.append(_['rank'])
                        f_name2result[f_name] = _['rank']
                        passed = True
                        break
                    elif _['status'] in ('Compilation Error', 'braces rejected'):
                        num_compile_errors += 1
                if not passed:
                    result.append(-1)
                    f_name2result[f_name] = -1
                elif 'bracket_rej' in d[-1]:
                    num_rejects[d[-1]['bracket_rej']] += 1
            else:
                result.append(d['rank'])
    # print(len(result))
    return {
        'rank': result,
        'num_rejects': num_rejects,
        'non_compile_r': float(num_compile_errors / num_searches),
        'f_name2gold': f_name2gold,
        'f_name2result': f_name2result,
        '0 candidates': num_no_candidates
    }

def agg_stats(result):
    s = 'altogether %d files.\n' % len(result)
    s += '%d ready\n' % len([r for r in result if r != 'not finished'])
    s += '%d passes first time.\n' % len([r for r in result if r == 0])
    s += '%d passes in 10 time.\n' % len([r for r in result if isinstance(r, int) and 0 <= r < 10])
    s += '%d passes in 25 time.\n' % len([r for r in result if isinstance(r, int) and 0 <= r < 25])
    s += '%d passes in 100 times.\n' % len([r for r in result if isinstance(r, int) and 0 <= r < 100])
    return s

def calculate_result(result_dir, opt):
    f_range = kf_range(opt)
    d = subset_result(result_dir, f_range)
    pkl.dump(d, open('../spoc/' + result_dir.split('/')[-2] + opt + '.pkl', 'wb'))
    rank, num_rejs = d['rank'], d['num_rejects']
    print(opt)
    print(agg_stats(rank))
    print('%d has no candidates.' % d['0 candidates'])
    print('%.3f not compilable.' % d['non_compile_r'])
    print([(key, num_rejs[key]) for key in sorted(num_rejs.keys())])


if __name__ == '__main__':
    args = get_args()
    calculate_result(args.result_dir, args.opt)