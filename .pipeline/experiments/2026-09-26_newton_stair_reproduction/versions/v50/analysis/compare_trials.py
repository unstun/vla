"""Reproduce v50 results from original logs; never alter frozen source or runs."""
from pathlib import Path
import csv
import hashlib
import importlib.util
import json
import os
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = HERE.parent
BASE = VERSION.parents[1]
ROOT = BASE.parents[2]
spec = importlib.util.spec_from_file_location("v47_analysis", BASE / "versions/v47/analyze_trial.py")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + "\n")


def analyze(run):
    import numpy as np
    directory = BASE / "runs" / run
    metrics, rounds = core.analyze(run)
    starts, _ = core.parse_rounds(directory / "scan.log")
    lines = (directory / "scan.log").read_text().splitlines()
    for row in rounds:
        segment = lines[row["start_line"] - 1:row["end_line"]]
        row["profile"] = [json.loads(s.split("V50_PROFILE ", 1)[1])
                          for s in segment if "V50_PROFILE " in s]
        row["bounds_rejections"] = sum("V50_GOAL_REGION_EMPTY" in s for s in segment)
        row["warm_accepts"] = sum("V48_WARM_RESULT accepted=1" in s for s in segment)
        row["warm_fallbacks"] = sum("V48_WARM_RESULT accepted=0" in s for s in segment)
    # The inherited success-only interval rate excludes the post-success stall.
    # Retain it with an explicit name, then count completed events over ONE window.
    metrics["legacy_success_event_interval_hz"] = metrics.pop("actual_successful_round_hz")
    pace = metrics["realtime_pacing"]
    begin = pace["wall_anchor_monotonic_s"]
    end = begin + pace["wall_elapsed_s"]
    completed = [r for r in rounds if begin <= r["start_wall_s"] + r["wall_s"] <= end]
    attempts = [r for r in starts if begin <= r["start_wall_s"] <= end]
    metrics["whole_window_rates"] = dict(
        start_wall_s=begin, end_wall_s=end, duration_s=end-begin,
        attempt_starts=len(attempts), completed_rounds=len(completed),
        successful_completions=sum(r["success"] for r in completed),
        attempt_hz=len(attempts)/(end-begin),
        completed_hz=len(completed)/(end-begin),
        successful_hz=sum(r["success"] for r in completed)/(end-begin),
        definition="Events within original navigation pacing window, including stalls; success timestamp is round start plus elapsed solve time.")
    metrics["whole_window_solve_ms"] = core.distribution([r["wall_s"]*1000 for r in completed])
    metrics["emergency_transitions"] = sum(bool(re.search(r"from .* to EMERGENCY_STOP", s)) for s in lines)
    metrics["bounds_rejections"] = sum(r["bounds_rejections"] for r in rounds)
    metrics["warm_accepted_attempts"] = sum(r["warm_accepts"] for r in rounds)
    metrics["rounds_at_least_100ms"] = sum(r["wall_s"] >= .1 for r in rounds)
    metrics["rounds_at_least_1000ms"] = sum(r["wall_s"] >= 1 for r in rounds)
    profiles = [p for r in rounds for p in r["profile"]]
    metrics["inclusive_profile_stages"] = {
        stage: {"wall_ms": core.distribution([p[stage]["wall_ms"] for p in profiles]),
                "cpu_ms": core.distribution([p[stage]["cpu_ms"] for p in profiles]),
                "calls": sum(p[stage]["calls"] for p in profiles)}
        for stage in (profiles[0] if profiles else {})}
    sensor = [json.loads(s) for s in (directory / "sensor.jsonl").read_text().splitlines()]
    times = np.array([s["sim_time_s"] for s in sensor])
    xyz = np.array([s["body_sensor"]["position"] for s in sensor])
    progress = np.r_[0, np.cumsum(np.linalg.norm(np.diff(xyz, axis=0), axis=1))]
    assert abs(progress[-1]-metrics["measured_path_length_m"]) < 1e-8
    # Descriptive common-progress segment, not an identical-state causal comparison.
    stop_sim = float(np.interp(20, progress, times))
    matched = [r for r in rounds if r["ros_s"] <= stop_sim]
    matched_starts = [r for r in starts if r["ros_s"] <= stop_sim]
    metrics["first_20m_segment"] = dict(
        end_sim_s=stop_sim, rounds=len(matched),
        successful_rounds=sum(r["success"] for r in matched),
        local_solve_ms=core.distribution([r["wall_s"]*1000 for r in matched]),
        attempt_interval_hz=core.rate([r["start_wall_s"] for r in matched_starts]),
        scope="First 20 m cumulative measured 3D path; same route progress, different trajectories and wall timelines.")
    worst = max(rounds, key=lambda r:r["wall_s"])
    save(run + "_metrics.json", metrics)
    save(run + "_rounds.json", rounds)
    save(run + "_max_round.json", worst)
    with (HERE / (run + "_latency.csv")).open("w") as f:
        writer = csv.writer(f)
        writer.writerow(["simulation_time_s", "start_wall_s", "solve_ms", "success", "warm_accepts", "rebound_attempts"])
        writer.writerows((r["ros_s"], r["start_wall_s"], r["wall_s"]*1000, int(r["success"]), r["warm_accepts"], r["rebound_attempts"]) for r in rounds)
    # Match the v48 figure's trailing one WALL second estimator; plot on sim time.
    # Use common end-of-recording span, so unsuccessful/quiet time remains visible.
    grid = np.arange(max(begin, starts[0]["start_wall_s"]) + 1, end, .05)
    sw = np.array([r["start_wall_s"] for r in starts])
    cw = np.array(sorted(r["start_wall_s"]+r["wall_s"] for r in rounds if r["success"]))
    hz = np.searchsorted(sw, grid, side="right") - np.searchsorted(sw, grid-1, side="right")
    shz = np.searchsorted(cw, grid, side="right") - np.searchsorted(cw, grid-1, side="right")
    timed_starts = [r for r in starts if r["start_wall_s"] < end]
    sim = np.interp(grid, [r["start_wall_s"] for r in timed_starts]+[end],
                    [r["ros_s"] for r in timed_starts]+[metrics["physical_duration_s"]])
    with (HERE / (run + "_frequency.csv")).open("w") as f:
        writer = csv.writer(f)
        writer.writerow(["simulation_time_s", "wall_time_s", "attempt_hz_1wallsecond", "successful_completion_hz_1wallsecond"])
        writer.writerows(zip(sim, grid, hz, shz))
    return metrics, rounds, (sim, hz, shz), (times, progress)


def main():
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/v50-mpl")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    names = ["v48_realtime_trial01", "v48_realtime_trial02", "v50_realtime_trial01", "v50_realtime_trial02"]
    names = [n for n in names if (BASE / "runs" / n / "scan.log").exists()]
    data = {n: analyze(n) for n in names}
    save("comparison_metrics.json", {n:d[0] for n,d in data.items()})
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10, "axes.spines.top":False, "axes.spines.right":False})
    fig, axes = plt.subplots(3, len(names), figsize=(4.2*len(names), 10), sharex="col", sharey="row", squeeze=False)
    for col, (name, (m, rounds, frequency, path)) in enumerate(data.items()):
        a,b,c = axes[:,col]
        label = name.replace("_realtime_", " · ").replace("trial", "trial ")
        a.set_title(label + ("\ninitial transfer overlap" if name=="v50_realtime_trial02" else ""), fontsize=12, fontweight="bold")
        a.plot(frequency[0], frequency[1], color="#98A4B4", lw=.9, label="Attempts")
        a.plot(frequency[0], frequency[2], color="#126D8C", lw=1.2, label="Successful completions")
        a.axhline(30, color="#262626", ls="--", lw=.8)
        a.set_ylim(0,34)
        a.text(.03,.94, f"Whole-window success: {m['whole_window_rates']['successful_hz']:.2f} Hz", transform=a.transAxes, va="top", fontsize=9)
        window = m["whole_window_rates"]
        plotted = [r for r in rounds if window["start_wall_s"] <= r["start_wall_s"]+r["wall_s"] <= window["end_wall_s"]]
        xs = np.array([r["ros_s"] for r in plotted]); ys = np.array([r["wall_s"]*1000 for r in plotted])
        ok = np.array([r["success"] for r in plotted]); fast = ys < 10
        b.axhspan(.5,10,color="#E1F2E9",alpha=.9)
        for mask,color,label in [(ok & fast,"#17815C","Success <10 ms"),(ok & ~fast,"#176B94","Success ≥10 ms"),(~ok,"#B53B3B","Failed round")]:
            b.scatter(xs[mask],ys[mask],s=7,c=color,alpha=.65,label=label,rasterized=True)
        b.axhline(1000/30,color="#333333",ls="--",lw=.8)
        b.set_yscale("log");b.set_ylim(.5,2500)
        b.text(.03,.94,f"Max {ys.max():.1f} ms",transform=b.transAxes,va="top",fontsize=10)
        c.plot(path[0],path[1],color="#126D8C",lw=1.7)
        c.axhline(20,color="#888888",ls=":",lw=.8)
        c.set_ylim(0,35);c.set_xlim(10,90)
        c.text(.03,.92,f"Path {m['measured_path_length_m']:.2f} m\nLongest pause {max(m['pauses_over_1s'],default=0):.2f} s",transform=c.transAxes,va="top",fontsize=10)
        c.set_xlabel("Simulation time (s)")
        for ax in (a,b,c): ax.grid(True,alpha=.17)
    axes[0,0].set_ylabel("Local frequency (Hz)\nTrailing 1 wall second")
    axes[1,0].set_ylabel("Complete round latency (ms)\nLog scale")
    axes[2,0].set_ylabel("Measured 3D path (m)")
    axes[0,0].legend(loc="lower left",fontsize=8)
    axes[1,0].legend(loc="lower right",fontsize=8)
    fig.suptitle("v50 removes futile goal search; full-system tail and continuity gates still fail",fontsize=16,fontweight="bold",y=.98)
    fig.text(.5,.015,"Same gpu5070ti Building profile • Frozen v48 parent • No v49 timeouts or stop changes • Dashed lines: 30 Hz / 33.3 ms",ha="center",fontsize=10)
    fig.tight_layout(rect=(0,.045,1,.94))
    for ext in ("png","pdf","svg"): fig.savefig(HERE/("v48_v50_time_series."+ext),dpi=180)
    plt.close(fig)
    summary=json.loads((HERE/"paired_profile_summary.json").read_text())
    g=summary["groups"]
    fig,ax=plt.subplots(figsize=(9,4.6));x=np.arange(3);width=.34
    for mode,offset,color,label in [("0",-.5,"#8C9AAE","Original search + identical profiling"),("1",.5,"#147F75","v50 bounds precheck")]:
        y=[g[str(i)][mode]["max_wall_ms"] for i in range(3)]
        bars=ax.bar(x+offset*width,y,width,color=color,label=label)
        ax.bar_label(bars,fmt="%.2f ms",padding=3,fontsize=9)
    ax.set_xticks(x,["Fast warm input","Slow warm input","Original worst-round input*"])
    ax.set_ylabel("Maximum complete replay round (ms)");ax.set_ylim(0,125)
    ax.set_title("Paired replay isolates the upfront search improvement",fontweight="bold")
    ax.legend();ax.grid(axis="y",alpha=.15)
    fig.text(.07,.03,"3 alternating pairs per case; all 18 solves succeed with identical control points and knots.\n*The original 1,090 ms live spike was NOT reproduced: input replay omits exact DDS batches and unpublished state.",fontsize=9)
    fig.tight_layout(rect=(0,.1,1,1))
    for ext in ("png","pdf"):fig.savefig(HERE/("paired_replay_comparison."+ext),dpi=180)
    plt.close(fig)
    sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),BASE/"versions/v47/analyze_trial.py",HERE/"paired_profile_summary.json"]}
    for m,*_ in data.values():sources.update(m["source_sha256"])
    save("comparison_provenance.json",dict(source_sha256=sources, run_order=names,
        latency="Complete nominal planning round, including target selection, refresh and original recovery chain; not optimizer iteration time.",
        rates="Report uses successful completions / full navigation pacing wall duration, including stalls. Legacy event-interval values are retained separately and are not whole-run throughput.",
        frequency_plot="Trailing (t-1,t] wall-second counts sampled each .05 wall seconds; mapped to simulation time by interpolation of nominal start stamps. First partial window omitted.",
        profile="Inclusive wall/thread CPU stages overlap; never add them as exclusive costs.",
        trial02_caveat="v50 trial02 briefly overlapped trial01 artifact return; transfer paused then resumed after run. See artifact_transfer_pause.json.",
        acceptance="Component pass; physical latency/continuity/30 Hz objective not accepted."))
    print(json.dumps({n:{"maximum_ms":d[0]["local_solve_ms"]["maximum"],"rates":d[0]["whole_window_rates"],"progress_m":d[0]["measured_path_length_m"],"pauses_s":d[0]["pauses_over_1s"],"first20m":d[0]["first_20m_segment"]} for n,d in data.items()},indent=2))


if __name__ == "__main__": main()
