"""Build a small pinned work copy with observation-only execution auditing."""

import difflib
import hashlib
import shutil
from pathlib import Path


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError("Instrumentation anchor is not unique")
    return text.replace(old, new, 1)


def main():
    root = Path(__file__).resolve().parents[1]
    repo = root.parents[2]
    upstream = repo / "references/upstream/2026-08-20_tic_vla/source/TIC-VLA"
    files = (root / "manifests/source_files.txt").read_text().splitlines()
    work = root / "work"
    for relative in files:
        target = work / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(upstream / relative, target)
    relative = "DynaNav/behavior/nova_carter_test_ticvla.py"
    original = (work / relative).read_text()
    updated = replace_once(original,
        "        # Run model predict (this is the heavy call)\n",
        "        # Task-owned timing instrumentation; model inputs and outputs are unchanged.\n"
        "        audit_inference_started = time.perf_counter()\n"
        "        # Run model predict (this is the heavy call)\n")
    updated = replace_once(updated,
        "                    if cv2.imwrite(filename_front, img_bgr):\n",
        "                    if cv2.imwrite(filename_front, img_bgr):\n"
        "                        audit_frames = os.path.join(self._log_directory, 'retained_front_frames')\n"
        "                        os.makedirs(audit_frames, exist_ok=True)\n"
        "                        shutil.copyfile(filename_front, os.path.join(audit_frames, os.path.basename(filename_front)))\n")
    updated = replace_once(updated,
        "        wps = waypoints[0].float().cpu().numpy()  # (T,2) body/FLU\n",
        "        wps = waypoints[0].float().cpu().numpy()  # (T,2) body/FLU\n"
        "        with open(os.path.join(self._log_directory, 'inference_audit.jsonl'), 'a') as audit:\n"
        "            audit.write(json.dumps({\n"
        "                'wall_monotonic': time.monotonic(), 'simulation_frame': self._frame_count,\n"
        "                'seconds': time.perf_counter() - audit_inference_started,\n"
        "                'shape': list(waypoints.shape), 'finite': bool(np.isfinite(wps).all()),\n"
        "                'cache_available': bool(kv_cache_available), 'waypoints': wps.tolist(),\n"
        "                'cuda_allocated_bytes': torch.cuda.memory_allocated(),\n"
        "                'cuda_reserved_bytes': torch.cuda.memory_reserved(),\n"
        "            }) + '\\n')\n")
    updated = replace_once(updated,
        "                action = self._diff.forward(command=np.array([final_v, final_w], dtype=np.float32))\n"
        "                self._wheeled_robot.apply_wheel_actions(action)\n",
        "                action = self._diff.forward(command=np.array([final_v, final_w], dtype=np.float32))\n"
        "                self._wheeled_robot.apply_wheel_actions(action)\n"
        "                if self._frame_count % 3 == 0:\n"
        "                    with open(os.path.join(self._log_directory, 'control_audit.jsonl'), 'a') as audit:\n"
        "                        audit.write(json.dumps({\n"
        "                            'wall_monotonic': time.monotonic(), 'simulation_frame': self._frame_count,\n"
        "                            'v': float(final_v), 'w': float(final_w),\n"
        "                            'position': self._robot_position.tolist() if self._robot_position is not None else None,\n"
        "                            'backing_up': bool(self._is_backing_up),\n"
        "                            'waiting_after_backup': bool(self._waiting_for_inference_after_backup),\n"
        "                            'first_inference_complete': bool(self._first_inference_complete),\n"
        "                        }) + '\\n')\n")
    (work / relative).write_text(updated)
    patches = root / "patches"
    patches.mkdir(exist_ok=True)
    (patches / "0001-execution-audit.patch").write_text("".join(difflib.unified_diff(
        original.splitlines(keepends=True), updated.splitlines(keepends=True),
        fromfile="a/" + relative, tofile="b/" + relative)))
    relative = "DynaNav/benchmark.py"
    original = (work / relative).read_text()
    updated = replace_once(original,
        'APP_CONFIG = {"renderer": "RayTracedLighting", "headless": False, "width": 640, "height": 480}',
        'APP_CONFIG = {"renderer": "RayTracedLighting", "headless": False, "width": 640, "height": 480, "sync_loads": False}')
    updated = replace_once(updated,
        "    def _set_simulation_settings(self):\n        import carb\n        import omni.replicator.core as rep\n",
        "    def _set_simulation_settings(self):\n        import carb\n        import omni.replicator.core as rep\n"
        "        from omni.replicator.core.scripts.orchestrator import _Orchestrator\n"
        "        # Isaac Sim 5.1 capture re-enables asset sync loads; keep the tested\n"
        "        # task-only override while preserving synchronous image rendering.\n"
        "        original_capture_settings = _Orchestrator._set_capture_settings\n"
        "        if not getattr(original_capture_settings, '_ticvla_asset_override', False):\n"
        "            def task_capture_settings(orchestrator):\n"
        "                original_capture_settings(orchestrator)\n"
        "                settings = carb.settings.get_settings()\n"
        "                settings.set('/rtx/materialDb/syncLoads', False)\n"
        "                settings.set('/rtx/hydra/materialSyncLoads', False)\n"
        "                print('TICVLA_CAPTURE_ASSET_SYNC_DISABLED', flush=True)\n"
        "            task_capture_settings._ticvla_asset_override = True\n"
        "            _Orchestrator._set_capture_settings = task_capture_settings\n"
        "        settings = carb.settings.get_settings()\n"
        "        asset_flags = ('/rtx/materialDb/syncLoads', '/rtx/hydra/materialSyncLoads', '/omni.kit.plugin/syncUsdLoads')\n"
        "        def keep_asset_loads_async(*unused):\n"
        "            for flag in asset_flags:\n"
        "                if settings.get(flag):\n"
        "                    settings.set(flag, False)\n"
        "                    print('TICVLA_ASSET_SYNC_REVERTED', flag, flush=True)\n"
        "        self._asset_sync_subscriptions = [settings.subscribe_to_node_change_events(flag, keep_asset_loads_async) for flag in asset_flags]\n"
        "        keep_asset_loads_async()\n"
        "        print('TICVLA_RENDER_SETTINGS', {flag: settings.get(flag) for flag in (*asset_flags, '/app/asyncRendering', '/rtx/rendermode')}, flush=True)\n")
    updated = replace_once(updated,
        "    sim_app = SimulationApp(launch_config=APP_CONFIG)\n",
        "    sim_app = SimulationApp(launch_config=APP_CONFIG)\n"
        "    import faulthandler\n"
        "    faulthandler.dump_traceback_later(90, repeat=True)\n")
    (work / relative).write_text(updated)
    (patches / "0002-asynchronous-asset-loads.patch").write_text("".join(difflib.unified_diff(
        original.splitlines(keepends=True), updated.splitlines(keepends=True),
        fromfile="a/" + relative, tofile="b/" + relative)))
    (root / "manifests/work.sha256").write_text("".join(
        f"{hashlib.sha256((work / name).read_bytes()).hexdigest()}  {name}\n" for name in files))
    print("WORKCOPY_READY", len(files), "files")


if __name__ == "__main__":
    main()
