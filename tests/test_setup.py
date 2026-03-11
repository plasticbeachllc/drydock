import importlib.util
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

        self.assertFalse(self.module.needs_templating(src_dir))

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


if __name__ == "__main__":
    unittest.main()
