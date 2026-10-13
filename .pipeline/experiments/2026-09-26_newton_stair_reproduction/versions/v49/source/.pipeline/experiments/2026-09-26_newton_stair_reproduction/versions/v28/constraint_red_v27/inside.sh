set -e
source /opt/ros/humble/setup.bash
python3 /attempt/extract.py /workspace /attempt/generated
cmake -S /attempt -B /attempt/build
cmake --build /attempt/build -j2
python3 /attempt/run_cases.py
