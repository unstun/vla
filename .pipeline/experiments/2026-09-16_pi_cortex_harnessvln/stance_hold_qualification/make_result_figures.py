#!/usr/bin/env python3
"""Figures for the stance-hold RESULT.md and report page (task 09-17-isaac-runner-stance-hold, D1).

Every number is read from returned metrics.jsonl rows, review.json and the series ledgers; nothing is typed in.
Entry windows follow the frozen AC7 definitions in isaac_runner/stance_hold_thresholds.json: an entry is a
STAND_TRANSITION row whose previous row is not STAND_TRANSITION, the window is 1.0 s (+1 ms tolerance) from it, and
the PRD D7 post-result amendment ends it at the first later row whose mode is neither STAND_TRANSITION nor
FIXED_STAND (that row excluded). Still windows follow review_two_goal.py (see series_report.py).

    make_result_figures.py [--out report/figures]
"""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
RUNS = EXP / "isaac_runner/runs"
TWO_GOAL = EXP / "isaac_runner/two_goal_runs"
HOLD_LEDGER = HERE / "hold_series/series_ledger.jsonl"
OFF_LEDGER = EXP / "scan_fix_qualification/isaac_series/series_ledger.jsonl"

INK, MUTED, RULE = "#14201c", "#56655f", "#cfd8d4"
HOLD_ON, HOLD_OFF = "#0072b2", "#c75200"
MODE_COLOR = {"STAND_SETTLING": "#eda100", "STAND_TRANSITION": "#2a78d6", "FIXED_STAND": "#1baf7a",
              "REJOIN": "#e87ba4"}
MODE_LABEL = {"STAND_SETTLING": "STAND_SETTLING (policy drives, gates pending)",
              "STAND_TRANSITION": "STAND_TRANSITION (crossfade to the PD hold)",
              "FIXED_STAND": "FIXED_STAND (PD hold)", "REJOIN": "REJOIN (back to the policy)"}
HOLD_MODES = ("STAND_TRANSITION", "FIXED_STAND")
WINDOW_S, TOL_S = 1.0, 0.001
YAW_LIMIT, VZ_LIMIT = 0.15, 0.05

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6ebe9",
    "grid.linewidth": 0.8, "axes.axisbelow": True, "figure.facecolor": "white", "axes.facecolor": "white",
    "legend.frameon": False, "axes.titleweight": "bold", "axes.titlesize": 11, "axes.titlecolor": INK,
})


def rows_of(run_dir):
    path = Path(run_dir) / "returned_artifacts/runner_output/metrics.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def ledger(path):
    return [r for r in map(json.loads, Path(path).read_text().splitlines()) if r.get("run_id")]


def entries(rows):
    return [i for i, r in enumerate(rows) if r.get("stance_mode") == "STAND_TRANSITION"
            and (i == 0 or rows[i - 1].get("stance_mode") != "STAND_TRANSITION")]


def entry_window(rows, index, amended):
    t0 = rows[index]["sim_time_s"]
    part, restart = [], None
    for row in rows[index:]:
        if row["sim_time_s"] > t0 + WINDOW_S + TOL_S:
            break
        if amended and row is not rows[index] and row.get("stance_mode") not in HOLD_MODES:
            restart = row
            break
        part.append(row)
    return part, restart


def peak(part, key):
    if key == "yaw":
        return max(abs(r["yaw_rate_radps"]) for r in part)
    return max(abs(r["base_linear_velocity_world"][2]) for r in part)


def segments(rows):
    out, start = [], 0
    for i in range(1, len(rows) + 1):
        if i == len(rows) or rows[i].get("stance_mode") != rows[start].get("stance_mode"):
            out.append((rows[start].get("stance_mode"), rows[start]["sim_time_s"], rows[i - 1]["sim_time_s"] + 0.02))
            start = i
    return out


def zero_intervals(rows):
    zero = [max(abs(x) for x in r["admitted_command"]) <= 0.001 for r in rows]
    out, i = [], 0
    while i < len(rows):
        if not zero[i]:
            i += 1
            continue
        j = i
        while j < len(rows) and zero[j]:
            j += 1
        out.append((rows[i - 1]["sim_time_s"] if i else 0.0, rows[j - 1]["sim_time_s"]))
        i = j
    return out


def restarts(rows):
    """Start of each non-zero command after a zero-command interval, with the max |yaw| over the next 1.0 s."""
    zero = [max(abs(x) for x in r["admitted_command"]) <= 0.001 for r in rows]
    out = []
    for i in range(2, len(rows)):
        if zero[i - 1] and not zero[i]:
            t0 = rows[i]["sim_time_s"]
            out.append(max(abs(r["yaw_rate_radps"]) for r in rows[i:] if r["sim_time_s"] <= t0 + WINDOW_S + TOL_S))
    return out


