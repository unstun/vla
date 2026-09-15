"""Stationary recorder dry run with the model disconnected. No manual motion."""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import aiohttp


async def run(args):
    out = Path(args.run_dir)
    out.mkdir(parents=True, exist_ok=True)
    events = []

    def event(name, **fields):
        events.append({"event": name, "mono_ns": time.monotonic_ns(),
                       "utc": datetime.now(timezone.utc).isoformat(), **fields})

    base = f"http://{args.host}:{args.port}"
    snaps = (out / "snapshots.jsonl").open("w")
    async with aiohttp.ClientSession() as http:
        async with http.ws_connect(f"{base}/ws", heartbeat=20.0) as ws:
            event("ws_connected")
            await ws.send_json({"type": "reset"})
            event("reset_sent")
            deadline = time.monotonic() + args.seconds
            count = 0
            while time.monotonic() < deadline:
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue
                if msg.type is not aiohttp.WSMsgType.TEXT:
                    break
                payload = json.loads(msg.data)
                payload["_mono_ns"] = time.monotonic_ns()
                snaps.write(json.dumps(payload) + "\n")
                count += 1
            event("harness_stop_sending", reason="dry_run_complete")
            await ws.send_json({"type": "stop"})
            event("harness_stop_sent")
            await asyncio.sleep(0.5)
    snaps.close()
    summary = {"kind": "harness_check", "model_connected": False, "manual_motion": False,
               "seconds": args.seconds, "snapshots": count,
               "start_mono_ns": events[0]["mono_ns"], "end_mono_ns": events[-1]["mono_ns"]}
    (out / "check.json").write_text(json.dumps(summary, indent=2) + "\n")
    (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    print(json.dumps(summary), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8088)
    ap.add_argument("--seconds", type=float, default=12.0)
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
