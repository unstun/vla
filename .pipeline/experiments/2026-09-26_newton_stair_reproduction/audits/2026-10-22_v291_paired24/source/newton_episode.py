"""Identical v237 recorder; explicitly select the already-qualified stance adapter."""
from common import *
import sys
FROZEN=VERSIONS/'v237/newton_episode.py'

def activate_only():
 adapter=load(STANCE/'activate.py','paired_activation').install()
 assert Path(adapter.__file__).resolve()==(STANCE/'newton_stance.py').resolve()
 assert sha(adapter.SOURCE)==sha(STANCE/'stance_hold.py')
 return dict(variant=VARIANT,locomotion=LOCOMOTION_NAME,adapter=str(adapter.__file__),
             source=str(adapter.SOURCE),source_sha256=sha(adapter.SOURCE),physics_steps=0)

def main():
 if '--activation-only' in sys.argv:
  print(json.dumps(activate_only()));return
 source=FROZEN.read_text()
 substitutions={"integration='v237', navigation='v232'":f"integration={VARIANT!r}, navigation={VARIANT!r}",
                "VERSIONS / 'v216/activate.py'":"STANCE / 'activate.py'", "locomotion='v216'":"locomotion=LOCOMOTION_NAME"}
 for old,new in substitutions.items():assert old in source;source=source.replace(old,new)
 sys.path.insert(0,str(FROZEN.parent));out=Path(os.environ['NEWTON_RUN_DIR'])
 (out/'paired_recorder_binding.json').write_text(json.dumps(dict(variant=VARIANT,
   original_sha256=sha(FROZEN),executed_sha256=hashlib.sha256(source.encode()).hexdigest(),
   substitutions=substitutions,physics_and_scanner_code_unchanged=True),indent=2)+'\n')
 (out/'executed_paired_recorder_adapter.py').write_text(source)
 scope=dict(__file__=str(FROZEN),__name__='paired_frozen_recorder',STANCE=STANCE,LOCOMOTION_NAME=LOCOMOTION_NAME)
 exec(compile(source,str(FROZEN),'exec'),scope);scope['main']()
if __name__=='__main__':main()
