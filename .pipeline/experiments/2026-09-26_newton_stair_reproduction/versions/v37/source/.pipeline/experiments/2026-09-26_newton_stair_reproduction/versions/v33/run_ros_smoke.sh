#!/bin/bash
# Run K5 (ros_smoke.py) in the pinned image with the environment native_inside.sh uses.
# Usage: run_ros_smoke.sh <multi|trial> <attempt>. Writes ros_smoke_<variant>_attemptNN.json and
# ros_smoke_<variant>_attemptNN_stdout.log into versions/v33 (the only writable mount), and first copies the
# harness it runs to k5_harness/ros_smoke_<variant>_attemptNN.py (checked unchanged afterwards). It refuses to
# start if any of these exists (review round 1, N2; round 2, N6: an explicit exit, since set -e does not stop
# a failed test inside an && list).
set -euo pipefail
VARIANT="$1"
ATTEMPT=$(printf '%02d' "$2")
P=/Users/sun/tongbu/study/phdproject/vla
E="${P}/.pipeline/experiments/2026-09-26_newton_stair_reproduction"
V="${E}/versions/v33"
LOG="${V}/ros_smoke_${VARIANT}_attempt${ATTEMPT}_stdout.log"
JSON="${V}/ros_smoke_${VARIANT}_attempt${ATTEMPT}.json"
HARNESS="${V}/k5_harness/ros_smoke_${VARIANT}_attempt${ATTEMPT}.py"
for existing in "${LOG}" "${JSON}" "${HARNESS}"; do
  if [ -e "${existing}" ]; then
    echo "refusing to overwrite ${existing}" >&2
    exit 1
  fi
done
cp -p "${V}/ros_smoke.py" "${HARNESS}"
set +e
docker run --rm --pull=never --platform=linux/amd64 -e ROS_DOMAIN_ID=219 -e ROS_LOCALHOST_ONLY=1 \
  -e PYTHONDONTWRITEBYTECODE=1 -v "${P}:${P}:ro" -v "${V}:${V}:rw" \
  -v "${E}/runtime/scan64_input_refresh_v31:/workspace:ro" --entrypoint /bin/bash \
  sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb -c "
set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
export PYTHONPATH=${E}/runtime/foreground_py310:${E}/runtime_sources/backend_adapter:${E}/runtime_sources/backend_ros:${E}/runtime_sources/bridge:${E}/runtime_sources/pct_runtime/python:\${PYTHONPATH:-}
export LD_LIBRARY_PATH=${E}/runtime_sources/pct_runtime/lib:\${LD_LIBRARY_PATH:-}
python3 ${V}/ros_smoke.py ${VARIANT} ${ATTEMPT}" 2>&1 | tee "${LOG}"
STATUS=${PIPESTATUS[0]}
set -e
# The copy is the harness that ran: it must still equal ros_smoke.py after the run, whether or not the run passed
# (review round 3, N3).
cmp "${V}/ros_smoke.py" "${HARNESS}"
exit "${STATUS}"
