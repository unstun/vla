"""Publish version-index facts only after physical, display and archive checks pass."""
from pathlib import Path
import difflib
import hashlib
import json

ROOT = Path.cwd()
BASE = ROOT/'.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions'
TASK = Path('/private/tmp/vla_stop_audit_20261012')
RESULTS = BASE/'v196/results/v196_mac_full_attempt01'
DISPLAY = BASE/'v197'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    trial = read(RESULTS/'trial_analysis.json')
    archive = read(RESULTS/'remote_verification.json')
    video = read(DISPLAY/'returned/delivery_verification.json')
    remote_video = read(DISPLAY/'returned/remote_video_verification.json')
    source_archive = read(DISPLAY/'returned/source_archive_verified.json')
    freeze = read(DISPLAY/'returned/freeze_verification.json')
    assert all((trial['full_route_gate_passed'], archive['verified'], video['passed'],
                remote_video['verified'], source_archive['verified'], freeze['passed']))
    rel_video = str((DISPLAY/'delivered/v196_mac_full_attempt01.mp4').relative_to(ROOT))
    data = read(BASE/'current.json')
    scope = ('One newly executed frozen v196 Mac ARM64 CPU Newton / ARM64 Foxy original historical_full '
             'Building attempt after reboot: FINISHED, route_arrived=true, full-route gate and final PD hold passed. '
             'No repeated reliability, sustained 30 Hz, general collision-clearance or real-robot validation.')
    data.update(current='v197', status='frozen_display_v196_mac_full_attempt01_full_route_passed',
                last_validated_trial_version='v196',
                last_validated_condition='One Mac original historical_full Building trial with final PD hold and XYZ/yaw gate; no general reliability acceptance',
                validated_scope=scope, latest_physical_trial_version='v196',
                latest_physical_trial_run='v196_mac_full_attempt01',
                latest_physical_trial_results=str((RESULTS/'RESULTS.md').relative_to(ROOT)),
                latest_display_version='v197',latest_display_source_version='v196',
                latest_display_results=str((DISPLAY/'VISUAL_QA.md').relative_to(ROOT)),
                latest_review_video_provenance=str((DISPLAY/'delivery_return.json').relative_to(ROOT)),
                last_attempted_version='v196',last_attempted_status=scope,
                development_version='v197',development_parent='v196',development_status='frozen_display_verified',
                execution='v196_mac_full_attempt01_finished_full_route_gate_passed_raw_archive_verified_v197_video_verified',
                next_version='v198 uncreated; v196 physical attempt and v197 display are complete and archived.',
                full_building_navigation_validation_scope=scope)
    data['physical_attempts']['v196_mac_full_attempt01']=scope
    data['v196_physical_trial_20261014']={
        'run':trial['run'],'reexecuted_after_reboot':True,'preflight_failures_before_physics':1,
        'physical_attempts_this_resume':1,'terminal_status':trial['terminal_status'],
        'full_route_gate_passed':True,'final_pd_hold':True,
        'navigation_sim_s':trial['navigation_sim_s'],'navigation_wall_s':trial['navigation_wall_s'],
        'actual_rtf':trial['actual_rtf'],'local_planning_successful_wall_hz':trial['local_planning_successful_wall_hz'],
        'controller_wall_hz':trial['controller_wall_hz'],'pct_route_publications':trial['pct_route_publications'],
        'refresh_status':trial['pct_refresh']['refresh_status'],'retained_count':trial['pct_refresh']['retained_count'],
        'old_second_floor_ten_second_stall_observed':False,
        'remote_archive':read(RESULTS/'ARTIFACTS.json')['remote_archive'],
        'archive_sha256':archive['archive_sha256'],'archive_bytes':archive['archive_bytes'],
        'results':str((RESULTS/'RESULTS.md').relative_to(ROOT)),
        'comparison':str((RESULTS/'comparison.json').relative_to(ROOT)),
        'frozen_manifest_sha256':sha(BASE/'v196/manifest.json'),'frozen_sources_unchanged':True,
        'scope':scope}
    data['v197']={
        'parent':'v196','display_parent':'v195','native_implementation':'v196',
        'physical_source':'v196_mac_full_attempt01','video':rel_video,
        'video_sha256':video['video_sha256'],'video_bytes':video['video_bytes'],
        'frames':video['frames'],'duration_s':video['duration_s'],'fps':30,'resolution':[1280,720],
        'physics_steps_executed':0,'full_route_gate_passed':True,'route_arrived':True,'final_pd_hold':True,
        'terminal_frame':video['terminal_frame'],'terminal_trajectory_id':None,
        'remote_sha256_verified':True,'remote_video':remote_video['path'],
        'freeze_verified':True,'source_pairs':freeze['source_pairs'],
        'manifest':'v197/manifest.json','manifest_sha256':sha(DISPLAY/'manifest.json'),
        'quality':'v197/quality.json','quality_sha256':sha(DISPLAY/'quality.json'),
        'source_archive':'v197/returned/source_archive_verified.json',
        'source_archive_sha256':source_archive['archive_sha256'],
        'claim_scope':'Display of one passed v196 capture; zero new physics or reliability evidence.'}
    (BASE/'current.json').write_text(json.dumps(data,indent=2)+'\n')
    text=(BASE/'README.md').read_text()
    text=text.replace('**run_mac_full.py was not executed; no navigation goal or physics advance.**',
                      '**At component freeze, run_mac_full.py had not been executed; no navigation goal or physics advance had occurred.**')
    text=text.replace('This is component and graph qualification only. v194 remains the latest physical\n'
                      'trial and v195 remains its display review. The observation-age expansion and\n'
                      'physical effects of the repairs still require a separately authorized run.',
                      'That historical record covers component and graph qualification only. At that\n'
                      'point, v194 was the latest physical trial and v195 its display review. The\n'
                      'authorized v196 execution and v197 display are recorded below.')
    text=text.replace('physical trial and its single-trial acceptance boundary is unchanged.',
                      'physical trial in that historical record. The later v196/v197 delivery is recorded below.')
    text+='''

## v196 reboot recovery, physical trial and v197 delivery (2026-10-14)

The execution workspace was restored from all 11 pinned environment archives.
The native overlay was rebuilt and passed 93 colcon test entries with zero
errors, failures or skips. An initial receipt mismatch stopped before physics;
the failure is retained. Every one of 3,650 pinned source/install files was
verified after restoring the semantically identical source-identity JSON's
original formatting. The original runtime receipt then passed the unchanged
gate. Fresh build/test evidence remains separate. Frozen v196 files are unchanged.

The new **v196_mac_full_attempt01 passed the original full-route gate**:
FINISHED, route arrival, final PD hold and held XYZ/yaw all passed. The erased
pre-reboot capture is not combined with this result. Navigation took
115.561238 simulation seconds / 118.348344 wall seconds (RTF 0.976450), versus
126.507451 / 126.540360 for v194. Successful planning measured 24.630678 wall Hz;
controller output measured 29.935137 wall Hz. The old 10.194397-second
second-floor stall did not recur within its 1 m neighborhood. Direct-command
stops fell from 17 to 9, while emergency entries increased from 9 to 12.
PCT published 102 routes; final refresh_status=terminal_approach, retained_count=3.
These are individual captures, not repeated reliability or a causal speedup test.

See the [complete trial analysis](v196/results/v196_mac_full_attempt01/RESULTS.md),
[four-version comparison](v196/results/v196_mac_full_attempt01/comparison.json),
and [verified trial/overlay archives](v196/results/v196_mac_full_attempt01/ARTIFACTS.json).
The trial archive contains 287 regular files, one symlink and 1,160 verified
raw ZIP members, at gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v196_20261014/.

**v197 is the frozen display version**, with parent/native implementation v196
and display parent v195. The [regular MP4](v197/delivered/v196_mac_full_attempt01.mp4)
contains 3,880 frames at 1280x720/30 FPS (129.333333 seconds), from actual physics
time 0.0 through the final 126.582062-second held state. All pauses remain;
startup uses recorded simulation time and navigation uses original wall time.
All 14 overlay/timeline tests, every causal frame, full decode, source identity,
nine decoded visual samples, remote video SHA and display freeze checks passed.
No physics steps were executed during rendering. See [visual QA](v197/VISUAL_QA.md),
[delivery provenance](v197/delivery_return.json), and
[source archive verification](v197/returned/source_archive_verified.json).
'''
    (BASE/'README.md').write_text(text)
    patch=''
    for name in ('README.md','current.json'):
        before=TASK/'evidence/indexes_before'/name
        patch+=''.join(difflib.unified_diff(before.read_text().splitlines(True),(BASE/name).read_text().splitlines(True),
                                          fromfile='before/'+name,tofile='after/'+name))
    (RESULTS/'version_index_changes.patch').write_text(patch)
    report=(RESULTS/'RESULTS.md').read_text().split('## Artifacts and reproducibility')[0]
    report+='''## Recovery and preserved identity

All 11 environment archives passed the hashes in frozen v196/verification/environment_archives.json. The ARM64 Foxy rebuild passed 93 colcon entries, zero errors/failures/skips, generated profiles and both terminal probes. The first launch was rejected before physics because a fresh test receipt differs from the frozen receipt. Its failed preflight and fresh rebuild evidence were preserved. Restoring the original formatting of semantically identical source_identity.json made all 3,650 pinned source/install file hashes match. The pinned receipt then passed the original runtime gate. No frozen v196 code, configuration, manifest, quality or verification file was changed.

'''
    report+=f'''## Verified archives

- Trial: gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v196_20261014/v196_mac_full_attempt01.tar
- Trial bytes: {archive['archive_bytes']}; SHA-256: `{archive['archive_sha256']}`.
- Remote verification: 287 files, one symlink and all 1,160 raw ZIP members.
- Native overlay: recovery_v196.tar in the same directory; SHA-256 `{read(RESULTS/'overlay_archive_manifest.json')['archive_sha256']}`.
- Restoration/build/preflight evidence: resume_evidence.tar in the same directory.
- Frozen display source/provenance: v197_source_provenance.tar.gz; SHA-256 `{source_archive['archive_sha256']}`.
- Local compact provenance: {RESULTS/'ARTIFACTS.json'}.

## Completed v197 video

Video: [{rel_video}]({DISPLAY/'delivered/v196_mac_full_attempt01.mp4'})

The regular MP4 is {video['video_bytes']} bytes, {video['frames']} frames, 1280x720, 30 FPS and {video['duration_s']:.9f} seconds. SHA-256: `{video['video_sha256']}`. The remote MP4 at gpu5070ti:{remote_video['path']} has identical bytes. Startup begins at actual zero physics steps; navigation uses original wall time at 1:1; all pauses and the final PD hold are retained. All 14 unit tests, causal timeline/curve checks, full decoding and nine manually inspected decoded samples passed. The final frame says `{video['terminal_frame']}` and shows no expired cyan spline. Rendering executed zero physics steps.

Visual QA: {DISPLAY/'VISUAL_QA.md'}

Contact sheet: {DISPLAY/'returned/visual_qa/contact_sheet.jpg'}

Frozen v196 verification passed after execution and rendering: 5,019 source pairs and 618 runtime inputs. v197 freeze and verify passed with {freeze['source_pairs']} source pairs. The version index now points to v197 display and v196 as the latest physical trial. The result remains one declared simulator trial, not repeated reliability or real-robot validation.
'''
    (TASK/'codex_v196_trial_and_video.md').write_text(report)
    (RESULTS/'RESUME_SUMMARY.md').write_text(report)
    artifacts=read(RESULTS/'ARTIFACTS.json')
    artifacts.update(review_video_created=True,display_version='v197',video=rel_video,
                     video_sha256=video['video_sha256'],video_remote=remote_video['path'],
                     summary=str((RESULTS/'RESUME_SUMMARY.md').relative_to(ROOT)))
    (RESULTS/'ARTIFACTS.json').write_text(json.dumps(artifacts,indent=2)+'\n')
    print('VERSION_INDEXES_AND_COMPLETE_SUMMARY_WRITTEN')


if __name__ == '__main__':
    main()
