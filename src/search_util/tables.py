undeclared = {'cout', 'cin', 'endl', 'break', 'min', 'true', 'max', 'false', 'sort', 'abs', 'continue',
              'memset', 'puts', 'int', 'getchar', 'swap', 'strlen', 'getline', 'sqrt', 'INT_MAX', 'ceil',
              'reverse', 'acos', 'strcmp', '__gcd', 'gets', 'make_pair', 'pow', 'char', 'exit', 'tolower',
              'string', 'fabs', 'register', 'fixed', 'freopen', 'toupper', 'isdigit', 'strcpy', 'max_element',
              'putchar', 'INT_MIN', 'floor', 'greater', 'pair', 'setprecision', 'long', 'unique', 'ios', 'stdin',
              'isupper','double', 'min_element', 'next_permutation', 'atoi', 'log2', 'count', 'stdout', 'strstr', 'transform',
              'find', 'cerr', 'isalpha', 'lower_bound', 'fill', 'upper_bound', 'assert', 'islower', 'data', 'NULL', '__builtin_popcount',
              'LLONG_MAX', 'bitset', 'clock', 'deque', 'bool', 'static_cast', 'binary_search', 'srand', 'log', 'ostringstream', '__typeof',
              'multiset', 'memcpy', 'auto', 'iterator', 'multimap', 'CLOCKS_PER_SEC', 'numeric_limits','esto', 'temp',
              'modf', 'accumulate', 'tmp', 'LONG_MAX', 'time', 'int32_t', 'put_char', 'cnt', 'float', 'ULL', 'LONG_LONG_MAX',
              'tuple', 'vector', 'make_tuple', 'get', 'not', 'rand', 'Home', 'exp', 'strcat', 'log10', 'clock_t', 'towupper',
              'memcmp', 'remove', 'flush', 'round', 'time_p', 'asm', 'EOF', 'len', 'signed', 'fmod', '__builtin_clz', 'stringstream',
              'INFINITY', 'atan', 'fill_n', 'strchr', 'list', 'atoll', 'stable_sort', '__float128', 'LLONG_MIN', '__builtin_popcountll',
              'loc', 'locale', 'basic_string', 'levl', 'trunc', 'cbrt', 'clog', '__builtin_ctz', 'xor', 'reverse_iterator', 'LONG_LONG_MIN',
              'toascii', 'map', 'stderr', 'enum', 'RAND_MAX', 'int64_t', 'const', 'maxn', 'LC_ALL', 'setlocale', '__lg', 'strncpy', 'set',
              'unsigned', 'less', 'EXIT_SUCCESS', 'equal', 'abort', 'showpoint', 'iter_swap', 'qsort', 'powl', 'isalnum', 'ios_base', 'free', 'log2l'}


def increment_check(tables, indent, atoms_declared, atoms_used, prototype, typed, debug=False):
    indent = int(indent)
    if len(tables) < indent + 2:
        tables.append({})
    else:
        tables = tables[:indent + 1] + [{}]

    for var_name, var_info in atoms_declared.items():
        if typed:
            var_type, depth = var_info
        else:
            depth = var_info
        # if variable name in this level of symbol table
        # and was not declared as a prototype

        if var_name in tables[indent + depth]:
            var_info = tables[indent + depth][var_name]
            is_prototype = var_info if not typed else var_info[1]
            if not is_prototype:
                if debug:
                    print('var %s declared.' % var_name)
                return False, tables
        is_prototype = var_name == prototype
        tables[indent + depth][var_name] = is_prototype if not typed else (var_type, is_prototype)

    for var_name, depth in atoms_used.items():
        if var_name in undeclared:
            continue
        found = False
        for idx in range(indent + 1 + depth):
            if var_name in tables[idx]:
                found = True
                break
        if not found:
            return False, tables
    return True, tables
