"""Frozen v232 graph/driver with new execution tag and cross-floor profile."""
from pathlib import Path
FROZEN=Path(__file__).resolve().parent.parent/'v232/native_graph.py'
source=FROZEN.read_text()
before='request.get("integration_version") != "v232"'
assert source.count(before)==1
source=source.replace(before,'request.get("integration_version") != "v243"')
before='("historical_full", "corner_start")'
assert source.count(before)==1
source=source.replace(before,'("historical_full", "corner_start", "generalization")')
namespace={'__file__':str(FROZEN),'__name__':'v243_frozen_v232_graph'}
exec(compile(source,str(FROZEN),'exec'),namespace)
if __name__=='__main__':namespace['main']()
