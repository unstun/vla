"""Strict v135 ablation using the unchanged installed v240 C++ Search."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import struct
import subprocess

BASE = Path('/data/sun/vla_mppi_20261009')
HERE = Path(__file__).resolve().parent
VERSIONS = HERE.parents[1] / 'versions'
OUT = BASE / 'physical_traversability_v247/ablation'
IMAGE = 'sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('native_export', VERSIONS / 'v201/tools/export_pct_map.py')
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    original = BASE / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/inputs/new_building.pickle'
    assert sha(original) == 'ab5499ff100fe233f6cfabb59ce7592290cddd042c92ead5e37e9e2b593d24da'
    restored = OUT / 'original.pct'
    if not restored.exists():
        exporter.export_map(original, restored)
    frozen = BASE / 'callback_failure_v232/fixtures/building/route.pct'
    assert sha(frozen) == 'f4f72f27b5330d6353a3d62f3e630dedf7d70c294a97d960ec0d6b0d549aa10d'
    # Second control changes only cost/gradients; gateway bytes stay frozen.
    old, raw = bytearray(frozen.read_bytes()), restored.read_bytes()
    assert old[:60] == raw[:60]
    _, layers, nx, ny, *_ = struct.unpack('<8sIII5d', raw[:60])
    size = layers * nx * ny * 8
    for channel in (0, 4, 5):
        a = 60 + channel * size
        old[a:a + size] = raw[a:a + size]
    cost_only = OUT / 'costs_restored_gateway_frozen.pct'
    cost_only.write_bytes(old)
    setup = 'source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /task/callback_failure_v232/install/setup.bash && source /work/install/setup.bash'
    shell = setup + ' && cmake -S /observer -B /evaluation/build && cmake --build /evaluation/build -j2'
    mounts = ['docker', 'run', '--rm', '--pull=never', '--user', f'{os.getuid()}:{os.getgid()}',
              '--cpus=6', '--memory=6g', '-v', str(BASE) + ':/task:ro',
              '-v', str(BASE / 'cooperative_search_v240') + ':/work:ro',
              '-v', str(HERE) + ':/observer:ro', '-v', str(OUT) + ':/evaluation:rw',
              '-v', str(BASE / 'generalization_v242/cases') + ':/cases:ro',
              '--entrypoint', '/bin/bash', IMAGE, '-c']
    subprocess.run(mounts + [shell], check=True)
    rows = []
    for name, route in [('v135', '/task/callback_failure_v232/fixtures/building/route.pct'),
                        ('costs_restored', '/evaluation/costs_restored_gateway_frozen.pct'),
                        ('original_native', '/evaluation/original.pct')]:
        target = OUT / name
        target.mkdir(exist_ok=False)
        # Keep separate output ownership for each actual native graph dump.
        command = setup + ' && /evaluation/build/ablation_search ' + route + ' /cases/*/endpoints.txt'
        run = mounts.copy()
        insert = run.index('--entrypoint')
        run[insert:insert] = ['-v', str(target) + ':/evaluation/results:rw']
        command = command.replace('/evaluation/build/ablation_search', '/evaluation/build/ablation_search')
        env = 'export ABLATION_OUTPUT=/evaluation/results'
        with (target / 'search.log').open('x') as log:
            subprocess.run(run + [setup + ' && ' + env + ' && ' + command[len(setup) + 4:]], stdout=log, stderr=subprocess.STDOUT, check=True)
        log = (target / 'search.log').read_text()
        for match in re.finditer(r'QUERY (\w+) reverse=(\d) reached=(\d) visited=(\d+)', log):
            case, reverse, reached, visited = match.groups()
            rows.append(dict(treatment=name, case_id=case, reverse=int(reverse), reached=bool(int(reached)), visited=int(visited)))
    receipt = dict(installed_native='v240 unchanged', source_map_sha256=sha(original),
                   frozen_route_sha256=sha(frozen), restored_route_sha256=sha(restored),
                   cost_only_route_sha256=sha(cost_only), calls=rows,
                   changes='cost/gradient only and native original export controls; no ENV or support threshold change')
    (OUT / 'summary.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
