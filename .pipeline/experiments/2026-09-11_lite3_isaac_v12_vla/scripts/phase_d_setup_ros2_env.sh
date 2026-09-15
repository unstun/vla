#!/usr/bin/env bash
# Phase D.0c environment: ROS 2 Jazzy + Nav2 collision_monitor from RoboStack, in a task-owned prefix on the host.
# Approved by Dr Sun 2026-09-14 ("RoboStack Jazzy conda env"). No sudo, no Docker, nothing outside $ROOT is written.
#
#   bash phase_d_setup_ros2_env.sh dry-run   # solve only; prints package count and download size
#   bash phase_d_setup_ros2_env.sh install   # create the environment, verify, export the explicit lock
#
# Channels: robostack-jazzy from anaconda.org (not mirrored), conda-forge from the Tsinghua mirror (anaconda.org is
# slow from this host). Rollback: rm -rf "$ROOT/ros2_jazzy" "$ROOT/mamba_root".
set -euo pipefail
MODE=${1:?dry-run or install}
ROOT=${VLA_RUN_ROOT:-$HOME/vla-runs/2026-09-11_lite3_isaac_v12_vla}
MM=$ROOT/tools/micromamba
MM_SHA256=${MM_SHA256:?expected sha256 of the micromamba binary}
ENV=$ROOT/ros2_jazzy
export MAMBA_ROOT_PREFIX=$ROOT/mamba_root
MIN_FREE_GB=8
PACKAGES=(
  "ros-jazzy-nav2-collision-monitor=1.3.12"
  ros-jazzy-nav2-lifecycle-manager
  ros-jazzy-rclpy ros-jazzy-sensor-msgs ros-jazzy-nav-msgs ros-jazzy-geometry-msgs ros-jazzy-rosgraph-msgs
  ros-jazzy-ros2cli ros-jazzy-ros2run ros-jazzy-ros2pkg ros-jazzy-ros2topic ros-jazzy-ros2param ros-jazzy-ros2lifecycle
)
CHANNELS=(--override-channels --strict-channel-priority
  -c https://conda.anaconda.org/robostack-jazzy
  -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge)

[[ -x $MM ]] || { echo "missing $MM" >&2; exit 64; }
[[ $(sha256sum "$MM" | awk '{print $1}') == "$MM_SHA256" ]] || { echo "micromamba sha256 mismatch" >&2; exit 65; }
free_gb=$(df -Pk "$ROOT" | awk 'NR==2 {print int($4 / 1048576)}')
(( free_gb >= MIN_FREE_GB )) || { echo "refusing: ${free_gb} GB free < ${MIN_FREE_GB} GB" >&2; exit 66; }
echo "micromamba $("$MM" --version); free ${free_gb} GB"

case $MODE in
  dry-run)
    "$MM" create -y --dry-run --json -p "$ENV" "${CHANNELS[@]}" "${PACKAGES[@]}" > "$ROOT/ros2_jazzy_dryrun.json"
    python3 - "$ROOT/ros2_jazzy_dryrun.json" <<'EOF'
import json, sys
j = json.load(open(sys.argv[1]))
link = j.get('actions', {}).get('LINK', [])
fetch = j.get('actions', {}).get('FETCH', [])
by_channel = {}
for p in fetch:
    key = 'robostack-jazzy' if 'robostack' in p.get('channel', '') or 'robostack' in p.get('url', '') else 'conda-forge'
    by_channel.setdefault(key, [0, 0]); by_channel[key][0] += 1; by_channel[key][1] += int(p.get('size', 0))
print('packages to link', len(link), '| to fetch', len(fetch), '| fetch MB',
      round(sum(int(p.get('size', 0)) for p in fetch) / 1e6, 1), '| by channel', {k: (v[0], round(v[1] / 1e6, 1)) for k, v in by_channel.items()})
cm = [p for p in link if p['name'] in ('ros-jazzy-nav2-collision-monitor', 'ros2-nav2-collision-monitor', 'python')]
print('key packages', [(p['name'], p['version'], p['build_string']) for p in cm])
EOF
    ;;
  install)
    [[ ! -e $ENV ]] || { echo "refusing: $ENV exists" >&2; exit 67; }
    "$MM" create -y -p "$ENV" "${CHANNELS[@]}" "${PACKAGES[@]}"
    "$MM" env export -p "$ENV" --explicit --md5 > "$ROOT/ros2_jazzy_explicit_lock.txt"
    "$MM" list -p "$ENV" --json > "$ROOT/ros2_jazzy_list.json"
    echo "## verify"
    "$MM" run -p "$ENV" bash -c 'export ROS_DOMAIN_ID=87 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST;
      python -c "import rclpy, sensor_msgs.msg, nav_msgs.msg, geometry_msgs.msg; print(\"rclpy ok\")";
      ros2 pkg prefix nav2_collision_monitor; ros2 pkg executables nav2_collision_monitor;
      ls "$CONDA_PREFIX"/share/nav2_collision_monitor/params 2>/dev/null'
    du -sh "$ENV" "$MAMBA_ROOT_PREFIX"
    df -h "$ROOT" | tail -1
    echo ROS2_ENV_DONE
    ;;
  *) echo "unknown mode $MODE" >&2; exit 64 ;;
esac
