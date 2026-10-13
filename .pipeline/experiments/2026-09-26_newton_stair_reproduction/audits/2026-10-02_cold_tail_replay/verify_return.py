"""Verify compact returned evidence against remote and frozen source manifests."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=HERE/'attempt01'
    remote=json.loads((out/'remote_artifacts.json').read_text())
    identity=json.loads((out/'source_identity.json').read_text())
    frozen=json.loads((BASE/'versions/v50/manifest.json').read_text())
    assert identity['native_sources']==frozen['native_source_sha256']
    for name,digest in identity['audit_sources'].items(): assert sha(HERE/name)==digest,name
    files=[p for p in out.rglob('*') if p.is_file() and p.name!='remote_artifacts.json']
    for p in files:
        record=remote['files'][str(p.relative_to(out))]
        assert p.stat().st_size==record['bytes'] and sha(p)==record['sha256'],p
    result=json.loads((out/'result.json').read_text())
    assert result['determinism_passed'] and result['native_source_unchanged']
    lines=(BASE/'runs/v50_realtime_trial01/scan.log').read_text().splitlines()
    cases=sorted(json.loads((HERE/'cases.json').read_text()),key=lambda x:x['start_wall_s'])
    seeds=[]
    for row,diag in zip(cases,result['diagnostics']):
        captured=next(json.loads(s.split('spline_seed_capture ',1)[1]) for s in lines[row['start_line']-1:row['end_line']] if 'spline_seed_capture ' in s)
        digest=hashlib.sha256(json.dumps(captured,sort_keys=True).encode()).hexdigest()
        assert digest==diag['first_seed']['sha256']
        seeds.append({'simulation_s':row['ros_s'],'seed_sha256':digest,'matches_original_first_seed':True})
    check={'native_source_files':len(identity['native_sources']), 'returned_files_checked':len(files),
           'returned_bytes_including_locator':sum(p.stat().st_size for p in out.rglob('*') if p.is_file()),
           'original_seed_matches':seeds,'all_checks_passed':True}
    (HERE/'verification.json').write_text(json.dumps(check,indent=2)+'\n')
    print(json.dumps(check,indent=2))
if __name__=='__main__': main()
