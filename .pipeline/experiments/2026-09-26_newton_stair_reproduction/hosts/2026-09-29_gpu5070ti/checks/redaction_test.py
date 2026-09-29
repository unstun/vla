"""Synthetic test of host_sampler_linux.redact (port review round 3, N25: the round-2 test had no saved output).
Every input is invented; no real credential is used. Prints each case and whether it behaved as intended."""
import importlib.util
from pathlib import Path
import sys

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("sampler", Path(__file__).resolve().parents[1] / "host_sampler_linux.py")
sampler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sampler)
redacted = {
    "cloudflared tunnel run --token eyJhIjoiU1lOVEhFVElDIiwidCI6IkZBS0UiLCJzIjoiTk9UUkVBTCJ9": "SYNTHETIC",
    "x11vnc -rfbauth /etc/x11vnc.pass": "x11vnc.pass",
    "tool --api-key=SYNTHETICvalue123 --password hunter2": "hunter2",
    "tool --password 'two words'": "two words",
    'tool --client-secret="quoted value"': "quoted value",
    "git clone https://someone:SYNTHETICpass@example.org/repo.git": "SYNTHETICpass",
    "app positional Q2xhdWRlU3ludGhldGljVGVzdFN0cmluZzEyMzQ1Njc4OQ": "Q2xhdWRl",
}
kept = ["python3 /home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/scripts/run_local_episode.py --backend-executor single",
        "podman run docker.io/koide3/direct_visual_lidar_calibration@sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"]
known_misses = ["tool -p hunter2", "tool --pw shorttoken12"]
ok = True
for text, secret in redacted.items():
    out = sampler.redact(text)
    good = secret not in out
    ok &= good
    print("redacted" if good else "NOT REDACTED", "|", out)
for text in kept:
    good = sampler.redact(text) == text
    ok &= good
    print("kept" if good else "CHANGED", "|", text[-70:])
for text in known_misses:
    print("known miss (keyword-less or short):", sampler.redact(text))
print("all intended cases:", ok)
