"""Re-render the unchanged recording with an existing close-follow camera mode."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import time

assert os.environ['V283_CASE_ID']=='CM07'
os.environ.update(V283_RENDER_ID='03',V283_RENDER_CAMERA='close_body')
import postprocess_case as case
from render_resources import sample


def main():
    assert sample()['passed']
    archive=case.CASEOUT/'display_revision02'
    assert not archive.exists()
    archive.mkdir()
    for path in case.CASEOUT.iterdir():
        if path.is_file() and path.suffix in ('.json','.py'):
            shutil.copy2(path,archive/path.name)
    old=case.RESULTS/'local_video_delivery.json'
    shutil.copy2(old,case.RESULTS/'local_video_delivery_render02.json')
    shutil.copy2(case.RESULTS/'camera_revision.json',case.RESULTS/'camera_revision_render02.json')
    receipt=dict(utc_s=time.time(),case_id=case.CASE,physics_steps=0,
        original_video=json.loads(old.read_text()),old_render='02',new_render='03',
        reason='Near camera removes pillar occlusion; widen FOV to retain full legs.',
        camera_mode='close_body',trail_m=.35,height_m=.50,ahead_m=0.,down_m=.05,
        yaw_time_constant_s=.2,fov_degrees=95.,scene_geometry_changed=False,
        repair_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        native_manifest_sha256=case.sha(case.VERSIONS/'v283/native_manifest.json'),
        execution_manifest_sha256=case.sha(case.VERSIONS/'v283/manifest.json'),
        source_snapshot={str(p.relative_to(case.CASEOUT)):case.sha(p) for p in archive.iterdir()})
    (case.RESULTS/'camera_revision.json').write_text(json.dumps(receipt,indent=2)+'\n')
    case.render()
    print('Camera-only revision complete; no physics rerun',flush=True)


if __name__=='__main__':
    main()
