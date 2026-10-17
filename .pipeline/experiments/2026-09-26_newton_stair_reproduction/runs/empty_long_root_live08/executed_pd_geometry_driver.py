"""Add explicit startup readiness to the verified original geometry driver."""
import importlib.util
from pathlib import Path


def startup_ready(snapshot):
    control = snapshot.get("control", {})
    return (control.get("startup_mode") == "pd_stand"
            and control.get("phase") == "policy"
            and control.get("navigation_ready") is True
            and control.get("policy_observation_valid") is True)


def main():
    # The launcher places this adapter beside its hash-verified driver snapshot.
    path = Path(__file__).with_name("executed_geometry_driver.py")
    spec = importlib.util.spec_from_file_location("startup_base_driver", path)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    original_ready = driver.snapshot_ready_to_walk
    driver.snapshot_ready_to_walk = lambda snapshot: startup_ready(snapshot) and original_ready(snapshot)
    driver.main()


if __name__ == "__main__":
    main()
