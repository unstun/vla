"""Retain the failed terminal gate; derive display metrics from a nonterminal capture."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent;VERSIONS=HERE.parents[1]/'versions'
sys.path.insert(0,str(VERSIONS/'v196'))
import analyze_remote,shared_state
RAW=Path('/data/sun/vla_mppi_20261009/trials/v233_linux_full_attempt01/runs/v233_linux_full_attempt01')
OUT=HERE/'results/diagnostic_metrics'
original=shared_state.verify_capture
def verify_or_record_failure(capture):
 try:return original(capture)
 except AssertionError:
  report=capture.json('shared_state.json')
  assert report['verified'] is False,report
  assert not (RAW/'artifacts/external_episode/finish_request.json').exists()
  return False
shared_state.verify_capture=verify_or_record_failure
analyze_remote.analyze(RAW,OUT,True)
p=OUT/'metrics.json';metrics=json.loads(p.read_text())
metrics.update(native_version='v232 navigation / v233 execution binding',full_qualification=False,
 diagnostic_only=True,shared_state_terminal_verification='FAILED; original analyzer failed and its log is retained',
 original_analyzer_sha256=hashlib.sha256((VERSIONS/'v196/analyze_remote.py').read_bytes()).hexdigest(),
 adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
p.write_text(json.dumps(metrics,indent=2)+'\n')
