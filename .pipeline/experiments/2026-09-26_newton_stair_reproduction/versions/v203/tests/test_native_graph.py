"""Capture launch commands with fake children; never starts ROS or physics."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

VERSION = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('v203_graph', VERSION/'native_graph.py')
graph = importlib.util.module_from_spec(spec);spec.loader.exec_module(graph)


class Child:
    def __init__(self,*args,**kwargs): pass
    def poll(self): return None
    def terminate(self): pass
    def wait(self,**kwargs): pass


class GraphTest(unittest.TestCase):
    def test_single_terrain_entry_and_latest_bridge(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory);manifest = out/'terrain.json';manifest.write_text('{}')
            request = {'integration_version':'v203','applied_transport':'shared','native_variant':'candidate',
                       'run_epoch_ns':1,'scene':'building_full','geometry_obstacles':True,'probe':True}
            (out/'episode_request.json').write_text(json.dumps(request))
            with patch.object(sys,'argv',['graph','--output',directory,'--terrain-manifest',str(manifest)]), \
                    patch.object(graph.subprocess,'Popen',Child),patch.object(graph.signal,'signal'), \
                    patch.object(graph,'get_json',return_value={}), \
                    patch.object(graph.time,'sleep',side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):graph.main()
            commands = json.loads((out/'native_commands.json').read_text())
            self.assertEqual(set(commands),{'frequency_observer','clock_responder','health','body_tf','bridge','nav2'})
            self.assertIn('terrain_manifest:='+str(manifest.resolve()),commands['nav2'])
            self.assertFalse(any(x.startswith('pct_map:') for x in commands['nav2']))
            self.assertIn(str(VERSION.parent/'v198/runtime/bridge'),commands['bridge'])


if __name__ == '__main__':unittest.main()
