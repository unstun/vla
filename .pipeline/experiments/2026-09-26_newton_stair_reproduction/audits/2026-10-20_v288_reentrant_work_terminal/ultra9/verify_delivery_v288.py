"""Verify the returned strict results, explicit timing exception, and ten videos."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

H=Path(__file__).resolve().parent
E=H.parents[2]
V=E/'versions/v288'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())

def main():
    native=load(V/'native_manifest.json')
    for rel,digest in native['source_files'].items():assert sha(V/rel)==digest,rel
    manifest=load(H/'evidence/physical_manifest01.json')
    assert manifest['native_manifest_sha256']==sha(V/'native_manifest.json')
    assert manifest['new_host_native_manifest_sha256']==sha(H/'native_manifest01.json')
    assert manifest['authorized_attempts_per_case']==1
    assert manifest['hard_radius_m']==.35 and manifest['sensor_period_s']==.1
    assert sha(H/'execution_policy.py')==manifest['files']['migration/execution_policy.py']
    for name in ('physical.py','physical_setup.py','batch.py','preflight.py'):
        assert sha(H/name)==manifest['files']['migration/'+name],name
    assert sha(H/'evidence/user_timing_decision01.json')==manifest['files']['evidence/user_timing_decision01.json']
    gate=load(H/'offline/offline_gate.json')
    assert gate['calls']==53 and gate['positive_total']==50 and gate['positive_passed']>=48
    assert gate['illegal_controls']==gate['illegal_correct_rejections']==3
    assert gate['zero_admitted_negative_raw_margin'] and gate['zero_published_negative_raw_margin']
    assert gate['global_median_s']>1.5 and not gate['passed']
    admission=manifest['execution_admission']
    assert admission['timing_exception_authorized'] and admission['all_non_timing_gates_passed']
    assert not admission['timing_target_met'] and not admission['benchmark_acceptance_passed']
    assert admission['strict_offline_gate_sha256']==sha(H/'offline/offline_gate.json')
    audits=load(H/'offline/audit_ledger.json');ledger=load(H/'offline/native_ledger.json')
    assert len(audits)==len(ledger)==53
    assert all(r['exit_code']==0 for r in audits) and all(r['state']=='finished' for r in ledger)
    preflight=load(H/'evidence/physical_preflights01.json')
    assert preflight['passed'] and len(preflight['cases'])==10
    assert all(r['physics_steps']==r['exit_code']==0 for r in preflight['cases'])
    status=load(H/'evidence/physical_batch_status.json')
    assert [r['case_id'] for r in status]==manifest['physical_cases']
    assert all(r['physics_steps']>0 and r['stage']=='closed' for r in status)
    for row in status:
        p=H/'physical_return'/row['case_id']/'execution/physical_launch_once.json'
        assert p.is_file(),row['case_id']
    inv=load(H/'physical_return/return_inventory.json')
    assert inv['execution_manifest_sha256']==sha(H/'evidence/physical_manifest01.json')
    assert inv['physical_attempts']==10 and inv['attempts_per_case']==1
    for rel,digest in inv['analysis_sources'].items():assert sha(H/rel)==digest,rel
    for rel,record in inv['files'].items():assert sha(H/'physical_return'/rel)==record['sha256'],rel
    for name,record in inv['videos'].items():
        p=H/'delivered'/name
        assert p.is_file() and not p.is_symlink() and sha(p)==record['sha256'],name
    decode=load(H/'evidence/local_full_video_decode01.json')
    media=load(H/'evidence/local_media_verification01.json')
    assert decode['passed'] and len(decode['files'])==len(inv['videos'])==10
    assert media['regular_files']==10 and media['visual_samples']==20
    assert not media['visual_review_pending']
    trees=[ET.parse(p).getroot() for p in (H/'native_results').rglob('*.xml')]
    assert len(trees)==20 and sum(int(r.get('tests',0)) for r in trees)==178
    assert all(int(r.get('failures',0))==int(r.get('errors',0))==0 for r in trees)
    summary=load(H/'physical_summary.json');accepted=load(H/'acceptance.json')
    assert summary['formal_attempts']==summary['local_full_videos']==10
    assert accepted['offline_passed']==gate['passed'] and not accepted['overall_passed']
    assert (H/'RESULTS_zh.md').is_file()
    result=dict(passed=True,scope='Evidence and delivery verification, not navigation acceptance',
        overall_navigation_acceptance_passed=False,strict_timing_target_met=False,
        user_authorized_timing_exception=True,unit_executions=178,offline_cases=53,
        independent_audits=53,once_only_physical_cases=10,local_regular_complete_videos=10,
        local_video_bytes=sum(r['bytes'] for r in inv['videos'].values()),
        frozen_native_manifest_sha256=sha(V/'native_manifest.json'),
        frozen_execution_manifest_sha256=sha(H/'evidence/physical_manifest01.json'),
        report_sha256=sha(H/'RESULTS_zh.md'),physics_steps=0)
    (H/'evidence/local_delivery_verification01.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
