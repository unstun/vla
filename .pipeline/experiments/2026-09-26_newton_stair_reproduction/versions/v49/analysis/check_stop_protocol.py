"""Execute the exact frozen admission-handler AST against a minimal port fixture."""
import ast,hashlib,json,threading
from pathlib import Path
from types import SimpleNamespace
P=Path(__file__).resolve().parents[1]
source=P/'backend_ros/p2b_backend_ros/node.py'
tree=ast.parse(source.read_text())
klass=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='RosScanPort')
method=next(x for x in klass.body if isinstance(x,ast.FunctionDef) and x.name=='_on_admission')
namespace={'Any':object,'ScanAdmission':SimpleNamespace}
exec(compile(ast.Module(body=[method],type_ignores=[]),str(source),'exec'),namespace)
class Identity:
 def matches(self,other):return self is other
 def to_dict(self):return {'fixture':'same_exact_owner'}
identity=Identity()
results={}
for reason in ('native_solve_timeout','native_replan_exhausted'):
 closed=[]; zeros=[];faults=[]
 gate=SimpleNamespace(owner=identity,cancel_pending=False,close=closed.append)
 fixture=SimpleNamespace(gate=gate,_condition=threading.Condition(),_admissions=[],_identity_from_msg=lambda msg:identity,_fault=lambda *x:faults.append(x),_publish_zero=lambda:zeros.append(True),_last_block_reason='ok')
 msg=SimpleNamespace(consumer='fsm',status='rejected',message=reason,hold_confirmed=False,measured_stillness_confirmed=False)
 namespace['_on_admission'](fixture,msg)
 results[reason]={'closed':closed,'zero_publications':len(zeros),'faults':faults,'last_block_reason':fixture._last_block_reason}
assert results['native_solve_timeout']['closed']==[]
assert results['native_replan_exhausted']['closed']==['native_replan_exhausted']
result={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'method':'Exact frozen handler AST; synthetic same-owner admission. No ROS or physical-stop claim.','results':results}
(P/'analysis/stop_protocol_result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
