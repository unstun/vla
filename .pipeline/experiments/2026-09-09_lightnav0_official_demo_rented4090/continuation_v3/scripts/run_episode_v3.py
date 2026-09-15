"""One bounded official-case episode against the running vln_mujoco demo (v3).

Frames, states and joins are recorded by the demo process itself (v3_capture).
This harness owns only the /ws session: reset, the exact instruction, snapshot
capture, native-stop detection, the bounded post-stop observation and the
harness stop. It never sends manual twists and never sends a second start.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import aiohttp

INSTRUCTION = "move forward, then go to the trashcan on the right"
INSTRUCTION_SHA256 = "87ef6df01a076e5d78c06ad6badab2f5f8c1c80a587d687c7a4222fe5a35427e"


def now_pair() -> tuple[int, str]:
    return time.monotonic_ns(), datetime.now(timezone.utc).isoformat()


async def run(args: argparse.Namespace) -> dict:
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    assert hashlib.sha256(INSTRUCTION.encode()).hexdigest() == INSTRUCTION_SHA256

    events: list[dict] = []
    snapshots_path = run_dir / "snapshots.jsonl"
    base = f"http://{args.host}:{args.port}"

    def event(name: str, **fields) -> None:
        mono, utc = now_pair()
        events.append({"event": name, "mono_ns": mono, "utc": utc, **fields})

    termination = None
    termination_detail = ""
    native_stop_mono = None
    native_stop_seq = None
    accept_mono = None
    instruction_mono = None
    max_seq = 0
    snapshot_count = 0
    start_pose = None
    end_pose = None

    async with aiohttp.ClientSession() as http:
        async with http.ws_connect(f"{base}/ws", heartbeat=20.0) as ws:
            event("ws_connected", url=f"{base}/ws")
            snap_file = snapshots_path.open("w")

            async def drain(seconds: float) -> None:
                nonlocal snapshot_count, start_pose, end_pose, max_seq
                deadline = time.monotonic() + seconds
                while time.monotonic() < deadline:
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=max(0.01, deadline - time.monotonic()))
                    except asyncio.TimeoutError:
                        return
                    if msg.type is not aiohttp.WSMsgType.TEXT:
                        return
                    payload = json.loads(msg.data)
                    record(payload)

            def record(payload: dict) -> dict:
                nonlocal snapshot_count, start_pose, end_pose, max_seq
                mono, utc = now_pair()
                payload["_mono_ns"] = mono
                payload["_utc"] = utc
                snap_file.write(json.dumps(payload) + "\n")
                if payload.get("type") in ("runtime", "snapshot"):
                    snapshot_count += 1
                    data = payload.get("data", {})
                    pose = data.get("simulation", {}).get("pose")
                    if pose is not None:
                        if start_pose is None:
                            start_pose = pose
                        end_pose = pose
                    seq = int(data.get("vln", {}).get("sequence") or 0)
                    max_seq = max(max_seq, seq)
                return payload

            await ws.send_json({"type": "reset"})
            event("reset_sent")
            await drain(args.reset_settle)
            async with http.get(f"{base}/api/health") as resp:
                health = await resp.json()
            (run_dir / "health_after_reset.json").write_text(json.dumps(health, indent=2) + "\n")
            start_pose = health.get("simulation", {}).get("pose", start_pose)
            event("reset_settled", pose=start_pose)

            instruction_mono, instruction_utc = now_pair()
            await ws.send_json({"type": "set_vln", "enabled": True, "instruction": INSTRUCTION})
            event("instruction_sent", instruction_sha256=INSTRUCTION_SHA256)

            deadline = instruction_mono / 1e9 + args.wall_timeout
            post_stop_deadline = None
            try:
                while True:
                    now = time.monotonic()
                    if native_stop_mono is None and now > deadline:
                        termination = "watchdog_timeout"
                        break
                    if post_stop_deadline is not None and now >= post_stop_deadline:
                        termination = "model_stop"
                        break
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=0.25)
                    except asyncio.TimeoutError:
                        continue
                    if msg.type is not aiohttp.WSMsgType.TEXT:
                        if msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED,
                                        aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.ERROR):
                            termination = "disconnect"
                            termination_detail = str(msg.type)
                            break
                        continue
                    payload = record(json.loads(msg.data))
                    if payload.get("type") == "command_result":
                        if accept_mono is None and payload.get("ok") and "VLN started" in str(payload.get("message")):
                            accept_mono = payload["_mono_ns"]
                            event("instruction_accepted")
                        if not payload.get("ok"):
                            termination = "invalid_output"
                            termination_detail = f"command_result: {payload.get('message')}"
                            break
                        continue
                    if payload.get("type") not in ("runtime", "snapshot"):
                        continue
                    data = payload.get("data", {})
                    vln = data.get("vln", {})
                    control = data.get("control", {})
                    if str(vln.get("state")) == "ERROR":
                        termination = "invalid_output"
                        termination_detail = f"vln error: {vln.get('error')}"
                        break
                    if max_seq >= args.decision_cap:
                        termination = "decision_cap"
                        break
                    if (native_stop_mono is None and vln.get("stop") is True
                            and str(control.get("source")) == "idle"):
                        native_stop_mono = payload["_mono_ns"]
                        native_stop_seq = int(vln.get("sequence") or 0)
                        event("native_stop_observed", seq=native_stop_seq)
                        post_stop_deadline = time.monotonic() + args.post_stop
            finally:
                event("harness_stop_sending", termination=termination or "unset")
                try:
                    await ws.send_json({"type": "set_vln", "enabled": False})
                    event("harness_stop_sent")
                    await drain(0.5)
                except Exception as exc:  # pragma: no cover - connection already gone
                    event("harness_stop_failed", error=str(exc))
                snap_file.close()

    end_mono, end_utc = now_pair()
    episode = {
        "rep": args.rep,
        "run_dir": str(run_dir),
        "instruction": INSTRUCTION,
        "instruction_sha256": INSTRUCTION_SHA256,
        "termination": termination,
        "termination_detail": termination_detail,
        "decisions": max_seq,
        "native_stop_observed": native_stop_mono is not None,
        "native_stop_seq": native_stop_seq,
        "native_stop_mono_ns": native_stop_mono,
        "instruction_send_mono_ns": instruction_mono,
        "instruction_accept_mono_ns": accept_mono,
        "end_mono_ns": end_mono,
        "measured_seconds": (
            (native_stop_mono - instruction_mono) / 1e9 if native_stop_mono else
            (end_mono - instruction_mono) / 1e9
        ),
        "total_session_seconds": (end_mono - events[0]["mono_ns"]) / 1e9,
        "start_pose": start_pose,
        "end_pose": end_pose,
        "snapshot_count": snapshot_count,
        "post_stop_observe_s": args.post_stop,
        "wall_timeout_s": args.wall_timeout,
        "decision_cap": args.decision_cap,
        "harness_pid": os.getpid(),
        "ended_utc": end_utc,
    }
    (run_dir / "episode.json").write_text(json.dumps(episode, indent=2) + "\n")
    (run_dir / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    print(json.dumps(episode, indent=2), flush=True)
    return episode


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rep", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8088)
    ap.add_argument("--wall-timeout", type=float, default=180.0)
    ap.add_argument("--decision-cap", type=int, default=180)
    ap.add_argument("--post-stop", type=float, default=3.0)
    ap.add_argument("--reset-settle", type=float, default=2.0)
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
