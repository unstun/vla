"""Frozen v232 task graph, v282 tag/profile and explicit PCT configuration only."""
from pathlib import Path
FROZEN=Path(__file__).resolve().parent.parent/'v232/native_graph.py'
source=FROZEN.read_text()
source=source.replace('request.get("integration_version") != "v232"','request.get("integration_version") != "v282"')
source=source.replace('("historical_full", "corner_start")','("historical_full", "corner_start", "generalization")')
source=source.replace('["ros2", "launch", "lite3_nav2_bridge", "navigation.launch.py",','["ros2", "launch", str(VERSION.parent / "v282/navigation_physical.launch.py"),')
source=source.replace('VERSION / "long_route_driver.py"','(VERSION.parent / "v257/long_route_driver.py")')
source=source.replace('executed_long_route_driver_v232.py','executed_long_route_driver_v257.py')
namespace=dict(__file__=str(FROZEN),__name__='v282_frozen_graph')
exec(compile(source,str(FROZEN),'exec'),namespace)
if __name__=='__main__':namespace['main']()
