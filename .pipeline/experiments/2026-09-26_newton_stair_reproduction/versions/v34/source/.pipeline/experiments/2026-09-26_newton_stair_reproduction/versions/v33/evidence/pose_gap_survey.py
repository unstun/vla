"""Survey the wall-time and simulation-time gaps between body-pose callbacks in every recorded run (v33 basis).

The backend's odom gate today compares wall time between body-pose receipts with 0.25 s. v33 compares the pose's
simulation-time age instead. For every run with runs/<run>/backend_body_callbacks.jsonl (written by
scripts/native_backend_entry.py: entered_ns on the backend's monotonic clock, stamp_ns the pose's header stamp)
and at least 50 callbacks, this reports:
- the longest wall gap between consecutive callbacks and the simulation-time gap across it;
- the longest simulation-time gap between consecutive callbacks and the wall gap across it;
- every wall gap over 0.25 s (where today's gate trips if it is evaluated inside the gap) and the largest
  simulation-time gap among them.
Between two receipts the backend's /clock cannot run ahead of the newest simulation sample the bridge has
published, so the simulation-time gap across a pause bounds the pose's simulation-time age during it (the
scans that also advance /clock are stamped at capture, no later than the newest pose sample).
Writes pose_gap_survey.json next to this script.
"""
import glob
import json
from pathlib import Path

H = Path(__file__).resolve().parent
E = H.parents[2]


def main():
    runs = []
    for path in sorted(glob.glob(str(E / "runs/*/backend_body_callbacks.jsonl"))):
        rows = [json.loads(line) for line in open(path) if line.strip()]
        if len(rows) < 50:
            continue
        wall = [(b["entered_ns"] - a["entered_ns"]) / 1e9 for a, b in zip(rows, rows[1:])]
        sim = [(b["stamp_ns"] - a["stamp_ns"]) / 1e9 for a, b in zip(rows, rows[1:])]
        iw = max(range(len(wall)), key=wall.__getitem__)
        isim = max(range(len(sim)), key=sim.__getitem__)
        over = [i for i, w in enumerate(wall) if w > .25]
        runs.append({"run": Path(path).parent.name, "callbacks": len(rows),
                     "longest_wall_gap_s": round(wall[iw], 4), "sim_gap_across_it_s": round(sim[iw], 4),
                     "longest_sim_gap_s": round(sim[isim], 4), "wall_gap_across_it_s": round(wall[isim], 4),
                     "wall_gaps_over_0p25_s": len(over),
                     "largest_sim_gap_among_them_s": round(max((sim[i] for i in over), default=0.), 4)})
    summary = {"runs": len(runs), "callbacks": sum(r["callbacks"] for r in runs),
               "longest_wall_gap_s": max(r["longest_wall_gap_s"] for r in runs),
               "longest_sim_gap_s": max(r["longest_sim_gap_s"] for r in runs),
               "runs_with_wall_gap_over_0p25_s": sum(r["wall_gaps_over_0p25_s"] > 0 for r in runs),
               "largest_sim_gap_at_a_wall_gap_over_0p25_s": max(r["largest_sim_gap_among_them_s"] for r in runs)}
    (H / "pose_gap_survey.json").write_text(json.dumps({"summary": summary, "runs": runs}, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
