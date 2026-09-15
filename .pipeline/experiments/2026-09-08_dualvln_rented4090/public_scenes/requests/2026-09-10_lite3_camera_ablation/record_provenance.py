"""Record SHA-256 of every lead-authored file of this request, in two forms:
provenance.json (with the baseline YAML identity and the per-condition diff
summary) and authored_files.sha256 (sha256sum -c format, relative to the
experiment root) for the Sync Gate check on the remote copy.

Run from the experiment root:
  python3 public_scenes/requests/2026-09-10_lite3_camera_ablation/record_provenance.py
"""
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REQ = Path(__file__).resolve().parent
REQ_REL = REQ.relative_to(ROOT)

AUTHORED = [
    f'{REQ_REL}/conditions.json', f'{REQ_REL}/make_condition_yamls.py', f'{REQ_REL}/yaml_diffs.json',
    f'{REQ_REL}/preflight_cam.py', f'{REQ_REL}/run_cam_eval.sh', f'{REQ_REL}/run_matrix.sh',
    f'{REQ_REL}/summarise_conditions.py', f'{REQ_REL}/request.json',
    f'{REQ_REL}/OPUS_EXECUTION_PACKAGE.md', f'{REQ_REL}/record_provenance.py',
    'public_scenes/configs/habitat_dual_system_cam_cfg.py',
    'public_scenes/configs/vln_cam_c1_lite3_rig.yaml', 'public_scenes/configs/vln_cam_c2_height_only.yaml',
    'public_scenes/configs/vln_cam_c3_fov_only.yaml', 'public_scenes/configs/vln_cam_c4_raised_mount.yaml',
    'public_scenes/configs/vln_cam_c5_head_level.yaml', 'public_scenes/configs/vln_cam_c6_head_down15.yaml',
    # round 5 (2026-09-11): fused virtual camera
    f'{REQ_REL}/fused_camera.py', f'{REQ_REL}/fused_camera_plugin.py', f'{REQ_REL}/test_fused_camera.py',
    f'{REQ_REL}/make_fused_yamls.py', f'{REQ_REL}/yaml_diffs_fused.json', f'{REQ_REL}/preflight_fused.py',
    'public_scenes/configs/habitat_dual_system_fused_cfg.py',
    'public_scenes/configs/vln_cam_c7_fused_level.yaml', 'public_scenes/configs/vln_cam_c8_fused_level_720.yaml',
    # round 6 (2026-09-11): the same fusion with the virtual camera pitched 9 deg down
    'public_scenes/configs/vln_cam_c9_fused_down9.yaml',
]
BASELINE = ['public_scenes/configs/vln_public_scenes.yaml', 'public_scenes/configs/habitat_dual_system_public_cfg.py',
            'public_scenes/runs/public_eval_v5/inputs.json']


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def main():
    conds = json.loads((REQ / 'conditions.json').read_text())
    diffs = json.loads((REQ / 'yaml_diffs.json').read_text())
    if (REQ / 'yaml_diffs_fused.json').exists():
        diffs.update(json.loads((REQ / 'yaml_diffs_fused.json').read_text()))
    prov = {
        'request_id': conds['request_id'],
        'recorded_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'authored_files_sha256': {f: sha(ROOT / f) for f in AUTHORED},
        'baseline_identity_sha256': {f: sha(ROOT / f) for f in BASELINE},
        'baseline_evaluator_sha256': json.loads((ROOT / BASELINE[2]).read_text())['input_sha256'][
            'internnav/habitat_extensions/vln/habitat_vln_evaluator.py'],
        'yaml_diff_changed_lines': {
            k: [l.rstrip('\n') for l in v.splitlines(True) if (l.startswith('+') or l.startswith('-'))
                and not l.startswith('+++') and not l.startswith('---')]
            for k, v in diffs.items()},
    }
    (REQ / 'provenance.json').write_text(json.dumps(prov, indent=2, sort_keys=True) + '\n')
    lines = [f"{prov['authored_files_sha256'][f]}  {f}" for f in AUTHORED]
    (REQ / 'authored_files.sha256').write_text('\n'.join(lines) + '\n')
    print(json.dumps(prov['authored_files_sha256'], indent=1))
    print('PROVENANCE_WRITTEN', REQ_REL / 'provenance.json', REQ_REL / 'authored_files.sha256')


if __name__ == '__main__':
    main()
