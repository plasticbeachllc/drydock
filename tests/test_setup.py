import importlib.util
import json
import os
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

    def test_seed_secrets_template_creates_file(self):
        zshrc_local = self.root / ".zshrc.local"
        self.assertFalse(zshrc_local.exists())

        with mock.patch.object(self.module, "ZSHRC_LOCAL", zshrc_local):
            self.module.seed_zshrc_local_secrets_template()

        content = zshrc_local.read_text()
        self.assertIn("# --- 1Password secrets ---", content)
        self.assertIn("op://Vault/Item/field", content)

    def test_seed_secrets_template_appends_to_existing(self):
        zshrc_local = self.root / ".zshrc.local"
        zshrc_local.write_text("# existing config\nexport FOO=bar\n")

        with mock.patch.object(self.module, "ZSHRC_LOCAL", zshrc_local):
            self.module.seed_zshrc_local_secrets_template()

        content = zshrc_local.read_text()
        self.assertTrue(content.startswith("# existing config\n"))
        self.assertIn("# --- 1Password secrets ---", content)

    def test_seed_secrets_template_skips_if_marker_present(self):
        zshrc_local = self.root / ".zshrc.local"
        original = "# --- 1Password secrets ---\n# already here\n"
        zshrc_local.write_text(original)

        with mock.patch.object(self.module, "ZSHRC_LOCAL", zshrc_local):
            self.module.seed_zshrc_local_secrets_template()

        self.assertEqual(zshrc_local.read_text(), original)

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


class PlatformDetectionTests(unittest.TestCase):
    def setUp(self):
        self.module = load_setup_module()

    def test_platform_constants_are_booleans(self):
        self.assertIsInstance(self.module.IS_MACOS, bool)
        self.assertIsInstance(self.module.IS_LINUX, bool)

    def test_platform_constants_are_mutually_exclusive_on_known_os(self):
        # On any real system, at most one should be True
        self.assertFalse(self.module.IS_MACOS and self.module.IS_LINUX)

    def test_op_ssh_agent_sock_differs_by_platform(self):
        sock_path = str(self.module.OP_SSH_AGENT_SOCK)
        if self.module.IS_MACOS:
            self.assertIn("Library", sock_path)
        elif self.module.IS_LINUX:
            self.assertIn(".1password", sock_path)


class ConfigureAppIconsPlatformTests(unittest.TestCase):
    def setUp(self):
        self.module = load_setup_module()

    def test_configure_app_icons_skips_on_linux(self):
        with mock.patch.object(self.module, "IS_MACOS", False):
            with mock.patch("builtins.print") as mock_print:
                self.module.configure_app_icons()
            mock_print.assert_called_once()
            self.assertIn("macOS only", mock_print.call_args[0][0])


class SetDefaultBrowserPlatformTests(unittest.TestCase):
    def setUp(self):
        self.module = load_setup_module()

    def test_linux_uses_xdg_settings(self):
        mock_which = mock.MagicMock(return_value="/usr/bin/google-chrome")
        mock_run = mock.MagicMock(return_value=mock.MagicMock(returncode=0))
        with (
            mock.patch.object(self.module, "IS_MACOS", False),
            mock.patch.object(self.module, "IS_LINUX", True),
            mock.patch.object(self.module.shutil, "which", mock_which),
            mock.patch.object(self.module.subprocess, "run", mock_run),
        ):
            self.module.set_default_browser()
        # Should have called xdg-settings
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "xdg-settings")

    def test_macos_skips_when_chrome_missing(self):
        with (
            mock.patch.object(self.module, "IS_MACOS", True),
            mock.patch.object(self.module, "IS_LINUX", False),
            mock.patch.object(Path, "exists", return_value=False),
            mock.patch("builtins.print") as mock_print,
        ):
            self.module.set_default_browser()
        output = mock_print.call_args[0][0]
        self.assertIn("Chrome not installed", output)


class NonInteractiveTests(unittest.TestCase):
    def setUp(self):
        self.module = load_setup_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def test_parse_args_non_interactive_flag(self):
        args = self.module.parse_args(["--non-interactive"])
        self.assertTrue(args.non_interactive)

    def test_parse_args_default_is_interactive(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            args = self.module.parse_args([])
            self.assertFalse(args.non_interactive)

    def test_parse_args_ci_env_enables_non_interactive(self):
        with mock.patch.dict(os.environ, {"CI": "1"}):
            args = self.module.parse_args([])
            self.assertTrue(args.non_interactive)

    def test_prompt_identity_non_interactive_from_env(self):
        identity_file = self.root / "identity.json"
        with (
            mock.patch.object(self.module, "IDENTITY_FILE", identity_file),
            mock.patch.dict(os.environ, {
                "DOTFILES_NAME": "CI User",
                "DOTFILES_EMAIL": "ci@example.com",
            }),
        ):
            result = self.module.prompt_identity(non_interactive=True)

        self.assertEqual(result["__NAME__"], "CI User")
        self.assertEqual(result["__EMAIL__"], "ci@example.com")

    def test_prompt_identity_non_interactive_from_saved(self):
        identity_file = self.root / "identity.json"
        identity_file.parent.mkdir(parents=True, exist_ok=True)
        identity_file.write_text(json.dumps({
            "__NAME__": "Saved User",
            "__EMAIL__": "saved@example.com",
        }))

        with (
            mock.patch.object(self.module, "IDENTITY_FILE", identity_file),
            mock.patch.dict(os.environ, {}, clear=True),
        ):
            result = self.module.prompt_identity(non_interactive=True)

        self.assertEqual(result["__NAME__"], "Saved User")
        self.assertEqual(result["__EMAIL__"], "saved@example.com")

    def test_prompt_identity_non_interactive_missing_value_exits(self):
        identity_file = self.root / "identity.json"
        with (
            mock.patch.object(self.module, "IDENTITY_FILE", identity_file),
            mock.patch.dict(os.environ, {}, clear=True),
        ):
            with self.assertRaises(SystemExit) as ctx:
                self.module.prompt_identity(non_interactive=True)
            self.assertEqual(ctx.exception.code, 1)

    def test_prompt_identity_non_interactive_env_overrides_saved(self):
        identity_file = self.root / "identity.json"
        identity_file.parent.mkdir(parents=True, exist_ok=True)
        identity_file.write_text(json.dumps({
            "__NAME__": "Old Name",
            "__EMAIL__": "old@example.com",
        }))

        with (
            mock.patch.object(self.module, "IDENTITY_FILE", identity_file),
            mock.patch.dict(os.environ, {
                "DOTFILES_NAME": "New Name",
                "DOTFILES_EMAIL": "new@example.com",
            }),
        ):
            result = self.module.prompt_identity(non_interactive=True)

        self.assertEqual(result["__NAME__"], "New Name")
        self.assertEqual(result["__EMAIL__"], "new@example.com")


class SshConfigTemplateTests(unittest.TestCase):
    def setUp(self):
        self.module = load_setup_module()

    def test_ssh_config_has_placeholder(self):
        ssh_config = REPO_ROOT / "ssh" / "config"
        content = ssh_config.read_text()
        self.assertIn("__OP_SSH_AGENT_SOCK__", content)

    def test_ssh_config_needs_templating(self):
        ssh_config = REPO_ROOT / "ssh" / "config"
        self.assertTrue(
            self.module.needs_templating(ssh_config, ["__OP_SSH_AGENT_SOCK__"])
        )

    def test_ssh_config_renders_with_socket_path(self):
        ssh_config = REPO_ROOT / "ssh" / "config"
        rendered = self.module.render_template(
            ssh_config,
            {"__OP_SSH_AGENT_SOCK__": "/home/user/.1password/agent.sock"},
        )
        self.assertIn("/home/user/.1password/agent.sock", rendered)
        self.assertNotIn("__OP_SSH_AGENT_SOCK__", rendered)


class ZprofileTests(unittest.TestCase):
    def test_zprofile_handles_both_brew_paths(self):
        zprofile = REPO_ROOT / "shell" / "zprofile"
        content = zprofile.read_text()
        self.assertIn("/opt/homebrew/bin/brew", content)
        self.assertIn("/home/linuxbrew/.linuxbrew/bin/brew", content)

    def test_zprofile_is_valid_shell(self):
        """zprofile should pass bash -n syntax check (zsh superset)."""
        import subprocess
        result = subprocess.run(
            ["bash", "-n", str(REPO_ROOT / "shell" / "zprofile")],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr.decode())


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.module = load_setup_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.home = self.root / "home"
        self.home.mkdir()

    def test_snapshot_copies_existing_files(self):
        target = self.home / ".gitconfig"
        target.write_text("[user]\nname = Old\n")

        with mock.patch.object(self.module, "SNAPSHOT_DIR", self.root / "snaps"), \
             mock.patch("pathlib.Path.home", return_value=self.home):
            snap_dir = self.module.snapshot_targets([target])

        self.assertIsNotNone(snap_dir)
        snapped = snap_dir / ".gitconfig"
        self.assertTrue(snapped.exists())
        self.assertEqual(snapped.read_text(), "[user]\nname = Old\n")

    def test_snapshot_preserves_symlinks(self):
        real_file = self.home / "real.txt"
        real_file.write_text("content")
        target = self.home / ".zshrc"
        target.symlink_to(real_file)

        with mock.patch.object(self.module, "SNAPSHOT_DIR", self.root / "snaps"), \
             mock.patch("pathlib.Path.home", return_value=self.home):
            snap_dir = self.module.snapshot_targets([target])

        snapped = snap_dir / ".zshrc"
        self.assertTrue(snapped.is_symlink())
        self.assertEqual(snapped.readlink(), real_file)

    def test_snapshot_returns_none_when_nothing_exists(self):
        target = self.home / ".nonexistent"

        with mock.patch.object(self.module, "SNAPSHOT_DIR", self.root / "snaps"), \
             mock.patch("pathlib.Path.home", return_value=self.home):
            snap_dir = self.module.snapshot_targets([target])

        self.assertIsNone(snap_dir)

    def test_restore_replaces_current_with_snapshot(self):
        # Set up original state
        target = self.home / ".gitconfig"
        target.write_text("[user]\nname = Old\n")

        # Snapshot it
        with mock.patch.object(self.module, "SNAPSHOT_DIR", self.root / "snaps"), \
             mock.patch("pathlib.Path.home", return_value=self.home):
            snap_dir = self.module.snapshot_targets([target])

        # Simulate provisioning changing the file
        target.write_text("[user]\nname = New\n")

        # Restore
        with mock.patch("pathlib.Path.home", return_value=self.home):
            self.module.restore_snapshot(snap_dir)

        self.assertEqual(target.read_text(), "[user]\nname = Old\n")

    def test_restore_restores_symlinks(self):
        real_file = self.home / "real.txt"
        real_file.write_text("content")
        target = self.home / ".zshrc"
        target.symlink_to(real_file)

        with mock.patch.object(self.module, "SNAPSHOT_DIR", self.root / "snaps"), \
             mock.patch("pathlib.Path.home", return_value=self.home):
            snap_dir = self.module.snapshot_targets([target])

        # Simulate provisioning replacing the symlink
        target.unlink()
        target.write_text("replaced")

        with mock.patch("pathlib.Path.home", return_value=self.home):
            self.module.restore_snapshot(snap_dir)

        self.assertTrue(target.is_symlink())
        self.assertEqual(target.readlink(), real_file)

    def test_snapshot_handles_nested_paths(self):
        target = self.home / ".config" / "jj" / "config.toml"
        target.parent.mkdir(parents=True)
        target.write_text("key = 'value'\n")

        with mock.patch.object(self.module, "SNAPSHOT_DIR", self.root / "snaps"), \
             mock.patch("pathlib.Path.home", return_value=self.home):
            snap_dir = self.module.snapshot_targets([target])

        snapped = snap_dir / ".config" / "jj" / "config.toml"
        self.assertTrue(snapped.exists())
        self.assertEqual(snapped.read_text(), "key = 'value'\n")


if __name__ == "__main__":
    unittest.main()
