"""Verify locally returned observation PNGs against setup/observation_manifest.json.

Closes the archival gate raised as lead-review finding R6: every unique remote
output must be present locally with a matching SHA-256.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def main():
    man = json.loads((ROOT / 'setup' / 'observation_manifest.json').read_text())
    report = {'runs': {}, 'total_expected': 0, 'total_present': 0,
              'total_hash_ok': 0, 'total_missing': 0, 'total_mismatch': 0}
    for run, blk in man.items():
        missing, mismatch, ok = [], [], 0
        entries = blk['observations'] + blk.get('video', [])
        for e in entries:
            p = ROOT / e['path']
            report['total_expected'] += 1
            if not p.exists():
                missing.append(e['path'])
                continue
            report['total_present'] += 1
            if sha256(p) == e['sha256']:
                ok += 1
                report['total_hash_ok'] += 1
            else:
                mismatch.append(e['path'])
        report['runs'][run] = {
            'expected': len(entries), 'hash_verified': ok,
            'missing_count': len(missing), 'mismatch_count': len(mismatch),
            'missing': missing[:20], 'mismatch': mismatch[:20],
            'bytes_expected': blk['observation_bytes'] + sum(v['bytes'] for v in blk.get('video', [])),
        }
        report['total_missing'] += len(missing)
        report['total_mismatch'] += len(mismatch)
    report['archive_gate_closed'] = (report['total_missing'] == 0 and report['total_mismatch'] == 0)
    out = ROOT / 'setup' / 'observation_archive_verification.json'
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'runs'}, indent=2))
    for r, v in report['runs'].items():
        print('%-18s expected=%d verified=%d missing=%d mismatch=%d'
              % (r, v['expected'], v['hash_verified'], v['missing_count'], v['mismatch_count']))
    return 0 if report['archive_gate_closed'] else 1


if __name__ == '__main__':
    sys.exit(main())
