import importlib.util
import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SETUP_PATH = REPO_ROOT / "setup.py"


def load_setup_module():
    spec = importlib.util.spec_from_file_location("dotfiles_setup", SETUP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SetupPyTests(unittest.TestCase):
    def setUp(self):
        self.module = load_setup_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def test_render_template_substitutes_identity_values(self):
        src = self.root / "template.txt"
        src.write_text("name=__NAME__ email=__EMAIL__\n")

        rendered = self.module.render_template(
            src,
            {"__NAME__": "Taylor", "__EMAIL__": "taylor@example.com"},
        )

        self.assertEqual(rendered, "name=Taylor email=taylor@example.com\n")

    def test_needs_templating_false_for_directories(self):
        src_dir = self.root / "nvim"
        src_dir.mkdir()

        self.assertFalse(self.module.needs_templating(src_dir, ["__NAME__"]))

    def test_create_symlink_backs_up_existing_file(self):
        source = self.root / "source.txt"
        target = self.root / "target.txt"
        source.write_text("new\n")
        target.write_text("old\n")

        status = self.module.create_symlink(source, target)

        self.assertTrue(target.is_symlink())
        self.assertEqual(target.resolve(), source.resolve())
        self.assertIn("backed up original", status)
        backups = list(self.root.glob("target.txt.bak.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "old\n")

    def test_create_symlink_relinks_wrong_symlink(self):
        source = self.root / "source.txt"
        wrong = self.root / "wrong.txt"
        target = self.root / "target.txt"
        source.write_text("new\n")
        wrong.write_text("old\n")
        target.symlink_to(wrong)

        status = self.module.create_symlink(source, target)

        self.assertEqual(status, "relinked (was pointing elsewhere)")
        self.assertTrue(target.is_symlink())
        self.assertEqual(target.resolve(), source.resolve())

    def test_write_secret_to_zshrc_local_replaces_existing_value(self):
        zshrc_local = self.root / ".zshrc.local"
        zshrc_local.write_text('export OPENAI_API_KEY="old"\n')

        with mock.patch.object(self.module, "ZSHRC_LOCAL", zshrc_local):
            self.module.write_secret_to_zshrc_local("OPENAI_API_KEY", "new")

        self.assertEqual(zshrc_local.read_text(), 'export OPENAI_API_KEY="new"\n')

    def test_write_secret_to_zshrc_local_appends_new_value(self):
        zshrc_local = self.root / ".zshrc.local"
        zshrc_local.write_text('export EXISTING="1"\n')

        with mock.patch.object(self.module, "ZSHRC_LOCAL", zshrc_local):
            self.module.write_secret_to_zshrc_local("OPENAI_API_KEY", "new")

        self.assertEqual(
            zshrc_local.read_text(),
            'export EXISTING="1"\nexport OPENAI_API_KEY="new"\n',
        )

    def test_write_secret_sets_restrictive_permissions(self):
        zshrc_local = self.root / ".zshrc.local"

        with mock.patch.object(self.module, "ZSHRC_LOCAL", zshrc_local):
            self.module.write_secret_to_zshrc_local("OPENAI_API_KEY", "sk-test")

        mode = zshrc_local.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_configure_claude_code_handles_malformed_json(self):
        settings_dir = self.root / ".claude"
        settings_dir.mkdir()
        settings_file = settings_dir / "settings.json"
        settings_file.write_text("{bad json")

        with mock.patch.object(self.module, "CLAUDE_SETTINGS_DIR", settings_dir):
            self.module.configure_claude_code()

        result = json.loads(settings_file.read_text())
        self.assertIn("statusLine", result)

    def test_configure_claude_code_uses_absolute_path(self):
        settings_dir = self.root / ".claude"
        settings_dir.mkdir()

        with mock.patch.object(self.module, "CLAUDE_SETTINGS_DIR", settings_dir):
            self.module.configure_claude_code()

        result = json.loads((settings_dir / "settings.json").read_text())
        command = result["statusLine"]["command"]
        self.assertNotIn("~", command)
        self.assertTrue(command.startswith("/"))


    def test_set_btop_color_theme_creates_new_file(self):
        conf = self.root / "btop.conf"

        self.module._set_btop_color_theme(conf, "Deep Water")

        self.assertEqual(conf.read_text(), 'color_theme = "Deep Water"\n')

    def test_set_btop_color_theme_updates_existing_key(self):
        conf = self.root / "btop.conf"
        conf.write_text('vim_keys = true\ncolor_theme = "Old Theme"\nupdate_ms = 2000\n')

        self.module._set_btop_color_theme(conf, "Desert Island")

        lines = conf.read_text().splitlines()
        self.assertEqual(lines[0], "vim_keys = true")
        self.assertEqual(lines[1], 'color_theme = "Desert Island"')
        self.assertEqual(lines[2], "update_ms = 2000")

    def test_set_btop_color_theme_appends_when_key_missing(self):
        conf = self.root / "btop.conf"
        conf.write_text("vim_keys = true\n")

        self.module._set_btop_color_theme(conf, "Plastic Beach Basic")

        lines = conf.read_text().splitlines()
        self.assertEqual(lines[-1], 'color_theme = "Plastic Beach Basic"')

    def test_render_template_theme_before_identity(self):
        """__THEME_NAME__ must be replaced before __NAME__ to avoid partial match."""
        src = self.root / "template.txt"
        src.write_text("theme=__THEME_NAME__ user=__NAME__\n")

        rendered = self.module.render_template(
            src,
            {
                "__NAME__": "Taylor",
                "__THEME_NAME__": "Plastic Beach Basic",
            },
        )

        self.assertEqual(rendered, "theme=Plastic Beach Basic user=Taylor\n")

    def test_needs_templating_detects_theme_placeholders(self):
        src = self.root / "config.toml"
        src.write_text('highlight = "__THEME_HIGHLIGHT_COLOR__"\n')

        self.assertTrue(
            self.module.needs_templating(src, ["__NAME__", "__THEME_HIGHLIGHT_COLOR__"])
        )


if __name__ == "__main__":
    unittest.main()
