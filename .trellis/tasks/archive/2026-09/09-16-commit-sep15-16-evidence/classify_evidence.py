#!/usr/bin/env python3
"""Classify the uncommitted Sep 15-16 work into commit groups and local-only bytes.

Adapted from archive/2026-09/09-14-commit-backlog-evidence/classify_backlog.py. Read-only on evidence.
Writes only under --review (small, committed) and --scratch (session-local lists).

  python3 classify_evidence.py --review <task>/review --scratch <scratchpad>
  python3 classify_evidence.py ... --write-manifests   # also write <root>/LOCAL_ONLY_BYTES.sha256

Any path that is unclassified, or claimed by two groups, is a hard error.
"""
import argparse
import collections
import hashlib
import json
import os
import re
import subprocess
import sys

REPO = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
TASK = ".trellis/tasks/09-16-commit-sep15-16-evidence/"
MANIFEST = "LOCAL_ONLY_BYTES.sha256"
BLOCK_MARK = "# 2026-09-16 evidence commit"

# Dr Sun, 2026-09-16: left out of this commit.
DEFERRED = (".playwright-cli/", "output/", "docs/research/papers/pdf/")

HARNESS = r"^\.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/"

# Local-only by directory: per-run copies of the materialized PCT runtime (native libraries plus pinned Python
# source). Identity: p2b_execution/pct_runtime_manifest.json and each run's source_env_hashes.json.
LOCAL_DIRS = (
    re.compile(HARNESS + r"(.+/)?pct_runtime/"),
)

# Local-only text over 5 MB: point-cloud and journal dumps from the HarnessVLN runs (decision C1 in prd.md).
BIG_TEXT_BYTES = 5 << 20
BIG_TEXT_ROOTS = (re.compile(HARNESS),)

# New D.1 files that the existing Isaac block (.gitignore, 2026-09-11_lite3_isaac_v12_vla) already ignores. They
# get manifest lines like any other local-only file.
ADOPT_IGNORED = (
    re.compile(r"^\.pipeline/experiments/2026-09-11_lite3_isaac_v12_vla/(analysis/phase_d1b_|runs/phase_d1b_|setup/phase_d1_)"),
)

# Local-only by content type, always scoped to one root in .gitignore.
LOCAL_EXT = {
    # video and images
    "mp4", "mov", "avi", "mkv", "webm", "gif", "png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff", "exr",
    # archives
    "gz", "tgz", "bz2", "xz", "zst", "zip", "tar", "7z",
    # arrays, raw buffers and pickles
    "npy", "npz", "f64", "f32", "raw", "h5", "hdf5", "bin", "pickle", "pkl",
    # meshes, scenes, CAD
    "glb", "gltf", "obj", "stl", "usd", "usda", "usdc", "usdz", "navmesh", "ply", "pcd", "step", "stp",
    # audio
    "wav", "aiff", "mp3", "flac",
    # documents, models, packages, recordings, native libraries
    "pdf", "onnx", "whl", "pyz", "pt", "pth", "ckpt", "safetensors", "engine", "mcap", "bag", "db3",
    "so", "dylib",
}

ROOT_PATTERNS = (
    re.compile(r"^(\.pipeline/experiments/[^/]+)/"),
    re.compile(r"^(\.pipeline/survey/[^/]+)/"),
    re.compile(r"^(\.trellis/tasks/[^/]+)/"),
    re.compile(r"^(references/upstream/[^/]+)/"),
)

# Ordered (group, message, prefixes). A path must match exactly one group.
GROUPS = [
    (1, "chore: path-specific ignores and local-only manifests", (".gitignore",)),
    (2, "feat(isaac): D.1 InteriorAgent kujiale_0031 fetch and D.1b stage audit", (
        ".pipeline/experiments/2026-09-11_lite3_isaac_v12_vla/", ".trellis/tasks/09-11-internvla-n1-lite3-isaac-sim/")),
    (3, "feat(harnessvln): Pi+Cortex runtime, native PCT/SCAN Isaac pilots and surveys", (
        ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/", ".trellis/tasks/09-16-emos-harnessvln-reimplementation/",
        "references/upstream/2026-09-16_pi_cortex_harnessvln/", "references/upstream/2026-09-16_lite3_isaac_harness_backend/",
        ".pipeline/survey/2026-09-16_embodied_harness_alternatives", ".pipeline/survey/2026-09-16_harness_vln_open_source")),
    (4, "docs(mip): Sep 16 MIP 5070 Ti preparation and first DeepSeek episode", (
        ".pipeline/experiments/2026-09-16_mip_5070ti/", ".trellis/tasks/09-16-mip-5070ti-reproduction/",
        "references/upstream/2026-09-16_mip/")),
    (5, "docs: sync literature index, memory and journal", (
        ".pipeline/experiments/README.md", ".pipeline/literature/index.md", "bigmemory/热区/", "bigmemory/冷区/",
        ".trellis/workspace/", TASK)),
]


