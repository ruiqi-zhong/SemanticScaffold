from copy import deepcopy

class Beam:

    def __init__(self, topk, candidate_init, input2log_prob_l, test_mode=False):
        self.candidates = [[candidate_init()]]
        self.topk = topk
        self.input2log_prob_l = input2log_prob_l
        self.test_mode = test_mode
        self.extend_count = 0
        self.search_success = self.search()

    def step(self, next_input_scores):
        new_candidates = []
        cur_candidates = self.candidates[-1]
        next_input_scores = sorted(next_input_scores, key=lambda x: -x[1])
        extensions_made_per_candidate = [0 for _ in range(len(cur_candidates))]

        for next_input, score in next_input_scores:

            if next_input is None:
                continue
            for candidate_idx, candidate in enumerate(cur_candidates):
                if extensions_made_per_candidate[candidate_idx] >= self.topk:
                    continue
                new_candidate = deepcopy(candidate)
                step_accepted = new_candidate.step(next_input, score)
                self.extend_count += 1
                if step_accepted:
                    new_candidates.append(new_candidate)
                    extensions_made_per_candidate[candidate_idx] += 1
                elif self.test_mode:
                    print('searching fails with input ')
                    print(next_input)
        new_candidates = sorted(new_candidates, key=lambda candidate: -candidate.score)[:self.topk]
        for rank, candidate in enumerate(new_candidates):
            candidate.rank_history.append(rank)
        self.candidates.append(new_candidates)

    def search(self):
        for input2log_prob in self.input2log_prob_l:
            if type(input2log_prob) == dict:
                input2log_prob = input2log_prob.items()
            self.step(input2log_prob)
        search_success = len(self.candidates[-1]) != 0
        return search_success

    # the lower the score of the candidates the better
    def fetch_candidates(self):
        return [(candidate.history, -candidate.score) for candidate in self.candidates[-1] if candidate.complete]

    def get_tables(self):
        return [candidate.table_history for candidate in self.candidates[-1] if candidate.complete]

    def get_beam_histories(self):
        return (
            [candidate.rank_history for candidate in self.candidates[-1] if candidate.complete],
            [candidate.score_history for candidate in self.candidates[-1] if candidate.complete]
        )