"""Record exact bytes excluded by this experiment's narrow local-only rules."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parents[1]
PREFIXES = ("runtime", "runs/go2_video_v2/frames", "runs/go2_video_v3/frames", "runs/lite3_video_v2/frames")


def main():
    records = []
    for prefix in PREFIXES:
        for path in sorted((BASE / prefix).rglob("*")):
            if path.is_symlink():
                records.append({"path": str(path.relative_to(BASE)), "symlink": str(path.readlink())})
            elif path.is_file():
                with path.open("rb") as f:
                    sha = hashlib.file_digest(f, "sha256").hexdigest()
                records.append({"path": str(path.relative_to(BASE)), "bytes": path.stat().st_size, "sha256": sha})
    out = {"created_utc": datetime.now(timezone.utc).isoformat(), "storage_root": str(BASE),
           "scope": list(PREFIXES), "review": "Main-session scope review; only local runtime and exact raw-frame directories.",
           "reconstruction": "README.md and setup/requirements_lite3.lock; raw frame attempts retained locally.",
           "total_file_bytes_including_hardlink_duplicates": sum(r.get("bytes", 0) for r in records),
           "files": records}
    (BASE / "setup/LOCAL_ONLY_BYTES.json").write_text(json.dumps(out, indent=2) + "\n")
    # Keep third-party attribution available even without the ignored runtime.
    root = BASE / "runtime/assets/newton-assets_unitree_go2_ed136937_f8fb7abc"
    licenses = BASE / "setup/licenses"
    licenses.mkdir(exist_ok=True)
    for name, source in (("newton_assets_LICENSE", root / "LICENSE"),
                         ("go2_LICENSE", root / "unitree_go2/LICENSE"),
                         ("go2_README.md", root / "unitree_go2/README.md"),
                         ("go2_policy_LICENSE", root / "unitree_go2/rl_policies/LICENSE")):
        shutil.copyfile(source, licenses / name)
    print(json.dumps({"entries": len(records), "bytes_with_hardlink_duplicates": out["total_file_bytes_including_hardlink_duplicates"],
                      "free_gib": shutil.disk_usage(BASE).free / 1024**3}))


if __name__ == "__main__":
    main()