def git_z(*args):
    out = subprocess.run(["git", *args], capture_output=True, check=True, cwd=REPO).stdout
    return [p.decode("utf-8") for p in out.split(b"\0") if p]


def root_of(path):
    for pat in ROOT_PATTERNS:
        m = pat.match(path)
        if m:
            return m.group(1)
    return None


def ext_of(path):
    base = os.path.basename(path)
    if re.search(r"\.so(\.\d+)+$", base):  # versioned shared libraries, e.g. libgtsam.so.4
        return "so"
    return base.rsplit(".", 1)[-1].lower() if "." in base else ""


def size(path):
    return os.path.getsize(os.path.join(REPO, path))


def local_reason(path):
    for pat in LOCAL_DIRS:
        m = pat.search(path)
        if m:
            return "dir:" + m.group(0)
    if ext_of(path) in LOCAL_EXT:
        return "ext:" + ext_of(path)
    if any(p.search(path) for p in BIG_TEXT_ROOTS) and size(path) > BIG_TEXT_BYTES:
        return "big:" + os.path.basename(path)
    return None


def group_of(path):
    if os.path.basename(path) == MANIFEST:
        return 1
    return [g for g, _, prefixes in GROUPS if any(path == p or path.startswith(p) for p in prefixes)]


def sha256(path):
    h = hashlib.sha256()
    with open(os.path.join(REPO, path), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_manifest(root, text):
    return {root + "/" + l[66:]: l + "\n" for l in text.splitlines() if len(l) > 66 and l[64:66] == "  "}


def manifest_entries(manifest_path):
    with open(os.path.join(REPO, manifest_path), encoding="utf-8") as fh:
        return set(parse_manifest(os.path.dirname(manifest_path), fh.read()))


def committed_manifest_entries(manifest_path):
    """Entries in the HEAD version of a manifest: local-only files an earlier commit already recorded."""
    r = subprocess.run(["git", "show", f"HEAD:{manifest_path}"], capture_output=True, cwd=REPO)
    return set(parse_manifest(os.path.dirname(manifest_path), r.stdout.decode("utf-8"))) if r.returncode == 0 else set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", required=True)
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--write-manifests", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.review, exist_ok=True)
    os.makedirs(args.scratch, exist_ok=True)

    untracked = set(git_z("ls-files", "-z", "--others", "--exclude-standard"))
    ignored_now = set(git_z("ls-files", "-z", "--others", "--ignored", "--exclude-standard"))
    # After the .gitignore edit, re-include files an earlier run marked local-only (scratch list or manifests).
    prior = set()
    local_prior = os.path.join(args.scratch, "local_only.txt")
    if os.path.exists(local_prior):
        with open(local_prior, encoding="utf-8") as fh:
            prior |= {l.rstrip("\n") for l in fh if l.strip()}
    committed_local = set()
    for m in git_z("ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", f"*{MANIFEST}"):
        if os.path.basename(m) == MANIFEST and os.path.exists(os.path.join(REPO, m)):
            done = committed_manifest_entries(m)
            committed_local |= done
            prior |= manifest_entries(m) - done
    prior -= committed_local
    with open(os.path.join(REPO, ".gitignore"), encoding="utf-8") as fh:
        block_present = BLOCK_MARK in fh.read()
    if block_present and not os.path.exists(local_prior):
        sys.exit("evidence ignore block exists but the scratch local-only list is missing; refusing to classify, "
                 "because files the new block ignores would be silently dropped")
    untracked |= {p for p in prior & ignored_now if os.path.exists(os.path.join(REPO, p))}
    adopted = {p for p in ignored_now if any(a.search(p) for a in ADOPT_IGNORED)
               and "/__pycache__/" not in p and not p.endswith(".pyc")}
    untracked |= adopted
    modified = set(git_z("diff", "-z", "--no-renames", "--name-only"))
    staged = set(git_z("diff", "-z", "--no-renames", "--cached", "--name-only"))
    if staged - modified - untracked and not block_present:
        print(f"note: {len(staged)} staged paths present", file=sys.stderr)
    candidates = sorted(untracked | modified | staged)

    deferred, local, track = [], [], []
    reasons = {}
    for p in candidates:
        if p.startswith(DEFERRED):
            deferred.append(p)
        elif p in modified or p in staged or os.path.basename(p) == MANIFEST:
            track.append(p)
        else:
            r = local_reason(p) or ("adopted:existing rule" if p in adopted else None)
            if r:
                local.append(p)
                reasons[p] = r
            else:
                track.append(p)

    errors = []
    groups = collections.defaultdict(list)
    for p in track:
        g = group_of(p)
        if isinstance(g, int):
            groups[g].append(p)
        elif len(g) == 1:
            groups[g[0]].append(p)
        else:
            errors.append(f"{'UNCLAIMED' if not g else 'MULTI ' + str(g)}: {p}")
    errors += [f"LOCAL WITHOUT ROOT: {p}" for p in local if root_of(p) is None]
    if errors:
        print("\n".join(errors[:200]), file=sys.stderr)
        sys.exit(f"{len(errors)} classification errors")

    for g, msg, _ in GROUPS:
        out = os.path.join(args.review, f"group_{g:02d}.txt")
        if not groups[g] and os.path.exists(out) and os.path.getsize(out):
            continue  # already committed: keep the approved list
        with open(out, "w", encoding="utf-8") as fh:
            fh.write("".join(p + "\n" for p in sorted(groups[g])))
    with open(local_prior, "w", encoding="utf-8") as fh:
        fh.write("".join(p + "\n" for p in local))

    # Files the EXISTING rules already ignore inside touched roots but that no manifest lists yet
    # (e.g. new D.1b figures under an older extension rule). Nested .gitignore files are reported separately.
    touched_roots = {root_of(p) for p in candidates if root_of(p)}
    manifested = set()
    for r in touched_roots:
        mp = os.path.join(r, MANIFEST)
        if os.path.exists(os.path.join(REPO, mp)):
            manifested |= manifest_entries(mp)
    unlisted = collections.defaultdict(list)
    for p in ignored_now - prior - adopted:
        r = root_of(p)
        if r in touched_roots and p not in manifested and not p.endswith((".pyc", ".DS_Store")) \
                and "/__pycache__/" not in p:
            unlisted[r].append(p)

    by_root = collections.defaultdict(list)
    for p in local:
        by_root[root_of(p)].append(p)

    summary = {"deferred": deferred, "groups": {}, "local_only_roots": {}, "ignored_not_manifested": {}}
    for g, msg, _ in GROUPS:
        files = groups[g]
        big = sorted(((size(p), p) for p in files if size(p) > 5 << 20), reverse=True)
        tops = collections.Counter("/".join(p.split("/")[:4]) for p in files)
        summary["groups"][g] = {
            "message": msg, "paths": len(files), "bytes": sum(size(p) for p in files),
            "top_dirs": tops.most_common(10), "over_5mb": [[s, p] for s, p in big],
            "modified_tracked": sorted(p for p in files if p in modified),
            "staged": sum(1 for p in files if p in staged),
        }
    for r, files in sorted(by_root.items()):
        rules = collections.Counter(reasons[p].split(":", 1)[0] + ":" + (
            reasons[p].split(":", 1)[1] if not reasons[p].startswith("big:") else reasons[p][4:]) for p in files)
        summary["local_only_roots"][r] = {
            "files": len(files), "bytes": sum(size(p) for p in files), "rules": dict(rules.most_common()),
        }
    for r, files in sorted(unlisted.items()):
        top = collections.Counter("/".join(p[len(r) + 1:].split("/")[:3]) for p in files)
        summary["ignored_not_manifested"][r] = {
            "files": len(files), "bytes": sum(size(p) for p in files), "top": top.most_common(12),
        }
    with open(os.path.join(args.review, "classification.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(args.scratch, "ignored_not_manifested.txt"), "w", encoding="utf-8") as fh:
        fh.write("".join(p + "\n" for r in sorted(unlisted) for p in sorted(unlisted[r])))

    if args.write_manifests:
        for r, files in sorted(by_root.items()):
            mp = os.path.join(REPO, r, MANIFEST)
            lines = {}
            if os.path.exists(mp):  # an older manifest's lines are kept verbatim
                with open(mp, encoding="utf-8") as fh:
                    lines = parse_manifest(r, fh.read())
            for p in files:
                if p not in lines:
                    lines[p] = f"{sha256(p)}  {p[len(r) + 1:]}\n"
            with open(mp, "w", encoding="utf-8") as fh:
                fh.write("".join(lines[k] for k in sorted(lines, key=lambda k: k[len(r) + 1:])))

    for g, msg, _ in GROUPS:
        s = summary["groups"][g]
        print(f"G{g:02d} {s['paths']:6d} paths {s['bytes'] / 2**20:8.1f} MB  {msg}")
    print(f"local-only: {len(local)} files {sum(size(p) for p in local) / 2**20:.1f} MB in {len(by_root)} roots")
    for r, v in summary["local_only_roots"].items():
        print(f"  {r}: {v['files']} files {v['bytes'] / 2**20:.1f} MB")
    print(f"deferred: {len(deferred)}")
    for r, v in summary["ignored_not_manifested"].items():
        print(f"already ignored, not in a manifest: {r}: {v['files']} files {v['bytes'] / 2**20:.1f} MB {v['top'][:6]}")


if __name__ == "__main__":
    main()
