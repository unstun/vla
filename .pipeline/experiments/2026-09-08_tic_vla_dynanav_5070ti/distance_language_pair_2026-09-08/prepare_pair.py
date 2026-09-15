"""Build one shared bilingual metric-stop package from the verified probe."""
import datetime
import difflib
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent / 'distance_stop_2026-09-08'
PARENT_SHA = 'cd3d13f7b90114b9ad211f7a97a86a00ab5906c32c6acc575264f38087e8eda2'
ENGLISH = 'Go straight forward for 3 meters, then stop.'


def change(path, old, new):
    text = path.read_text()
    assert text.count(old) == 1, (path, old[:100])
    path.write_text(text.replace(old, new, 1))


def main():
    manifest = PARENT / 'manifests/source.json'
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == PARENT_SHA
    entries = json.loads(manifest.read_text())
    for entry in entries:
        source = PARENT / entry['path']
        assert hashlib.sha256(source.read_bytes()).hexdigest() == entry['sha256']
        target = ROOT / entry['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    (ROOT / 'manifests/metric_parent_source.json').write_bytes(manifest.read_bytes())
    change(ROOT / 'scripts/distance_probe.py', 'TARGET_METERS = 3.0\n',
           f'ENGLISH_INSTRUCTION = {ENGLISH!r}\nALLOWED_INSTRUCTIONS = (INSTRUCTION, ENGLISH_INSTRUCTION)\nTARGET_METERS = 3.0\n')
    change(ROOT / 'scripts/protocol.py',
           'from distance_probe import INSTRUCTION as DISTANCE_INSTRUCTION\nGOALS.add(re.sub(r"[。！？!?,，.;；]", "", DISTANCE_INSTRUCTION))',
           'from distance_probe import ALLOWED_INSTRUCTIONS\nGOALS.update(re.sub(r"[。！？!?,，.;；]", "", text).lower() for text in ALLOWED_INSTRUCTIONS)')
    change(ROOT / 'scripts/run_demo.py',
           'from distance_probe import INSTRUCTION as DISTANCE_INSTRUCTION\n        if instruction != DISTANCE_INSTRUCTION:',
           'from distance_probe import ALLOWED_INSTRUCTIONS\n        if instruction not in ALLOWED_INSTRUCTIONS:')
    change(ROOT / 'scripts/demo_bridge.py',
           '                    rows = ["COMMAND: GO STRAIGHT 3m THEN STOP (Chinese input)",',
           '                    language = "Chinese" if any(ord(c) > 127 for c in behavior._instruction) else "English"\n'
           '                    rows = [f"COMMAND: GO STRAIGHT 3m THEN STOP ({language} input)",')
    # Reuse the reviewed measurement analyzer, routing by each actual request.
    shutil.copy2(PARENT / 'analyze_distance.py', ROOT / 'analyze_distance.py')
    change(ROOT / 'analyze_distance.py',
           'from distance_probe import INSTRUCTION, sustained_stop_windows',
           'from distance_probe import ALLOWED_INSTRUCTIONS, sustained_stop_windows')
    change(ROOT / 'analyze_distance.py',
           "    assert base['finite_30x2'] and base['model_instructions'] == [INSTRUCTION]",
           "    instruction = meta['instruction']\n    assert instruction in ALLOWED_INSTRUCTIONS\n"
           "    assert base['finite_30x2'] and base['model_instructions'] == [instruction]")
    change(ROOT / 'analyze_distance.py', "s['instruction'] == INSTRUCTION", "s['instruction'] == instruction")
    change(ROOT / 'analyze_distance.py', "'instruction': INSTRUCTION", "'instruction': instruction")
    change(ROOT / 'analyze_distance.py', 'one Chinese instruction trial', 'one metric-language instruction trial')
    change(ROOT / 'analyze_distance.py',
           "    fig.suptitle('Chinese command: go straight 3 meters, then stop')",
           "    language = 'Chinese' if any(ord(c) > 127 for c in instruction) else 'English'\n"
           "    fig.suptitle(f'{language} command: go straight 3 meters, then stop')")
    original_plan = json.loads((PARENT / 'plan.json').read_text())
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    plan = {'stage': 'experiment and analysis', 'parent_source_sha256': PARENT_SHA,
            'metric_criteria': original_plan['target'], 'scenario_seed': 36, 'inference_seed': 36,
            'goal_termination_enabled': False, 'automatic_backup_enabled': False,
            'order': ['zh', 'en'], 'camera_view': 'top_down', 'cases': [
                {'language': 'zh', 'run_id': stamp+'_metric_zh', 'instruction': original_plan['instruction']},
                {'language': 'en', 'run_id': stamp+'_metric_en', 'instruction': ENGLISH}],
            'comparison_time_basis': 'recorded simulator timeline after instruction, not wall throughput',
            'claim_boundary': 'one exploratory matched pair, not general multilingual validation'}
    assert not (ROOT / 'pair_plan.json').exists(), 'Do not overwrite a predeclared pair'
    (ROOT / 'pair_plan.json').write_text(json.dumps(plan, indent=2, ensure_ascii=False)+'\n')
    for name in ['runs', 'logs', 'requests', 'comparison']:
        (ROOT / name).mkdir(exist_ok=True)
    for case in plan['cases']:
        request = {'instruction': case['instruction'], 'instruction_mode': 'verbatim', 'inference_seed': 36}
        (ROOT / 'requests' / (case['run_id']+'.json')).write_text(json.dumps(request, indent=2, ensure_ascii=False)+'\n')
    patch = []
    for entry in entries:
        old, new = PARENT / entry['path'], ROOT / entry['path']
        if old.read_bytes() != new.read_bytes():
            patch.extend(difflib.unified_diff(old.read_text().splitlines(True), new.read_text().splitlines(True),
                                            fromfile='a/'+entry['path'], tofile='b/'+entry['path']))
    (ROOT / 'manifests/language_pair.patch').write_text(''.join(patch))
    sources = {ROOT / e['path'] for e in entries}
    sources.update((ROOT / 'scripts').glob('*.py'))
    sources.update([ROOT/'prepare_pair.py', ROOT/'run_pair.py', ROOT/'analyze_distance.py', ROOT/'pair_plan.json',
                    ROOT/'manifests/metric_parent_source.json', ROOT/'manifests/language_pair.patch'])
    records = [{'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
               for p in sorted(sources)]
    (ROOT / 'manifests/source.json').write_text(json.dumps(records, indent=2)+'\n')
    print(json.dumps({'sources':len(records),'cases':plan['cases']},ensure_ascii=False))


if __name__ == '__main__':
    main()
