"""Reuse the frozen v233 profile gate against locally returned baseline YAML."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
PREFIX = json.loads((HERE / 'binding.json').read_text())['remote_root']
FROZEN = HERE.parent / 'v233/verify_profile.py'
source = FROZEN.read_text()
before = "REMOTE=Path('/data/sun/vla_mppi_20261009')"
assert source.count(before) == 1
source = source.replace(before, f'REMOTE=Path({PREFIX!r})')
before = "baseline=REMOTE/'trials/v219_linux_full_attempt01/runs/v219_linux_full_attempt01'"
assert source.count(before) == 1
baseline = BASE / 'audits/2026-10-17_v232_physical_comparison/results/execution_receipts'
source = source.replace(before, f'baseline=Path({str(baseline)!r})')
namespace = {'__file__': str(FROZEN), '__name__': 'v234_frozen_profile_gate'}
exec(compile(source, str(FROZEN), 'exec'), namespace)
verify = namespace['verify']
