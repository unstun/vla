"""Case-owned execution binding; transform the immutable v241 launcher only."""
from pathlib import Path
import hashlib,json,sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from case_binding import CASE,case_scenario
PARENT=HERE.parent/'v241'
manifest=json.loads((PARENT/'manifest.json').read_text())
frozen=PARENT/'launch.py'
assert hashlib.sha256(frozen.read_bytes()).hexdigest()==manifest['source_files']['launch.py']
source=frozen.read_text().replace('v241','v243')
# These are adapter identity changes, never changes to inherited guard values.
source=source.replace('v243_linux_full_attempt01',f'v243_{CASE}_attempt01')
source=source.replace('v243-linux-full-attempt01',f'v243-{CASE.lower()}-attempt01')
source=source.replace('v243_linux_preflight01',f'v243_{CASE}_preflight01')
source=source.replace('v243-linux-preflight01',f'v243-{CASE.lower()}-preflight01')
source=source.replace("'historical_full'","'generalization'")
# Insert the parser adapter at the stable loop seam; avoid duplicating v196.
seam='    for before,after in changes.items():'
assert source.count(seam)==1
source=source.replace(seam,"    changes['(\"short_stair\", \"historical_full\", \"corner_start\")'] = '(\"short_stair\", \"historical_full\", \"corner_start\", \"generalization\")'\n"+seam)
seam='runtime_qualification=qualification,verify_integration_version=version_check,'
assert source.count(seam)==1
source=source.replace(seam,'runtime_qualification=qualification,building_scenario=case_scenario,verify_integration_version=version_check,')
# The source's __file__ remains this adapter, preserving HERE and V219=v243.
source=source.replace("REMOTE/'evidence/v243_physical_launch_once.json'","EVIDENCE/'physical_launch_once.json'")
outputs=('source_gate_before.json','resource_admission.json','execution_request.json',
         'native_preflight.json','graph_preflight.json','execution.json')
for name in outputs:source=source.replace("HERE/'"+name+"'","EVIDENCE/'"+name+"'")
namespace=dict(__file__=str(HERE/'launch.py'),__name__=__name__,case_scenario=case_scenario,
    EVIDENCE=Path('/data/sun/vla_mppi_20261009/generalization_v243')/CASE)
namespace['EVIDENCE'].mkdir(parents=True,exist_ok=True)
exec(compile(source,str(HERE/'adapted_v241_launch.py'),'exec'),namespace)
