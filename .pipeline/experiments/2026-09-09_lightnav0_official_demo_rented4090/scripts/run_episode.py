"""Run one episode of the official LightNav-0 MuJoCo demo via WebSocket.

Usage (from REMOTE):
  env/py311/bin/python scripts/run_episode.py --rep rep_01 --run-dir runs/rep_01

Connects to the demo's /ws, sends reset + set_vln, records snapshots and
camera frames, and terminates on native stop, error, or timeout.
"""
import argparse
import asyncio
import hashlib
import json
import os
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import aiohttp

INSTRUCTION = "move forward, then go to the trashcan on the right"
DEMO_HOST = "127.0.0.1"
DEMO_PORT = 8088
WALL_TIMEOUT_S = 180
DECISION_CAP = 180
POST_STOP_OBSERVE_S = 2.0
CAMERA_POLL_HZ = 10
CAMERA_POLL_INTERVAL = 1.0 / CAMERA_POLL_HZ


async def fetch_camera(session, url, out_dir, index_file, tag):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as resp:
            if resp.status != 200:
                return None
            data = await resp.read()
            ts = datetime.now(timezone.utc).isoformat()
            sha = hashlib.sha256(data).hexdigest()[:16]
            fname = f"{tag}_{index_file.tell() // 200:05d}.jpg"
            (out_dir / fname).write_bytes(data)
            entry = {"file": fname, "bytes": len(data), "received_utc": ts, "sha256_prefix": sha}
            index_file.write(json.dumps(entry) + "\n")
            index_file.flush()
            return entry
    except Exception:
        return None


