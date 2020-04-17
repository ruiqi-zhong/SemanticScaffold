from collections import defaultdict
from parse.type_line import type_line
from utils.spoc_utils import freeze_config, unfreeze_config, normalize_scores
from search_util.tables import increment_check
import numpy as np
from search_util.beam import Beam
from typing import List, Union


debug = False

line_types = {'dowhile', 'if', 'else', 'else if', 'while', 'for', 'close_curly_only',
              'open_curly_only', 'line', 'function', 'prototype', 'marker', 'do', 'empty'}
scope_keys = ['line_type', 'line_complete', 'start_w_close_curly', 'end_w_open_curly']


def str2syntax_config(s):
    if len(s.split(' ')) != 4:
        return None
    toks = s.split(' ')
    info_dict = {k: v == 'True' if k != 'line_type' else v.replace('-', ' ') for k, v in zip(scope_keys, toks)}
    config = freeze_config(info_dict)
    return config


def marginalize_config(sents_config, probs):
    config_probs = defaultdict(float)
    for sent_config, prob in zip(sents_config, probs):
        if sent_config is None:
            continue
        config_probs[sent_config] += prob
    config_logprobs = [(key, np.log(config_probs[key])) for key in config_probs]
    return config_logprobs


def rej_by_syntax_config(sents, scores, config):
    result_sents, result_scores = [], []
    info_dict = unfreeze_config(config)
    info_dict['indent'] = None
    config = freeze_config(info_dict)
    for sent, score in zip(sents, scores):
        try:
            if extract_syntax_config(sent) == config:
                result_sents.append(sent)
                result_scores.append(score)
        except:
            continue
    return result_sents, result_scores


def rej_by_table_config(sents, scores, config, typed):
    result_sents, result_scores = [], []
    info_dict = unfreeze_config(config)
    info_dict['indent'] = None
    config = freeze_config(info_dict)
    for sent, score in zip(sents, scores):
        try:
            extracted_config = extract_semantics_config(sent,
                                                    extra_info={'indent': None}, typed=typed)
            if extracted_config == config:
                result_sents.append(sent)
                result_scores.append(score)
        except Exception as e:
            continue
    return result_sents, result_scores


def validate_syntax_config(config):
    info_dict = unfreeze_config(config)
    line_type = info_dict['line_type']
    if line_type not in line_types:
        return False
    if line_type == 'close_curly_only' and not info_dict['start_w_close_curly']:
        return False
    if line_type == 'open_curly_only' and not info_dict['end_w_open_curly']:
        return False
    if info_dict['end_w_open_curly'] and info_dict['line_complete']:
        return False
    return True


def filter_scopes(sent_scopes_l, scores_l):
    new_sent_scopes_l, new_scores_l  = [], []
    for sent_scopes, scores in zip(sent_scopes_l, scores_l):
        new_sent_scopes, new_scores = [], []
        for sent_scope, score in zip(sent_scopes, scores):
            config = str2syntax_config(sent_scope)
            if config is None:
                continue
            if validate_syntax_config(config):
                new_sent_scopes.append(config)
                new_scores.append(score)
        new_sent_scopes_l.append(new_sent_scopes)
        new_scores_l.append(new_scores)
    return new_sent_scopes_l, new_scores_l

def rej_by_type_line(sents_l, scores_l):
    new_sents_l, new_scores_l, rejected_mass_l = [], [], []
    for sents, scores in zip(sents_l, scores_l):
        new_sents, new_scores, rejected_mass = [], [], 0
        for sent, score in zip(sents, scores):
            try:
                if type_line(sent) is not None:
                    new_sents.append(sent)
                    new_scores.append(score)
                else:
                    rejected_mass += np.e ** (-score)
            except:
                rejected_mass += np.e ** (-score)
        new_sents_l.append(new_sents)
        new_scores_l.append(new_scores)
        rejected_mass_l.append(rejected_mass)
    return new_sents_l, new_scores_l, rejected_mass_l

scope_info_needed = {'line_type', 'line_complete', 'start_w_close_curly', 'end_w_open_curly', 'indent'}
table_info_needed = {'line_type', 'line_complete', 'start_w_close_curly', 'end_w_open_curly', 'indent',
                     'atoms_declared', 'atoms_used', 'prototype'}

def extract_syntax_config(sent, extra_info=None):
    try:
        info_dict = type_line(sent)
    except:
        return None
    if info_dict is None:
        return None
    if extra_info is not None:
        for key in extra_info:
            info_dict[key] = extra_info[key]
    config = freeze_config(info_dict, scope_info_needed)
    return config


