#!/bin/bash
# Read-only capture of the Lite3 head camera plus torso IMU and joint states. No actuation.
# Usage: capture_head_cam.sh <label> [n_frames]
# Requires: Mac joined to the robot Wi-Fi (192.168.2.1 reachable), ffmpeg, ssh key for ysc@192.168.2.1.
set -u
LABEL="${1:?label}"; N="${2:-3}"
HERE="$(cd "$(dirname "$0")" && pwd)"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$HERE/capture_${TS}_${LABEL}"; mkdir -p "$OUT"
echo "out: $OUT"
# IMU + joints + ultrasound (Xavier via motion host jump)
ssh -o BatchMode=yes -o ConnectTimeout=8 -o ProxyJump=ysc@192.168.2.1 ysc@192.168.1.103 \
  'source /opt/ros/noetic/setup.bash 2>/dev/null; export ROS_MASTER_URI=http://localhost:11311;
   echo "# utc $(date -u +%Y-%m-%dT%H:%M:%SZ)"; echo "## /imu/data"; timeout 6 rostopic echo -n1 /imu/data 2>&1;
   echo "## /joint_states"; timeout 6 rostopic echo -n1 /joint_states 2>&1 | grep -E "^name|^  - |^position";
   echo "## /us_publisher/ultrasound_distance"; timeout 5 rostopic echo -n1 /us_publisher/ultrasound_distance 2>&1 | head -2' \
  > "$OUT/xavier_state.txt" 2>&1
# frames, 1 s apart, from the live H.264 stream
for i in $(seq 1 "$N"); do
  ffmpeg -v error -y -rtsp_transport tcp -timeout 8000000 -i rtsp://192.168.2.1:8554/test -frames:v 1 "$OUT/frame_${i}.png" 2>>"$OUT/ffmpeg_err.txt"
  sleep 1
done
python3 - "$OUT" <<'PY'
import sys,re,math,glob,os
out=sys.argv[1]; t=open(f"{out}/xavier_state.txt").read()
m=re.search(r"orientation:\s*\n\s*x: (\S+)\n\s*y: (\S+)\n\s*z: (\S+)\n\s*w: (\S+)",t)
if m:
    x,y,z,w=map(float,m.groups())
    roll=math.degrees(math.atan2(2*(w*x+y*z),1-2*(x*x+y*y)))
    pitch=math.degrees(math.asin(max(-1,min(1,2*(w*y-z*x)))))
    print(f"torso roll {roll:+.2f} deg, pitch {pitch:+.2f} deg (ZYX from /imu/data quaternion)")
    open(f"{out}/derived.txt","w").write(f"roll_deg {roll:.3f}\npitch_deg {pitch:.3f}\n")
p=re.search(r"position: \[([^\]]+)\]",t)
if p:
    v=[float(s) for s in p.group(1).split(",")]; print("knees (rad):", [round(v[i],3) for i in (2,5,8,11)])
print("frames:", sorted(os.path.basename(f) for f in glob.glob(f"{out}/frame_*.png")))
PY
(cd "$OUT" && shasum -a 256 frame_*.png xavier_state.txt > SHA256SUMS.txt)
echo "done: $OUT"
