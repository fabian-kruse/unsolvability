#! /usr/bin/env python
# -*- coding: utf-8 -*-

from lab.environments import LocalEnvironment, BaselSlurmEnvironment
from downward.experiment import FastDownwardExperiment
from downward.reports.absolute import AbsoluteReport
from downward.reports.scatter import ScatterPlotReport

import os
import os.path
import platform

def fd_finished(run):
    if 'error' not in run:
        print run['run_dir']
        run['fd_finished'] = 0
    elif(run['error'] == 'search-unsolvable-incomplete'):
        run['fd_finished'] = 1
    else:
        run['fd_finished'] = 0
    return run

def verify_timeout(run):    
    if('verify_returncode' in run and run['verify_returncode'] == 7):
        run['verify_timeout'] = 1
    else:
        run['verify_timeout'] = 0
    return run
def verify_oom(run):
    if('verify_returncode' in run and run['verify_returncode'] == 6):
        run['verify_oom'] = 1
    else:
        run['verify_oom'] = 0
    return run
def verify_finished(run):
    if(not run['unsolv_is_certificate'] == 'unknown'):
        run['verify_finished'] = 1
    else:
        run['verify_finished'] = 0 
    return run
def invalid_certificate(run):
    if(run['unsolv_is_certificate'] == 'no'):
        run['invalid_certificate'] = 1
    else:
        run['invalid_certificate'] = 0
    return run
def valid_certificate(run):
    if(run['unsolv_is_certificate'] == 'yes'):
        run['valid_certificate'] = 1
    else:
        run['valid_certificate'] = 0
    return run


#SUITE = ["3unsat", "bag-barman", "bag-gripper", "bag-transport", "bottleneck", "cave-diving", "chessboard-pebbling", "diagnosis", "document-transfer", "mystery", "over-nomystery", "over-rovers", "over-tpp", "pegsol", "pegsol-row5", "sliding-tiles", "tetris", "unsat-nomystery", "unsat-rovers", "unsat-tpp"]
# for test purposes on the grid
SUITE = ['3unsat:sat-3-22-5-1.pddl']


NODE = platform.node()
if NODE.endswith(".scicore.unibas.ch") or NODE.endswith(".cluster.bc2.ch"):
    ENV = BaselSlurmEnvironment(partition="infai_1", email="fabian.kruse@unibas.ch")
else:
    SUITE = ['bottleneck:prob03.pddl']
    ENV = LocalEnvironment(processes=2)

# paths to repository and benchmarks 
REPO = os.path.expanduser('~/downward-unsolvability/')
BENCHMARKS_DIR = os.path.expanduser('~/unsolv-total')

exp = FastDownwardExperiment(environment=ENV)

# Add default parsers to the experiment.
exp.add_parser(exp.EXITCODE_PARSER)
exp.add_parser(exp.TRANSLATOR_PARSER)
exp.add_parser(exp.SINGLE_SEARCH_PARSER)
exp.add_parser(exp.PLANNER_PARSER)

exp.add_suite(BENCHMARKS_DIR, SUITE)

# Algorithms
# Algorithms
REVISIONS = ['HEAD']
#UNSOLV_TYPE = ['none', 'certificate', 'certificate_fastdump', 'certificate_nohints', 'proof', 'proof_discard']
UNSOLV_TYPE = ['proof']
CONFIGS = []

#CONFIGS.append(['mas', 'merge_and_shrink(merge_strategy=merge_precomputed(merge_tree=linear()), shrink_strategy=shrink_bisimulation(), label_reduction=exact(before_shrinking=true,before_merging=false), prune_unreachable_states=false)'])
#CONFIGS.append(['hmax', 'hmax(unsolv_subsumption=false)'])
#CONFIGS.append(['hmax_sub', 'hmax(unsolv_subsumption=true)'])
#CONFIGS.append(['hm', 'hm()'])
#CONFIGS.append(['mas-hm', 'max([merge_and_shrink(merge_strategy=merge_precomputed(merge_tree=linear()), shrink_strategy=shrink_bisimulation(), label_reduction=exact(before_shrinking=true,before_merging=false), prune_unreachable_states=false),hm()])'])

CONFIGS.append(['blind', 'const()'])
CONFIGS.append(['hm', 'hm()'])


ALGS = []
for rev in REVISIONS:
   for config in CONFIGS:
       for unsolv_type in UNSOLV_TYPE:
           config_name, config_desc = config
           ALGS.append(config_name)
           exp.add_algorithm(config_name, REPO, rev, 
                             ["--search", "astar(%s, unsolv_verification=%s, unsolv_directory=$TMPDIR)" % (config_desc, unsolv_type)], 
                             driver_options=["--translate-time-limit", "30m", "--translate-memory-limit","2G"])

# Add script to print filesize
exp.add_resource('filesize_script', 'print_filesize')
exp.add_command('print-filesize', ['./{filesize_script}'])

exp.add_resource('helve', '../helve/helve')
exp.add_command('verify', ['./{helve}', '$TMPDIR/task.txt', '$TMPDIR/proof.txt'], time_limit=14400, memory_limit=3584)

# Add custom parser only after filesize is printed, as it parses for this
exp.add_parser('myparser.py')

# Add step that writes experiment files to disk.
exp.add_step('build', exp.build)

# Add step that executes all runs.
exp.add_step('start', exp.start_runs)

# Add step that collects properties from run directories and
# writes them to *-eval/properties.
exp.add_fetcher(name='fetch')


# Example report over all configs and with most important attributes
report = os.path.join(exp.eval_dir, 'thesis-experiment.html')
exp.add_report(AbsoluteReport(filter_algorithm=ALGS, filter=[fd_finished, verify_timeout, verify_oom, verify_finished, invalid_certificate, valid_certificate], attributes=['fd_finished', 'verify_timeout','verify_oom', 'verify_finished', 'invalid_certificate', 'valid_certificate', 'run_dir', 'error', 'raw_memory', 'evaluated', 'dead_ends', 'expansions', 'search_time', 'total_time', 'unsolv_total_time', 'unsolv_actions', 'unsolv_is_certificate', 'unsolv_memory', 'unsolv_abort_memory', 'unsolv_abort_time', 'unsolv_exit_message', 'verify_returncode', 'certificate_size_kb']), outfile=report)


#Example for scatterplot
#exp.add_report(ScatterPlotReport(format='tex', attributes=['total_time'], filter_algorithm=['mas', 'mas-certifying']), outfile=os.path.join(exp.eval_dir, 'test.tex'))


exp.run_steps()

