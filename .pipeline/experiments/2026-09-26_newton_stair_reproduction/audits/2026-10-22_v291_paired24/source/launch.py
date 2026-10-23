"""Original bounded physical protocol, rebound to a unique paired invocation."""
from common import *
import sys,types,shutil,socket,time
CASE=os.environ['PAIR_CASE'];REPEAT=int(os.environ.get('PAIR_REPEAT','1'));assert CASE in ('D07','CD12','S04','A04') and 1<=REPEAT<=3
PREFLIGHT='--preflight-only' in sys.argv
RUN=f'pair24_{VARIANT}_{CASE}_r{REPEAT}'+('_preflight'+os.environ.get('PAIR_PREFLIGHT_TAG','01') if PREFLIGHT else '')
TASK=CAMPAIGN/'physical_runs'/RUN;EVIDENCE=CAMPAIGN/'evidence'/RUN
EVIDENCE.mkdir(parents=True,exist_ok=True)
os.environ['V290_CASE_ID']=CASE
sys.path.insert(0,str(OLD/'migration'));original=load(OLD/'migration/physical.py','parent_physical')

def admission():
 assert json.loads((VERSION_ROOT/'benchmark/offline_gate.json').read_text())['passed']
 return dict(physical_execution_authorized=True,scope='24 user-authorized same-host paired attempts',variant=VARIANT)

def resource_admit():
 source=(VERSIONS/'v290/resource_admission.py').read_text();old="OUTPUT_ROOT=Path('/home/sun/vla_exec/physical_runs_v290')";assert source.count(old)==1
 scope=dict(__file__=str(VERSIONS/'v290/resource_admission.py'));exec(compile(source.replace(old,'OUTPUT_ROOT=Path('+repr(str(CAMPAIGN/'physical_runs'))+')'),'<paired-resource>','exec'),scope)
 result=scope['admit']();result.update(load_average=list(os.getloadavg()),logical_cpus=os.cpu_count(),physics_cpu_affinity=sorted(os.sched_getaffinity(0)))
 return result


def materialize():
 source=(BINDING/'parent_physical_template.py').read_text()
 changes={
  "'if integration_version != \\\"v290\\\":'":"'if integration_version != \\\"'+VARIANT+'\\\":'",
  'This trial requires frozen integration version v290':'This trial requires the selected frozen integration version',
  "assert version=='v290'":"assert version==VARIANT",
  "execution='v290',navigation='v290'":"execution=VARIANT,navigation=VARIANT",
  "integration_version='v290'":"integration_version=VARIANT",
  "'--integration-version','v290'":"'--integration-version',VARIANT",
  "LOCOMOTION_VERSION=V216":"LOCOMOTION_VERSION=STANCE",
  "NAVIGATION_VERSION=V219,TELEMETRY_VERSION=V219":"NAVIGATION_VERSION=BINDING,TELEMETRY_VERSION=BINDING",
  "if name=='native_graph.py':return V219/name":"if name=='native_graph.py':return BINDING/name",
  "if name=='newton_episode.py':return V219/name":"if name=='newton_episode.py':return BINDING/name",
  "REMOTE/'migration/physical.py'":"BINDING/'launch.py'",
  "REMOTE/'migration/physical_manifest01.json'":"BINDING/'campaign_manifest.json'",
  "str(V219/'native_graph.py')":"str(BINDING/'native_graph.py')",
  "str(REMOTE/'migration/bin')":"str(BINDING/'bin')",
  "'locomotion':'v216'":"'locomotion':LOCOMOTION_NAME",
  "locomotion='v216 supported transfer'":"locomotion=LOCOMOTION_NAME",
  "integration='v290'":"integration=VARIANT",
  "navigation='v290 shared endpoint/local geometry and measured-state continuity'":"navigation=VARIANT",
  "'-e','ROS_DOMAIN_ID=219'":"'-e','PAIR_VARIANT='+VARIANT,'-e','ROS_DOMAIN_ID=219'",
  "'-v',f'{REMOTE}:{REMOTE}:ro'":"'-v',f'{REMOTE}:{REMOTE}:ro','-v',f'{CAMPAIGN}:{CAMPAIGN}:ro','-v',f'{NEW}:{NEW}:ro'",
 }
 # The dictionary expression itself contains the quoted version check.
 first="'if integration_version != \\\"v290\\\":'"
 changes.pop(first)
 before="'if integration_version != \"v290\":'"
 assert before in source
 source=source.replace(before,"('if integration_version != '+repr(VARIANT)+':')")
 changes={k:v for k,v in changes.items() if k!="'locomotion':'v216'"}
 for before,after in changes.items():assert before in source,before;source=source.replace(before,after)
 return source


def main():
 source=materialize();compile(source,'<paired-physical>','exec')
 derived=EVIDENCE/'bound_launch.py'
 if derived.exists():assert derived.read_text()==source
 else:derived.write_text(source)
 (EVIDENCE/'binding.json').write_text(json.dumps(dict(variant=VARIANT,case_id=CASE,repeat=REPEAT,run=RUN,
   parent_template_sha256=sha(BINDING/'parent_physical_template.py'),executed_sha256=hashlib.sha256(source.encode()).hexdigest(),
   native_root=str(VERSION_ROOT/'native'),locomotion_root=str(STANCE)),indent=2)+'\n')
 case=original.bind_case();sys.modules['resource_admission']=types.SimpleNamespace(admit=resource_admit)
 scope=dict(__file__=str(VERSIONS/'v290/launch.py'),__name__='paired_execution',EVIDENCE=EVIDENCE,
            case_scenario=case.case_scenario,verify_sources=verify,verify_execution_admission=admission,
            BINDING=BINDING,CAMPAIGN=CAMPAIGN,NEW=NEW,VARIANT=VARIANT,STANCE=STANCE,LOCOMOTION_NAME=LOCOMOTION_NAME)
 exec(compile(source,str(derived),'exec'),scope)
 scope.update(TASK=TASK,RUN=RUN,WORK=VERSION_ROOT/'native',CONTAINER=RUN.lower().replace('_','-'))
 original_module=scope['module'];scope['module']=lambda path,name:types.SimpleNamespace(verify=original.verify_profile) if path==VERSIONS/'v290/verify_profile.py' else original_module(path,name)
 if '--derive-only' in sys.argv:print(json.dumps(dict(passed=True,physics_steps=0,run=RUN)));return
 if Path(sys.argv[0]).name=='run_bounded.py':scope['supervisor']()
 elif '--episode' in sys.argv:scope['episode']()
 else:scope['launch']()
if __name__=='__main__':main()
