"""Exercise the actual timeline function without loading the optional GL runtime."""
import ast
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np

source=Path(__file__).with_name('render_episode_v51.py')
tree=ast.parse(source.read_text())
function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='load_recorded_rows')
namespace={'json':json,'np':np}
exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),namespace)
load=namespace['load_recorded_rows']


class TimelineTests(unittest.TestCase):
    def rows(self,values):
        with tempfile.TemporaryDirectory() as name:
            p=Path(name);(p/'video_states.json').write_text(json.dumps(values));return load(p)

    def test_startup_prefix_omitted_and_recorded_states_causally_selected(self):
        values=[{'pose':'startup'},*({'wall_monotonic_s':t,'pose':p} for t,p in [(0,'A'),(.1,'B'),(.2,'C')])]
        rows=self.rows(values)
        self.assertEqual([r['pose'] for r in rows],['A','A','A','B','B','B','C'])
        self.assertEqual([r['source_state_index'] for r in rows],[1,1,1,2,2,2,3])

    def test_internal_missing_timestamp_is_not_silently_filtered(self):
        with self.assertRaisesRegex(ValueError,'inside navigation'):
            self.rows([{'wall_monotonic_s':0},{'pose':'missing'},{'wall_monotonic_s':.2}])

    def test_no_wall_time_does_not_invent_timing(self):
        with self.assertRaisesRegex(ValueError,'No recorded'):
            self.rows([{'physics_time_s':0},{'physics_time_s':.1}])


if __name__=='__main__':unittest.main()
