#  variable names that do not need to be declared in the program
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


# check whether atoms_declared (new variables declared)
# and the atoms_used (variable used) of the next code piece
# satisfy the SymTable constraint based on the current symbol table
def increment_check(tables, indent, atoms_declared, atoms_used, prototype, typed, debug=False):
    # tables is a list of dictionary, each of which is a symbol table for each scope level
    # a symbol table is a mapping from variable name to a boolean, True if it is a prototype
    indent = int(indent)
    if len(tables) < indent + 2:
        tables.append({})
    else:
        tables = tables[:indent + 1] + [{}]

    # for every variable being declared
    for var_name, var_info in atoms_declared.items():
        if typed:
            var_type, depth = var_info
        else:
            # depth = 1 is the variable occurs in a new scope
            # 0 if it occurs in the current scope
            depth = var_info
        # if variable name in this level of symbol table
        # and was not declared as a prototype

        #  return false if it has been declared in the same scope
        # and is not a function prototype
        if var_name in tables[indent + depth]:
            var_info = tables[indent + depth][var_name]
            is_prototype = var_info if not typed else var_info[1]
            if not is_prototype:
                if debug:
                    print('var %s declared.' % var_name)
                return False, tables
        is_prototype = var_name == prototype
        tables[indent + depth][var_name] = is_prototype if not typed else (var_type, is_prototype)

    # for every variable being used
    # iterate through the symbol table of the previous scopes
    # to check wehther it has been decalred
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
