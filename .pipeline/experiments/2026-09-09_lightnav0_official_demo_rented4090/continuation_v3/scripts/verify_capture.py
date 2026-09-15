"""Prove capture completeness for one v3 capture directory."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def verify(root: Path, state_record_bytes: int | None = None) -> dict:
    rows, malformed = [], 0
    for line in (root / "frames_index.jsonl").read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            malformed += 1
    front = list((root / "frames" / "front").glob("*.jpg"))
    third = list((root / "frames" / "third").glob("*.jpg"))
    status = json.loads((root / "recorder_status.json").read_text())
    size = state_record_bytes or status.get("state_size_bytes") or 0
    states_bytes = (root / "states.f64").stat().st_size
    states = states_bytes // size if size else 0
    hash_ok, hash_checked = True, 0
    for row in rows[:: max(1, len(rows) // 40 or 1)]:
        data = (root / row["front_file"]).read_bytes()
        hash_checked += 1
        if hashlib.sha256(data).hexdigest() != row["front_sha256"]:
            hash_ok = False
    ids = [r["frame_id"] for r in rows]
    result = {
        "root": str(root),
        "index_rows": len(rows),
        "front_files": len(front),
        "third_files": len(third),
        "saved_states": states,
        "states_bytes": states_bytes,
        "state_record_bytes": size,
        "state_bytes_exact_multiple": size > 0 and states_bytes % size == 0,
        "malformed_index_lines": malformed,
        "duplicate_file_names": len(rows) - len({r["front_file"] for r in rows}),
        "frame_ids_unique": len(set(ids)) == len(ids),
        "frame_ids_contiguous": bool(ids) and ids == list(range(min(ids), max(ids) + 1)),
        "recorder_status": status,
        "sampled_hash_checked": hash_checked,
        "sampled_hash_ok": hash_ok,
    }
    result["counts_equal"] = (
        len(rows) == len(front) == len(third) == states == status["written_frames"]
    )
    result["zero_losses"] = (
        status["queue_drops"] == 0 and status["write_failures"] == 0
        and status["duplicate_names"] == 0 and status["malformed_rows"] == 0
        and malformed == 0
    )
    result["passed"] = bool(result["counts_equal"] and result["zero_losses"]
                            and result["frame_ids_unique"] and hash_ok
                            and result["state_bytes_exact_multiple"])
    return result


if __name__ == "__main__":
    out = verify(Path(sys.argv[1]))
    print(json.dumps(out, indent=2))
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(out, indent=2) + "\n")
    raise SystemExit(0 if out["passed"] else 1)
