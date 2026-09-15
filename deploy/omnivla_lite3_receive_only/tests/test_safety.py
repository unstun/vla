import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_IMPORT_PREFIXES = (
    "rclpy",
    "rospy",
    "geometry_msgs",
    "motion_sdk",
    "motionsdk",
    "lite3_motion",
)
FORBIDDEN_CALL_NAMES = {
    "send_cmd",
    "send_command",
    "publish_cmd_vel",
    "sender_sendcmd",
}


class SafetyTests(unittest.TestCase):
    def test_runtime_sources_have_no_actuation_import_or_sender(self):
        runtime_files = [
            ROOT / "protocol.py",
            ROOT / "server.py",
            ROOT / "engine_original.py",
            ROOT / "lite3_client.py",
        ]
        findings = []
        for path in runtime_files:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.lower().startswith(FORBIDDEN_IMPORT_PREFIXES):
                            findings.append("%s imports %s" % (path.name, alias.name))
                elif isinstance(node, ast.ImportFrom):
                    module = (node.module or "").lower()
                    if module.startswith(FORBIDDEN_IMPORT_PREFIXES):
                        findings.append("%s imports from %s" % (path.name, module))
                elif isinstance(node, ast.Call):
                    name = ""
                    if isinstance(node.func, ast.Name):
                        name = node.func.id.lower()
                    elif isinstance(node.func, ast.Attribute):
                        name = node.func.attr.lower()
                    if name in FORBIDDEN_CALL_NAMES:
                        findings.append("%s calls %s" % (path.name, name))
        self.assertEqual(findings, [])

    def test_lite3_client_has_no_loop_statement(self):
        path = ROOT / "lite3_client.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        loops = [node for node in ast.walk(tree) if isinstance(node, (ast.For, ast.While))]
        self.assertEqual(loops, [])


if __name__ == "__main__":
    unittest.main()

