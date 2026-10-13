"""Existing simulator HTTP vocabulary translated to the standard Nav2 action.

This adapter does not plan, admit raw commands, run recovery, or decide arrival.
Only the authoritative gateway's action result can create a terminal record.
"""
import copy
import dataclasses
import math
import time
import uuid

from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from unique_identifier_msgs.msg import UUID
from backend_adapter.contracts import require_finite, require_identifier
from p2b_backend_ros.runtime import parse_goal_payload, TerminalLedger, start_http_server


class LegacyHttpPort:
    def __init__(self, gateway):
        self.gateway = gateway
        self.config = gateway.config
        self.client = ActionClient(gateway, NavigateToPose, '/navigate_to_pose', callback_group=gateway.group)
        self.contexts, self.jobs, self.handles = {}, {}, {}
        self.ledger = TerminalLedger()
        http = self.config['http']
        self.server = start_http_server(self, http['host'], http['port'])

    def close(self):
        self.server.shutdown(); self.server.server_close(); self.client.destroy()

    def submit_goal(self, payload):
        goal = parse_goal_payload(payload, self.config)
        with self.gateway.lock:
            if goal.frame_id != self.gateway.frame or goal.map_epoch != self.config['map']['epoch'] or goal.map_revision != self.config['map']['revision']:
                raise ValueError('Requested map/frame differs from the active navigation map')
            if goal.request_id in self.jobs:
                raise ValueError('Request ID already used in this execution')
            if len(self.jobs) >= 200:
                raise ValueError('Mission journal capacity reached; use a new execution')
            if not self.client.server_is_ready():
                raise ValueError('Nav2 mission gateway unavailable')
            if self.gateway.reserved or any(j['status']=='pending' for j in self.jobs.values()):
                raise ValueError('A prior mission has not finished')
            request = NavigateToPose.Goal()
            request.pose = PoseStamped()
            request.pose.header.frame_id = goal.frame_id
            request.pose.header.stamp = self.gateway.get_clock().now().to_msg()
            xyz = goal.target_ground_xyz
            request.pose.pose.position.x,request.pose.pose.position.y = xyz[:2]
            request.pose.pose.position.z = xyz[2] + self.gateway.height
            yaw = require_finite('target_yaw_rad',payload.get('target_yaw_rad',0.0))
            request.pose.pose.orientation.z = math.sin(yaw/2)
            request.pose.pose.orientation.w = math.cos(yaw/2)
            goal_uuid = UUID(uuid=list(uuid.uuid4().bytes))
            key = bytes(goal_uuid.uuid).hex()
            self.contexts[key] = {'request_id':goal.request_id,'goal_id':goal.goal_id,
                'pose':copy.deepcopy(request.pose),'path_heading':'target_yaw_rad' not in payload}
            self.jobs[goal.request_id] = {'request_id':goal.request_id,'goal_id':goal.goal_id,
                'status':'pending','action_uuid':key,'cancel_requested':False}
            future = self.client.send_goal_async(request, goal_uuid=goal_uuid)
            future.add_done_callback(lambda f:self.accepted(goal.request_id,key,f))
        return {'ok':True,'request_id':goal.request_id,'status':'pending'}

    def accepted(self, request_id, key, future):
        with self.gateway.lock:
            try:
                handle = future.result()
                if not handle.accepted:
                    self.contexts.pop(key,None)
                    self.terminal(request_id,'rejected','Nav2 rejected mission')
                    return
                self.handles[request_id] = handle
                self.jobs[request_id]['status'] = 'running'
                result = handle.get_result_async()
                result.add_done_callback(lambda f:self.completed(request_id,f))
                if self.jobs[request_id]['cancel_requested']: handle.cancel_goal_async()
            except Exception as exc:
                self.contexts.pop(key,None)
                self.terminal(request_id,'failed',str(exc))

    def completed(self, request_id, future):
        with self.gateway.lock:
            try:
                code = future.result().status
                status = {4:'arrived',5:'cancelled',6:'failed'}.get(code,'failed')
                self.terminal(request_id,status,'Nav2 action status '+str(code))
            except Exception as exc:
                self.terminal(request_id,'failed',str(exc))

    def terminal(self, request_id, status, cause):
        job = self.jobs[request_id]
        job['status'] = status
        self.handles.pop(request_id,None)
        self.ledger.append(request_id,job['goal_id'],status,cause,
            data={'action_uuid':job['action_uuid'],'source':'authoritative_nav2_gateway'})

    def cancel(self, payload):
        require_identifier('request_id',payload.get('request_id'))
        target = require_identifier('target_request_id',payload.get('target_request_id'))
        with self.gateway.lock:
            if target not in self.jobs: raise ValueError('Unknown target request')
            job = self.jobs[target]
            if job['status'] in ('arrived','cancelled','rejected','failed'):
                return {'ok':True,'status':job['status'],'target_request_id':target}
            job['cancel_requested'] = True
            handle = self.handles.get(target)
            if handle is not None: handle.cancel_goal_async()
        return {'ok':True,'status':'pending','target_request_id':target}

    def state(self):
        with self.gateway.lock:
            body = None
            error = None
            try: body = dataclasses.asdict(self.gateway.port.measurement_provider())
            except Exception as exc: error = str(exc)
            evidence = {'configured':True,'ready':False}
            try:
                snapshot = self.gateway.reader.read()
                if snapshot.run_id != self.config['run_id'] or snapshot.run_epoch_ns != self.config['run_epoch_ns']:
                    raise ValueError('Applied execution identity mismatch')
                evidence['ready'] = True
            except Exception as exc:
                error = str(exc)
            owner = self.gateway.gate.owner
            return {'run_id':self.config['run_id'],'run_epoch_ns':self.config['run_epoch_ns'],
                'readiness':{'body_pose_ready':body is not None,'applied_snapshot':evidence,'last_error':error},
                'measurement_body_pose':body,'service':{'current_owner':None if owner is None else owner.to_dict()},
                'jobs':copy.deepcopy(self.jobs),'terminal_results':self.ledger.snapshot(),
                'backend':{'command_gate':self.gateway.gate.snapshot()},
                'navigation_authority':'Nav2','monotonic_s':time.monotonic()}