def still_windows(run_dir, rows):
    review = json.loads((Path(run_dir) / "review.json").read_text())
    pilot = json.loads((Path(run_dir) / "inputs/pilot.json").read_text())
    out = []
    for item in review["terminals"]:
        terminal = item["terminal"]
        before = [r for r in rows if r["state_sample_monotonic_ns"] <= terminal["monotonic_s"] * 1e9]
        window = []
        for row in reversed(before):
            window.append(row)
            if window[0]["sim_time_s"] - window[-1]["sim_time_s"] >= pilot["stop_dwell_sim_seconds"]:
                break
        out.append({"status": item["status"], "start": window[-1]["sim_time_s"], "end": window[0]["sim_time_s"],
                    "yaw": max(abs(r["yaw_rate_radps"]) for r in window)})
    return out


def jitter(n, width=0.22):
    return [(-width + 2 * width * k / (n - 1)) if n > 1 else 0.0 for k in range(n)]


def limit_line(ax, value, text, xpos=1.0, ha="right", va="bottom"):
    ax.axhline(value, color=INK, lw=1, ls=(0, (4, 3)))
    ax.text(xpos, value, " " + text + " ", color=INK, va=va, ha=ha, fontsize=9, transform=ax.get_yaxis_transform())


def fig_entry_variants(out):
    runs = [("ramp", "walk_20260917T145650Z_hold_auto_ramp", "C1d"),
            ("step1", "walk_20260917T145650Z_hold_auto_step1", "C1d"),
            ("step2p5", "walk_20260917T145650Z_hold_auto_step2p5", "C1d"),
            ("xfade1s", "walk_20260917T181650Z_hold_auto_xfade1s", "D6"),
            ("xfade2s", "walk_20260917T181650Z_hold_auto_xfade2s", "D6")]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.9), constrained_layout=True)
    data = []
    for name, run, _ in runs:
        rows = rows_of(RUNS / run)
        windows = [entry_window(rows, i, amended=False)[0] for i in entries(rows)]
        data.append((name, [peak(w, "yaw") for w in windows], [peak(w, "vz") for w in windows]))
    for ax, key, limit, label in ((axes[0], 1, YAW_LIMIT, "max |yaw rate| in the entry window (rad/s)"),
                                  (axes[1], 2, VZ_LIMIT, "max |vertical speed| in the entry window (m/s)")):
        for x, item in enumerate(data):
            values = item[key]
            color = HOLD_ON if item[0].startswith("xfade") else MUTED
            for dx, v in zip(jitter(len(values)), values):
                over = v > limit
                ax.scatter(x + dx, v, s=46, color="white" if over else color, edgecolor=HOLD_OFF if over else color,
                           linewidth=1.8, zorder=3)
        limit_line(ax, limit, "AC7 limit %.2f" % limit)
        ax.set_xticks(range(len(data)), [d[0] for d in data])
        ax.set_ylabel(label)
        ax.set_ylim(0, max(max(d[key]) for d in data) * 1.12)
        ax.axvline(2.5, color=RULE, lw=1)
        ax.text(1.0, ax.get_ylim()[1], "C1d variants (PRD D5)", ha="center", va="top", color=MUTED, fontsize=9)
        ax.text(3.5, ax.get_ylim()[1], "D6 crossfade", ha="center", va="top", color=MUTED, fontsize=9)
    fig.suptitle("Scripted walk, three stops per run: every hold entry, by entry variant "
                 "(open orange = above the limit)", color=INK, fontsize=11)
    fig.savefig(out / "fig1_entry_variants.png", dpi=160)
    plt.close(fig)


def fig_walk_trace(out):
    off = rows_of(RUNS / "walk_20260917T145650Z_hold_off")
    on = rows_of(RUNS / "walk_20260917T181650Z_hold_auto_xfade1s")
    fig, (ax, band) = plt.subplots(2, 1, figsize=(10.5, 4.4), sharex=True, constrained_layout=True,
                                   gridspec_kw={"height_ratios": [5, 1]})
    for start, end in zero_intervals(on):
        ax.axvspan(start, end, color="#f3f5f4", lw=0, zorder=0)
    ax.plot([r["sim_time_s"] for r in off], [abs(r["yaw_rate_radps"]) for r in off], color=HOLD_OFF, lw=1.1,
            label="hold off (V12 on zero command)")
    ax.plot([r["sim_time_s"] for r in on], [abs(r["yaw_rate_radps"]) for r in on], color=HOLD_ON, lw=1.4,
            label="hold on, xfade1s entry")
    limit_line(ax, YAW_LIMIT, "review stillness limit 0.15", xpos=0.995)
    ax.set_ylabel("|yaw rate| (rad/s)")
    ax.set_ylim(0, 0.42)
    ax.legend(loc="upper left", ncol=2)
    ax.text(0.995, 0.41, "grey bands: zero command (stops)", color=MUTED, fontsize=9, ha="right", va="top",
            transform=ax.get_yaxis_transform())
    draw_modes(band, on, 0.0, 0.8)
    band.set_yticks([])
    band.set_ylim(-0.1, 0.9)
    band.set_ylabel("hold on", rotation=0, ha="right", va="center")
    band.grid(False)
    band.set_xlabel("simulation time (s)")
    band.legend(handles=mode_handles(("STAND_SETTLING", "STAND_TRANSITION", "FIXED_STAND", "REJOIN")),
                loc="upper center", bbox_to_anchor=(0.5, -0.9), ncol=2, fontsize=8.5)
    fig.suptitle("Scripted walk (PRD D5 command script): yaw rate with the hold off and on", color=INK, fontsize=11)
    fig.savefig(out / "fig2_walk_d6_yaw.png", dpi=160)
    plt.close(fig)


