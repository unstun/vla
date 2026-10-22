"""Actual loopback lifecycle replies gate an already discoverable action."""
import threading,time
from unittest.mock import patch
from lifecycle_msgs.srv import GetState
from lifecycle_msgs.msg import State
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionServer
from rclpy.callback_groups import ReentrantCallbackGroup
from test_mission_bridge import bridge,wait,goal_payload


def lifecycle(node,io,initial):
 names=('/controller_server','/planner_server','/recoveries_server','/nav2_internal/bt_navigator')
 states={name:initial for name in names};servers=[]
 for name in names:
  def reply(request,response,key=name):
   response.current_state.id=states[key];return response
  servers.append(io.create_service(GetState,name+'/get_state',reply))
 with node._lock:
  node._require_active_navigation=True
  node._liveness_clients={name:node.create_client(GetState,name+'/get_state',callback_group=node._health_group) for name in names}
 return states,servers


def action(node,io,goals):
 def execute(handle):
  goals.append(handle.request);handle.succeed();return NavigateToPose.Result()
 server=ActionServer(io,NavigateToPose,'/nav2_internal/navigate_to_pose',execute_callback=execute,callback_group=ReentrantCallbackGroup())
 node._test_action_servers.append(server);wait(node._client.server_is_ready)


def test_interface_ready_but_inactive_waits_then_dispatches_exactly_once(bridge):
 node,io=bridge;goals=[];action(node,io,goals)
 states,servers=lifecycle(node,io,State.PRIMARY_STATE_INACTIVE)
 node.submit_goal(goal_payload('delayed'))
 wait(lambda:len(node._lifecycle_state)==4)
 with node._lock:
  assert node.jobs['delayed']['status']=='pending'
  assert not node.jobs['delayed']['sent'] and not goals and not node._test_sessions
  states.update({name:State.PRIMARY_STATE_ACTIVE for name in states})
 wait(lambda:node.jobs['delayed']['status']=='arrived')
 assert len(goals)==1
 assert len(node.jobs['delayed']['navigation_active'])==4
 assert all(v['state_id']==State.PRIMARY_STATE_ACTIVE for v in node.jobs['delayed']['navigation_active'].values())
 assert len([s for s in node._test_sessions if s.operation==s.BEGIN])==1
 node.submit_goal(goal_payload('delayed'));assert len(goals)==1


def test_permanently_inactive_reports_nodes_and_closes_normally(bridge):
 node,io=bridge;goals=[];action(node,io,goals)
 states,servers=lifecycle(node,io,State.PRIMARY_STATE_INACTIVE)
 node.submit_goal(goal_payload('inactive'))
 wait(lambda:len(node._lifecycle_state)==4)
 with node._lock:node.jobs['inactive']['submitted_s']-=5.1
 wait(lambda:node.jobs['inactive']['status']=='failed')
 result=node.terminal_results[-1]
 assert result['cause']=='nav2_nodes_not_active'
 assert result['data']['nodes']==states
 assert node.current_owner is None and not goals and not node.jobs['inactive']['sent']


def test_cancel_during_activation_never_sends_goal(bridge):
 node,io=bridge;goals=[];action(node,io,goals)
 states,servers=lifecycle(node,io,State.PRIMARY_STATE_INACTIVE)
 node.submit_goal(goal_payload('cancel-pending'))
 wait(lambda:len(node._lifecycle_state)==4)
 node.cancel_goal({'request_id':'cancel','target_request_id':'cancel-pending'})
 wait(lambda:node.jobs['cancel-pending']['status']=='cancelled')
 states.update({name:State.PRIMARY_STATE_ACTIVE for name in states})
 assert not goals and not node.jobs['cancel-pending']['sent']
