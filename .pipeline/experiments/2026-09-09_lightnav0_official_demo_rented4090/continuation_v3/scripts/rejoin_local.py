"""Recompute the exact (connection, seq, JPEG SHA-256) join from local evidence."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v3_join import join_predictions

pkg = Path(sys.argv[1])
records_root = pkg / "records"
entries_all = []
for run_dir in sorted(p for p in records_root.iterdir() if p.is_dir()):
    for conn in sorted(run_dir.iterdir()):
        for episode in sorted(conn.glob("episode_*")):
            actions = episode / "actions.json"
            if not actions.exists():
                continue
            for entry in json.loads(actions.read_text()):
                image = episode / f"image_{entry['step']:06d}.jpg"
                entry["image_path"] = str(image.relative_to(pkg))
                entry["image_sha256"] = hashlib.sha256(image.read_bytes()).hexdigest() if image.exists() else None
                entry["official_key"] = f"{run_dir.name}/{conn.name}/{episode.name}"
                entries_all.append(entry)
print("official entries:", len(entries_all))
by_key = {}
for e in entries_all:
    by_key.setdefault(e["official_key"], []).append(e)

stamp_index = Path(sys.argv[2])
all_frames = [json.loads(l) for l in (stamp_index / "frames_index.jsonl").read_text().splitlines() if l.strip()]
summary = {}
for rep in ("rep_04", "rep_05", "rep_06"):
    path = pkg / "analysis" / f"{rep}_slice.json"
    data = json.loads(path.read_text())
    joined_all, problems = [], []
    for conn in data["connection_ids"]:
        # Pass 1: resolve which official episode this connection wrote, using only
        # unambiguous exact-hash matches. Identical early frames stay ambiguous.
        probe, _ = join_predictions(all_frames, data["requests"], data["responses"],
                                    entries_all, conn)
        votes = {}
        for item in probe:
            key = (item.get("record") or {}).get("official_key")
            if key:
                votes[key] = votes.get(key, 0) + 1
        if not votes:
            problems.append({"kind": "no_official_episode_resolved", "connection_id": conn})
            continue
        key = max(votes, key=votes.get)
        if sorted(votes.values(), reverse=True)[1:2] and sorted(votes.values(), reverse=True)[1] > 0:
            problems.append({"kind": "multiple_official_episodes_voted", "votes": votes})
        # Pass 2: join only against the resolved episode, so byte-identical spawn
        # frames shared across runs are no longer ambiguous.
        joined, probs = join_predictions(all_frames, data["requests"], data["responses"],
                                         by_key[key], conn)
        joined_all += joined
        problems += probs
        data["resolved_official_episode"] = key
        data["official_episode_votes"] = votes
    for item in joined_all:
        item.pop("frame", None)
        item.pop("response", None)
        item["official_key"] = (item.get("record") or {}).get("official_key")
    data["joined"] = sorted(joined_all, key=lambda j: j["seq"])
    data["join_problems"] = problems
    data["join_method"] = "connection_id + seq + exact front JPEG SHA-256 against all official episodes"
    path.write_text(json.dumps(data, indent=2) + "\n")
    known = {f["frame_id"] for f in data["frames"]}
    for item in data["joined"]:
        if item["frame_id"] not in known:
            extra = next(f for f in all_frames if f["frame_id"] == item["frame_id"])
            data["frames"].append(extra)
            known.add(extra["frame_id"])
    data["frames"].sort(key=lambda f: f["frame_id"])
    keys = sorted({j["official_key"] for j in data["joined"]})
    with_record = sum(1 for j in data["joined"] if j.get("record"))
    summary[rep] = {"requests": len(data["requests"]), "joined": len(data["joined"]),
                    "with_official_record": with_record, "problems": len(problems),
                    "official_keys": keys}
print(json.dumps(summary, indent=2))
