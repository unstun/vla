"""Symbolize the replay's crash-time frames with addr2line inside the pinned image."""
from pathlib import Path
import json
import re
import subprocess

ATTEMPT = Path("/attempt")
BINARY = ATTEMPT / "probe_build/crash_probe"
log = (ATTEMPT / "replay.log").read_text(errors="replace").splitlines()

stack, inside = [], False
for line in log:
    if line.startswith("[CRASH-STACK-BEGIN]"):
        inside, stack = True, []
    elif line.startswith("[CRASH-STACK-END]"):
        inside = False
    elif inside:
        stack.append(line)

frames = []
for index, line in enumerate(stack):
    frame = {"index": index, "raw": line}
    match = re.search(r"crash_probe\(\+(0x[0-9a-f]+)\)", line)
    if match:
        # Return addresses point after the call; step back one byte to the call line.
        address = hex(int(match.group(1), 16) - 1)
        result = subprocess.run(["addr2line", "-f", "-C", "-i", "-p", "-e", str(BINARY), address],
                                capture_output=True, text=True, check=True)
        frame.update(address=address, source=result.stdout.strip().splitlines())
    frames.append(frame)

last_replay = [line for line in log if line.startswith("[CRASH-REPLAY]")][-1:]
report = {
    "exit_code": int((ATTEMPT / "probe_exit_code.txt").read_text().strip()),
    "signal": next((line for line in stack if line.startswith("[CRASH-SIGNAL]")), None),
    "assertion": [line for line in log if "Assertion" in line],
    "last_replay": last_replay[0] if last_replay else None,
    "frames": frames,
}
(ATTEMPT / "stack.json").write_text(json.dumps(report, indent=2) + "\n")
with (ATTEMPT / "stack.txt").open("w") as output:
    for frame in frames:
        output.write(f"#{frame['index']} {frame['raw']}\n")
        for source in frame.get("source", []):
            output.write(f"      {source}\n")
print(json.dumps({key: report[key] for key in ("exit_code", "signal", "assertion", "last_replay")}, indent=2))
