set -e
export PYTHONPATH=/base/runtime_sources/backend_adapter:/base/runtime_sources/pct_runtime/python
export LD_LIBRARY_PATH=/base/runtime_sources/pct_runtime/lib
export OPENBLAS_NUM_THREADS=1
python3 /audit/probe.py