def extract_semantics_config(sent, extra_info, typed):
    try:
        info_dict = type_line(sent)
    except:
        return None
    if info_dict is None:
        return None
    atoms_declared = info_dict['atoms_declared']
    info_dict['atoms_declared'] = {k[1]: (str(atoms_declared[k][0]), atoms_declared[k][1]) if typed else atoms_declared[k][1]
                                   for k in info_dict['atoms_declared'].keys()}

    for key in extra_info:
        info_dict[key] = extra_info[key]

    config = freeze_config(info_dict, table_info_needed)
    info_dict = {key: info_dict[key] for key in table_info_needed}
    round_trip = unfreeze_config(config)
    assert info_dict == round_trip
    return config


class ScopeInfo:

    def __init__(self, scope_type, open_curly, potentially_complete):
        self.scope_type, self.open_curly, self.potentially_complete = scope_type, open_curly, potentially_complete

    def __repr__(self):
        return 'ScopeInfo: (' + self.scope_type + '; ' + 'open curly: ' + str(self.open_curly) \
               + '; potentially complete: ' + str(self.potentially_complete) + ')'

class SearchError(Exception):
    pass


class StructureCandidate:

    def __init__(self, consider_scope=False, consider_table=False, table_typed=False, use_code=False):

        # criteria consider_scope, consider_table, table_typed are ordered
        # cannot consider lower precedence without higher ones
        self.consider_scope, self.consider_table, self.table_typed = consider_scope, consider_table, table_typed
        if not consider_table and table_typed:
            raise SearchError
        if not consider_scope and consider_table:
            raise SearchError
        self.score, self.rank_history, self.history, self.score_history = 0, [], [], []
        self.complete = False
        self.use_code = use_code

        # general properties of candidates
        self.cur_indent_level, self.indentation_history = 0, []

        # build the variable table
        if self.consider_table:
            self.tables = [{}]

        if self.table_typed:
            self.table_history = []

        # variable keeping track of the scopes
        if self.consider_scope:
            self.scope_types = []
            self.closed_scope_type = None

    def stack_top_brace_indent(self):
        stack_top_brace_indent = len(self.scope_types) - 1
        while stack_top_brace_indent >= 0:
            if self.scope_types[stack_top_brace_indent].open_curly:
                break
            stack_top_brace_indent -= 1
        return stack_top_brace_indent

    def delete_unused_info(self, next_input):
        if self.consider_scope and not self.consider_table:
            next_input = {key: next_input.get(key) for key in scope_info_needed}
            return next_input

        if self.consider_table:
            next_input = {key: next_input.get(key) for key in table_info_needed}
            return next_input

    """
    Procedure summarization for conisder_scope:

    a)
    if the next input is starting with close curly, then we need to close the previous scope and keep all the information
        we reject this input if there is no scope to be closed
        we cannot use the braces to close a sequence that is not potentially complete
        else if/else needs to come after a closing of if/else if
        this scope is complete, making previous statements potentially complete
    if not if/else if we will close all the previous scope
    if there is open curly only and the scope on top is without open curly, we add the open curly to the previous open curly

    ## do something in between e.g. logging the current indentation level, etc.

    b)
    we open a new scope if the input says so
    if no new scope is opened and the input is incomplete
    we mark all the scope up to the brace on stack top to be potentially complete.

    Cannot parse goto statements.
    """

    def step(self, next_input, score):
        if self.use_code:
            code, next_input = next_input['code'], next_input['config']
        if type(next_input) == tuple:
            next_input = unfreeze_config(next_input)
        config = freeze_config(next_input)

        next_input = self.delete_unused_info(next_input)
        self.score += score
        self.score_history.append(score)

        indent_this_input = None
        # ignore empty lines or line markers
        if next_input['line_type'] in ('empty', 'marker'):
            self.indentation_history.append(indent_this_input)
            if not self.use_code:
                self.history.append(config)
            else:
                self.history.append(code)
            if self.table_typed:
                self.save_table()
            return True

        if self.consider_scope:
            open_new_scope = not next_input['line_complete']
            if next_input['start_w_close_curly']:
                # close all the scopes up to the last open curly
                stack_top_brace_indent = self.stack_top_brace_indent()
                indent_this_input = stack_top_brace_indent
                # reject if there is no brace on top of the stack
                if stack_top_brace_indent < 0:
                    if debug:
                        print('nothing on top of the stack')
                    return False
                for _ in range(stack_top_brace_indent + 1, len(self.scope_types)):
                    if not self.scope_types[_].potentially_complete:
                        if debug:
                            print('closing non-potentially complete scopes above the stack top')
                        return False

                if len(self.scope_types) == 0:
                    if debug:
                        print('scope list length 0')
                    return False
                # none acceptable closing of scopes
                if next_input['line_type'] in ('else', 'else if') and self.scope_types[
                    stack_top_brace_indent].scope_type not in ('if', 'else if'):
                    if debug:
                        print('else does not match')
                    return False

                if next_input['line_type'] == 'while' and self.scope_types[stack_top_brace_indent].scope_type != 'do':
                    return False

                # closing the previous scope if start with close curly
                self.cur_indent_level = stack_top_brace_indent
                self.closed_scope_type = self.scope_types[stack_top_brace_indent].scope_type
                self.scope_types = self.scope_types[:stack_top_brace_indent]

                # since the statement is complete, anything up to the current
                # open brace on top of the stack is potentially complete
                stack_top_brace_indent = self.stack_top_brace_indent()
                for idx in range(stack_top_brace_indent + 1, len(self.scope_types)):
                    self.scope_types[idx].potentially_complete = True
            # if other line type writes after the scope closing
            # then forget about the closed scope type information
            elif next_input['line_type'] not in ('else', 'else if'):
                self.closed_scope_type = None

            # now close all potentially complete scopes unless there is a match for if-else
            scope_clear_start = len(self.scope_types) - 1

            while scope_clear_start >= 0 and self.scope_types[scope_clear_start].potentially_complete:
                scope_clear_start -= 1
            scope_clear_start += 1

            if next_input['line_type'] in ('else', 'else if'):
                if self.closed_scope_type in ('if', 'else if'):
                    max_indent_match = self.cur_indent_level
                else:
                    max_indent_match = self.cur_indent_level - 1
                    if max_indent_match < 0:
                        if debug:
                            print('Empty stack, nothing to match else scope')
                        return False
                    while self.scope_types[max_indent_match].scope_type not in ('if', 'else if') \
                            and max_indent_match >= scope_clear_start:
                        if not self.scope_types[max_indent_match].potentially_complete:
                            print('else/else if closes a non potentially complete other type of scope')
                            return False
                        max_indent_match -= 1
                    if max_indent_match < scope_clear_start:
                        if debug:
                            print('no matching previous if or else if')
                        return False
                self.cur_indent_level = max_indent_match
                self.scope_types = self.scope_types[:self.cur_indent_level]

            # if seeing another line type (e.g. for) that is contradictory to if, else if
            # then close all previous potentially complete scopes
            elif next_input['line_type'] not in ('close_curly_only', 'open_curly_only'):
                self.scope_types = self.scope_types[:scope_clear_start]
                self.cur_indent_level = scope_clear_start

            if next_input['line_type'] == 'open_curly_only' and len(self.scope_types) > 0 and not self.scope_types[-1].open_curly:
                indent_this_input = self.cur_indent_level - 1
                self.scope_types[-1].open_curly = True
                open_new_scope = False

            if indent_this_input is None:
                indent_this_input = self.cur_indent_level

            gold_indent = next_input.get('indent')
            # reject if the indentation is different from the gold one
            if gold_indent is not None and gold_indent != indent_this_input:
                if debug:
                    print('indentation is wrong.')
                return False
            self.indentation_history.append(indent_this_input)

        if self.consider_table:
            atoms_declared, atoms_used, prototype = [next_input[key] for key in ['atoms_declared', 'atoms_used', 'prototype']]
            search_success, self.tables = increment_check(tables=self.tables, indent=indent_this_input,
                                                          atoms_declared=atoms_declared, atoms_used=atoms_used,
                                                          prototype=prototype, typed=self.table_typed,
                                                          debug=debug
                                                          )
            if not search_success:
                if debug:
                    print('Variable constraint fails.')
                return False

        assert self.cur_indent_level == len(self.scope_types)

        if self.table_typed:
            self.save_table()

        if self.consider_scope:
            # start a new scope
            if open_new_scope:
                self.cur_indent_level += 1
                self.scope_types.append(ScopeInfo(next_input['line_type'], next_input['end_w_open_curly'], False))
                self.new_scope_opened = True
            else:
                self.new_scope_opened = False

            # mark all previous scopes without open curly as potentially complete
            # if no new scope is declared
            if not self.new_scope_opened and next_input['line_complete']:
                potential_complete_start = self.stack_top_brace_indent()
                for _ in range(potential_complete_start + 1, len(self.scope_types)):
                    self.scope_types[_].potentially_complete = True
        if not self.use_code:
            self.history.append(config)
        else:
            self.history.append(code)
        self.complete = (self.cur_indent_level == 0)
        return True

    def save_table(self):
        var_table_this_line = {}
        for table in self.tables:
            for var_name in table:
                var_table_this_line[var_name] = table[var_name]
        self.table_history.append(var_table_this_line)


