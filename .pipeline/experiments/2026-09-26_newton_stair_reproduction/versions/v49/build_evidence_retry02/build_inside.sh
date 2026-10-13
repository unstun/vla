set -e
source /opt/ros/humble/setup.bash
cd /workspace
python3 --version
g++ --version
dpkg-query -W > package_versions.txt
colcon build --base-paths src --executor sequential --event-handlers console_direct+ --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF
