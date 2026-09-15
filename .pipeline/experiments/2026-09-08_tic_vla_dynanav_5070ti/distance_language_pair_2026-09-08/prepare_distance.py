"""Rebuild the isolated metric-stop probe from the pinned successful demo."""
import difflib
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent / 'demo'
PARENT_SHA = '4a940f97a40d7cb513efd044f7df707daf71a13073f303b7395a4f050832c8c0'


def replace(path, old, new):
    text = path.read_text()
    assert text.count(old) == 1, (path, old[:80], text.count(old))
    path.write_text(text.replace(old, new, 1))


def main():
    manifest = PARENT / 'manifests/source.json'
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == PARENT_SHA
    entries = json.loads(manifest.read_text())
    for entry in entries:
        source = PARENT / entry['path']
        assert hashlib.sha256(source.read_bytes()).hexdigest() == entry['sha256']
        target = ROOT / entry['path']
        target.parent.mkdir(exist_ok=True, parents=True)
        shutil.copy2(source, target)
    (ROOT / 'manifests/parent_source.json').write_bytes(manifest.read_bytes())
    replace(ROOT / 'scripts/protocol.py', 'STOPS = {',
            'from distance_probe import INSTRUCTION as DISTANCE_INSTRUCTION\n'
            'GOALS.add(re.sub(r"[。！？!?,，.;；]", "", DISTANCE_INSTRUCTION))\n'
            'STOPS = {')
    replace(ROOT / 'scripts/run_demo.py', '        env = os.environ.copy()\n',
            '        from distance_probe import INSTRUCTION as DISTANCE_INSTRUCTION\n'
            '        if instruction != DISTANCE_INSTRUCTION:\n'
            '            raise ValueError("This isolated probe requires its predeclared metric instruction")\n'
            '        env = os.environ.copy()\n')
    replace(ROOT / 'scripts/run_demo.py', '"instruction": instruction, "instruction_mode": "verbatim",',
            '"instruction": instruction, "instruction_mode": "verbatim",\n'
            '                "test_type": "native_metric_stop", "goal_termination_enabled": False,\n'
            '                "automatic_backup_enabled": False, "distance_is_evaluation_only": True,')
    behavior = ROOT / 'work/DynaNav/behavior/nova_carter_test_ticvla.py'
    replace(behavior,
            '        if self._first_inference_complete and not self._is_backing_up and not self._waiting_for_inference_after_backup:\n',
            '        # Metric-stop probe: intentional stillness must not trigger automatic reverse.\n'
            '        if False and self._first_inference_complete and not self._is_backing_up and not self._waiting_for_inference_after_backup:\n')
    replace(behavior,
            '                            \'position\': self._robot_position.tolist() if self._robot_position is not None else None,\n',
            '                            \'position\': self._robot_position.tolist() if self._robot_position is not None else None,\n'
            '                            \'actual_velocity\': self._robot_velocity.tolist(),\n'
            '                            \'actual_yaw_speed\': float(self._robot_yaw_speed),\n'
            '                            \'desired_action\': self._current_action.tolist(),\n'
            '                            \'timeline_seconds\': float(get_timeline_interface().get_current_time()),\n')
    benchmark = ROOT / 'work/DynaNav/benchmark.py'
    replace(benchmark, '    import faulthandler\n    faulthandler.dump_traceback_later(90, repeat=True)\n',
            '    # Retry probe: omit periodic thread dumps after a SIGSEGV coincident with the first dump.\n')
    replace(benchmark, '                # reached goal?\n',
            '                # Metric-stop probe: reaching the measuring point must not stop the robot.\n')
    replace(benchmark,
            '        """Check if robot has reached the goal."""\n',
            '        """Goal is measurement-only for the native metric-stop probe."""\n'
            '        return False  # End only at the fixed observation timeout.\n')
    bridge = ROOT / 'scripts/demo_bridge.py'
    replace(bridge, '        self.plan_frame = None\n',
            '        self.plan_frame = None\n'
            '        from distance_probe import DistanceMeter\n'
            '        self.distance_meter = DistanceMeter()\n')
    replace(bridge, '            self.latch.acknowledge(command)\n',
            '            if command["action"] == "goal":\n'
            '                from omni.timeline import get_timeline_interface\n'
            '                self.distance_meter.start(behavior._robot_position.tolist(), behavior._robot_quaternion.tolist(),\n'
            '                                          get_timeline_interface().get_current_time(), behavior._frame_count)\n'
            '                print("TICVLA_METRIC_STOP_PROBE goal_stop=False automatic_backup=False distance_control=False", flush=True)\n'
            '            self.latch.acknowledge(command)\n')
    replace(bridge, '        images = {}\n',
            '        from omni.timeline import get_timeline_interface\n'
            '        state["distance_probe"] = self.distance_meter.sample(\n'
            '            position, behavior._robot_velocity.tolist(), behavior._robot_yaw_speed,\n'
            '            behavior._current_action.tolist(), [v, w],\n'
            '            get_timeline_interface().get_current_time(), frame,\n'
            '            behavior._first_inference_complete and not self.latch.is_held()\n'
            '            and not behavior._is_backing_up and not behavior._waiting_for_inference_after_backup)\n'
            '        state["backing_up"] = bool(behavior._is_backing_up)\n'
            '        state["waiting_after_backup"] = bool(behavior._waiting_for_inference_after_backup)\n'
            '        images = {}\n')
    replace(bridge, '                    goal = getattr(behavior, "_goal_position", None)\n',
            '                    goal = None\n'
            '                    if self.distance_meter.origin is not None:\n'
            '                        goal = [self.distance_meter.origin[i] + 3.0 * self.distance_meter.heading[i] for i in range(2)]\n')
    replace(bridge, ' 0.06], "GOAL", (90,230,120)))',
            ' 0.06], "3m REFERENCE", (90,230,120)))')
    replace(bridge, '                label = "HOLD" if self.latch.is_held() else "NAVIGATING"\n',
            '                probe = state["distance_probe"]\n'
            '                if probe is not None:\n'
            '                    rows = ["COMMAND: GO STRAIGHT 3m THEN STOP (Chinese input)",\n'
            '                            f"Forward {probe[\'forward_m\']:.2f}m / 3.00m   Cross-track {probe[\'lateral_m\']:+.2f}m   Path {probe[\'sampled_path_length_m\']:.2f}m",\n'
            '                            f"Actual speed {probe[\'actual_planar_speed_m_s\']:.2f}m/s   Yaw {probe[\'actual_yaw_rate_rad_s\']:+.2f}rad/s",\n'
            '                            "MEASUREMENT ONLY: no automatic stop at 3m"]\n'
            '                    cv2.rectangle(bgr, (0, bgr.shape[0]-119), (bgr.shape[1], bgr.shape[0]), (25,25,25), -1)\n'
            '                    for n, row in enumerate(rows):\n'
            '                        cv2.putText(bgr, row, (18, bgr.shape[0]-92+n*26), cv2.FONT_HERSHEY_SIMPLEX, .56, (255,255,255), 1, cv2.LINE_AA)\n'
            '                label = "HOLD" if self.latch.is_held() else "NAVIGATING"\n')
    import yaml
    from sys import path as module_paths
    module_paths.insert(0, str(ROOT / 'scripts'))
    from distance_probe import INSTRUCTION
    scenario = yaml.safe_load((ROOT / 'hospital_demo.yaml').read_text())
    scenario['success_threshold'] = 0.25  # Diagnostic metadata; goal termination is disabled.
    episode = scenario['episode_hospital_demo']
    episode.update(goal=[0.0, -1.2, 0.01], instruction=INSTRUCTION, timeout=34)
    (ROOT / 'hospital_demo.yaml').write_text(yaml.safe_dump(scenario, allow_unicode=True, sort_keys=False))
    plan = {
        'instruction': INSTRUCTION, 'instruction_mode': 'verbatim', 'inference_seed': 36,
        'parent_source_sha256': PARENT_SHA, 'stage': 'experiment and analysis',
        'target': {'forward_m': 3.0, 'position_tolerance_m': .25, 'cross_track_tolerance_m': .25,
                   'speed_tolerance_m_s': .05, 'yaw_rate_tolerance_rad_s': .10,
                   'stop_hold_timeline_seconds': 2.0},
        'distance_reference': 'projection on initial heading at command application, not cumulative path length',
        'goal_termination_enabled': False, 'automatic_backup_enabled': False,
        'model_and_waypoint_controller_changed': False, 'target_coordinates_fed_to_policy': False,
        'periodic_traceback_dump_enabled': False,
        'timeout_frame_derived_seconds': 34, 'runtime_wall_deadline_seconds': 600,
        'claim_boundary': 'one exploratory Chinese metric-stop simulation; timeout is not learned stopping',
    }
    (ROOT / 'plan.json').write_text(json.dumps(plan, indent=2, ensure_ascii=False) + '\n')
    changed = []
    for entry in entries:
        new = ROOT / entry['path']
        if hashlib.sha256(new.read_bytes()).hexdigest() != entry['sha256']:
            old = PARENT / entry['path']
            changed.extend(difflib.unified_diff(old.read_text().splitlines(keepends=True),
                                               new.read_text().splitlines(keepends=True),
                                               fromfile='a/'+entry['path'], tofile='b/'+entry['path']))
    (ROOT / 'manifests/distance_probe.patch').write_text(''.join(changed))
    files = {ROOT / e['path'] for e in entries}
    files.update((ROOT / 'scripts').glob('*.py'))
    files.update([Path(__file__), ROOT / 'plan.json', ROOT / 'manifests/distance_probe.patch',
                  ROOT / 'manifests/parent_source.json'])
    records = [{'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
               for p in sorted(files) if p.is_file()]
    (ROOT / 'manifests/source.json').write_text(json.dumps(records, indent=2) + '\n')
    print('METRIC_PROBE_SOURCE_READY', len(records))


if __name__ == '__main__':
    main()