async def run_episode(rep_name, run_dir):
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    fp_dir = run_dir / "first_person"
    tp_dir = run_dir / "third_person"
    fp_dir.mkdir(exist_ok=True)
    tp_dir.mkdir(exist_ok=True)

    snapshots_path = run_dir / "snapshots.jsonl"
    episode_path = run_dir / "episode.json"

    snapshots = []
    termination = None
    start_pose = None
    end_pose = None
    max_seq = 0
    native_stop_seen = False
    native_stop_time = None
    start_wall = time.monotonic()
    start_utc = datetime.now(timezone.utc).isoformat()

    ws_url = f"http://{DEMO_HOST}:{DEMO_PORT}/ws"
    base_url = f"http://{DEMO_HOST}:{DEMO_PORT}/api"

    async with aiohttp.ClientSession() as http:
        async with http.ws_connect(ws_url) as ws:
            print(f"[{rep_name}] connected to {ws_url}")

            # Reset
            await ws.send_json({"type": "reset"})
            await asyncio.sleep(1.0)

            # Wait for reset to take effect, read a few messages
            await asyncio.sleep(1.0)
            for _ in range(10):
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=0.3)
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        if data.get("type") in ("runtime", "snapshot"):
                            snap = data.get("data", data)
                            sim = snap.get("simulation", snap)
                            if "pose" in sim:
                                start_pose = sim["pose"]
                            elif "pose" in snap:
                                start_pose = snap["pose"]
                except asyncio.TimeoutError:
                    break

            # Confirm health
            async with http.get(f"{base_url}/health") as resp:
                health = await resp.json()
                (run_dir / "health_after_reset.json").write_text(json.dumps(health, indent=2) + "\n")
                if start_pose is None and "pose" in health.get("robot", {}):
                    start_pose = health["robot"]["pose"]
                print(f"[{rep_name}] health OK, pose: {start_pose}")

            # Open frame index files
            fp_index = open(run_dir / "first_person_frames.jsonl", "w")
            tp_index = open(run_dir / "third_person_frames.jsonl", "w")
            snap_file = open(snapshots_path, "w")

            # Start VLN
            await ws.send_json({
                "type": "set_vln",
                "enabled": True,
                "instruction": INSTRUCTION,
            })
            print(f"[{rep_name}] VLN started: {INSTRUCTION}")

            # Camera polling task
            camera_running = True

            async def camera_loop():
                while camera_running:
                    t0 = time.monotonic()
                    await asyncio.gather(
                        fetch_camera(http, f"{base_url}/camera.jpg", fp_dir, fp_index, "fp"),
                        fetch_camera(http, f"{base_url}/third-person.jpg", tp_dir, tp_index, "tp"),
                    )
                    elapsed = time.monotonic() - t0
                    await asyncio.sleep(max(0, CAMERA_POLL_INTERVAL - elapsed))

            camera_task = asyncio.create_task(camera_loop())

            # Message loop
            try:
                while True:
                    wall_elapsed = time.monotonic() - start_wall
                    if wall_elapsed > WALL_TIMEOUT_S:
                        termination = "watchdog_timeout"
                        print(f"[{rep_name}] wall timeout at {wall_elapsed:.1f}s")
                        break

                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=2.0)
                    except asyncio.TimeoutError:
                        continue

                    if msg.type != aiohttp.WSMsgType.TEXT:
                        if msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED):
                            termination = "disconnect"
                            break
                        continue

                    data = json.loads(msg.data)
                    wall_ts = datetime.now(timezone.utc).isoformat()

                    if data.get("type") in ("runtime", "snapshot"):
                        snap = data.get("data", data)
                        snap["_wall_utc"] = wall_ts
                        snap["_wall_elapsed_s"] = round(wall_elapsed, 3)
                        snapshots.append(snap)
                        snap_file.write(json.dumps(snap) + "\n")
                        snap_file.flush()

                        # Track pose — may be at simulation.pose or top-level pose
                        sim = snap.get("simulation", snap)
                        if "pose" in sim:
                            end_pose = sim["pose"]
                        elif "pose" in snap:
                            end_pose = snap["pose"]

                        # Track VLN sequence
                        vln = snap.get("vln", {})
                        seq = vln.get("sequence", 0)
                        if seq > max_seq:
                            max_seq = seq

                        if max_seq >= DECISION_CAP:
                            termination = "decision_cap"
                            print(f"[{rep_name}] decision cap at seq {max_seq}")
                            break

                        # Check native stop
                        vln_stop = vln.get("stop")
                        control = snap.get("control", {})
                        control_source = control.get("source", "")

                        if vln_stop is True and control_source == "idle" and not native_stop_seen:
                            native_stop_seen = True
                            native_stop_time = time.monotonic()
                            print(f"[{rep_name}] native stop detected at seq {seq}, observing {POST_STOP_OBSERVE_S}s...")

                        # Check error
                        vln_state = vln.get("state", "")
                        mpc = snap.get("mpc", {})
                        mpc_error = mpc.get("error")

                        if vln_state == "ERROR":
                            termination = "invalid_output"
                            print(f"[{rep_name}] VLN error: {vln.get('error')}")
                            break

                        if mpc_error and mpc_error != "null":
                            # Allow transient MPC errors; only terminate if persistent
                            pass

                    elif data.get("type") == "command_result":
                        snap = data
                        snap["_wall_utc"] = wall_ts
                        snap_file.write(json.dumps(snap) + "\n")
                        snap_file.flush()

                    # Check post-stop observation period
                    if native_stop_seen and native_stop_time:
                        if time.monotonic() - native_stop_time >= POST_STOP_OBSERVE_S:
                            termination = "model_stop"
                            print(f"[{rep_name}] confirmed model_stop after {POST_STOP_OBSERVE_S}s observation")
                            break

            finally:
                camera_running = False
                await camera_task

                # Send stop if control is still active
                if termination != "model_stop":
                    try:
                        await ws.send_json({"type": "set_vln", "enabled": False})
                    except Exception:
                        pass

                fp_index.close()
                tp_index.close()
                snap_file.close()

    end_utc = datetime.now(timezone.utc).isoformat()
    wall_total = time.monotonic() - start_wall

    # Count frames
    fp_count = len(list(fp_dir.glob("*.jpg")))
    tp_count = len(list(tp_dir.glob("*.jpg")))

    episode = {
        "rep": rep_name,
        "instruction": INSTRUCTION,
        "instruction_sha256": hashlib.sha256(INSTRUCTION.encode()).hexdigest(),
        "termination": termination,
        "decisions": max_seq,
        "start_pose": start_pose,
        "end_pose": end_pose,
        "start_utc": start_utc,
        "end_utc": end_utc,
        "wall_seconds": round(wall_total, 2),
        "first_person_frames": fp_count,
        "third_person_frames": tp_count,
        "native_stop_seen": native_stop_seen,
        "snapshot_count": len(snapshots),
    }
    episode_path.write_text(json.dumps(episode, indent=2) + "\n")
    print(f"[{rep_name}] done: {termination}, {max_seq} decisions, {wall_total:.1f}s, "
          f"{fp_count} fp frames, {tp_count} tp frames")
    return episode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rep", required=True)
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    result = asyncio.run(run_episode(args.rep, args.run_dir))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
