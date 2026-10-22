"""Local source freeze only after adapter controls; results append separately."""
from pathlib import Path
import hashlib,json,shutil

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert not (HERE/'manifest.json').exists()
    assert (HERE/'cases_manifest.json').is_file()
    files={p.name:sha(p) for p in HERE.iterdir() if p.is_file() and p.name!='manifest.json'}
    snapshot=HERE/'source';snapshot.mkdir(exist_ok=False)
    for name in files:shutil.copy2(HERE/name,snapshot/name)
    value=dict(version='v242',parent='v240',execution_control='v241',frozen=True,
        status='adapter_controls_passed_before_60_scored_fresh_calls',source_files=files,
        snapshot_locations={name:'source/'+name for name in files},
        cases_manifest_sha256=sha(HERE/'cases_manifest.json'),
        parent_manifest_sha256=sha(HERE.parent/'v240/manifest.json'),
        historical_control_manifest_sha256=sha(HERE.parent/'v241/manifest.json'),
        hard_collision_support_m=.35,sensor_period_s=.1,scan_deadline_s=.1,
        claim='Evaluation adapter freeze, not native algorithm change or acceptance')
    (HERE/'manifest.json').write_text(json.dumps(value,indent=2)+'\n')

if __name__=='__main__':main()
