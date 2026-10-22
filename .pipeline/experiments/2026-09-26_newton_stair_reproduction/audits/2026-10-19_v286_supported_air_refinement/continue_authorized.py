"""Continue the approved single-attempt batch after zero-step qualification."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = Path('/home/sun/vla_exec/supported_air_refinement_v286')
TAG=os.environ.get('V286_CONTINUATION_ID','01')
assert len(TAG)==2 and TAG.isdigit()
RECEIPT=ROOT/f'authorized_continuation{TAG}.json'
QUALIFICATION=os.environ.get('V286_EXPECT_QUALIFICATION_ID','01')
assert len(QUALIFICATION)==2 and QUALIFICATION.isdigit()


def main():
    row = dict(pid=os.getpid(), started_utc_s=time.time(),
               stage='waiting_for_execution_qualification',
               coordinator_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               authorization='User requested v286 strict 50+3 followed by ten single attempts')
    with RECEIPT.open('x') as output:
        json.dump(row, output, indent=2)

    def save():
        temporary=RECEIPT.with_suffix('.tmp')
        temporary.write_text(json.dumps(row, indent=2) + '\n')
        temporary.replace(RECEIPT)

    try:
        while True:
            try:
                qualified = json.loads((ROOT / f'execution_qualification{QUALIFICATION}.json').read_text())
            except json.JSONDecodeError:
                # Existing qualifier updates can overlap this read.
                time.sleep(.2)
                continue
            if 'returncode' in qualified:
                assert qualified['returncode'] == 0, 'Qualification failed; preserve and inspect'
                break
            time.sleep(30)
        for stage, script in [('ten_single_physical_attempts', 'execute_batch.py'),
                              ('recorded_state_analysis_and_delivery', 'after_physics.py')]:
            row.update(stage=stage)
            save()
            subprocess.run([sys.executable, str(HERE / script)], check=True)
        row.update(stage='ready_for_local_return', finished_utc_s=time.time(), returncode=0)
        save()
    except Exception as error:
        row.update(stage='stopped_for_inspection', error=str(error),
                   finished_utc_s=time.time(), returncode=1)
        save()
        raise


if __name__ == '__main__':
    main()
