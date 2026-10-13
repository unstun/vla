"""Verify diagnostic semantics and preservation of native decision code."""
from pathlib import Path
import json, re, subprocess, tempfile, unittest

HERE = Path(__file__).resolve().parent


def native_decisions(text):
    text = re.sub(r'\s*// V122_DIAGNOSTIC_BEGIN.*?// V122_DIAGNOSTIC_END', '', text, flags=re.S)
    text = re.sub(r'return (?:planner_manager_->)?planningRejected\([^;]+; // V122_REJECT',
                  'return false;', text)
    # The observed A* rejection gained a brace only to insert a diagnostic call.
    text = re.sub(r'(if \(search->AstarSearch\([^\n]+\) != ASTAR_RET::SUCCESS\))\s*\{\s*return \{\};\s*\}',
                  r'\1 return {};', text)
    text = re.sub(r'//[^\n]*|/\*.*?\*/', '', text, flags=re.S)
    return re.findall(r'\w+|[^\w\s]', text)


class StepOneTests(unittest.TestCase):
    def test_native_control_flow_is_preserved(self):
        files = ('plan_env/include/plan_env/grid_map.h',
                 'plan_manage/include/plan_manage/planner_manager.h',
                 'plan_manage/src/planner_manager.cpp', 'plan_manage/src/scan_replan_fsm.cpp')
        for file in files:
            with self.subTest(file=file):
                parent = (HERE.parent/'v114/src'/file).read_text()
                candidate = (HERE/'src'/file).read_text()
                self.assertEqual(native_decisions(parent), native_decisions(candidate))
        self.assertNotEqual(native_decisions('return false;'), native_decisions('return true;'))

    def test_cpp_round_semantics_and_json(self):
        with tempfile.TemporaryDirectory(prefix='vla_outcome_test_') as folder:
            target = Path(folder)/'outcome_test'
            subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                '-I'+str(HERE/'src/plan_manage/include'), str(HERE/'outcome_contract_test.cpp'),
                '-o', str(target)], check=True)
            rows = [json.loads(line) for line in subprocess.check_output([str(target)], text=True).splitlines()]
            self.assertEqual([row['success'] for row in rows], [False, True, True])
            self.assertEqual([row['rejections'] for row in rows], [2, 1, 0])
            self.assertEqual(rows[0]['first']['stage'], 'seed_search')
            self.assertEqual(rows[0]['last']['observation'], 'stale')
            self.assertEqual(rows[2]['counts']['optimizer'], 0)


if __name__ == '__main__':
    unittest.main()
