"""Exercise project-only discovery without network or a vendor checkout."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class SyncSkillsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vla skill sync ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copy2(ROOT / "sync-skills.sh", self.root / "sync-skills.sh")
        self.agents = self.root / ".agents/skills"
        self.claude = self.root / ".claude/skills"
        self.cursor = self.root / ".cursor/skills"
        for path in (self.agents, self.claude, self.cursor):
            path.mkdir(parents=True)
        self.skill(self.agents / "project-example", "canonical")

    @staticmethod
    def skill(path, text):
        path.mkdir(parents=True, exist_ok=True)
        (path / "SKILL.md").write_text(text)

    def sync(self):
        subprocess.run(
            ["bash", str(self.root / "sync-skills.sh")],
            check=True, capture_output=True, text=True, cwd=self.root,
        )

    def test_fresh_checkout_needs_no_vendor_or_network(self):
        self.sync()
        for folder in (self.claude, self.cursor):
            target = folder / "project-example"
            self.assertTrue(target.is_symlink())
            self.assertEqual((target / "SKILL.md").read_text(), "canonical")
        self.assertFalse((self.root / ".skills-upstream").exists())

    def test_repeat_is_idempotent(self):
        self.sync()
        link = self.claude / "project-example"
        before = (os.readlink(link), link.lstat().st_mtime_ns)
        self.sync()
        self.assertEqual((os.readlink(link), link.lstat().st_mtime_ns), before)

    def test_real_platform_override_survives(self):
        self.skill(self.claude / "project-example", "platform override")
        self.sync()
        self.assertFalse((self.claude / "project-example").is_symlink())
        self.assertEqual(
            (self.claude / "project-example/SKILL.md").read_text(),
            "platform override",
        )

    def test_custom_link_override_survives(self):
        self.skill(self.root / "custom", "custom override")
        link = self.claude / "project-example"
        link.symlink_to("../../custom")
        self.sync()
        self.assertEqual(os.readlink(link), "../../custom")
        self.assertEqual((link / "SKILL.md").read_text(), "custom override")

    def test_vendor_links_removed_but_vendor_source_preserved(self):
        source = self.root / ".skills-upstream/skills/example"
        self.skill(source, "local vendor edits")
        for folder in (self.agents, self.claude, self.cursor):
            (folder / "vendor-example").symlink_to(
                "../../.skills-upstream/skills/example"
            )
        self.sync()
        for folder in (self.agents, self.claude, self.cursor):
            self.assertFalse((folder / "vendor-example").is_symlink())
        self.assertEqual((source / "SKILL.md").read_text(), "local vendor edits")

    def test_dangling_generated_links_removed_custom_link_preserved(self):
        for folder in (self.agents, self.claude, self.cursor):
            (folder / "retired").symlink_to("../../.agents/skills/missing")
            (folder / "old-vendor").symlink_to("../../.skills-upstream/missing")
            (folder / "custom-missing").symlink_to("../../custom-missing")
        self.sync()
        for folder in (self.agents, self.claude, self.cursor):
            self.assertFalse((folder / "retired").is_symlink())
            self.assertFalse((folder / "old-vendor").is_symlink())
            self.assertEqual(
                os.readlink(folder / "custom-missing"), "../../custom-missing"
            )

    def test_vendor_link_collision_becomes_project_link(self):
        (self.claude / "project-example").symlink_to(
            "../../.skills-upstream/skills/example"
        )
        self.sync()
        self.assertEqual(
            (self.claude / "project-example").resolve(),
            (self.agents / "project-example").resolve(),
        )

    def test_empty_catalog_is_valid(self):
        shutil.rmtree(self.agents / "project-example")
        self.sync()
        self.assertEqual(list(self.claude.iterdir()), [])
        self.assertEqual(list(self.cursor.iterdir()), [])


class ProjectConfigurationTests(unittest.TestCase):
    def test_claude_wrapper_is_preserved(self):
        self.assertEqual((ROOT / "CLAUDE.md").read_bytes(), b"@AGENTS.md\n")

    def test_project_hooks_are_absent(self):
        data = json.loads((ROOT / ".claude/settings.json").read_text())
        self.assertNotIn("hooks", data)
        for path in (
            ".codex/hooks.json", ".cursor/hooks.json",
            ".claude/hooks", ".codex/hooks", ".cursor/hooks",
        ):
            with self.subTest(path=path):
                self.assertFalse((ROOT / path).exists())

    def test_active_catalog_and_platform_links_resolve(self):
        expected = {
            "trellis-before-dev", "trellis-brainstorm", "trellis-break-loop",
            "trellis-channel", "trellis-check", "trellis-continue",
            "trellis-finish-work", "trellis-meta", "trellis-session-insight",
            "trellis-spec-bootstrap", "trellis-start", "trellis-update-spec",
        }
        for folder in (".agents/skills", ".claude/skills", ".cursor/skills"):
            with self.subTest(folder=folder):
                entries = {p.name for p in (ROOT / folder).iterdir()}
                self.assertEqual(entries, expected)
                for name in expected:
                    self.assertTrue((ROOT / folder / name / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
