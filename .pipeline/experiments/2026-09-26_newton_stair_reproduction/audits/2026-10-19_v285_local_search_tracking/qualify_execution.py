"""Zero-physics execution qualification after the complete offline evidence."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
VERSION = HERE.parents[1] / 'versions/v285'
ROOT = Path('/home/sun/vla_exec/local_search_tracking_v285')
TAG = os.environ.get('V285_QUALIFICATION_ID', '01')
assert len(TAG) == 2 and TAG.isdigit()
RECEIPT = ROOT / f'execution_qualification{TAG}.json'


def main():
    row = dict(pid=os.getpid(), physics_steps=0, started_utc_s=time.time(),
               stage='waiting_for_complete_offline',
               coordinator_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    with RECEIPT.open('x') as output:
        json.dump(row, output, indent=2)

    def save():
        RECEIPT.write_text(json.dumps(row, indent=2) + '\n')

    try:
        deadline = time.monotonic() + 7200
        while not (ROOT / 'benchmark/complete.json').exists():
            assert time.monotonic() < deadline, 'Offline completion wait expired'
            time.sleep(10)
        row['stage'] = 'verifying_complete_strict_offline_gate'
        save()
        for script, arguments in [
            ('execution_admission.py', [] if (VERSION / 'execution_review.json').exists()
             else ['--record']), ('prepare_execution.py', []),
        ]:
            subprocess.run([sys.executable, str(VERSION / script), *arguments], check=True)
        subprocess.run([sys.executable,str(HERE/'verify_all_starts.py')],check=True)
        row['all50_start_verification_sha256']=hashlib.sha256((HERE/'results/all50_start_verification.json').read_bytes()).hexdigest()
        save()
        cases = json.loads((VERSION / 'native_manifest.json').read_text())['physical_cases']
        row['preflight_cases'] = []
        from watch_resources import sample
        for case in cases:
            while True:
                resource = sample()
                row.update(stage='waiting_resources_for_zero_physics_preflight',
                           current_case=case, resource_check=resource)
                save()
                if resource['passed']:
                    break
                time.sleep(30)
            evidence = Path('/data/sun/vla_mppi_20261009/generalization_v285') / case
            preflight_tag = next(f'{n:02d}' for n in range(1, 100)
                                 if not (evidence / ('deadline_tests.log' if n == 1
                                         else f'deadline_tests_{n:02d}.log')).exists())
            row.update(stage='zero_physics_preflight', current_case=case)
            save()
            subprocess.run([sys.executable, str(VERSION / 'preflight_runner.py')],
                           env=dict(os.environ, V285_CASE_ID=case,
                                    V285_PREFLIGHT_ID=preflight_tag), check=True)
            row['preflight_cases'].append(case)
            save()
        subprocess.run([sys.executable, str(VERSION / 'freeze_execution.py')], check=True)
        sys.path.insert(0, str(VERSION))
        from identity import verify_sources
        row.update(stage='qualified_and_frozen', source_verification=verify_sources(),
                   finished_utc_s=time.time(), returncode=0)
        save()
    except Exception as error:
        row.update(stage='stopped_for_inspection', error=str(error), returncode=1,
                   finished_utc_s=time.time())
        save()
        raise


if __name__ == '__main__':
    main()
