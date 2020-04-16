import sys
sys.path.append('.')
sys.path.append('../opennmt/')

from translate import _get_parser
from onmt.utils.parse import ArgumentParser
from onmt.translate.translator import build_translator
from onmt_dir.prepare_for_onmt import to_onmt, to_code

dummy_out = 'onmt_dir/dummy.txt'
src_dummy = 'RAREFILENAME.txt'

def obtain_scalar(ll):
    result = [[-_.data.item() for _ in _ll] for _ll in ll]
    return result

def candidates2code(candidates):
    result = [[to_code(candidate) for candidate in candidates_] for candidates_ in candidates]
    return result

class MyTranslator:

    def __init__(self, model_dir, beam_size=100, top_k=100, preprocess=True, gpu=-1):
        self.beam_size, self.top_k = beam_size, top_k
        self.model_dir = model_dir
        self.opt = self.create_args()
        self.opt.gpu = gpu
        self.preprocess = preprocess
        self.translator = build_translator(self.opt, report_score=False)

    def create_args(self):
        parser = _get_parser()
        opt = parser.parse_args(['--beam_size', str(self.beam_size),
                          '--output', dummy_out,
                          '--src', src_dummy,
                          '--model', self.model_dir,
                          '--n_best', str(self.top_k)
                          ])
        opt.src = None # this is a dummy variable
        ArgumentParser.validate_translate_opts(opt)
        return opt

    # returns first the candidate code then the score
    def translate(self, comments):
        # batchify
        batch_input = True
        if type(comments) == str:
            batch_input = False
            comments = [comments]

        if self.preprocess:
            onmt_srcs = [to_onmt(comment)
                         for comment in comments]
        else:
            onmt_srcs = comments[:]
        src_shard = MyTranslator.srcs2shard(onmt_srcs)
        result = self.translator.translate(
            src=src_shard,
            tgt=None,
            src_dir=self.opt.src_dir,
            batch_size=self.opt.batch_size,
            batch_type=self.opt.batch_type,
            attn_debug=self.opt.attn_debug
        )
        ll, candidates = result
        ll, candidates = obtain_scalar(ll), candidates2code(candidates)
        if not batch_input:
            ll, candidates = ll[0], candidates[0]
        return candidates, ll

    @staticmethod
    def srcs2shard(onmt_srcs):
        result = []
        for sent in onmt_srcs:
            result.append((sent + '\n').encode())
        return result