"""Resume full53 after restoring a missing legacy-control mount path.

No planner, evaluator, input, or threshold changes. The interrupted failed
deployment batch is retained in benchmark_failed_binding01, outside this cohort.
"""
from pathlib import Path
import hashlib
import json
import sys
import offline

ROOT = offline.ROOT
MANIFEST = offline.MANIFEST
PRIVATE_PYTHON = offline.PRIVATE_PYTHON
IMAGE = offline.IMAGE
SUPPLEMENT = ROOT / 'migration/runtime_binding02.json'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
native_verify = offline.verify

def verify():
    result = native_verify()
    supplement = json.loads(SUPPLEMENT.read_text())
    assert supplement['original_migration_manifest_sha256'] == sha(offline.MANIFEST)
    for rel, digest in supplement['files'].items():
        assert sha(ROOT / rel) == digest, rel
    return result

if __name__ == '__main__':
    offline.verify = verify
    dict(verify=verify, matrix=offline.matrix)[sys.argv[1]]()
