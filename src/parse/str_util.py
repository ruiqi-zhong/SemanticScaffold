def cmp_sub(t, s, start):
    for idx, c in enumerate(t):
        if start + idx >= len(s):
            return False
        if s[start + idx] != c:
            return False
    return True


def split_keep_space(t, offset):
    prev_space, seg_symbols = None, [0]
    for idx, c in enumerate(t):
        if c == ' ' or prev_space:
            seg_symbols.append(idx)
        prev_space = (c == ' ')
    seg_symbols.append(len(t))
    result = [(t[seg_symbols[i]:seg_symbols[i + 1]], seg_symbols[i] + offset) for i in range(len(seg_symbols) - 1)]
    post_process = []
    for r in result:
        if len(r[0]) >= 2 and r[0][-2:] == '\\n':
            post_process.append((r[0][:-2], r[1]))
            post_process.append(('\\n', r[1] + len(r[0][:-2])))
        else:
            post_process.append(r)
    assert ''.join([x[0] for x in post_process]) == t
    return post_process