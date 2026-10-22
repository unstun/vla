"""Bind the user-approved timing exception without changing the offline verdict."""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import offline02

ROOT = Path('/home/ubuntu/sun/vla_v288_20261020')
VERSION = ROOT / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v288'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def verify():
    offline02.verify()
    spec = importlib.util.spec_from_file_location('frozen_offline_evaluation', VERSION / 'execution_admission.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.BENCH = ROOT / 'benchmark'
    result = module.evaluate()
    assert result['non_timing_passed'], result['checks']
    path = ROOT / 'evidence/user_timing_decision01.json'
    decision = json.loads(path.read_text())
    assert decision['version'] == 'v288'
    assert decision['decision'] == 'continue_ten_timing_target_unmet'
    assert decision['user_answer'] == '继续十条，耗时记未达标'
    assert decision['native_manifest_sha256'] == result['native_manifest_sha256']
    assert math.isclose(decision['reported_global_median_s'], result['global_median_s'], abs_tol=1e-9)
    assert decision['global_median_target_s'] == 1.5
    assert decision['all_non_timing_gates_required']
    assert decision['hard_radius_m'] == .35 and decision['sensor_period_s'] == .1
    assert decision['authorized_attempts_per_case'] == 1
    return dict(physical_execution_authorized=True, authorized_attempts_per_case=1,
        offline_evaluation=result,
        original_native_manifest_sha256=sha(VERSION / 'native_manifest.json'),
        new_host_native_manifest_sha256=sha(offline02.MANIFEST),
        strict_offline_gate_sha256=sha(ROOT / 'benchmark/offline_gate.json'),
        benchmark_acceptance_passed=result['benchmark_acceptance_passed'],
        timing_target_met=result['timing_acceptance_passed'],
        timing_exception_authorized=True, all_non_timing_gates_passed=True,
        timing_decision_sha256=sha(path), same_53_requests=True,
        hard_radius_m=.35, sensor_period_s=.1)