def draw_modes(ax, rows, y, height):
    for mode, start, end in segments(rows):
        if mode in MODE_COLOR:
            ax.broken_barh([(start, end - start - 0.02)], (y, height), facecolor=MODE_COLOR[mode],
                           edgecolor="white", linewidth=1, hatch="////" if mode == "REJOIN" else None)
    ax.plot([rows[0]["sim_time_s"], rows[-1]["sim_time_s"]], [y + height / 2] * 2, color=RULE, lw=0.8, zorder=0)


def mode_handles(modes):
    return [Patch(facecolor=MODE_COLOR[m], edgecolor="white", hatch="////" if m == "REJOIN" else None,
                  label=MODE_LABEL[m]) for m in modes] + [Patch(facecolor="white", edgecolor=RULE, label="RL (policy)")]


def fig_two_goal_stops(out):
    series = {}
    for name, path in (("hold on", HOLD_LEDGER), ("hold off", OFF_LEDGER)):
        still, rest = [], []
        for record in ledger(path):
            run_dir = TWO_GOAL / record["run_id"]
            rows = rows_of(run_dir)
            still += [w["yaw"] for w in still_windows(run_dir, rows)]
            rest += restarts(rows)
        series[name] = (still, rest)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0), sharey=True, constrained_layout=True)
    titles = ("review still window before each terminal (24 per series)",
              "1.0 s after each resumed command (24 per series)")
    for k, ax in enumerate(axes):
        for x, (name, color) in enumerate((("hold off", HOLD_OFF), ("hold on", HOLD_ON))):
            values = sorted(series[name][k])
            xs = [x + d for d in jitter(len(values), 0.28)]
            ax.scatter(xs, values, s=30, color=color, alpha=0.85, edgecolor="white", linewidth=0.8, zorder=3)
            median = values[len(values) // 2 - 1] / 2 + values[len(values) // 2] / 2
            ax.plot([x - 0.34, x + 0.34], [median, median], color=INK, lw=1.6, zorder=4)
            ax.text(x + 0.36, median, " median %.3f\n max %.3f" % (median, values[-1]), va="center", fontsize=8.5,
                    color=INK)
        if k == 0:
            limit_line(ax, YAW_LIMIT, "review limit 0.15")
        else:
            limit_line(ax, YAW_LIMIT, "0.15 (stop limit, for scale)", xpos=1.0 / 2.4, ha="center", va="top")
        ax.set_xticks([0, 1], ["hold off\nSCAN series", "hold on\nxfade1s series"])
        ax.set_xlim(-0.5, 1.9)
        ax.set_title(titles[k], fontsize=10, fontweight="normal", color=MUTED)
    axes[0].set_ylabel("max |yaw rate| (rad/s)")
    axes[0].set_ylim(0, 0.37)
    fig.suptitle("Two-goal series, 8 episodes each: the hold leaves the stop windows unchanged and softens restarts",
                 color=INK, fontsize=11)
    fig.savefig(out / "fig3_two_goal_stops.png", dpi=160)
    plt.close(fig)


def fig_timelines(out):
    records = ledger(HOLD_LEDGER)
    fig, ax = plt.subplots(figsize=(10.5, 5.2), constrained_layout=True)
    for k, record in enumerate(records):
        y = len(records) - 1 - k
        run_dir = TWO_GOAL / record["run_id"]
        rows = rows_of(run_dir)
        draw_modes(ax, rows, y - 0.28, 0.56)
        for w in still_windows(run_dir, rows):
            ax.plot([w["start"], w["end"]], [y + 0.38] * 2, color=INK, lw=1.6, solid_capstyle="butt")
            ax.plot([w["end"]], [y + 0.38], marker="v" if w["status"] == "cancelled" else "o", color=INK, ms=4.5)
    ax.set_yticks(range(len(records)), ["e%02d  %.2f m" % (r["episode"], r["cancel_displacement_m"])
                                        for r in reversed(records)])
    ax.set_xlabel("simulation time (s)")
    ax.set_ylim(-0.6, len(records) - 0.2)
    ax.grid(axis="y", visible=False)
    handles = mode_handles(("STAND_SETTLING", "STAND_TRANSITION", "REJOIN"))
    handles.append(plt.Line2D([], [], color=INK, lw=1.6, marker="o", ms=4.5,
                              label="review still window, ending at the terminal (▼ cancel, ● arrival)"))
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=8.5)
    ax.set_title("Hold modes per episode (label: episode and cancel distance). No stop lasts long enough to reach "
                 "FIXED_STAND", fontsize=10.5)
    fig.savefig(out / "fig4_two_goal_timelines.png", dpi=160)
    plt.close(fig)


