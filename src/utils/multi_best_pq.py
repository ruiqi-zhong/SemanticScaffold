import numpy as np
import heapq

# smaller scores are better
class Multipq:

    def __init__(self, groups, use_base_score=False):
        self.groups = groups
        self.last_popped_pq_id = None
        self.pqs = []
        self.use_base_score = use_base_score
        for group in self.groups:
            sents_l, scores_l, base_score = group
            self.pqs.append(PQ(sents_l, scores_l, base_score, self.use_base_score))
        self.size = sum([pq.size for pq in self.pqs])

    def pop(self):
        # peek each priority queue and decide which to pop
        min_score, min_pq_id = np.float('inf'), None
        for next_pq_idx, pq in enumerate(self.pqs):
            next_score = pq.peek_score()
            if next_score < min_score:
                min_score, min_pq_id = next_score,  next_pq_idx

        # pop the priority queue with the lowest score
        if min_pq_id is None:
            return None
        self.last_popped_pq_id = min_pq_id
        code = self.pqs[min_pq_id].pop()
        return code

class PQ:

    def __init__(self, sents_l, scores_l, base_score, use_base_score=False):
        self.sents_l, self.scores_l = sents_l, scores_l
        self.use_base_score = use_base_score
        self.length = len(self.sents_l)
        if not self.check_empty():
            self.heap = [(np.sum([scores[0] for scores in scores_l]), tuple([0] * self.length))]
            self.accessed = set(self.heap[0][1])
        else:
            self.heap = []
            self.accessed = set()
        self.base_score = base_score
        self.get_self_size()

    def get_self_size(self):
        self.size = 1
        for sents in self.sents_l:
            self.size *= len(sents)


    def peek_score(self):
        if not self.is_empty():
            return self.heap[0][0] + (0 if not self.use_base_score else self.base_score)
        return np.float('inf')

    def check_empty(self):
        for sents in self.sents_l:
            if len(sents) == 0:
                return True
        return False

    def next_candidate_score(self):
        return self.peek_score()

    def pop(self):
        candidate = heapq.heappop(self.heap)
        score, config = candidate
        for mod_idx in range(self.length):
            mod_num_candidates = len(self.sents_l[mod_idx])
            if config[mod_idx] >= mod_num_candidates:
                continue
            new_config = tuple([config[i] if i != mod_idx else config[i] + 1 for i in range(self.length)])
            if new_config in self.accessed:
                continue
            self.accessed.add(new_config)
            if new_config[mod_idx] >= mod_num_candidates:
                continue

            new_score = score + self.scores_l[mod_idx][config[mod_idx] + 1] - self.scores_l[mod_idx][config[mod_idx]]
            heapq.heappush(self.heap, (new_score, new_config))
        code = '\n'.join([self.sents_l[idx][config[idx]] for idx in range(self.length)])
        return code

    def is_empty(self):
        return len(self.heap) == 0