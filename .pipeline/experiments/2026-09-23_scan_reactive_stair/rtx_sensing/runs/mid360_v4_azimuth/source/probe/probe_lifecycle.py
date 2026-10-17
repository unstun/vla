"""Capture the original RTX import exception before Isaac shutdown can hide it."""
import argparse
import json
from pathlib import Path
import traceback


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--enable-extension", action="store_true")
    args = parser.parse_args()
    state = {"state": "launch_started", "enable_extension": args.enable_extension}

    def save(**values):
        state.update(values)
        args.output.write_text(json.dumps(state, indent=2) + "\n")
        print("RTX_LIFECYCLE " + json.dumps(state), flush=True)

    from isaaclab.app import AppLauncher
    app = AppLauncher(headless=True, enable_cameras=True, device="cuda:0", fast_shutdown=False).app
    failed = False
    try:
        import omni.kit.app
        manager = omni.kit.app.get_app().get_extension_manager()
        save(state="application_ready", rtx_enabled_before=manager.is_extension_enabled("isaacsim.sensors.rtx"))
        if args.enable_extension:
            enabled = manager.set_extension_enabled_immediate("isaacsim.sensors.rtx", True)
            save(state="extension_enable_returned", enable_return=enabled,
                 rtx_enabled_after=manager.is_extension_enabled("isaacsim.sensors.rtx"))
        from isaacsim.sensors.rtx import LidarRtx
        save(state="module_import_completed", imported_class=str(LidarRtx), module_import_completed=True)
    except BaseException as exc:
        failed = True
        save(state="import_failed", failure_type=type(exc).__name__, failure_message=str(exc),
             traceback=traceback.format_exc(), module_import_completed=False)
        traceback.print_exc()
    save(teardown_started=True)
    app.close()
    save(state="teardown_completed", teardown_completed=True)
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
