"""Wall-time presentation timeline built from recorded monotonic clocks only.

Every presentation frame holds the newest already-captured camera frame and the
newest already-arrived prediction. Nothing is interpolated or shown early.
"""
from __future__ import annotations


def build_timeline(start_ns: int, end_ns: int, frames, predictions, fps: int = 20):
    step_ns = int(round(1_000_000_000 / fps))
    frames = sorted(frames, key=lambda f: f["capture_mono_ns"])
    predictions = sorted(predictions, key=lambda p: p["receive_mono_ns"])
    timeline = []
    frame_index = -1
    pred_index = -1
    t = int(start_ns)
    while t <= int(end_ns):
        while frame_index + 1 < len(frames) and frames[frame_index + 1]["capture_mono_ns"] <= t:
            frame_index += 1
        while (pred_index + 1 < len(predictions)
               and predictions[pred_index + 1]["receive_mono_ns"] <= t):
            pred_index += 1
        frame = frames[frame_index] if frame_index >= 0 else None
        prediction = predictions[pred_index] if pred_index >= 0 else None
        timeline.append({
            "t_ns": t,
            "elapsed_s": (t - int(start_ns)) / 1e9,
            "frame_id": frame["frame_id"] if frame else None,
            "frame": frame,
            "frame_age_ns": (t - frame["capture_mono_ns"]) if frame else None,
            "prediction": prediction,
            "prediction_age_ns": (t - prediction["receive_mono_ns"]) if prediction else None,
        })
        t += step_ns
    return timeline
