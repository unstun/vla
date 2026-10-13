"""Run after the cohort closes; compact five immutable, hash-verified captures."""
import argparse,json
from pathlib import Path
from extract import extract
p=argparse.ArgumentParser();p.add_argument('--task',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
for n in range(6,11):
 tag=f'v177_full_candidate_attempt{n:02d}';trial=a.task/'trials'/tag
 assert (trial/'evidence/execution.json').is_file(),'Do not analyze an active physical run'
 assert (a.task/'results/v177_full_repeats'/tag/'outcome.json').is_file(),'Closeout missing'
 extract(trial/'runs'/tag,a.output/f'attempt{n:02d}')
