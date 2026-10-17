"""Create an explicit source/input transfer list; no old trial captures or caches."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'AGENTS.md').is_file())
EXPERIMENTS = ROOT / '.pipeline/experiments'
STAIR = EXPERIMENTS / '2026-09-26_newton_stair_reproduction'
POLICY = EXPERIMENTS / '2026-09-26_newton_macos_policy'
FACTORY = EXPERIMENTS / '2026-09-27_lite3_factory_runtime_audit'
OMIT = {'__pycache__', '.pytest_cache', '.DS_Store'}


def files():
    selected = {ROOT / 'AGENTS.md'}
    # Frozen v232 includes its compact original evidence, required by source_gate.
    trees = [HERE / 'bin'] + [STAIR / p for p in ('inputs', 'references', 'scripts', 'runtime_sources/bridge',
                                 'config_archived', 'versions/v232', 'versions/v233',
                                 'versions/v40/physics', 'versions/v198/runtime')]
    trees += [POLICY / p for p in ('scripts', 'references', 'policy', 'assets', 'runtime/assets')]
    trees += [FACTORY / 'private_snapshot',
              EXPERIMENTS / '2026-09-23_scan_reactive_stair/runtime_integration/runs/walk_scan28_height030_right_v1/bridge']
    trees += [STAIR / p for p in (
        'versions/v134/src/plan_env/include', 'versions/v201/tools',
        'versions/v203/tools', 'versions/v203/src/lite3_nav2_bridge',
        'versions/v224/tools', 'versions/v225/tools', 'versions/v225/results/fixtures',
        'versions/v224/src/plan_env')]
    for tree in trees:
        assert tree.is_dir(), tree
        selected.update(p for p in tree.rglob('*') if p.is_file()
                        and not (set(p.relative_to(tree).parts) & OMIT) and p.suffix != '.pyc')
    # Only top-level version helpers/configuration; no historical runs/builds.
    for version in ('v51', 'v81', 'v84', 'v134', 'v135', 'v187', 'v196', 'v198',
                    'v201', 'v216', 'v219', 'v220', 'v234'):
        selected.update(p for p in (STAIR / 'versions' / version).iterdir() if p.is_file())
    for name in ('source_identity.json',):
        selected.add(STAIR / 'setup' / name)
    selected.add(POLICY / 'setup/lite3_inputs.json')
    selected.update(STAIR / 'audits/2026-09-27_dense_static_sampling' / name for name in
                    ('map.pickle', 'map_float32.npz', 'raw_cost_observation.npz', 'raw_ground.f32'))
    selected.update(p for p in FACTORY.iterdir() if p.is_file())
    selected.add(FACTORY / 'analysis/abi_summary.json')
    selected.update(STAIR / 'repairs/2026-09-26_generic_occupancy' / p
                    for p in ('geometry_driver.py', 'driver_identity.json'))
    selected.update(STAIR / 'hosts/2026-09-29_gpu5070ti' / p
                    for p in ('requirements_linux.lock', 'gpu5070ti_worker_environment.json'))
    receipts = STAIR / 'audits/2026-10-17_v232_physical_comparison/results/execution_receipts'
    selected.update(p for p in receipts.iterdir() if p.is_file())
    return sorted(selected)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Use a new sync attempt directory'
    args.output.mkdir(parents=True)
    manifest = {}
    for path in files():
        assert path.is_file(), path
        path.resolve().relative_to(ROOT)  # No unpinned sibling source imports.
        rel = str(path.relative_to(ROOT))
        assert '\n' not in rel
        data = path.read_bytes()
        manifest[rel] = dict(size=len(data), sha256=hashlib.sha256(data).hexdigest())
    (args.output / 'files.txt').write_text('\n'.join(manifest) + '\n')
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(files=len(manifest), bytes=sum(v['size'] for v in manifest.values()),
                          output=str(args.output))))


if __name__ == '__main__':
    main()
