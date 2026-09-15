"""Focused pre-run checks for the v3 recorder, joins and film timeline.

Run with the demo interpreter and PYTHONPATH pointing at the v3 work copy:
  MUJOCO_GL=egl PYTHONPATH=$W/mujoco_demo $DEMO_PY scripts/test_v3.py
"""
from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}", flush=True)


def fresh_recorder(root: Path, queue_max: int = 2048):
    os.environ["LIGHTNAV_V3_TRACE_DIR"] = str(root)
    os.environ["LIGHTNAV_V3_QUEUE_MAX"] = str(queue_max)
    import vln_mujoco.v3_capture as mod
    mod = importlib.reload(mod)
    return mod, mod.recorder()


def test_index_rows_and_completeness() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        mod, rec = fresh_recorder(root)
        state_size = 3034 * 8
        count = 250
        for i in range(count):
            payload = {
                "frame_id": rec.next_frame_id(),
                "capture_mono_ns": time.monotonic_ns(),
                "sim_time": i * 0.05,
                # deliberately variable-length rows: the old harness derived file
                # names from byte offsets, which collided on variable JSON length
                "note": "x" * (i % 97),
                "_front_jpeg": b"\xff\xd8front" + str(i).encode(),
                "_third_jpeg": b"\xff\xd8third" + str(i).encode(),
                "_state": bytes(state_size),
            }
            rec.submit_frame(payload)
        rec.flush()
        rows = [json.loads(line) for line in (root / "frames_index.jsonl").read_text().splitlines()]
        front = sorted((root / "frames" / "front").glob("*.jpg"))
        third = sorted((root / "frames" / "third").glob("*.jpg"))
        states = (root / "states.f64").stat().st_size // state_size
        status = rec.status()
        check("variable_length_rows_no_collision",
              len(rows) == count == len(front) == len(third) == states,
              f"rows={len(rows)} front={len(front)} third={len(third)} states={states}")
        check("row_lengths_actually_varied",
              len({len(json.dumps(r)) for r in rows}) > 10,
              f"distinct_row_lengths={len({len(json.dumps(r)) for r in rows})}")
        check("frame_ids_unique_monotonic",
              [r["frame_id"] for r in rows] == list(range(count)))
        check("no_losses_reported",
              status["queue_drops"] == 0 and status["write_failures"] == 0
              and status["duplicate_names"] == 0 and status["malformed_rows"] == 0,
              json.dumps({k: status[k] for k in
                          ("queue_drops", "write_failures", "duplicate_names", "malformed_rows")}))
        p95 = status["enqueue_p95_ns"]
        check("enqueue_p95_under_1ms", p95 is not None and p95 < 1_000_000,
              f"p95_ns={p95} max_ns={status['enqueue_max_ns']}")
        rec.close()


def test_duplicate_and_write_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        mod, rec = fresh_recorder(root)
        payload = lambda fid: {
            "frame_id": fid, "sim_time": 0.0,
            "_front_jpeg": b"a", "_third_jpeg": b"b", "_state": bytes(16),
        }
        rec.submit_frame(payload(7))
        rec.submit_frame(payload(7))  # deliberate duplicate file name
        rec.flush()
        status = rec.status()
        check("duplicate_name_rejected_and_reported",
              status["duplicate_names"] == 1 and status["write_failures"] == 1
              and status["written_frames"] == 1,
              json.dumps({k: status[k] for k in ("duplicate_names", "write_failures", "written_frames")}))
        traces = [json.loads(line) for line in (root / "traces.jsonl").read_text().splitlines()]
        check("recorder_failure_is_traced",
              any(t["trace"] == "recorder_failure" for t in traces))
        # malformed state record size
        rec.submit_frame({"frame_id": 8, "sim_time": 0.0, "_front_jpeg": b"a",
                          "_third_jpeg": b"b", "_state": bytes(24)})
        rec.flush()
        check("state_size_change_is_a_failure", rec.status()["malformed_rows"] == 1,
              f"malformed_rows={rec.status()['malformed_rows']}")
        rec.close()


def test_queue_overflow_reported() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        mod, rec = fresh_recorder(root, queue_max=4)
        rec._stop.set()
        rec._thread.join(timeout=2.0)  # stall the writer on purpose
        for i in range(40):
            rec.submit_frame({"frame_id": 1000 + i, "sim_time": 0.0, "_front_jpeg": b"a",
                              "_third_jpeg": b"b", "_state": bytes(16)})
        status = rec.status()
        check("queue_overflow_counted_not_silent", status["queue_drops"] >= 30,
              f"queue_drops={status['queue_drops']} enqueued={status['enqueued_frames']}")
        check("overflow_never_blocks_producer", status["enqueue_max_ns"] < 5_000_000,
              f"max_ns={status['enqueue_max_ns']}")


def test_join_rules() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from v3_join import join_predictions

    frames = [{"frame_id": i, "stamp_ns": 1000 + i, "front_sha256": f"h{i}",
               "capture_mono_ns": i * 1000} for i in range(5)]
    requests = [{"seq": 1, "stamp_ns": 1002, "jpeg_sha256": "h2", "connection_id": "c",
                 "send_mono_ns": 5000}]
    responses = [{"seq": 1, "connection_id": "c", "receive_mono_ns": 6000, "decode_status": "ok"}]
    records = [{"seq": 1, "image_sha256": "h2", "raw_text": "t"}]
    joined, problems = join_predictions(frames, requests, responses, records, "c")
    check("exact_hash_join_succeeds", len(joined) == 1 and not problems, json.dumps(problems))

    bad = [{"seq": 1, "stamp_ns": 1002, "jpeg_sha256": "MISMATCH", "connection_id": "c",
            "send_mono_ns": 5000}]
    joined, problems = join_predictions(frames, bad, responses, records, "c")
    check("hash_mismatch_rejected", not joined and problems, json.dumps(problems)[:120])

    late = [{"seq": 1, "stamp_ns": 999999, "jpeg_sha256": "h2", "connection_id": "c",
             "send_mono_ns": 5000}]
    joined, problems = join_predictions(frames, late, responses, records, "c")
    check("unknown_stamp_rejected", not joined and problems, json.dumps(problems)[:120])

    other = [{"seq": 1, "stamp_ns": 1002, "jpeg_sha256": "h2", "connection_id": "OTHER",
              "send_mono_ns": 5000}]
    joined, problems = join_predictions(frames, other, responses, records, "c")
    check("wrong_connection_rejected", not joined, json.dumps(problems)[:120])