def search_structured_groups(sents_l: List[List[str]],  # L x C list of list
                             scores_l: List[List[float]],  # L x C list of list
                             search_option: str,  # base/syntax/semantics
                             indent: Union[None, List[str]] = None,
                             #  if not None it is a length L list of indentation level for each line
                             config_logprobs_l=None,
                             top_k=20,
                             beam_size=50,
                             use_code=False,
                             structure_only=False
                             ):
    if not structure_only:
        program_length = len(sents_l)
        # directly reject the fragments we cannot parse
        # as mentioned in section 5. in our paper
        sents_l, scores_l, rejected_mass = rej_by_type_line(sents_l, scores_l)

        # if the base case, no constraint is active and hence no search is needed
        # directly return the function input
        if search_option == 'base':
            return {
                'groups': [(sents_l, scores_l, 0)],
                'rejected_prob': rejected_mass
            }

    candidate_init, sent_configs_l = None, []

    # extract_syntax_config and extract_semantics_config
    # extract the configuration of each code fragment
    if search_option == 'base':
        pass
    if search_option == 'syntax':
        candidate_init = lambda: StructureCandidate(consider_scope=True, use_code=use_code)
        if not structure_only:
            for line_id, sents in enumerate(sents_l):
                if indent is None:
                    extra_info = None
                else:
                    extra_info = {'indent': int(indent[line_id])}
                sent_configs_l.append([(extract_syntax_config(sent, extra_info)) for sent in sents])

    elif search_option == 'semantics':
        candidate_init = lambda: StructureCandidate(consider_scope=True, consider_table=True, use_code=use_code)
        if not structure_only:
            for line_id, sents in enumerate(sents_l):
                if structure_only:
                    break
                if indent is None:
                    extra_info = None
                else:
                    extra_info = {'indent': int(indent[line_id])}
                sent_configs_l.append([(extract_semantics_config(sent, extra_info, typed=False)) for sent in sents])

    else:
        raise Exception('Option %s not understood' % search_option)
    # sent_configs_l is an L x C list of list of configs
    # candidate_init is a function that returns a new hypothesis class instantiation
    # this class can check whether a certain extension is possible
    # e.g. whether the next code piece satisfy the syntax/semantics constraint

    if config_logprobs_l is None and not use_code:
        config_logprobs_l = [marginalize_config(sent_configs, np.e ** (-np.array(scores)))
                             for sent_configs, scores in zip(sent_configs_l, scores_l)]
    if use_code:
        config_logprobs_l = [[({'code': sent, 'config': sent_config}, -score)
                              for sent, sent_config, score in zip(sents, sent_configs, scores)
                              if sent_config is not None]
                             for sents, sent_configs, scores in zip(sents_l, sent_configs_l, scores_l)]
    # config_logprobs_l is now a list (length L) of dictionaries mapping
    # from config score for a line
    # to the log probability of the config

    # now we beam search over the configuration space
    b = Beam(beam_size, candidate_init, config_logprobs_l)
    if not structure_only:
        extend_amortized = float(b.extend_count) / program_length
    candidate_table_history = None
    if len(b.candidates[-1]) == 0:
        if not structure_only:
            return {
                'groups': None,
                'rejected_prob': rejected_mass,
                'candidate_table_histories': candidate_table_history,
                'extend_amortized': extend_amortized
            }
        else:
            return {
                'groups': None,
                'candidates': None,
                'candidate_table_histories': candidate_table_history,
                'extend_amortized': extend_amortized
            }

    candidates = b.fetch_candidates()[:top_k]
    candidate_rank_history, candidate_score_history = b.get_beam_histories()

    if structure_only:
        return {
            'candidates': candidates,
            'candidate_rank_histories': candidate_rank_history,
            'candidate_score_histories': candidate_score_history,
            'candidate_table_histories': candidate_table_history,
            'extend_amortized': extend_amortized
        }

    if use_code:
        return {'groups': ['\n'.join(candidate[0]) for candidate in candidates]}

    groups = [([[] for _ in range(program_length)], [[] for _ in range(program_length)],
               candidates[candidate_idx][1])
              for candidate_idx in range(len(candidates))]

    # group each line
    # for each line
    for line_idx in range(program_length):
        config2group_idx = defaultdict(list)
        # for each candidate config of that line, group them together
        # i.e. dictionary[config] = [<candidate idx that have this config>]
        for candidate_idx, (candidates_l, score) in enumerate(candidates):
            if len(candidates_l) != program_length:
                raise Exception
            config2group_idx[candidates_l[line_idx]].append(candidate_idx)
        # for each config in sents_l
        # group the sentences to the corresponding config
        for sent, config, score in zip(sents_l[line_idx], sent_configs_l[line_idx], scores_l[line_idx]):
            group_idxes = config2group_idx[config]
            for group_idx in group_idxes:
                groups[group_idx][0][line_idx].append(sent)
                groups[group_idx][1][line_idx].append(score)
    return {
        'groups': groups,
        'rejected_prob': rejected_mass,
        'candidate_rank_histories': candidate_rank_history,
        'candidate_scores': [group[2] for group in groups],
        'candidate_score_histories': candidate_score_history,
        'candidates': candidates,
        'candidate_table_histories': candidate_table_history,
        'extend_amortized': extend_amortized
    }