def fig_e06(out):
    record = next(r for r in ledger(HOLD_LEDGER) if r["episode"] == 6)
    rows = rows_of(TWO_GOAL / record["run_id"])
    index = next(i for i in entries(rows) if abs(rows[i]["sim_time_s"] - 6.66) < 0.011)
    full, _ = entry_window(rows, index, amended=False)
    amended, restart = entry_window(rows, index, amended=True)
    t0, t_full, t_restart = rows[index]["sim_time_s"], full[-1]["sim_time_s"], restart["sim_time_s"]
    view = [r for r in rows if t0 - 0.5 <= r["sim_time_s"] <= t0 + 1.12]
    fig, (ax, vz_ax, band) = plt.subplots(3, 1, figsize=(10.5, 5.6), sharex=True, constrained_layout=True,
                                          gridspec_kw={"height_ratios": [4, 2.4, 0.8]})
    for axis, key, limit, unit in ((ax, "yaw", YAW_LIMIT, "|yaw rate| (rad/s)"),
                                   (vz_ax, "vz", VZ_LIMIT, "|vertical speed| (m/s)")):
        values = [abs(r["yaw_rate_radps"]) if key == "yaw" else abs(r["base_linear_velocity_world"][2]) for r in view]
        axis.plot([r["sim_time_s"] for r in view], values, color=HOLD_ON, lw=1.5)
        axis.axvspan(t0, t_full, color="#f7dedb", lw=0, zorder=0)
        axis.axvspan(t0, t_restart - 0.001, color="#dcefe4", lw=0, zorder=0)
        limit_line(axis, limit, "AC7 limit %.2f" % limit)
        axis.set_ylabel(unit)
        axis.axvline(t0, color=INK, lw=1)
        axis.axvline(t_restart, color=HOLD_OFF, lw=1.2, ls=(0, (3, 2)))
    y_full, y_amended = peak(full, "yaw"), peak(amended, "yaw")
    ax.annotate("as frozen (full 1.0 s window): max %.3f, fails" % y_full,
                xy=(next(r["sim_time_s"] for r in full if abs(r["yaw_rate_radps"]) == y_full), y_full),
                xytext=(t0 + 0.50, 0.215), color=INK, fontsize=9, va="center",
                arrowprops=dict(arrowstyle="-", color=INK, lw=0.8))
    ax.text(t0 - 0.01, 0.235, "entry %.2f s" % t0, color=INK, fontsize=9, ha="right", va="center")
    ax.text(t_restart + 0.01, 0.255, "restart %.2f s (first REJOIN row)" % t_restart, color=HOLD_OFF, fontsize=9,
            va="center")
    ax.text(t0 - 0.01, 0.195, "amended window (D7): max %.3f" % y_amended, color="#1b7a4a", fontsize=9,
            ha="right", va="center")
    ax.set_ylim(0, 0.27)
    vz_ax.set_ylim(0, max(0.06, 1.15 * max(abs(r["base_linear_velocity_world"][2]) for r in view)))
    draw_modes(band, view, 0.0, 0.8)
    band.set_yticks([])
    band.grid(False)
    band.set_xlabel("simulation time (s)")
    band.legend(handles=mode_handles(("STAND_SETTLING", "STAND_TRANSITION", "REJOIN")), loc="upper center",
                bbox_to_anchor=(0.5, -1.6), ncol=2, fontsize=8.5)
    fig.suptitle("Episode 6, entry at %.2f s: red = AC7 window as frozen, green = window ended at the restart "
                 "(post-result, PRD D7)" % t0, color=INK, fontsize=11)
    fig.savefig(out / "fig5_e06_ac7_window.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=HERE / "report/figures")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    fig_entry_variants(args.out)
    fig_walk_trace(args.out)
    fig_two_goal_stops(args.out)
    fig_timelines(args.out)
    fig_e06(args.out)
    for path in sorted(args.out.glob("*.png")):
        print(path.name, path.stat().st_size)


if __name__ == "__main__":
    main()
