"""Validate synchronized inference evidence and summarize actual measurements."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics

parser=argparse.ArgumentParser()
parser.add_argument('run')
parser.add_argument('--reload-run')
args=parser.parse_args()
root=Path(args.run).resolve()

def validate(run):
    manifest=json.loads((run/'artifact_manifest.json').read_text())
    for item in manifest['files']:
        path=run/item['path']
        assert path.stat().st_size==item['size'],str(path)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'],str(path)
    meta=json.loads((run/'meta.json').read_text())
    assert meta['exit_code']==0 and not meta['timed_out'],meta
    result=json.loads((run/'results/metadata.json').read_text())
    assert result['complete'] and result['linear4bit_count']>0
    assert all(c['raw_output'] for c in result['cases'])
    return result,len(manifest['files'])

result,count=validate(root)
cases=result['cases']
original=cases[0]
repeat=next((c for c in cases if c['name']=='repeat_first_identical_input'),None)
repeat_match=None if repeat is None else repeat['output_ids']==original['output_ids']
if repeat is not None:assert repeat_match
gpu_samples=[json.loads(l) for l in (root/'gpu_samples.jsonl').read_text().splitlines()]
memory=[float(x['gpu'].split(',')[0]) for x in gpu_samples if x['exit_code']==0 and x['gpu']]
summary={'validated_artifact_files':count,'scope':'recorded-image NF4 inference; no closed-loop navigation',
 'model_load_seconds':result['load_seconds'],'four_bit_layers':result['linear4bit_count'],
 'cases':len(cases),'all_nonempty':True,'repeat_output_ids_equal':repeat_match,
 'first_inference_seconds':cases[0]['inference_seconds'],
 'later_inference_median_seconds':statistics.median(c['inference_seconds'] for c in cases[1:]),
 'max_torch_allocated_GiB':max(c['peak_allocated_GiB'] for c in cases),
 'max_sampled_total_gpu_MiB':max(memory),
 'outputs':[{'name':c['name'],'instruction':c['instruction'],'output':c['raw_output'],
             'seconds':c['inference_seconds']} for c in cases]}
if args.reload_run:
    reloaded,reload_count=validate(Path(args.reload_run).resolve())
    assert reloaded['cases'][0]['input_sha256']==original['input_sha256']
    assert reloaded['cases'][0]['prompt']==original['prompt']
    equal=reloaded['cases'][0]['output_ids']==original['output_ids']
    assert equal,'Exported checkpoint changed the repeated greedy output'
    summary.update(reload_output_ids_equal=equal,reload_artifact_files=reload_count,
                   reload_model_load_seconds=reloaded['load_seconds'])
(root/'local_validation.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
print(json.dumps(summary,indent=2,ensure_ascii=False))
