"""Plot closed v82 trials from retained CSVs without restoring heavy captures."""
from pathlib import Path
import csv
import hashlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
inputs = {}
for number, color in [(1, "#126D8C"), (2, "#D97922")]:
    folder = BASE / "versions/v82/analysis" / f"trial{number:02d}"
    for name in ["frequency.csv", "latency.csv"]:
        path = folder / name
        inputs[str(path.relative_to(BASE))] = hashlib.sha256(path.read_bytes()).hexdigest()
    with (folder / "frequency.csv").open() as stream:
        frequency = list(csv.DictReader(stream))
    with (folder / "latency.csv").open() as stream:
        latency = list(csv.DictReader(stream))
    assert frequency and latency
    label = f"Trial {number:02d}"
    axes[0].plot([float(row["simulation_s"]) for row in frequency],
                 [float(row["successful_hz_1wallsecond"]) for row in frequency],
                 color=color, linewidth=.8, label=label)
    axes[1].scatter([float(row["simulation_s"]) for row in latency],
                    [float(row["solve_ms"]) for row in latency],
                    s=7, color=color, alpha=.5, label=label, zorder=3)

axes[0].axhline(30, linestyle="--", color="#555555", label="30 Hz target")
axes[0].set_ylim(0, 35)
axes[0].set_ylabel("Successful plans / wall second")
axes[0].set_title("v82 Mac corner: heartbeat preserved; continuity and 30 Hz FAILED")
axes[1].axhspan(.01, 10, color="#E1F2E9", zorder=0, label="Fast regime <10 ms")
axes[1].axhline(1000 / 30, linestyle="--", color="#555555", label="33.3 ms period")
axes[1].set_yscale("log")
axes[1].set_ylim(.07, 750)
axes[1].set_ylabel("Complete solve latency (ms)")
axes[1].set_xlabel("Simulation time (s)")
for axis in axes:
    axis.grid(alpha=.2, zorder=0)
    axis.legend(loc="upper right", fontsize=8)
fig.tight_layout()
for suffix in ["png", "pdf"]:
    fig.savefig(HERE / f"time_series_comparison.{suffix}", dpi=150)
plt.close(fig)
(HERE / "time_series_comparison_provenance.json").write_text(json.dumps({
    "physical_version": "v82",
    "candidate_acceptance": "failed_continuity_and_30hz",
    "inputs_sha256": inputs,
    "plotter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "frequency_definition": "Trailing (t-1,t] wall-second successful counts against simulation time",
    "latency_population": "All complete rounds, including failures",
    "background_zorder": 0,
    "scatter_zorder": 3,
    "regeneration": "Run this script with matplotlib from any directory; only retained CSVs are needed."
}, indent=2) + "\n")
