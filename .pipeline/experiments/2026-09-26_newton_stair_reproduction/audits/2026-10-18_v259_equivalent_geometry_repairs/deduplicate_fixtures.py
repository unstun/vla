"""Byte-verified reversible hardlink deduplication of frozen nav fixtures.

Every logical path and its bytes remain present. Models, trials, videos,
source/install files, active v261 and all IsaacLab locations are excluded.
Restore independent files by copy-to-temp, atomic replace and recorded utime.
"""
from pathlib import Path
import hashlib, json, os, sys, time

BASE = Path('/data/sun/vla_mppi_20261009')
NAMES = ['blocked_feedback_v230', 'callback_failure_v232',
 'command_continuity_v206_20261015', 'cooperative_search_v239',
 'cooperative_search_v240', 'endpoint_connectivity_v244/native',
 'environment_interpolation_v226', 'environment_lattice_v228',
 'environment_lookup_v225', 'environment_score_v224',
 'environment_support_v227', 'event_replan_v212', 'floor_reason_v223',
 'generic_mechanisms_v249/native', 'generic_mechanisms_v250/native',
 'generic_mechanisms_v251/native', 'generic_mechanisms_v253/native',
 'generic_mechanisms_v254/native', 'generic_mechanisms_v256/native',
 'generic_mechanisms_v259/native', 'generic_mechanisms_v260/native',
 'pct_scan_traversability_v221', 'physical_traversability_v247/native',
 'starvation_recovery_v217', 'starvation_recovery_v219',
 'support_height_v229', 'terminal_approach_v238']
OUT = BASE / 'geometry_storage_audit_20261018'
OUT.mkdir(exist_ok=True)
sha = lambda p: hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
if sys.argv[1] == 'inventory':
    groups = {}
    for name in NAMES:
        root = BASE / name / 'fixtures'
        for p in sorted(root.rglob('*')):
            if (not p.is_file() or p.is_symlink() or p.stat().st_size < 1000000
                or p.suffix not in ('.env', '.pct', '.f32', '.support')
                and p.name != 'oracle_poses225.txt'):
                continue
            st = p.stat()
            key = (st.st_size, sha(p), st.st_mode, st.st_uid, st.st_gid)
            groups.setdefault(key, []).append(dict(path=str(p), device=st.st_dev,
                inode=st.st_ino, links=st.st_nlink, mode=st.st_mode,
                uid=st.st_uid, gid=st.st_gid, atime_ns=st.st_atime_ns,
                mtime_ns=st.st_mtime_ns, bytes=st.st_size))
    planned = []
    for (size, digest, *_), rows in groups.items():
        if len(rows) < 2:
            continue
        canonical = rows[0]
        for row in rows[1:]:
            if (row['device'], row['inode']) == (canonical['device'], canonical['inode']):
                continue
            assert row['device'] == canonical['device']
            planned.append(dict(original=row, canonical=canonical['path'], sha256=digest))
    receipt = dict(action='hardlink byte-identical immutable nav fixtures only',
        paths_preserved=True, unique_bytes_deleted=False, plan=planned,
        reclaimable_bytes=sum(r['original']['bytes'] for r in planned),
        excluded=['active v261', 'trials', 'models', 'videos', 'IsaacLab',
                  'source', 'install', 'build', 'unique raw data'])
    (OUT / 'plan.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k:v for k,v in receipt.items() if k != 'plan'}))
elif sys.argv[1] == 'apply':
    assert not (OUT / 'completed.json').exists()
    plan = json.loads((OUT / 'plan.json').read_text())
    records = []
    for entry in plan['plan']:
        p = Path(entry['original']['path']); canonical = Path(entry['canonical'])
        assert sha(p) == sha(canonical) == entry['sha256']
        tmp = p.with_name(p.name + '.verified-link-' + str(os.getpid()))
        assert not tmp.exists()
        os.link(canonical, tmp)
        os.replace(tmp, p)
        assert sha(p) == entry['sha256'] and p.stat().st_ino == canonical.stat().st_ino
        records.append(entry)
        (OUT / 'progress.json').write_text(json.dumps(records, indent=2) + '\n')
    receipt = dict(completed=True, logical_paths_preserved=len(records),
        bytes_reclaimed=sum(e['original']['bytes'] for e in records),
        free_bytes_after=os.statvfs(BASE).f_bavail * os.statvfs(BASE).f_frsize,
        plan_sha256=sha(OUT / 'plan.json'),
        restore='copy each linked path to a temporary independent file, atomic replace, then os.utime with original atime_ns/mtime_ns in plan.json')
    (OUT / 'completed.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
else:
    raise SystemExit('inventory | apply')
