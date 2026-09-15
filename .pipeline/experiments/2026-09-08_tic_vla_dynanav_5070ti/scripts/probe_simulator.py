"""Initialize the installed simulator and the upstream-required extensions."""

import json
import faulthandler
import os
import sys
import time
from pathlib import Path

from isaacsim import SimulationApp

started = time.monotonic()
app = SimulationApp({"headless": True, "width": 640, "height": 480,
                     "sync_loads": "--async-loads" not in sys.argv})
try:
    import omni.kit.app
    manager = omni.kit.app.get_app().get_extension_manager()
    extensions = ["omni.kit.scripting", "omni.anim.graph.core",
                  "omni.anim.navigation.core", "omni.anim.people",
                  "isaacsim.replicator.agent.core", "isaacsim.sensors.physics"]
    for name in extensions:
        manager.set_extension_enabled_immediate(name, True)
    for _ in range(20):
        app.update()
    states = {name: manager.is_extension_enabled(name) for name in extensions}
    from isaacsim.replicator.agent.core.simulation import SimulationManager
    from isaacsim.robot.wheeled_robots.controllers.differential_controller import DifferentialController
    from omni.anim.people.settings import PeopleSettings, AgentEvent
    import cv2, timm, accelerate, torch, transformers
    report = {"extensions": states, "seconds": time.monotonic() - started,
              "torch": torch.__version__, "transformers": transformers.__version__,
              "cv2": cv2.__version__, "gpu": torch.cuda.get_device_name(0)}
    print("SIMULATOR_PROBE", json.dumps(report), flush=True)
    if not all(states.values()):
        raise RuntimeError("Required upstream extension is unavailable")
    if "--scene" in sys.argv:
        faulthandler.dump_traceback_later(45)
        import numpy as np
        from isaacsim.core.utils.stage import open_stage, is_stage_loading
        from isaacsim.core.utils.viewports import set_camera_view
        from omni.kit.viewport.utility import get_active_viewport, capture_viewport_to_file
        scene = "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.0/Isaac/Environments/Hospital/hospital.usd"
        print("SCENE_OPEN_START", scene, flush=True)
        if not open_stage(scene):
            raise RuntimeError("Hospital stage did not open")
        print("SCENE_OPEN_RETURNED", time.monotonic() - started, flush=True)
        loading_started = time.monotonic()
        while is_stage_loading():
            if time.monotonic() - loading_started > 180:
                raise RuntimeError("Hospital stage loading exceeded 180 seconds")
            app.update()
        print("SCENE_LOADING_FINISHED", time.monotonic() - started, flush=True)
        set_camera_view(eye=np.array([-3.0, -4.0, 2.0]), target=np.array([4.0, 0.0, 1.0]))
        for _ in range(40):
            app.update()
        print("SCENE_RENDERED", time.monotonic() - started, flush=True)
        image_path = Path(os.environ["TICVLA_TASK_ROOT"]) / "logs/hospital_scene_preview.png"
        capture = capture_viewport_to_file(get_active_viewport(), str(image_path))
        for _ in range(40):
            app.update()
        if not image_path.is_file():
            raise RuntimeError("Hospital preview was not saved")
        print("SCENE_PREVIEW_READY", str(image_path), "no robot or navigation test", flush=True)
        faulthandler.cancel_dump_traceback_later()
finally:
    app.close()
