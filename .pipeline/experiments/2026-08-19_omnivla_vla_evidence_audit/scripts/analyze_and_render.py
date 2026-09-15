#!/usr/bin/env python3
"""Validate raw records, compute comparisons, render overlays and review HTML."""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from audit_contract import canonical_bytes, load_records, scheduled_attempts
from metrics import pairwise_difference, repeat_dispersion, trajectory_metrics


LABELS = {
    "move_forward": "move forward",
    "turn_left": "turn left",
    "turn_right": "turn right",
    "stop": "stop",
    "real_lite3": "real Lite3",
    "upstream_sample": "upstream sample",
    "real_lite3_mirror": "Lite3 mirror",
    "real_lite3_blur": "Lite3 blur",
}


def mean_trajectory(trajectories: List[List[List[float]]]) -> List[List[float]]:
    return [
        [
            sum(trajectory[row][column] for trajectory in trajectories) / len(trajectories)
            for column in range(4)
        ]
        for row in range(8)
    ]


def condition_key(record: dict) -> Tuple[str, str]:
    if record["panel"] == "language":
        return ("language", record["prompt_id"])
    return ("vision", record["image_id"])


def plot_overlay(path: Path, title: str, conditions: Dict[str, dict]) -> None:
    fig, axis = plt.subplots(figsize=(7.5, 7.0), dpi=150)
    axis.plot([0.0], [0.0], marker="s", color="black", label="origin")
    for condition_id, condition in conditions.items():
        trajectory = condition.get("mean_trajectory")
        if trajectory is None:
            continue
        x_front = [0.0] + [row[0] for row in trajectory]
        y_left = [0.0] + [row[1] for row in trajectory]
        axis.plot(y_left, x_front, marker="o", linewidth=2, label=LABELS[condition_id])
    axis.set_xlabel("normalized lateral y (positive = left per upstream comment)")
    axis.set_ylabel("normalized forward x")
    axis.set_title(title + "\nuncalibrated normalized upstream trajectory")
    axis.grid(True, alpha=0.25)
    axis.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def analyze(root: Path) -> dict:
    record_paths = sorted((root / "raw").glob("*/records/*.json"))
    records = load_records(record_paths)
    grouped: Dict[str, Dict[Tuple[str, str], List[dict]]] = defaultdict(lambda: defaultdict(list))
    for record in records:
        grouped[record["model_id"]][condition_key(record)].append(record)
    models: Dict[str, Any] = {}
    for model_id in ("omnivla_original", "omnivla_edge"):
        expected = {row["model_id"] + "__" + row["panel"] + "__" + row["image_id"] + "__" + row["prompt_id"] + "__r" + str(row["repeat_index"]) for row in scheduled_attempts(model_id)}
        actual = {record["run_id"] for record in records if record["model_id"] == model_id}
        condition_results: Dict[str, Dict[str, dict]] = {"language": {}, "vision": {}}
        failures = []
        for (panel, condition_id), group in grouped[model_id].items():
            successes = [record for record in group if record["status"] == "success"]
            failures.extend(record for record in group if record["status"] == "failure")
            trajectories = [record["trajectory_normalized"] for record in successes]
            mean = mean_trajectory(trajectories) if trajectories else None
            condition_results[panel][condition_id] = {
                "scheduled": 3,
                "success": len(successes),
                "failure": len(group) - len(successes),
                "run_ids": [record["run_id"] for record in group],
                "repeat_dispersion": repeat_dispersion(trajectories),
                "mean_trajectory": mean,
                "trajectory_metrics": trajectory_metrics(mean) if mean else None,
            }
        comparisons: Dict[str, dict] = {}
        for panel, conditions in condition_results.items():
            base_id = "move_forward" if panel == "language" else "real_lite3"
            base = conditions.get(base_id)
            if not base or base["mean_trajectory"] is None:
                continue
            repeat_max = base["repeat_dispersion"]["max_pairwise_abs"]
            for condition_id, condition in conditions.items():
                if condition_id == base_id or condition["mean_trajectory"] is None:
                    continue
                difference = pairwise_difference(base["mean_trajectory"], condition["mean_trajectory"])
                difference["base_condition"] = base_id
                difference["condition"] = condition_id
                difference["base_repeat_max_abs"] = repeat_max
                difference["counterfactual_exceeds_base_repeat_max"] = (
                    repeat_max is not None and difference["max_abs"] > repeat_max
                )
                comparisons[panel + ":" + condition_id] = difference
        models[model_id] = {
            "scheduled": 24,
            "retained": len(actual),
            "success": sum(record["status"] == "success" for record in records if record["model_id"] == model_id),
            "failure": sum(record["status"] == "failure" for record in records if record["model_id"] == model_id),
            "missing_run_ids": sorted(expected - actual),
            "unexpected_run_ids": sorted(actual - expected),
            "conditions": condition_results,
            "comparisons": comparisons,
            "failures": [
                {"run_id": record["run_id"], "failure": record["failure"]} for record in failures
            ],
        }
    return {
        "schema_version": 1,
        "record_count": len(records),
        "success_count": sum(record["status"] == "success" for record in records),
        "failure_count": sum(record["status"] == "failure" for record in records),
        "models": models,
        "final_vla_verdict": None,
        "actuation_enabled": False,
    }


