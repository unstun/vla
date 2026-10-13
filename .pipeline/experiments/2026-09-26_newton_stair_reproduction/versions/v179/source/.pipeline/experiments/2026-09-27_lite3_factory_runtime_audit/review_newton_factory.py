"""Read-only review of an existing factory/Newton episode; never rerun physics."""

import hashlib
import json
from pathlib import Path
import struct
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent
SCENE = ROOT.parent / "2026-09-26_newton_stair_reproduction"


def review(run_name):
    source = SCENE / "runs" / run_name
    original = json.loads((source / "result.json").read_text())
    request = json.loads((source / "episode_request.json").read_text())
    with np.load(source / "full_rate.npz") as archive:
        data = archive["records"]
        replies = archive["factory_replies"]
        lower, upper = archive["joint_lower"], archive["joint_upper"]
    expected = np.float32(0.)
    clock_error = 0.
    for actual in data[:, 0]:
        clock_error = max(clock_error, abs(float(expected) - actual))
        expected = np.float32(expected + np.float32(.001))
    clock_error = max(clock_error, abs(float(expected) - original["physics_time_s"]))
    frames = json.loads((source / "video_states.json").read_text())
    frames_match = True
    for i, frame in enumerate(frames[1:], start=1):
        row = min(i * 80, len(data)) - 1
        frames_match &= np.array_equal(np.array(frame["joint_q"]), data[row, 132:151])
    uploaded_motor = np.array([np.frombuffer(row.tobytes(), dtype="<f8", count=72, offset=288)
                               for row in replies])
    motor_match = np.array_equal(uploaded_motor, data[:, 48:120])
    post_q = data[:, 132:151]
    # Resolve stored joint indices from the pinned model's unique names by the
    # initial-state ordering. Driver inputs already contain the named 12 hinges.
    measured_q = data[:, 3:15]
    limit_excursion = float(np.maximum(np.maximum(lower - measured_q, measured_q - upper), 0.).max())
    drift = np.linalg.norm(post_q[:, :2], axis=1)
    standing = data[data[:, 0] >= 10.]
    zero = data[data[:, 2] == 1]
    executable = (ROOT / "private_snapshot/bin/jy_exe").read_bytes()
    references = {"hip_x_left": struct.unpack_from("<d", executable, 0xc5080)[0],
                  "hip_x_right": struct.unpack_from("<d", executable, 0xc5090)[0],
                  "hip_y": struct.unpack_from("<d", executable, 0xc5098)[0],
                  "knee": struct.unpack_from("<d", executable, 0xc50a0)[0]}
    calibration = {"factory_reference_rad": references,
                   "measured_q_at_zero_flag": zero[-1, 3:15].tolist() if len(zero) else None,
                   "urdf_hip_y_lower_rad": lower[1::3].tolist(),
                   "hip_y_reference_outside_model_range": bool(np.any(references["hip_y"] < lower[1::3])),
                   "encoder_turn_correction_applied": False,
                   "model": request["encoder_model"],
                   "claim": "Reference mismatch is verified; mechanical/encoder equivalence is not established"}
    report = {
        "source_run": run_name, "source_result_sha256": hashlib.sha256((source / "result.json").read_bytes()).hexdigest(),
        "full_rate_sha256": hashlib.sha256((source / "full_rate.npz").read_bytes()).hexdigest(),
        "original_checks_unchanged": original["algorithm_physics_checks"],
        "clock_review": {"native_type": "float32", "steps": len(data), "maximum_error_s": clock_error,
                         "continuous_native_clock": clock_error == 0.,
                         "initial_check_error": "Compared float32 accumulated native time to a float64 product; retained original failed check"},
        "factory_outputs_match_recorded_commands": motor_match,
        "render_frames_match_actual_joint_states": bool(frames_match),
        "max_xy_displacement_m": float(drift.max()), "max_xy_displacement_time_s": float(data[drift.argmax(), 0]),
        "final_xy_displacement_m": float(drift[-1]),
        "standing_height_range_m": [float(standing[:, 134].min()), float(standing[:, 134].max())],
        "standing_max_linear_speed_mps": float(np.linalg.norm(standing[:, 151:154], axis=1).max()),
        "standing_max_xy_displacement_m": float(np.linalg.norm(standing[:, 132:134], axis=1).max()),
        "max_joint_limit_excursion_rad": limit_excursion,
        "calibration": calibration,
        "strict_factory_crouch_zero_stand_passed": False,
        "in_place_threshold_m": .1,
        "in_place_passed": float(np.linalg.norm(standing[:, 132:134], axis=1).max()) < .1,
        "boundary": "Original algorithm drove a continuous crouch/zero-torque/stand episode; strict factory calibration and in-place acceptance remain unmet",
    }
    (source / "review.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(review(sys.argv[1]), indent=2))
