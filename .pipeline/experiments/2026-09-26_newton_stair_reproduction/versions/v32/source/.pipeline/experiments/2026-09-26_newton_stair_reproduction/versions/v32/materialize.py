"""Apply v32's one worker change after verifying the frozen parent v31.

v32 keeps the Newton worker's retained objects out of automatic full cyclic garbage collections: once
before the control loop and again after every 50th control step (1 s of simulation), gc.collect() reclaims
the garbage created since the last freeze and gc.freeze() then moves the survivors to the permanent
generation. Basis: audits/2026-09-29_wall_clock_chain/RESULT.md. Only scripts/newton_episode.py changes;
the edit is made on the bytes (the file is LF-only) and verified to be exactly three insertions.
Candidate 1 (attempt01/) froze without collecting; the round-1 review showed that this freezes pending
cyclic garbage for good (gc.freeze() also resets the collection counters), so every scan's discarded
kernel objects would leak.
"""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
EPISODE = BASE / "scripts/newton_episode.py"
INSERTIONS = [
    (b"import hashlib\n", b"import gc\n", "before"),
    (b"            for step in range(steps):\n",
     b"            # v32: collect, then move the surviving start-up heap out of the cyclic collector's reach.\n"
     b"            # Logged full collections in this worker took 99-176 ms, holding the GIL throughout\n"
     b"            # (audits/2026-09-29_wall_clock_chain). No computation changes.\n"
     b"            gc.collect()\n"
     b"            gc.freeze()\n", "before"),
    (b"                last_snapshot = snapshot\n",
     b"                # v32: each second of simulation, collect the garbage it left (such as each scan's discarded\n"
     b"                # kernel objects), then freeze the survivors, so a collection covers one second of objects.\n"
     b"                if (step + 1) % 50 == 0:\n"
     b"                    gc.collect()\n"
     b"                    gc.freeze()\n", "after"),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    assert not (HERE / "prepared.json").exists()
    parent = json.loads((HERE.parent / "v31/manifest.json").read_text())
    for name, digest in parent["source_files"].items():
        assert sha((ROOT / name).read_bytes()) == digest, name
    before = EPISODE.read_bytes()
    assert b"\r" not in before and b"import gc\n" not in before and b"gc.freeze" not in before
    preimage = HERE / "parent_source" / EPISODE.relative_to(BASE)
    preimage.parent.mkdir(parents=True, exist_ok=True)
    preimage.write_bytes(before)
    after = before
    for anchor, inserted, where in INSERTIONS:
        assert after.count(anchor) == 1, anchor
        after = after.replace(anchor, inserted + anchor if where == "before" else anchor + inserted)
    # Byte-exact record: removing the insertions gives the parent bytes back.
    restored = after
    for anchor, inserted, where in INSERTIONS:
        restored = restored.replace(inserted + anchor if where == "before" else anchor + inserted, anchor)
    assert restored == before
    EPISODE.write_bytes(after)
    for name in ("building_planner.yaml", "flat_planner.yaml"):
        shutil.copyfile(HERE.parent / "v31" / name, HERE / name)
    relative = str(EPISODE.relative_to(BASE))
    (HERE / "changes.patch").write_text("".join(difflib.unified_diff(
        before.decode().splitlines(True), after.decode().splitlines(True),
        fromfile="v31/" + relative, tofile="v32/" + relative)))
    prepared = json.loads((HERE.parent / "v31/prepared.json").read_text())
    (HERE / "prepared.json").write_text(json.dumps({
        "parent": "v31", "status": "unfrozen_candidate", "native_build": prepared["native_build"],
        "changed_files": [str(EPISODE.relative_to(ROOT))],
        "episode_before_sha256": sha(before), "episode_after_sha256": sha(after),
        "added_lines": after.count(b"\n") - before.count(b"\n"), "removed_lines": 0,
        "basis": ".pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-09-29_wall_clock_chain/RESULT.md",
    }, indent=2) + "\n")
    print(json.dumps({"added_lines": after.count(b"\n") - before.count(b"\n"), "after_sha256": sha(after)}))


if __name__ == "__main__":
    main()
