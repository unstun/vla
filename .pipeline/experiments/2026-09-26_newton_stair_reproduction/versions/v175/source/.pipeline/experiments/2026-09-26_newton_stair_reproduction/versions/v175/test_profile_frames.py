from pathlib import Path
import tempfile,unittest,yaml,xml.etree.ElementTree as ET
from lite3_nav2_bridge.profile import write_profile
from ament_index_python.packages import get_package_share_directory
class Tests(unittest.TestCase):
 def test_same_requested_frame_reaches_all_consumers(self):
  for frame in ['base','base_link']:
   with tempfile.TemporaryDirectory() as d:
    target=Path(d)/'profile.yaml';native=Path(get_package_share_directory('scan_planner'))/'config/planner.yaml'
    write_profile(target,native,True,base_frame=frame)
    data=yaml.safe_load(target.read_text());bt=data['/nav2_internal/bt_navigator']['ros__parameters'];tree=ET.parse(bt['default_bt_xml_filename']);node=tree.getroot().find('./BehaviorTree/MeasuredProgressRecovery')
    self.assertEqual(node.get('robot_base_frame'),frame);self.assertEqual(node.get('global_frame'),'world')
    self.assertEqual(bt['robot_base_frame'],frame);self.assertEqual(data['controller_server']['ros__parameters']['SCAN']['base_frame'],frame)
    self.assertEqual(data['local_costmap']['local_costmap']['ros__parameters']['robot_base_frame'],frame)
    with self.assertRaises(ValueError):write_profile(target,native,True,base_frame=frame)
 def test_orphan_bt_profile_is_not_overwritten(self):
  with tempfile.TemporaryDirectory() as d:
   target=Path(d)/'profile.yaml';prior=target.with_suffix('.bt.xml');prior.write_text('preserve')
   native=Path(get_package_share_directory('scan_planner'))/'config/planner.yaml'
   with self.assertRaises(ValueError):write_profile(target,native,True)
   self.assertEqual(prior.read_text(),'preserve')
if __name__=='__main__':unittest.main()