def write_csv(path: Path, summary: dict) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "model_id",
                "panel",
                "condition",
                "scheduled",
                "success",
                "failure",
                "repeat_mean_pairwise_mae",
                "endpoint_x",
                "endpoint_y",
                "path_length",
                "heading_radians",
            ]
        )
        for model_id, model in summary["models"].items():
            for panel, conditions in model["conditions"].items():
                for condition_id, condition in conditions.items():
                    dispersion = condition["repeat_dispersion"]
                    geometry = condition["trajectory_metrics"] or {}
                    writer.writerow(
                        [
                            model_id,
                            panel,
                            condition_id,
                            condition["scheduled"],
                            condition["success"],
                            condition["failure"],
                            dispersion["mean_pairwise_mae"],
                            geometry.get("endpoint_x"),
                            geometry.get("endpoint_y"),
                            geometry.get("path_length"),
                            geometry.get("heading_radians"),
                        ]
                    )


def render_html(root: Path, summary: dict) -> None:
    review = root / "review"
    review.mkdir(parents=True, exist_ok=True)
    rows = []
    comparisons = []
    failures = []
    for model_id, model in summary["models"].items():
        for panel, conditions in model["conditions"].items():
            for condition_id, condition in conditions.items():
                metrics = condition["trajectory_metrics"] or {}
                dispersion = condition["repeat_dispersion"]
                rows.append(
                    "<tr><td>%s</td><td>%s</td><td>%s</td><td>%d/%d</td><td>%.6g</td><td>%.6g</td><td>%.6g</td></tr>"
                    % (
                        html.escape(model_id),
                        html.escape(panel),
                        html.escape(LABELS[condition_id]),
                        condition["success"],
                        condition["scheduled"],
                        dispersion["mean_pairwise_mae"] or 0.0,
                        metrics.get("endpoint_x", float("nan")),
                        metrics.get("endpoint_y", float("nan")),
                    )
                )
        for name, comparison in model["comparisons"].items():
            comparisons.append(
                "<tr><td>%s</td><td>%s</td><td>%.6g</td><td>%.6g</td><td>%s</td></tr>"
                % (
                    html.escape(model_id),
                    html.escape(name),
                    comparison["mae"],
                    comparison["max_abs"],
                    html.escape(str(comparison["counterfactual_exceeds_base_repeat_max"])),
                )
            )
        for failure in model["failures"]:
            failures.append(
                "<article><h3>%s</h3><pre>%s</pre></article>"
                % (html.escape(failure["run_id"]), html.escape(json.dumps(failure["failure"], indent=2)))
            )
    if not failures:
        failures.append(
            "<article class='none'><h3>No retained runtime failures</h3><p>All 48 scheduled records validated as finite 8 x 4 successes. Warnings remain visible in raw stderr logs.</p></article>"
        )
    page = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><link rel="icon" href="data:,"><title>OmniVLA evidence audit</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;background:#f4f6f8;color:#17202a}main{max-width:1200px;margin:auto;padding:24px}
