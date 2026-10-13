"""Production gateway callbacks with mocked PCT/IO; no physics claim."""
import copy,threading,unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock
from builtin_interfaces.msg import Time
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path
from lite3_nav2_interfaces.srv import PlanRoute,BindRoute
from lite3_nav2_bridge.gateway import MissionGateway
from backend_adapter.pct_ipc import PlannerRejected,PlannerUnavailable
from backend_adapter.contracts import NativeRoute
from p2b_backend_ros.node import RosScanPort
class Tests(unittest.TestCase):
 def setUp(self):
  g=self.g=object.__new__(MissionGateway);g.lock=threading.RLock();g.frame='world';g.height=.3
  g.mission_id='mission';g.request_id='request';g.goal_id='goal';g.generation=2;g.closing=False;g.stopping=False;g.binding=None;g.ready=None
  g.config={'run_id':'run','run_epoch_ns':1,'map':{'epoch':'map','revision':1}}
  g.gate=NS(owner=None);g.path_heading=False;g.heading_resolved=True
  g.goal=PoseStamped();g.goal.header.frame_id='world';g.goal.pose.position.x=9.;g.goal.pose.position.z=3.3;g.goal.pose.orientation.w=1.;g.binding_goal=copy.deepcopy(g.goal.pose)
  path=Path();path.header.frame_id='world';path.header.stamp=Time(sec=1)
  a=PoseStamped();a.header=copy.deepcopy(path.header);a.pose.orientation.w=1.;a.pose.position.z=3.3;path.poses=[a,copy.deepcopy(g.goal)]
  route=NativeRoute('old_route','goal','world','map',1,((0.,0.,3.3),(9.,0.,3.3)))
  g.planned=(path,route);g.last_released_route=('mission','old_route',2);g.plan_bind_ready=False;g.plan_bind_reuse=False
  g.pct=NS(plan=Mock(side_effect=PlannerRejected('pct_no_route')))
  g.get_clock=lambda:NS(now=lambda:NS(to_msg=lambda:Time(sec=2)))
  g.get_logger=lambda:NS(warning=lambda *x:None)
  g.port=NS(_fill_identity=lambda msg,identity:RosScanPort._fill_identity(None,msg,identity))
  g.binding_pub=NS(publish=lambda msg:setattr(g,'ready',copy.deepcopy(msg)))
  self.request=PlanRoute.Request();self.request.goal=copy.deepcopy(g.goal);self.request.start=copy.deepcopy(g.goal);self.request.start.pose.position.x=8.076472282409668
 def replan(self):return self.g.plan_route(self.request,PlanRoute.Response())
 def bind(self):
  r=BindRoute.Request();r.goal=copy.deepcopy(self.g.goal);r.path=copy.deepcopy(self.g.planned[0]);return self.g.bind_route(r,BindRoute.Response())
 def test_no_route_after_measured_release_reuses_exact_reference_once(self):
  before=copy.deepcopy(self.g.planned);r=self.replan();self.assertFalse(r.accepted);self.assertEqual(r.message,'pct_no_route');self.assertTrue(self.g.plan_bind_ready);self.assertTrue(self.g.plan_bind_reuse);self.assertEqual(self.g.planned,before)
  b=self.bind();self.assertTrue(b.accepted,b.message);self.assertEqual(b.binding.route_id,'old_route');self.assertEqual(b.binding.generation,3);self.assertFalse(self.g.plan_bind_ready);self.assertFalse(self.bind().accepted)
 def test_never_reuses_without_released_owner(self):
  self.g.last_released_route=None;self.replan();self.assertFalse(self.g.plan_bind_ready);self.assertFalse(self.bind().accepted)
 def test_other_mission_release_rejected(self):
  self.g.last_released_route=('other','old_route',2);self.replan();self.assertFalse(self.g.plan_bind_ready)
 def test_changed_map_rejected(self):
  self.g.config['map']['revision']=2;self.replan();self.assertFalse(self.g.plan_bind_ready)
 def test_worker_unavailable_rejected(self):
  self.g.pct.plan.side_effect=PlannerUnavailable('offline');self.replan();self.assertFalse(self.g.plan_bind_ready)
 def test_other_native_rejection_rejected(self):
  self.g.pct.plan.side_effect=PlannerRejected('invalid_map');self.replan();self.assertFalse(self.g.plan_bind_ready)
 def test_active_owner_rejected(self):
  self.g.gate.owner=object();self.replan();self.assertFalse(self.g.plan_bind_ready)
 def test_cancel_rejects_bind_after_cached_offer(self):
  self.replan();self.g.closing=True;self.assertFalse(self.bind().accepted)
 def test_fresh_native_plan_still_binds(self):
  self.g.last_released_route=None;self.g.pct.plan.side_effect=None;self.g.pct.plan.return_value=self.g.planned[1];r=self.replan();self.assertTrue(r.accepted,r.message);self.assertTrue(self.g.plan_bind_ready);self.assertFalse(self.g.plan_bind_reuse);self.assertTrue(self.bind().accepted)
if __name__=='__main__':unittest.main()
