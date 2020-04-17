# Semantic Scaffolds for Pseudocode-to-Code Generation
## Ruiqi Zhong, Mitchell Stern, Dan Klein

This is the github repo that contains implementation that can reproduce the results in our paper.

## 1. Setup
change directory to ```src``` and run ```python3 setup_files.py```. 
It will automatically download the data, setup the directories and write the files 
we need for our implementation. Note that the result might be slightly different, as we used the initial dataset release of  Kulal et al., 2019 (rather than the updated version while we submitted our paper).
We define the id of each program/problem to be [subid]-[probid]-[workerid].

## 2. Code pieces
Since translating code pieces is not our focus, we precomputed all the translations and dumped it into spoc/pre_trans/ for ease of reproducibility.
To reproduce the training process, change directory to the  ```src``` folder and run 

```python3 onmt_dir/prepare_for_onmt.py comments```

Then the source/target data file for training a pseudocode2code translation model will appear in ```spoc/onmt/```.
We used the default hyper-parameters from OpenNMT to train the model, with command line arguments

```python3 -u ../opennmt/preprocess.py -train_src programscomments_train.src -train_tgt ../spoc/onmt/programscomments_train.tgt -save_data ../spoc/onmt/data --dynamic_dict```

```python3 -u ../opennmt/train.py -data=../spoc/onmt/data --copy_attn  -coverage_attn -lambda_coverage=0.1 --start_decay_steps=100000 --train_steps=200000```

and change the training config whenever needed.

The transform from C++ program to tokenized input for translation (and the reverse direction) is implemented in ```src/onmt_dir/prepare_for_onmt.py``` as ```to_onmt/to_code```

## 3. Search

Change directory to ```src/``` and run
```python3 search.py -h``` to get the list of configurations.
For example, to run hierarchical beam search with semantics constraint on the unseen problem test set, the command line arguments should be

```python3 search.py --search_opt=semantics --use_indent --target=problem ```

The search results will appear in the result_dir as printed by the process (in this case ```'../spoc/search_results/semantics-hierarchical-use_indent-structure_beam_size50structure_topk20budget100/```) 

and we use the following command to print out results.

```
python3 calculate_stats.py --result_dir=../spoc/search_results/semantics-hierarchical-use_indent-structure_beam_size50structure_topk20budget100/ --opt=problem
```

Note that the evaluation can be extremely slow because running testcases takes a lot of time. 
To alleviate this problem 
1. we memoize all the evaluation results in ```../spoc/eval_memo```
2. dump a lock to the result directory so that we can run several identical processes with different random seed to parallelize without conflicting each other.

## 4. Implementation

```evals/gold_judge.py``` evaluates whether a generated full program can pass all the testcases.

```parse/``` contains all the helper functionality to parse the C++ program. 
We used a lot of heuristics to write our own C++ parser in python3 to extract the syntactic/semantics configuration for each line
, since we failed to find any off-the-shelf tool to extract the features we want.
Functions ```extract_semantics_config/extract_syntax_config``` in ```src/search_util/structured_search.py``` extracts the configuration for each line.

```src/search_util/structured_search.py``` contains the main logic for hierarchical beam search. 
```StructureCandidate.step()``` implements the incremental check for beam search and ```src/search_util/tables.py``` check the SymTable constraint.

## 5. Error Analysis in 7.3

The error analysis sheet is hard_lines_category.csv .