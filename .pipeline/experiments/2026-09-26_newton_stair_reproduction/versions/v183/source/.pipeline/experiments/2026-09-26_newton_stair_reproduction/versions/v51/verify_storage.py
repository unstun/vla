"""Recheck completed maintenance against original hashes and archive members."""
import collections
import json
import os
from pathlib import Path
import shutil
import subprocess
import artifacts as a


def main():
    operations=[json.loads(s) for s in (a.AUDIT/'operations.jsonl').read_text().splitlines()]
    done=[r for r in operations if r.get('status')=='completed']
    frames=[r for r in done if r.get('kind')=='prune_frames']
    logs=[r for r in done if r.get('kind')=='compress_log']
    packs=[r for r in done if r.get('kind')=='pack_raw' and not r['run'].startswith('v51_')]
    for row in logs:
        p=a.BASE/row['path'];run=a.BASE/'runs'/p.relative_to(a.BASE/'runs').parts[0]
        if p.exists():assert a.digest(p)==row['sha256']
        else:
            receipt=json.loads((run/'raw_capture_manifest.json').read_text())
            assert receipt['members'][str(p.relative_to(run))]['sha256']==row['sha256']
    verified=[]
    for row in packs:
        receipt=a.archive_members(a.BASE/'runs'/row['run'])
        verified.append(dict(run=row['run'],members=len(receipt['members']),archive_bytes=receipt['archive_bytes']))
    for row in frames:
        run=a.BASE/'runs'/row['run'];r=json.loads((run/'result.json').read_text())
        assert a.digest(run/Path(r['video']).name)==row['video_sha256']
        assert a.digest(run/'frames.json')==row['original_frames_manifest_sha256']
        assert a.digest(a.BASE/'runs'/r['source_run']/'video_states.json')==row['source_states_sha256']
        assert not (run/'frames').exists()
        manifest=json.loads((run/'frames.json').read_text())
        for i in row['retained_sample_indices']:
            assert a.digest(run/'frame_samples'/Path(manifest[i]['file']).name)==manifest[i]['sha256']
    root=a.BASE.parents[2]
    manifest=json.loads((a.BASE/'versions/v49/trials/attempt02/return_manifest.json').read_text())
    receipt=json.loads((a.BASE/'runs/v49_realtime_trial02/raw_capture_manifest.json').read_text())
    for name,row in manifest.items():
        p=root/name
        if p.exists():assert a.digest(p)==row['sha256'],name
        else:assert receipt['members'][str(p.relative_to(a.BASE/'runs/v49_realtime_trial02'))]['sha256']==row['sha256'],name
    counts=collections.Counter();logical=collections.Counter();allocated=collections.Counter()
    for directory,_,files in os.walk(a.BASE/'runs'):
        for name in files:
            p=Path(directory)/name;s=p.stat()
            counts[p.suffix]+=1;logical[p.suffix]+=s.st_size;allocated[p.suffix]+=s.st_blocks*512
    summary=dict(pruned_render_runs=len(frames),png_frames_removed=sum(x['frame_count'] for x in frames),
        frame_allocated_bytes_reclaimed=sum(x['allocated_bytes']-x['retained_sample_bytes'] for x in frames),
        compressed_logs=len(logs),log_allocated_bytes_reclaimed=sum(x['allocated_before']-x['allocated_after'] for x in logs),
        archived_runs=verified,archive_additional_allocated_bytes_reclaimed=sum(x['allocated_before']-x['allocated_after'] for x in packs),
        archived_original_v49_files_verified=len(manifest),compressed_log_hashes_verified=len(logs),
        file_counts_after=dict(counts),logical_bytes_after=dict(logical),allocated_bytes_after=dict(allocated),
        disk_free_bytes_now=shutil.disk_usage(a.BASE).free,df_now=subprocess.check_output(['df','-k',str(a.BASE)],text=True),
        claim='Allocated-file accounting differs from filesystem free space; original content hashes and preserved video/state identities verified.')
    a.atomic_json(a.AUDIT/'verified_summary.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('file_counts_after','logical_bytes_after','allocated_bytes_after','df_now')},indent=2))


if __name__=='__main__':main()