def test_timeline_rules() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from v3_timeline import build_timeline

    t0 = 0
    frames = [{"frame_id": 0, "capture_mono_ns": 0}, {"frame_id": 1, "capture_mono_ns": 6_000_000_000}]
    preds = [{"seq": 1, "receive_mono_ns": 3_000_000_000, "frame_id": 0}]
    tl = build_timeline(t0, 6_000_000_000, frames, preds, fps=20)
    check("five_second_gap_preserved", len(tl) == 121, f"presentation_frames={len(tl)}")
    stale = [t for t in tl if t["frame_id"] == 0]
    check("stale_frame_held_not_invented", len(stale) == 120, f"held={len(stale)}")
    early = [t for t in tl if t["prediction"] is not None and t["t_ns"] < 3_000_000_000]
    check("no_prediction_before_arrival", not early, f"early={len(early)}")
    late = [t for t in tl if t["prediction"] is not None]
    check("prediction_visible_after_arrival", len(late) == 61, f"after={len(late)}")
    ages = [t["frame_age_ns"] for t in tl]
    check("frame_age_reported_and_grows", max(ages) >= 5_900_000_000, f"max_age_ns={max(ages)}")


def test_state_roundtrip_and_orthographic() -> None:
    try:
        import mujoco
        import numpy as np
        from vln_mujoco.robots.turtlebot import build_model
    except Exception as exc:
        check("mujoco_state_roundtrip", False, f"import failed: {exc}")
        return
    model = build_model()
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    size = mujoco.mj_stateSize(model, mujoco.mjtState.mjSTATE_INTEGRATION)
    buf = np.empty(int(size), dtype=np.float64)
    mujoco.mj_getState(model, data, buf, mujoco.mjtState.mjSTATE_INTEGRATION)
    baseline = buf.copy()
    data.qpos[:] += 0.01
    data.time += 1.0
    mujoco.mj_forward(model, data)
    mujoco.mj_setState(model, data, baseline, mujoco.mjtState.mjSTATE_INTEGRATION)
    mujoco.mj_forward(model, data)
    after = np.empty(int(size), dtype=np.float64)
    mujoco.mj_getState(model, data, after, mujoco.mjtState.mjSTATE_INTEGRATION)
    check("mujoco_state_roundtrip_exact", np.array_equal(baseline, after),
          f"state_size={int(size)}")

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from v3_render import make_overhead_renderer
    renderer, camera, hidden = make_overhead_renderer(model, width=320, height=240)
    rgb = renderer.render()
    flag = int(renderer.scene.camera[0].orthographic)
    check("effective_orthographic_projection", flag == 1, f"gl_orthographic={flag}")
    check("overhead_render_non_empty", rgb is not None and rgb.std() > 1.0,
          f"std={float(rgb.std()):.2f}")
    check("only_named_ceilings_hidden", len(hidden) == 10, f"hidden={len(hidden)}")
    renderer.close()


def test_deterministic_supplied_control_replay() -> None:
    """Identical supplied commands must give identical state with capture on/off."""
    try:
        import mujoco
        import numpy as np
        from vln_mujoco.robots.turtlebot import TurtleBotBackend
    except Exception as exc:
        check("deterministic_supplied_control_replay", False, f"import failed: {exc}")
        return
    commands = [(0.4, 0.0)] * 40 + [(0.3, -0.5)] * 40 + [(0.0, 0.0)] * 20
    signatures = []
    for enabled in (False, True):
        if enabled:
            os.environ["LIGHTNAV_V3_TRACE_DIR"] = tempfile.mkdtemp()
        else:
            os.environ.pop("LIGHTNAV_V3_TRACE_DIR", None)
        import vln_mujoco.v3_capture as mod
        importlib.reload(mod)
        backend = TurtleBotBackend()
        backend.reset()
        for command in commands:
            backend.step(command)
        size = mujoco.mj_stateSize(backend.model, mujoco.mjtState.mjSTATE_INTEGRATION)
        buf = np.empty(int(size), dtype=np.float64)
        mujoco.mj_getState(backend.model, backend.data, buf, mujoco.mjtState.mjSTATE_INTEGRATION)
        signatures.append(buf.copy())
    check("deterministic_supplied_control_replay",
          np.array_equal(signatures[0], signatures[1]),
          "identical state for capture disabled vs enabled (supplied commands only; "
          "this does NOT prove asynchronous model trajectories repeat)")


def main() -> int:
    test_index_rows_and_completeness()
    test_duplicate_and_write_failure()
    test_queue_overflow_reported()
    test_join_rules()
    test_timeline_rules()
    test_state_roundtrip_and_orthographic()
    test_deterministic_supplied_control_replay()
    failed = [name for name, ok, _ in RESULTS if not ok]
    summary = {"total": len(RESULTS), "failed": failed,
               "results": [{"name": n, "ok": o, "detail": d} for n, o, d in RESULTS]}
    out = os.environ.get("V3_TEST_OUT")
    if out:
        Path(out).write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"total": len(RESULTS), "failed": failed}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
