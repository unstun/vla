"""Execute frozen v232 graph/driver; adapt only the execution version tag."""
from pathlib import Path
import hashlib,json
FROZEN=Path(__file__).resolve().parent.parent/'v232/native_graph.py'
source=FROZEN.read_text()
before='request.get("integration_version") != "v232"'
assert source.count(before)==1
source=source.replace(before,'request.get("integration_version") != "v241"')
source=source.replace('v232 execution requires its v230 navigation binding','v241 execution requires its frozen v232 navigation binding')
namespace={'__file__':str(FROZEN),'__name__':'v241_frozen_v232_graph'}
exec(compile(source,str(FROZEN),'exec'),namespace)
if __name__=='__main__':
    namespace['main']()
