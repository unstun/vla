import hashlib
import json
import os
from pathlib import Path
import time

import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import PointCloud2

from lite3_nav2_bridge.terrain_bundle import TerrainBundle, ClockGate, TOPICS, FIELDS
from lite3_nav2_bridge.static_terrain import StaticTerrain

MANIFEST = Path(os.environ['TERRAIN_TEST_MANIFEST'])


def altered_manifest(tmp_path, mutate):
    metadata = json.loads(MANIFEST.read_text())
    for entry in [metadata['pct'], metadata['support_gap'], *metadata['clouds'].values()]:
        entry['file'] = str((MANIFEST.parent / entry['file']).resolve())
    mutate(metadata)
    path = tmp_path/'terrain.json'; path.write_text(json.dumps(metadata))
    return path


def test_original_payloads_remain_distinct_and_loaded_once(monkeypatch):
    bundle = TerrainBundle(MANIFEST)
    payloads = bundle.load_clouds()
    expected = {'navigation': '97d2dfbdb60c91e8473ab57f348923360f139da1130b4e9b7dd57e8655c15ca2',
                'surface': 'b68527dd9d2ea8a4647c64aaf59b884da16364e41b146943c03f2c6da68cfa56',
                'physical_floor': '20acd5cf1ef156c5bd336b12651efe9a18e9959816905b05178ed44b1a181c96'}
    assert {key: hashlib.sha256(value).hexdigest() for key,value in payloads.items()} == expected
    monkeypatch.setattr(Path, 'read_bytes', lambda *_: pytest.fail('Static payload reloaded'))
    assert bundle.load_clouds() is payloads


@pytest.mark.parametrize('fault', ['frame', 'role', 'layout', 'hash', 'source_id', 'gap_role'])
def test_bad_bundle_rejected(tmp_path, fault):
    def mutate(m):
        if fault == 'frame': m['frame'] = 'other'
        if fault == 'role': m['clouds']['navigation']['topic'] = TOPICS['surface']
        if fault == 'layout': m['clouds']['navigation']['points'] += 1
        if fault == 'hash': m['clouds']['navigation']['sha256'] = '0'*64
        if fault == 'source_id': m['clouds']['navigation']['source_id'] = 'wrong'
        if fault == 'gap_role': m['support_gap']['negative_only'] = False
    path = altered_manifest(tmp_path, mutate)
    with pytest.raises(ValueError): TerrainBundle(path).load_clouds()


def test_native_bundle_and_mask_hashes_are_checked(tmp_path):
    for kind in ['pct', 'support_gap']:
        path = altered_manifest(tmp_path, lambda m: m[kind].update(sha256='0'*64))
        with pytest.raises(ValueError): TerrainBundle(path).native_parameters()


def test_clock_gate_retains_zero_duplicate_backward_and_reset_behavior():
    gate = ClockGate()
    source = [0, 0, 100, 100, 200, 300, 0, 50, 60, 60, 40, 41]
    assert [gate.observe(x) for x in source] == [None,None,None,None,200,None,None,None,60,None,None,41]


def test_one_ros_publisher_retains_three_payloads_for_late_subscribers():
    rclpy.init()
    producer = observer = executor = None
    try:
        producer = StaticTerrain(parameter_overrides=[Parameter('terrain_manifest', value=str(MANIFEST)),
                                                       Parameter('use_sim_time', value=True)])
        observer = Node('static_terrain_observer')
        clock = observer.create_publisher(Clock, '/clock', 10)
        executor = SingleThreadedExecutor(); executor.add_node(producer); executor.add_node(observer)
        def spin_until(predicate, seconds=3):
            end = time.monotonic()+seconds
            while time.monotonic()<end:
                executor.spin_once(timeout_sec=.02)
                if predicate(): return True
            return False
        assert spin_until(lambda: clock.get_subscription_count() >= 1)
        for ns in [0, 1000000000, 1100000000]:
            message = Clock(); message.clock.sec, message.clock.nanosec = divmod(ns, 1000000000)
            clock.publish(message)
            assert spin_until(lambda: producer.gate._last_ns == ns)
        # Subscribers start only after all publications, exercising transient-local QoS.
        received = {role: [] for role in TOPICS}
        qos = QoSProfile(depth=1, reliability=QoSReliabilityPolicy.RELIABLE,
                         durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        subscriptions = [observer.create_subscription(PointCloud2, topic,
                         lambda msg, role=role: received[role].append(msg), qos)
                         for role,topic in TOPICS.items()]
        assert spin_until(lambda: all(received.values()))
        for role in TOPICS:
            msg = received[role][-1]
            assert bytes(msg.data) == producer.bundle.load_clouds()[role]
            assert msg.header.frame_id == 'world'
            assert (msg.header.stamp.sec, msg.header.stamp.nanosec) == (1,100000000)
            assert [(f.name,f.offset,f.datatype,f.count) for f in msg.fields] == list(FIELDS)
            assert (msg.height,msg.width,msg.point_step,msg.row_step) == (1,len(msg.data)//16,16,len(msg.data))
            assert not msg.is_dense and not msg.is_bigendian
        for ns in [0, 2000000000, 2100000000]:
            message = Clock(); message.clock.sec, message.clock.nanosec = divmod(ns,1000000000)
            clock.publish(message); assert spin_until(lambda: producer.gate._last_ns == ns)
        assert spin_until(lambda: all(len(x)==2 for x in received.values()))
        assert all((x[-1].header.stamp.sec,x[-1].header.stamp.nanosec)==(2,100000000) for x in received.values())
    finally:
        if executor: executor.shutdown()
        if producer: producer.destroy_node()
        if observer: observer.destroy_node()
        rclpy.shutdown()
