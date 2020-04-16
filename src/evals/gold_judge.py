import os
import shutil
import time
import subprocess
from timeit import default_timer as timer
import filecmp

testcase_dir = '../spoc/testcases/'
judge_space_dir = '../judge_space/'
test_input_symbol = '###ENDINPUT###\n'
test_output_symbol = '###ENDOUTPUT###\n'

source_header = '#include <bits/stdc++.h>\n\nusing namespace std;\n\n'

def prepare_judge_folder():
    try:
        shutil.rmtree(judge_space_dir)
    except FileNotFoundError:
        pass
    
    try:
        os.mkdir(judge_space_dir)
    except:
        pass
    
    # get all the problem folders and iterate through them
    all_problem_ids = [folder_name for folder_name in os.listdir(testcase_dir) 
                        if os.path.isdir(testcase_dir + folder_name)]
    
    # iterate through all the problems
    for problem_id in all_problem_ids:
        # create a corresponding folder in the judge space
        judge_problem_space = judge_space_dir + problem_id + '/'
        os.mkdir(judge_problem_space)
        
        # the folder that contain testcase files
        read_problem_folder = testcase_dir + problem_id + '/'
        test_files = [f_name for f_name in os.listdir(read_problem_folder) if f_name[-4:] == '.txt']
        
        # for each category of test case
        for test_file_name in test_files:
            
            read_test_file_dir = read_problem_folder + test_file_name
            f_info = test_file_name[:-4].split('_')
            if len(f_info) == 2:
                f_info.append('all')
            assert f_info[0] == problem_id
            
            # create directory to store individual testcasfes
            test_cases_output_dir = judge_problem_space + f_info[-1] + '/'
            os.mkdir(test_cases_output_dir)
            
            # read the test cases contained in a single file
            # and split them by the end symbol
            with open(read_test_file_dir, 'r') as in_file:
                test_case_str = in_file.read()
            test_str_by_cases = test_case_str.split(test_output_symbol)
            
            # iterate through test cases and create corresponding test files
            for test_id, test_str in enumerate(test_str_by_cases):
                if test_str == '':
                    continue
                test_input, test_output = test_str.split(test_input_symbol)
                testcase_prefix = test_cases_output_dir + str(test_id)
                with open(testcase_prefix + '.in', 'w') as out_file:
                    out_file.write(test_input)
                with open(testcase_prefix + '.out', 'w') as out_file:
                    out_file.write(test_output)
                    
# prepare_judge_folder()

class Judge:
    
    judge_id = 0
    # initialize a judge by locating the folder for problem id and judge type ('hidden', 'public', '')
    def __init__(self, problem_id, judge_type, eager=False, judge_id=None, compile_only=False):
        self.problem_id = problem_id
        test_cases_dir = '%s/%s/%s/' % (judge_space_dir, problem_id, judge_type)
        num_test_cases = len(os.listdir(test_cases_dir)) // 2
        self.intput_output_f_dir_name = [['%s%d.%s' % (test_cases_dir, test_case_id, suffix) for suffix in ['in', 'out']]
                                         for test_case_id in range(num_test_cases)]
        if judge_id is None:
            self.id = Judge.judge_id
        else:
            self.id = judge_id
        self.eager = eager
        Judge.judge_id += 1
        self.compile_only = compile_only

    def judge_program_str(self, program_str, program_suffix=''):
        result = self.judge_program_str_(program_str, program_suffix)
        shutil.rmtree(self.exec_folder)
        return result
    
    def judge_program_str_(self, program_str, program_suffix=''):
        # default program suffix is the current time to avoid creating the same folder at a time
        time_rounding = int(time.time() * 1000000) % 100000000
        program_suffix += 'time-' + str(time_rounding) + '-id-' + str(self.id) + str(self.problem_id)
         
        # put all the source & executable in this directory
        self.exec_folder = '%s%s/%s-exec/' % (judge_space_dir, self.problem_id, program_suffix)
        
        try:
            os.mkdir(self.exec_folder)
        except:
            program_suffix += 'time-' + str(time_rounding) + '-id-' + str(self.id) + str(self.problem_id)
            # put all the source & executable in this directory
            self.exec_folder = '%s%s/%s-exec/' % (judge_space_dir, self.problem_id, program_suffix)
            os.mkdir(self.exec_folder)

        # write the source file
        source_file = self.exec_folder + 'source.cc'
        with open(source_file, 'w') as out_file:
            out_file.write(source_header)
            out_file.write(program_str)
        exec_out = self.exec_folder + 'exe.o'
        compiler_message_file = self.exec_folder + 'compiler-message.txt'
        
        # try compilation
        subprocess.call('g++ %s -o %s > %s 2>&1' % (source_file, exec_out, compiler_message_file), shell=True, timeout=60)

        with open(compiler_message_file, 'r') as in_file:
            compile_msg = in_file.read()

        # if executable still does not exist, compilation fails
        if not os.path.exists(exec_out):
            return {
                'Status': 'Compilation Error',
                'Error Message': compile_msg
            }

        if self.compile_only:
            return {'Status': 'Compile Successful'}

        pass_status = []
        # test on each cases
        for testcase_id, (input_file, output_file) in enumerate(self.intput_output_f_dir_name):
            pred_out = '%s%dpred.txt' % (self.exec_folder, testcase_id)
            err_out = '%s%derr.txt' % (self.exec_folder, testcase_id)
            
            # execute and obtain the results
            fkwargs = {
                'stdin': open(input_file, 'r'),
                'stdout': open(pred_out, 'w'),
                'stderr': open(err_out, 'w')
            }
            try:
                result = subprocess.call(exec_out, **fkwargs, timeout=2)
            except subprocess.TimeoutExpired:
                pass_status.append((False, 'Time Limit Exceeds.'))
                if self.eager:
                    return {"Status": "TLE"}
                continue
            [fkwargs[key].close() for key in fkwargs]

            f_equal = filecmp.cmp(pred_out, output_file)

            # whether it is the same as ground truth
            if f_equal:
                pass_status.append((True, ''))
            else:
                with open(err_out, 'r') as in_file:
                    err_msg = in_file.read()
                pass_status.append((False, err_msg))
                if self.eager:
                    return {"Status": "Execution Error"}
        
        # all execution information has been collected
        
        all_passed = True
        for s, _ in pass_status:
            if not s:
                all_passed = False
                break
        if all_passed:
            return {'Status': 'Passed'}
        else:
            return {
                'Status': 'Execution Error',
                'Case Status': pass_status
            }
    
def debug_judge():
    j = Judge('86A', 'all')
    with open('evals/86A.sol', 'r') as in_file:
        program_str = in_file.read()
    result = j.judge_program_str(program_str)
    print(result)

if __name__ == '__main__':
    debug_judge()
    # def program_str(self, program_str):
    # def program_str(self, program_str):