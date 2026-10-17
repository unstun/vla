set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
python3 /attempt/replay_stair_inputs.py --inputs /attempt/inputs --output /attempt/result
