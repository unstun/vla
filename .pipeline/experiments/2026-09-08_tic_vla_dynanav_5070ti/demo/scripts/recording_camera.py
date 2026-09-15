"""Output-only fixed overhead camera; never modifies the model camera or scene."""
import os


def select_camera(stage, default_path):
    if os.environ.get("TICVLA_DEMO_VIEW", "third_person") != "top_down":
        return default_path
    from pxr import Gf, UsdGeom
    path = "/World/TICVLATopDownRecordingCamera"
    camera = UsdGeom.Camera.Define(stage, path)
    xform = UsdGeom.Xformable(camera.GetPrim())
    xform.ClearXformOpOrder()
    xform.SetResetXformStack(True)
    xform.AddTranslateOp().Set(Gf.Vec3d(4.0, 0.5, 8.0))
    camera.CreateProjectionAttr().Set(UsdGeom.Tokens.orthographic)
    # USD orthographic aperture is in tenths of a world unit.
    camera.CreateHorizontalApertureAttr().Set(200.0)
    camera.CreateVerticalApertureAttr().Set(112.5)
    camera.CreateClippingRangeAttr().Set(Gf.Vec2f(5.6, 20.0))
    camera.CreateFStopAttr().Set(0.0)
    print("TICVLA_TOP_DOWN_CAMERA", path, "footprint=20x11.25m", flush=True)
    return path


def recording_resolution():
    return (1280, 720) if os.environ.get("TICVLA_DEMO_VIEW") == "top_down" else (960, 540)
