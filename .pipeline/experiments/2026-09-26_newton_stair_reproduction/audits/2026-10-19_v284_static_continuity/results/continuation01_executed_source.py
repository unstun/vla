"""Continue the approved single-attempt batch after zero-step qualification."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = Path('/home/sun/vla_exec/static_continuity_v284')
RECEIPT = ROOT / 'authorized_continuation01.json'


def main():
    row = dict(pid=os.getpid(), started_utc_s=time.time(),
               stage='waiting_for_execution_qualification',
               coordinator_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               authorization='继续十条，耗时记未达标')
    with RECEIPT.open('x') as output:
        json.dump(row, output, indent=2)

    def save():
        RECEIPT.write_text(json.dumps(row, indent=2) + '\n')

    try:
        while True:
            qualified = json.loads((ROOT / 'execution_qualification02.json').read_text())
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
