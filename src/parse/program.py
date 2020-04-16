from parse.lexer import tokenize
from colorama import Fore
from itertools import chain
from collections import defaultdict
import random
import os

data_dir = '../spoc/data/'
program_dir = data_dir + 'programs/'
comment_dir = data_dir + 'comments/'
comment_revealed_dir = data_dir + 'comments_revealed/'
indent_dir = data_dir + 'indent/'

colored = True
if colored:
    COLORs = [Fore.RED, Fore.GREEN, Fore.BLUE, Fore.YELLOW, Fore.MAGENTA]
else:
    COLORs = ['']


class Program:
    
    def __init__(self, program):
        self.raw_lines = program.split('\n')
        self.tokens_by_line = [tokenize(raw_line) for raw_line in self.raw_lines]
        self.line_ids = list(chain(*[[line_num] * len(tokens) for line_num, tokens in enumerate(self.tokens_by_line)]))
        self.all_tokens = list(chain(*self.tokens_by_line))
        self.lc2token_idx = dict([((line_id + 1, token.offset + 1), token_idx) 
                             for token_idx, (line_id, token) in enumerate(zip(self.line_ids, self.all_tokens))])
        for idx, token in enumerate(self.all_tokens):
            token.set_pid(idx)
            token.set_program(self)
            token.set_lid(self.line_ids[idx])
        self.start_idx = self.lc2token_idx[(1, 1)]
        self.covered = [False for _ in range(len(self.all_tokens))]
    
    def retrieve_token(self, s):
        idx = self.lc2token_idx[s]
        return [self.all_tokens[idx]]
    
    def retrieve_span(self, s, e):
        return self.all_tokens[self.lc2token_idx[s]:self.lc2token_idx[e] + 1]
    
    def get_span_str(self, start_pid, end_pid):
        return ''.join([t.value for t in self.all_tokens[start_pid:end_pid + 1]])
    
    def print_coverage(self):
        for idx in range(self.start_idx, len(self.all_tokens)):
            if self.covered[idx] or self.all_tokens[idx].kind == 'whitespace':
                print(Fore.GREEN + self.all_tokens[idx].value, end='')
            else:
                print(Fore.RED + self.all_tokens[idx].value, end='')
        print(Fore.BLACK)
        
    def print_w_paren(self, parens):
        color_idx = 0
        paren_idx = 0
        result = ''
        id2open_count, id2close_count = defaultdict(list), defaultdict(list)
        for start_id, end_id in parens:
            id2open_count[start_id].append(COLORs[color_idx] + '$(%d)' % paren_idx)
            id2close_count[end_id + 1].append(COLORs[color_idx] + ('(%d)$' % paren_idx))
            paren_idx += 1
            color_idx = paren_idx % len(COLORs)
        for idx in range(self.start_idx, len(self.all_tokens)):
            for marker in id2close_count[idx][::-1]:
                result += marker
                print(marker, end='')
            for marker in id2open_count[idx]:
                result += marker
                print(marker, end='')
            if colored:
                result += Fore.BLACK
                print(Fore.BLACK, end='')
            print(self.all_tokens[idx].value, end='')
            result += self.all_tokens[idx].value
        if colored:
            result += Fore.BLACK
        return result
    
    @staticmethod
    def get_leaves(program):
        return program.all_tokens[program.start_idx:]
    
class Program_generator:
    
    def __init__(self, program_dir=program_dir):
        self.program_dir = program_dir
        self.f_names = sorted([f[:-3] for f in os.listdir(self.program_dir)])
        self.f_name2idx = {f_name:idx for idx, f_name in enumerate(self.f_names)}
        self.num_programs = len(self.f_names)

    def indexed_program(self, idx, all_info):
        result = {'idx': idx}

        f_name = self.f_names[idx]
        result['f_name'] = f_name

        with open(self.program_dir + f_name + '.cc') as in_file:
            program_str = in_file.read()
        result['program_str'] = program_str

        program_by_line = program_str.strip().split('\n')
        result['program_by_line'] = program_by_line

        p = Program(program_str)
        if not all_info:
            return p
        result['program'] = p

        with open(comment_dir + f_name + '.txt') as in_file:
            comments = in_file.read().split('\n')
        result['comments'] = comments

        with open(comment_revealed_dir + f_name + '.txt') as in_file:
            nan_revealed = in_file.read().split('\n')
        result['nan_revealed'] = nan_revealed

        with open(indent_dir + f_name + '.txt') as in_file:
            indent = in_file.read().split('\n')
        result['indent'] = indent

        result['leaves'] = p.all_tokens[p.start_idx:]

        return result
    
    def program_generator(self, all_info=False, file_range=None, shuffle=False, seed=None):
        if file_range is None:
            file_idx_range = range(self.num_programs)
        elif type(file_range) == str:
            file_idx_range = [self.f_name2idx[file_range]]
        else:
            file_idx_range = [self.f_name2idx[f] for f in file_range]
        file_idx_range = sorted(list(file_idx_range))
        if shuffle or seed is not None:
            if seed is not None:
                random.seed(seed)
            random.shuffle(file_idx_range)
        def gen():
            for idx in file_idx_range:
                yield self.indexed_program(idx, all_info)
        return gen()