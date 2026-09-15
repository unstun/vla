#!/usr/bin/env python3
"""Classify the uncommitted Aug 18 - Sep 14 backlog into commit groups and local-only bytes.

Read-only on evidence. Writes only under --review (small, committed) and --scratch (bulky lists).

  python3 classify_backlog.py --review <task>/review --scratch <scratchpad>
  python3 classify_backlog.py ... --write-manifests   # also write <root>/LOCAL_ONLY_BYTES.sha256

Rules are in design.md. Any path that is unclassified, or claimed by two groups, is a hard error.
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
TASK = ".trellis/tasks/09-14-commit-backlog-evidence/"
MANIFEST = "LOCAL_ONLY_BYTES.sha256"

DEFERRED = (".playwright-cli/", "output/")

# Local-only by directory: vendored third-party source, execution work copies, third-party scene assets.
LOCAL_DIRS = (
    re.compile(r"^\.pipeline/experiments/2026-08-19_omnivla_original_cuda_gpu40901/vendor-src/(transformers-openvla-oft|dlimp_openvla)/"),
    re.compile(r"^\.pipeline/experiments/2026-09-08_dualvln_rented4090/work/"),
    re.compile(r"^\.pipeline/experiments/2026-09-08_dualvln_rented4090/public_scenes/data/scene_data/"),
    re.compile(r"^\.pipeline/experiments/2026-09-08_tic_vla_dynanav_5070ti/(.+/)?work/"),
)

# Tracked despite a local-only extension: Dr Sun, 2026-09-15 review (authored episode definitions and tiny result arrays).
TRACK_EXCEPTIONS = (
    re.compile(r"^\.pipeline/experiments/2026-09-08_dualvln_rented4090/public_scenes/data/vln_ce/raw_data/public/.+\.json\.gz$"),
    re.compile(r"^\.pipeline/experiments/2026-08-20_tic_vla_orin_pretrained/runs/013_offline_cuda/[^/]+_waypoints\.npy$"),
)

# Local-only by content type, always scoped to one root in .gitignore.
LOCAL_EXT = {
    # video and images
    "mp4", "mov", "avi", "mkv", "webm", "gif", "png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff", "exr",
    # archives
    "gz", "tgz", "bz2", "xz", "zst", "zip", "tar", "7z",
    # arrays and raw buffers
    "npy", "npz", "f64", "f32", "raw", "h5", "hdf5",
    # meshes, scenes, CAD
    "glb", "gltf", "obj", "stl", "usd", "usda", "usdc", "usdz", "navmesh", "ply", "pcd", "step", "stp",
    # audio
    "wav", "aiff", "mp3", "flac",
    # documents, models, packages, recordings
    "pdf", "onnx", "whl", "pyz", "pt", "pth", "ckpt", "bin", "safetensors", "engine", "mcap", "bag", "db3",
    "so", "dylib",
}

ROOT_PATTERNS = (
    re.compile(r"^(\.pipeline/experiments/[^/]+)/"),
    re.compile(r"^(\.pipeline/survey/[^/]+)/"),
    re.compile(r"^(\.pipeline/external_tasks/[^/]+)/"),
    re.compile(r"^(\.pipeline/maintenance/[^/]+)/"),
    re.compile(r"^(\.trellis/tasks/archive/[^/]+/[^/]+)/"),
    re.compile(r"^(\.trellis/tasks/[^/]+)/"),
    re.compile(r"^(references/upstream/[^/]+)/"),
    re.compile(r"^(deploy/[^/]+)/"),
)

# Ordered (group, message, prefixes). A path must match exactly one group.
GROUPS = [
    (1, "chore(trellis): update templates to 0.6.15", (
        ".agents/", ".claude/", ".codex/", ".cursor/", ".trellis/scripts/", ".trellis/.template-hashes.json",
        ".trellis/.version", ".trellis/workflow.md", ".pipeline/maintenance/2026-09-09_trellis_0_6_15/", "AGENTS.md")),
    (2, "chore: path-specific ignores and local-only manifests", (".gitignore",)),
    (3, "docs(omnivla): Aug 18-19 CUDA, edge, receive-only and audit records", (
        ".pipeline/experiments/2026-08-19_", "deploy/omnivla_lite3_receive_only/",
        ".trellis/tasks/08-18-omnivla-original-cuda-gpu40901/", ".trellis/tasks/08-19-",
        ".trellis/tasks/archive/2026-08/08-19-omnivla-edge-orin64-receive-only-smoke/",
        ".pipeline/external_tasks/2026-08-19_omnivla_vla_evidence_audit/",
        "bigmemory/冷区/改动记录/2026-08-19-omnivla-original-lite3-receive-only.md")),
    (4, "docs(tic-vla): Aug 20 Orin reproduction and Active MVP v2 records", (
        ".pipeline/experiments/2026-08-20_", ".trellis/tasks/08-20-tic-vla-orin-upstream-reproduction/",
        "references/upstream/2026-08-20_tic_vla/", ".pipeline/survey/2026-08-20_")),
    (5, "docs: Sep 8-11 TIC-VLA DynaNav, NaVILA and DualVLN trials, incl. camera-ablation runs", (
        ".pipeline/experiments/2026-09-08_", ".trellis/tasks/09-08-", "references/upstream/2026-09-08_",
        ".pipeline/survey/2026-09-08_", ".trellis/spec/backend/")),
    (6, "docs(lightnav): Sep 9 LightNav-0 5070 Ti and 4090 demo records", (
        ".pipeline/experiments/2026-09-09_", ".trellis/tasks/09-09-", "references/upstream/2026-09-09_",
        ".pipeline/survey/2026-09-09_")),
    (7, "docs(navdp): Sep 10 X-NavDP Lite3 trial", (
        ".pipeline/experiments/2026-09-10_x_navdp_lite3_rented4090/", ".trellis/tasks/09-10-navdp-lite3-rented4090/",
        "references/upstream/2026-09-10_navdp_lite3/")),
    (8, "docs(camera): Sep 10-11 camera-study tasks and Sep 10-11 surveys", (
        ".trellis/tasks/09-10-lite3-camera-height-internvla-n1/", ".trellis/tasks/09-10-internvla-n1-camera-ablation-sim/",
        ".pipeline/survey/2026-09-10_", ".pipeline/survey/2026-09-11_habitat_lab_024_sensor_api/")),
    (9, "feat(isaac): InternVLA-N1 Lite3 Isaac loop, Phases A-D", (
        ".pipeline/experiments/2026-09-11_lite3_isaac_v12_vla/", ".trellis/tasks/09-11-internvla-n1-lite3-isaac-sim/",
        "references/upstream/2026-09-11_", "references/upstream/.gitignore",
        ".pipeline/survey/2026-09-11_lite3_isaac_vla_integration/",
        ".pipeline/survey/2026-09-14_")),
    (10, "docs: sync indexes, memory and journal", (
        ".pipeline/experiments/README.md", ".pipeline/literature/index.md", ".pipeline/terminology/terminology.md",
        "bigmemory/热区/", ".trellis/workspace/", ".trellis/spec/harness/project-harness-contract.md", TASK)),
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


def is_local(path):
    if any(p.search(path) for p in TRACK_EXCEPTIONS):
        return False
    if any(p.search(path) for p in LOCAL_DIRS):
        return True
    ext = path.rsplit(".", 1)[-1].lower() if "." in os.path.basename(path) else ""
    return ext in LOCAL_EXT


def group_of(path):
    if os.path.basename(path) == MANIFEST:
        return 2
    hits = [g for g, _, prefixes in GROUPS if any(path == p or path.startswith(p) for p in prefixes)]
    return hits


def sha256(path):
    h = hashlib.sha256()
    with open(os.path.join(REPO, path), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", required=True)
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--write-manifests", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.review, exist_ok=True)
    os.makedirs(args.scratch, exist_ok=True)

    # Candidate set: untracked + modified + staged. The ORIGINAL ignore state is not recoverable once rules are
    # added, so files that only our new rules ignore are re-included below.
    untracked = set(git_z("ls-files", "-z", "--others", "--exclude-standard"))
    ignored_now = set(git_z("ls-files", "-z", "--others", "--ignored", "--exclude-standard"))
    # After .gitignore edits, re-include files an earlier run marked local-only. The scratch list is
    # session-local, so the per-root manifests (durable, tracked after commit 2) are read as well; without
    # either source a re-run would silently report zero local-only files.
    prior = set()
    local_prior = os.path.join(args.scratch, "local_only.txt")
    if os.path.exists(local_prior):
        with open(local_prior, encoding="utf-8") as fh:
            prior |= {l.rstrip("\n") for l in fh if l.strip()}
    for m in git_z("ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", f"*{MANIFEST}"):
        if os.path.basename(m) != MANIFEST or not os.path.exists(os.path.join(REPO, m)):
            continue
        with open(os.path.join(REPO, m), encoding="utf-8") as fh:
            prior |= {os.path.dirname(m) + "/" + l[66:].rstrip("\n") for l in fh if len(l) > 66 and l[64:66] == "  "}
    with open(os.path.join(REPO, ".gitignore"), encoding="utf-8") as fh:
        block_present = "# 2026-09-14 backlog commit" in fh.read()
    if block_present and not prior:
        sys.exit("backlog ignore block exists but no prior local-only list or manifest was found; refusing to "
                 "classify, because the files it ignores would be silently dropped")
    untracked |= prior & ignored_now
    # --no-renames: a staged rename would otherwise list only its destination and drop the source path.
    modified = set(git_z("diff", "-z", "--no-renames", "--name-only"))
    staged = set(git_z("diff", "-z", "--no-renames", "--cached", "--name-only"))
    candidates = sorted(untracked | modified | staged)

    deferred, local, track = [], [], []
    for p in candidates:
        if p.startswith(DEFERRED):
            deferred.append(p)
        elif p in modified or p in staged:
            track.append(p)  # tracked or staged files are never made local-only
        elif os.path.basename(p) == MANIFEST:
            track.append(p)
        elif is_local(p):
            local.append(p)
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
    orphan_local = [p for p in local if root_of(p) is None]
    errors += [f"LOCAL WITHOUT ROOT: {p}" for p in orphan_local]
    if errors:
        print("\n".join(errors[:200]), file=sys.stderr)
        print(f"{len(errors)} classification errors", file=sys.stderr)
        sys.exit(2)

    for g, msg, _ in GROUPS:
        out = os.path.join(args.review, f"group_{g:02d}.txt")
        if not groups[g] and os.path.exists(out) and os.path.getsize(out):
            continue  # already committed: keep the approved list instead of overwriting it with an empty one
        with open(out, "w", encoding="utf-8") as fh:
            fh.write("".join(p + "\n" for p in sorted(groups[g])))
    with open(local_prior, "w", encoding="utf-8") as fh:
        fh.write("".join(p + "\n" for p in local))

    by_root = collections.defaultdict(list)
    for p in local:
        by_root[root_of(p)].append(p)

    size = lambda p: os.path.getsize(os.path.join(REPO, p))
    summary = {"deferred": deferred, "groups": {}, "local_only_roots": {}}
    for g, msg, _ in GROUPS:
        files = groups[g]
        big = sorted(((size(p), p) for p in files if os.path.exists(os.path.join(REPO, p)) and size(p) > 5 << 20), reverse=True)
        tops = collections.Counter("/".join(p.split("/")[:3]) for p in files)
        summary["groups"][g] = {
            "message": msg, "paths": len(files),
            "bytes": sum(size(p) for p in files if os.path.exists(os.path.join(REPO, p))),
            "top_dirs": tops.most_common(8), "over_5mb": [[s, p] for s, p in big],
            "modified_tracked": sorted(p for p in files if p in modified),
            "staged": sum(1 for p in files if p in staged),
        }
    for r, files in sorted(by_root.items()):
        exts = collections.Counter()
        dirs = collections.Counter()
        for p in files:
            d = next((m.group(0) for pat in LOCAL_DIRS for m in [pat.search(p)] if m), None)
            if d:
                dirs[d] += 1
            else:
                exts[p.rsplit(".", 1)[-1]] += 1
        summary["local_only_roots"][r] = {
            "files": len(files), "bytes": sum(size(p) for p in files),
            "dir_rules": dict(dirs), "ext_rules": dict(exts),
        }
    with open(os.path.join(args.review, "classification.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, ensure_ascii=False)

    if args.write_manifests:
        for r, files in sorted(by_root.items()):
            lines = sorted(f"{sha256(p)}  {p[len(r) + 1:]}\n" for p in files)
            lines.sort(key=lambda l: l[66:])
            with open(os.path.join(REPO, r, MANIFEST), "w", encoding="utf-8") as fh:
                fh.write("".join(lines))

    for g, msg, _ in GROUPS:
        s = summary["groups"][g]
        print(f"G{g:02d} {s['paths']:6d} paths {s['bytes'] / 2**20:8.1f} MB  {msg}")
    print(f"local-only: {len(local)} files {sum(size(p) for p in local) / 2**20:.1f} MB in {len(by_root)} roots")
    print(f"deferred: {len(deferred)}")


if __name__ == "__main__":
    main()
