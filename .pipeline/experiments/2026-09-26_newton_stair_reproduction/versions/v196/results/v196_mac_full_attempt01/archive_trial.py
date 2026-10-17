"""Create a byte-indexed closed-trial archive and a rebuilt overlay archive."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tarfile

ROOT = Path.cwd()
VERSION = ROOT / '.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v196'
TASK = Path('/private/tmp/vla_stop_audit_20261012')
RUN = 'v196_mac_full_attempt01'
OUT = VERSION / 'results' / RUN
ARCHIVES = TASK / 'outgoing_archives'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def bundle(directory, target):
    assert not target.exists(), target
    files, links = {}, {}
    for p in sorted(directory.rglob('*')):
        name = str(Path(directory.name) / p.relative_to(directory))
        if p.is_symlink():
            links[name] = str(p.readlink())
        elif p.is_file():
            files[name] = dict(sha256=sha(p), bytes=p.stat().st_size)
    with tarfile.open(target, 'w', format=tarfile.PAX_FORMAT, dereference=False) as tf:
        tf.add(directory, arcname=directory.name)
    return dict(archive_name=target.name, archive_bytes=target.stat().st_size,
                archive_sha256=sha(target), files=files, symlinks=links)


def main():
    ARCHIVES.mkdir(exist_ok=True)
    analysis = json.loads((OUT / 'trial_analysis.json').read_text())
    execution = json.loads((OUT / 'execution.json').read_text())
    assert execution['passed']
    manifest = dict(schema='v196-closed-trial-archive-v1', run=RUN,
                    **bundle(TASK / RUN, ARCHIVES / (RUN + '.tar')),
                    terminal_status=analysis['terminal_status'], route_arrived=analysis['route_arrived'],
                    full_route_gate_passed=analysis['full_route_gate_passed'],
                    full_route_verification_sha256=sha(OUT / 'full_route_verification.json'))
    write(OUT / 'trial_archive_manifest.json', manifest)
    write(ARCHIVES / 'trial_archive_manifest.json', manifest)
    shutil.copyfile(OUT / 'full_route_verification.json', ARCHIVES / 'full_route_verification.json')
    verifier = VERSION.parent / 'v194/results/v194_mac_full_attempt01/verify_archive.py'
    shutil.copyfile(verifier, OUT / 'verify_archive.py')
    shutil.copyfile(verifier, ARCHIVES / 'verify_archive.py')
    overlay = bundle(TASK / 'recovery_v196', ARCHIVES / 'recovery_v196.tar')
    overlay.update(schema='v196-rebuilt-overlay-v1', install_overlay_included=True,
                   source_identity_sha256=sha(TASK / 'recovery_v196/source_identity.json'),
                   native_receipt_sha256=sha(TASK / 'evidence/v196_native_receipt.json'),
                   image_id=(TASK / 'evidence/image_id.txt').read_text().strip())
    write(OUT / 'overlay_archive_manifest.json', overlay)
    write(ARCHIVES / 'overlay_archive_manifest.json', overlay)
    # Archive current task evidence, including the exact restoration/build request,
    # build log, fresh receipt and execution provenance, separately from the trial.
    evidence = bundle(TASK / 'evidence', ARCHIVES / 'resume_evidence.tar')
    write(OUT / 'resume_evidence_archive_manifest.json', evidence)
    write(ARCHIVES / 'resume_evidence_archive_manifest.json', evidence)
    print(json.dumps({k: manifest[k] for k in ('archive_bytes','archive_sha256')}))
    print(json.dumps({'overlay_bytes':overlay['archive_bytes'],'overlay_sha256':overlay['archive_sha256']}))


if __name__ == '__main__':
    main()
