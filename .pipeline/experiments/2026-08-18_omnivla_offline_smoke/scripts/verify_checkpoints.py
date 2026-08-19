#!/usr/bin/env python
"""Verify locally present checkpoint files against CHECKPOINT_MANIFEST.tsv.

Recomputes the hash of every file that exists locally and updates the
`verified` column. Files that are not present locally keep verified=no, which
means "identity recorded from the Hugging Face API at the pinned revision,
bytes not present locally" — never "checked".
Exit 0 if nothing mismatched, 1 otherwise.
"""
import hashlib, os, subprocess, sys

TP = "/Users/sun/tongbu/study/phdproject/vla/third_party/2026-08-18_omnivla_5182600"
P = f"{TP}/checkpoints/CHECKPOINT_MANIFEST.tsv"

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

lines = open(P).read().rstrip("\n").split("\n")
hdr = lines[0].split("\t")
out, ok, bad, absent = [lines[0]], 0, 0, 0
for ln in lines[1:]:
    c = dict(zip(hdr, ln.split("\t")))
    local = os.path.join(TP, c["local_path"])
    if os.path.isfile(local):
        if c["sha256_kind"] == "git-blob-sha1":
            h = subprocess.run(["git", "hash-object", local],
                               capture_output=True, text=True).stdout.strip()
        else:
            # lfs-sha256 (Hugging Face LFS oid) and url-embedded-sha256 (the
            # digest OpenAI puts in the CLIP download URL) are both plain
            # SHA-256 of the file content.
            h = sha256(local)
        if h == c["sha256"]:
            c["verified"] = "yes"; ok += 1
        else:
            c["verified"] = f"MISMATCH:{h}"; bad += 1
            print(f"MISMATCH {c['repo']}/{c['file']}", file=sys.stderr)
    else:
        absent += 1
    out.append("\t".join(c[k] for k in hdr))
open(P, "w").write("\n".join(out) + "\n")
print(f"verified={ok} mismatched={bad} not_present_locally={absent}")
sys.exit(1 if bad else 0)