.banner{background:#8b1e1e;color:white;padding:18px;font-size:24px;font-weight:800}.card{background:white;border:1px solid #ccd2d8;border-radius:10px;padding:18px;margin:16px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}img{max-width:100%%;border:1px solid #ddd}table{width:100%%;border-collapse:collapse;font-size:14px}th,td{padding:8px;border:1px solid #d8dde3;text-align:left}th{background:#eef1f4}.none{border:3px solid #2f855a;padding:12px}.decision{font-size:20px;line-height:2}.warning{color:#8b1e1e;font-weight:700}code{word-break:break-all}</style></head>
<body><div class="banner">AI-prepared evidence; human decision required</div><main>
<section class="card"><h1>OmniVLA receive-only evidence audit</h1><p class="warning">No final VLA verdict is selected. Normalized trajectories are uncalibrated for Lite3 and were not sent to any controller.</p>
<p>Records: <strong>%(records)d</strong>; successes: <strong>%(success)d</strong>; retained failures: <strong>%(failure)d</strong>. actuation_enabled: <code>false</code>.</p></section>
<section class="grid"><div class="card"><h2>OmniVLA-original: language</h2><img src="../overlays/omnivla_original_language.png"></div><div class="card"><h2>OmniVLA-original: vision</h2><img src="../overlays/omnivla_original_vision.png"></div><div class="card"><h2>OmniVLA-edge: language</h2><img src="../overlays/omnivla_edge_language.png"></div><div class="card"><h2>OmniVLA-edge: vision</h2><img src="../overlays/omnivla_edge_vision.png"></div></section>
<section class="card"><h2>Frozen inputs</h2><div class="grid"><figure><img src="../inputs/real_lite3.jpg"><figcaption>real Lite3</figcaption></figure><figure><img src="../inputs/upstream_sample.jpg"><figcaption>upstream sample</figcaption></figure><figure><img src="../inputs/real_lite3_mirror.png"><figcaption>deterministic mirror</figcaption></figure><figure><img src="../inputs/real_lite3_blur.png"><figcaption>Gaussian blur radius 4.0</figcaption></figure></div></section>
<section class="card"><h2>Condition summaries</h2><table><thead><tr><th>model</th><th>panel</th><th>condition</th><th>success/scheduled</th><th>repeat MAE</th><th>endpoint x</th><th>endpoint y</th></tr></thead><tbody>%(rows)s</tbody></table></section>
<section class="card"><h2>Counterfactual difference versus repeat variability</h2><table><thead><tr><th>model</th><th>comparison</th><th>MAE</th><th>max abs</th><th>exceeds base repeat max</th></tr></thead><tbody>%(comparisons)s</tbody></table><p>This comparison is evidence of numerical sensitivity only; semantic correctness is inspected separately and is not automatically classified.</p></section>
<section class="card"><h2>Failure gallery</h2>%(failures)s</section>
<section class="card"><h2>Code and claim evidence</h2><p><a href="../analysis/code_trace.md">code trace</a> · <a href="../analysis/observations.md">observations and limits</a> · <a href="../analysis/claim_matrix.md">claim matrix</a> · <a href="../analysis/run_ids.txt">all run IDs</a> · <a href="../analysis/summary.json">summary JSON</a> · <a href="../analysis/summary.csv">summary CSV</a></p></section>
<section class="card"><h2>Human decision — leave exactly one selection for Dr Sun</h2><div class="decision">☐ sufficient evidence<br>☐ insufficient evidence<br>☐ revise and rerun</div></section>
</main></body></html>""" % {
        "records": summary["record_count"],
        "success": summary["success_count"],
        "failure": summary["failure_count"],
        "rows": "".join(rows),
        "comparisons": "".join(comparisons),
        "failures": "".join(failures),
    }
    (review / "index.html").write_text(page, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.experiment_root.resolve()
    analysis = root / "analysis"
    overlays = root / "overlays"
    analysis.mkdir(parents=True, exist_ok=True)
    overlays.mkdir(parents=True, exist_ok=True)
    summary = analyze(root)
    (analysis / "summary.json").write_bytes(canonical_bytes(summary))
    write_csv(analysis / "summary.csv", summary)
    for model_id, model in summary["models"].items():
        for panel in ("language", "vision"):
            plot_overlay(
                overlays / (model_id + "_" + panel + ".png"),
                model_id + " — " + panel + " panel",
                model["conditions"][panel],
            )
    render_html(root, summary)
    print(json.dumps({"records": summary["record_count"], "success": summary["success_count"], "failure": summary["failure_count"]}))


if __name__ == "__main__":
    main()
