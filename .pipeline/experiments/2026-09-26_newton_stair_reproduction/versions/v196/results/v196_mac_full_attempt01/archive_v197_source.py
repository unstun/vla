"""Archive frozen display source and compact returned evidence, excluding the separate MP4."""
from pathlib import Path
import hashlib
import json
import tarfile

ROOT = Path.cwd()
V = ROOT / '.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v197'
OUT = Path('/private/tmp/vla_stop_audit_20261012/outgoing_archives')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    assert (V/'manifest.json').exists()
    target = OUT / 'v197_source_provenance.tar.gz'
    assert not target.exists()
    selected = [p for p in sorted(V.rglob('*')) if p.is_file() and not p.is_symlink()
                and 'delivered' not in p.relative_to(V).parts
                and '__pycache__' not in p.parts]
    files = {str(Path('v197')/p.relative_to(V)): dict(bytes=p.stat().st_size, sha256=sha(p))
             for p in selected}
    with tarfile.open(target, 'w:gz') as tf:
        for p in selected:
            tf.add(p, arcname=str(Path('v197')/p.relative_to(V)), recursive=False)
    manifest = dict(archive_name=target.name, archive_bytes=target.stat().st_size,
                    archive_sha256=sha(target), files=files,
                    display_manifest_sha256=sha(V/'manifest.json'),
                    quality_sha256=sha(V/'quality.json'),
                    video_archived_separately=True,
                    physical_parent='v196', display_parent='v195', native_implementation='v196',
                    physical_source='v196_mac_full_attempt01')
    (OUT/'v197_source_archive_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (V/'returned/source_archive_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k!='files'}))


if __name__ == '__main__':
    main()
