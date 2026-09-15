"""Synthetic Mandarin audio -> real ASR -> live simulator acceptance exercise."""
import json
import http.client
import math
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def request(endpoint, payload=None, audio=False):
    body = payload if audio else (json.dumps(payload).encode() if payload is not None else None)
    req = urllib.request.Request("http://127.0.0.1:18765/api/" + endpoint, data=body,
                                 headers={"X-Demo-Request": "1", "Content-Type": "application/octet-stream" if audio else "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=15))


def wait_for(predicate, seconds=45):
    start = time.monotonic()
    while time.monotonic() - start < seconds:
        try:
            state = request("status")
        except (OSError, http.client.HTTPException):
            time.sleep(.4)
            continue
        if predicate(state):
            return state
        time.sleep(.4)
    raise RuntimeError("Live simulator acceptance condition timed out")


def main():
    result = {"synthetic_audio": True, "started_unix": time.time(), "commands": []}
    evidence = ROOT / "logs/audio_simulator_test.json"
    def save():
        evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    def speak(name):
        asr = request("transcribe", (ROOT / "fixtures" / f"{name}.aiff").read_bytes(), audio=True)
        command = request("command", {"text": asr["text"], "source": "synthetic_audio_test"})
        result["commands"].append({"fixture": name, "asr": asr, "command": command})
        save()
        print("SPOKEN_COMMAND", name, command, flush=True)
        return wait_for(lambda s: s.get("ack", {}) is not None and s.get("ack", {}).get("id") == command["id"])
    try:
        initial = wait_for(lambda s: s.get("ready") and s.get("connected") and not s.get("stale"))
        result["run_id"] = initial["run_id"]
        result["initial_position"] = initial["position"]
        speak("goal")
        moving = wait_for(lambda s: s.get("v", 0) > .1 and len(s.get("planned_world", [])) == 30)
        result["first_moving_state"] = moving
        save()
        print("MODEL_TRAJECTORY_CONSUMED", moving["frame"], flush=True)
        wait_for(lambda s: s.get("position") and math.dist(s["position"][:2], initial["position"][:2]) > 2)
        stopped = speak("stop")
        stop_samples = []
        for _ in range(6):
            state = request("status")
            if state.get("connected") and not state.get("stale"):
                assert state["held"] and state["v"] == 0 and state["w"] == 0
                stop_samples.append(state)
            time.sleep(.5)
        assert len(stop_samples) >= 3, "Insufficient live stop samples"
        drift = max(math.dist(s["position"][:2], stopped["position"][:2]) for s in stop_samples)
        assert drift < .2, f"Unexpected stop drift: {drift}"
        result.update(stop_verified=True, stop_position_drift_m=drift, stopped_state=stopped,
                      stop_sample_count=len(stop_samples))
        save()
        print("STOP_LATCH_VERIFIED", drift, flush=True)
        speak("resume")
        resumed = wait_for(lambda s: s.get("v", 0) > .1 and not s.get("held"))
        result.update(resume_verified=True, resumed_state=resumed, passed=True)
        save()
        print("RESUME_VERIFIED", resumed["frame"], flush=True)
    except Exception as error:
        result.update(passed=False, error=str(error))
        save()
        raise


if __name__ == "__main__":
    main()
