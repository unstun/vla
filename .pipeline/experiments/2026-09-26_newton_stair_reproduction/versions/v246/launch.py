"""One attempt per admitted frozen case; inherit v241 numerical execution gates."""
from pathlib import Path
import hashlib,json,os,sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from case_binding import CASE,case_scenario
from identity import verify_sources
PARENT=HERE.parent/'v241';manifest=json.loads((PARENT/'manifest.json').read_text());frozen=PARENT/'launch.py'
assert hashlib.sha256(frozen.read_bytes()).hexdigest()==manifest['source_files']['launch.py']
source=frozen.read_text().replace('v241','v246')
source=source.replace('v246_linux_full_attempt01',f'v246_{CASE}_attempt01').replace('v246-linux-full-attempt01',f'v246-{CASE.lower()}-attempt01')
source=source.replace('v246_linux_preflight01',f'v246_{CASE}_preflight01').replace('v246-linux-preflight01',f'v246-{CASE.lower()}-preflight01')
source=source.replace("WORK=REMOTE/'cooperative_search_v240'","WORK=REMOTE/'endpoint_connectivity_v244/native'")
source=source.replace('def verify_sources():','def inherited_verify_sources_unused():')
# Port admission must reject active listeners, while allowing the previous
# owned TCP server's TIME_WAIT sockets, as the runtime server itself does.
source=source.replace("with socket.socket() as probe:probe.bind(('127.0.0.1',port))",
 "with socket.socket() as probe:\n            probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)\n            probe.bind(('127.0.0.1',port))")

source=source.replace("'historical_full'","'generalization'")
seam='    for before,after in changes.items():';assert source.count(seam)==1
source=source.replace(seam,"    changes['(\"short_stair\", \"historical_full\", \"corner_start\")'] = '(\"short_stair\", \"historical_full\", \"corner_start\", \"generalization\")'\n"+seam)
seam='runtime_qualification=qualification,verify_integration_version=version_check,';assert source.count(seam)==1
source=source.replace(seam,'runtime_qualification=qualification,building_scenario=case_scenario,verify_integration_version=version_check,')
source=source.replace("VERSIONS/'v240/results/offline_gate.json'","VERSIONS/'v245/results/protocol_offline_gate.json'")
source=source.replace('v240 terminal continuity on v232 shared score/height/feedback','v244 endpoint recovery on frozen v240 SCAN')
source=source.replace("'v240_runtime_binding.json'","'v244_runtime_binding.json'").replace("navigation='v240'","navigation='v244'")
source=source.replace("REMOTE/'evidence/v246_physical_launch_once.json'","EVIDENCE/'physical_launch_once.json'")
for name in ('source_gate_before.json','resource_admission.json','execution_request.json','native_preflight.json','graph_preflight.json','execution.json'):
 source=source.replace("HERE/'"+name+"'","EVIDENCE/'"+name+"'")
# Execute definitions first, so the bound identity checker owns every launch.
namespace=dict(__file__=str(HERE/'launch.py'),__name__='v246_inherited_launch',case_scenario=case_scenario,
 verify_sources=verify_sources,EVIDENCE=Path('/data/sun/vla_mppi_20261009/generalization_v246')/CASE/('preflight' if '--preflight-only' in sys.argv else 'execution'))
namespace['EVIDENCE'].mkdir(parents=True,exist_ok=True)
exec(compile(source,str(HERE/'adapted_v241_launch.py'),'exec'),namespace)
if __name__=='__main__':
 if Path(sys.argv[0]).name=='run_bounded.py':namespace['supervisor']()
 elif '--episode' in sys.argv:namespace['episode']()
 else:
  if '--preflight-only' in sys.argv:
   tag=os.environ.get('V246_PREFLIGHT_ID','01');assert tag.isdigit() and len(tag)==2
   namespace.update(TASK=namespace['REMOTE']/f'trials/v246_{CASE}_preflight{tag}',RUN=f'v246_{CASE}_preflight{tag}',CONTAINER=f'v246-{CASE.lower()}-preflight{tag}')
  namespace['launch']()
