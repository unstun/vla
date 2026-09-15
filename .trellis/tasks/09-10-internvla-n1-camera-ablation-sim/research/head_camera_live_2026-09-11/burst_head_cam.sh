#!/bin/bash
# Read-only burst capture of the Lite3 head camera stream: <fps> frames/s for <seconds>, JPEG q=2, into <outdir>.
# Usage: burst_head_cam.sh <outdir> [seconds=75] [fps=2]
set -u
OUT="${1:?outdir}"; SEC="${2:-75}"; FPS="${3:-2}"
mkdir -p "$OUT"
echo "burst start $(date -u +%Y-%m-%dT%H:%M:%SZ) sec=$SEC fps=$FPS out=$OUT" | tee "$OUT/burst_log.txt"
ffmpeg -v error -y -rtsp_transport tcp -timeout 8000000 -i rtsp://192.168.2.1:8554/test -t "$SEC" -vf "fps=$FPS" -q:v 2 "$OUT/b_%04d.jpg" 2>>"$OUT/burst_log.txt"
echo "burst end $(date -u +%Y-%m-%dT%H:%M:%SZ) frames=$(ls "$OUT"/b_*.jpg 2>/dev/null | wc -l | tr -d ' ')" | tee -a "$OUT/burst_log.txt"
