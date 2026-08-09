import importlib.util
import json
import os
import shutil
import stat
import subprocess
import tempfile
import tomllib
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

    def test_sync_branch_skill_is_repo_owned_symlink(self):
        self.assertEqual(
            self.module.SYMLINK_MAP["codex/skills/sync-branch"],
            Path.home() / ".codex" / "skills" / "sync-branch",
        )

    def test_rust_development_files_are_repo_owned(self):
        self.assertEqual(
            self.module.SYMLINK_MAP["cargo/rustc-wrapper.sh"],
            Path.home() / ".local" / "bin" / "drydock-rustc-wrapper",
        )
        self.assertNotIn("cargo/config.toml", self.module.SYMLINK_MAP)
        self.assertEqual(
            self.module.SYMLINK_MAP["rust/rust-analyzer.sh"],
            Path.home() / ".local" / "bin" / "rust-analyzer",
        )
        self.assertEqual(
            self.module.SYMLINK_MAP["codex/rust-fast.config.toml"],
            Path.home() / ".codex" / "rust-fast.config.toml",
        )

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

        self.module._set_btop_color_theme(conf, "Plastic Beach")

        lines = conf.read_text().splitlines()
        self.assertEqual(lines[-1], 'color_theme = "Plastic Beach"')

    def test_render_template_theme_before_identity(self):
        """__THEME_NAME__ must be replaced before __NAME__ to avoid partial match."""
        src = self.root / "template.txt"
        src.write_text("theme=__THEME_NAME__ user=__NAME__\n")

        rendered = self.module.render_template(
            src,
            {
                "__NAME__": "Taylor",
                "__THEME_NAME__": "Plastic Beach",
            },
        )

        self.assertEqual(rendered, "theme=Plastic Beach user=Taylor\n")

    def test_needs_templating_detects_theme_placeholders(self):
        src = self.root / "config.toml"
        src.write_text('highlight = "__THEME_HIGHLIGHT_COLOR__"\n')

        self.assertTrue(
            self.module.needs_templating(src, ["__NAME__", "__THEME_HIGHLIGHT_COLOR__"])
        )

    def test_cargo_config_renders_machine_home(self):
        cargo_config = REPO_ROOT / "cargo" / "config.toml"
        rendered = self.module.render_template(
            cargo_config,
            {"__HOME__": "/Users/example"},
        )

        self.assertIn(
            'rustc-wrapper = "/Users/example/.local/bin/drydock-rustc-wrapper"',
            rendered,
        )
        self.assertNotIn("__HOME__", rendered)

    def test_generate_theme_files_dry_run_does_not_write_files(self):
        theme = tomllib.loads(
            (REPO_ROOT / "themes" / "themes.toml").read_text()
        )["plastic-beach"]
        generated_dir = self.root / "generated"
        rendered_dir = self.root / "rendered"

        with mock.patch.object(self.module, "GENERATED_DIR", generated_dir), \
             mock.patch.object(self.module, "RENDERED_DIR", rendered_dir), \
             mock.patch("pathlib.Path.home", return_value=self.root):
            placeholders = self.module.generate_theme_files(
                "plastic-beach", theme, dry_run=True
            )

        self.assertFalse(generated_dir.exists())
        self.assertFalse(rendered_dir.exists())
        self.assertFalse((self.root / ".config").exists())
        self.assertEqual(placeholders["__THEME_NAME__"], "Plastic Beach")

    def test_merge_cargo_config_preserves_existing_settings(self):
        cargo_config = self.root / ".cargo" / "config.toml"
        cargo_config.parent.mkdir()
        cargo_config.write_text(
            "[net]\n"
            "git-fetch-with-cli = true\n\n"
            "[build]\n"
            'target-dir = "/tmp/target"\n'
        )

        status = self.module.merge_cargo_config(
            cargo_config,
            Path("/Users/example/.local/bin/drydock-rustc-wrapper"),
        )

        self.assertEqual(status, "merged Drydock Rust wrapper")
        merged = cargo_config.read_text()
        self.assertIn("[net]\ngit-fetch-with-cli = true", merged)
        self.assertIn('target-dir = "/tmp/target"', merged)
        self.assertIn(
            'rustc-wrapper = "/Users/example/.local/bin/drydock-rustc-wrapper"',
            merged,
        )
        self.module.tomllib.loads(merged)

    def test_merge_cargo_config_rejects_existing_non_drydock_wrapper(self):
        cargo_config = self.root / ".cargo" / "config.toml"
        cargo_config.parent.mkdir()
        original = '[build]\nrustc-wrapper = "/nix/store/wrapper"\n'
        cargo_config.write_text(original)

        with self.assertRaisesRegex(ValueError, "already sets build.rustc-wrapper"):
            self.module.merge_cargo_config(
                cargo_config,
                Path("/Users/example/.local/bin/drydock-rustc-wrapper"),
            )

        self.assertEqual(cargo_config.read_text(), original)

    def test_merge_cargo_config_replaces_legacy_managed_symlink(self):
        cargo_config = self.root / ".cargo" / "config.toml"
        cargo_config.parent.mkdir()
        cargo_config.symlink_to(REPO_ROOT / "cargo" / "config.toml")

        self.module.merge_cargo_config(
            cargo_config,
            Path("/Users/example/.local/bin/drydock-rustc-wrapper"),
        )

        self.assertFalse(cargo_config.is_symlink())
        self.assertIn("/Users/example", cargo_config.read_text())

    def test_merge_cargo_config_rejects_unmanaged_symlink(self):
        cargo_config = self.root / ".cargo" / "config.toml"
        cargo_config.parent.mkdir()
        shared_config = self.root / "shared" / "cargo.toml"
        shared_config.parent.mkdir()
        original = "[net]\ngit-fetch-with-cli = true\n"
        shared_config.write_text(original)
        cargo_config.symlink_to(shared_config)

        with self.assertRaisesRegex(ValueError, "unmanaged symlink"):
            self.module.merge_cargo_config(
                cargo_config,
                Path("/Users/example/.local/bin/drydock-rustc-wrapper"),
            )

        self.assertTrue(cargo_config.is_symlink())
        self.assertEqual(shared_config.read_text(), original)

    def test_active_cargo_config_prefers_and_merges_legacy_filename(self):
        cargo_dir = self.root / ".cargo"
        cargo_dir.mkdir()
        legacy_config = cargo_dir / "config"
        toml_config = cargo_dir / "config.toml"
        legacy_config.write_text("[net]\ngit-fetch-with-cli = true\n")
        toml_original = "[http]\ncheck-revoke = false\n"
        toml_config.write_text(toml_original)

        active_config = self.module.active_cargo_config(cargo_dir)
        self.module.merge_cargo_config(
            active_config,
            Path("/Users/example/.local/bin/drydock-rustc-wrapper"),
        )

        self.assertEqual(active_config, legacy_config)
        self.assertIn('rustc-wrapper = "/Users/example/.local/bin/drydock-rustc-wrapper"',
                      legacy_config.read_text())
        self.assertEqual(toml_config.read_text(), toml_original)

    def test_active_cargo_config_honors_cargo_home(self):
        cargo_home = self.root / "custom-cargo"

        with mock.patch.dict(os.environ, {"CARGO_HOME": str(cargo_home)}):
            self.assertEqual(
                self.module.active_cargo_config(),
                cargo_home / "config.toml",
            )

    def test_merge_cargo_config_handles_dotted_build_settings(self):
        cargo_config = self.root / ".cargo" / "config.toml"
        cargo_config.parent.mkdir()
        cargo_config.write_text('build.target-dir = "/tmp/target"\n')

        self.module.merge_cargo_config(
            cargo_config,
            Path("/Users/example/.local/bin/drydock-rustc-wrapper"),
        )

        merged = cargo_config.read_text()
        self.assertIn('build.target-dir = "/tmp/target"', merged)
        self.assertIn(
            'build.rustc-wrapper = "/Users/example/.local/bin/drydock-rustc-wrapper"',
            merged,
        )
        self.module.tomllib.loads(merged)

        status = self.module.merge_cargo_config(
            cargo_config,
            Path("/Users/example/.local/bin/drydock-rustc-wrapper"),
        )
        self.assertEqual(status, "skipped (Drydock Rust wrapper already configured)")
        self.assertEqual(cargo_config.read_text(), merged)

    def test_merge_cargo_config_handles_inline_build_settings(self):
        cargo_config = self.root / ".cargo" / "config.toml"
        cargo_config.parent.mkdir()
        cargo_config.write_text('build = { target-dir = "/tmp/target" }\n')

        self.module.merge_cargo_config(
            cargo_config,
            Path("/Users/example/.local/bin/drydock-rustc-wrapper"),
        )

        merged = cargo_config.read_text()
        parsed = self.module.tomllib.loads(merged)
        self.assertEqual(parsed["build"]["target-dir"], "/tmp/target")
        self.assertEqual(
            parsed["build"]["rustc-wrapper"],
            "/Users/example/.local/bin/drydock-rustc-wrapper",
        )

        status = self.module.merge_cargo_config(
            cargo_config,
            Path("/Users/example/.local/bin/drydock-rustc-wrapper"),
        )
        self.assertEqual(status, "skipped (Drydock Rust wrapper already configured)")
        self.assertEqual(cargo_config.read_text(), merged)


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

    def test_parse_args_dry_run_flag(self):
        args = self.module.parse_args(["--dry-run"])
        self.assertTrue(args.dry_run)

    def test_parse_args_default_no_dry_run(self):
        args = self.module.parse_args([])
        self.assertFalse(args.dry_run)

    def test_create_symlink_dry_run_does_not_create(self):
        source = self.root / "source.txt"
        source.write_text("content")
        target = self.root / "target.txt"

        status = self.module.create_symlink(source, target, dry_run=True)
        self.assertEqual(status, "would link")
        self.assertFalse(target.exists())

    def test_create_symlink_dry_run_reports_relink(self):
        source = self.root / "source.txt"
        source.write_text("content")
        wrong = self.root / "wrong.txt"
        wrong.write_text("wrong")
        target = self.root / "target.txt"
        target.symlink_to(wrong)

        status = self.module.create_symlink(source, target, dry_run=True)
        self.assertEqual(status, "would relink (currently pointing elsewhere)")
        # Symlink should still point to wrong
        self.assertEqual(target.resolve(), wrong.resolve())

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

    def test_prompt_identity_dry_run_does_not_save_identity(self):
        identity_file = self.root / "identity.json"

        with mock.patch.object(self.module, "IDENTITY_FILE", identity_file), \
             mock.patch.dict(os.environ, {
                 "DOTFILES_NAME": "CI User",
                 "DOTFILES_EMAIL": "ci@example.com",
             }):
            self.module.prompt_identity(non_interactive=True, dry_run=True)

        self.assertFalse(identity_file.exists())

    def test_prompt_theme_dry_run_does_not_save_selection(self):
        identity_file = self.root / "identity.json"

        with mock.patch.object(self.module, "IDENTITY_FILE", identity_file):
            key, _theme = self.module.prompt_theme(non_interactive=True, dry_run=True)

        self.assertEqual(key, "plastic-beach")
        self.assertFalse(identity_file.exists())

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


class PromptOpTeamNonInteractiveTests(unittest.TestCase):
    def setUp(self):
        self.module = load_setup_module()
        self.tmpdir = tempfile.mkdtemp()
        self.root = Path(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_prompt_op_team_non_interactive_from_env(self):
        identity_file = self.root / "identity.json"
        with (
            mock.patch.object(self.module, "IDENTITY_FILE", identity_file),
            mock.patch.dict(os.environ, {"DOTFILES_OP_TEAM": "myteam.1password.com"}),
        ):
            result = self.module.prompt_op_team(non_interactive=True)

        self.assertEqual(result, "myteam.1password.com")
        # Should persist the value
        saved = json.loads(identity_file.read_text())
        self.assertEqual(saved["__OP_TEAM__"], "myteam.1password.com")

    def test_prompt_op_team_non_interactive_from_saved(self):
        identity_file = self.root / "identity.json"
        identity_file.parent.mkdir(parents=True, exist_ok=True)
        identity_file.write_text(json.dumps({"__OP_TEAM__": "saved.1password.com"}))

        with (
            mock.patch.object(self.module, "IDENTITY_FILE", identity_file),
            mock.patch.dict(os.environ, {}, clear=True),
        ):
            result = self.module.prompt_op_team(non_interactive=True)

        self.assertEqual(result, "saved.1password.com")

    def test_prompt_op_team_non_interactive_missing_exits(self):
        identity_file = self.root / "identity.json"
        with (
            mock.patch.object(self.module, "IDENTITY_FILE", identity_file),
            mock.patch.dict(os.environ, {}, clear=True),
        ):
            with self.assertRaises(SystemExit) as ctx:
                self.module.prompt_op_team(non_interactive=True)
            self.assertEqual(ctx.exception.code, 1)


class OnePasswordCliTests(unittest.TestCase):
    def setUp(self):
        self.module = load_setup_module()

    def test_op_signin_uses_raw_force_and_verifies_session_for_account(self):
        signin_result = mock.Mock(returncode=0, stdout="session-token\n")
        whoami_result = mock.Mock(returncode=0)

        with mock.patch.object(
            self.module.subprocess,
            "run",
            side_effect=[signin_result, whoami_result],
        ) as run:
            self.assertTrue(self.module.op_signin("myteam.1password.com"))

        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[0], [
            "op", "signin", "--raw", "--force",
            "--account", "myteam.1password.com",
        ])
        self.assertEqual(commands[1], [
            "op", "whoami",
            "--account", "myteam.1password.com",
            "--session", "session-token",
        ])

    def test_op_signin_accepts_app_integration_without_session_token(self):
        signin_result = mock.Mock(returncode=0, stdout="")
        whoami_result = mock.Mock(returncode=0)

        with mock.patch.object(
            self.module.subprocess,
            "run",
            side_effect=[signin_result, whoami_result],
        ) as run:
            self.assertTrue(self.module.op_signin("myteam.1password.com"))

        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[1], [
            "op", "whoami",
            "--account", "myteam.1password.com",
        ])

    def test_op_authenticated_returns_false_when_whoami_fails(self):
        with mock.patch.object(
            self.module.subprocess,
            "run",
            side_effect=subprocess.CalledProcessError(1, ["op", "whoami"]),
        ):
            self.assertFalse(self.module.op_authenticated("myteam.1password.com"))


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

    def test_zprofile_reapplies_rustup_after_brew_shellenv(self):
        content = (REPO_ROOT / "shell" / "zprofile").read_text()
        self.assertIn("drydock_rustup_path", content)
        self.assertIn('$HOME/.cargo/bin', content)
        self.assertIn('$HOME/.local/bin', content)

    def test_zshenv_prioritizes_homebrew_rustup_in_non_login_shells(self):
        zsh = shutil.which("zsh")
        if not zsh:
            self.skipTest("zsh is not installed")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home = root / "home"
            home.mkdir()
            rustup_bin = root / "brew" / "opt" / "rustup" / "bin"
            rustup_bin.mkdir(parents=True)
            rustc = rustup_bin / "rustc"
            rustc.write_text("#!/bin/sh\nprintf 'rustup-rustc\\n'\n")
            rustc.chmod(rustc.stat().st_mode | stat.S_IXUSR)

            env = os.environ.copy()
            env["HOME"] = str(home)
            env["HOMEBREW_PREFIX"] = str(root / "brew")
            env["PATH"] = "/usr/bin:/bin"
            zshenv = REPO_ROOT / "shell" / "zshenv"
            result = subprocess.run(
                [
                    zsh,
                    "-dfc",
                    f'source "{zshenv}"; rustc',
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout, "rustup-rustc\n")

    def test_rustup_path_is_restored_after_homebrew_prepends_its_bin(self):
        zsh = shutil.which("zsh")
        if not zsh:
            self.skipTest("zsh is not installed")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home = root / "home"
            home.mkdir()
            rustup_bin = root / "brew" / "opt" / "rustup" / "bin"
            standalone_bin = root / "brew" / "bin"
            rustup_bin.mkdir(parents=True)
            standalone_bin.mkdir(parents=True)
            for path, output in (
                (rustup_bin / "rustc", "rustup-rustc"),
                (standalone_bin / "rustc", "standalone-rustc"),
            ):
                path.write_text(f"#!/bin/sh\nprintf '{output}\\n'\n")
                path.chmod(path.stat().st_mode | stat.S_IXUSR)

            env = os.environ.copy()
            env["HOME"] = str(home)
            env["HOMEBREW_PREFIX"] = str(root / "brew")
            env["PATH"] = "/usr/bin:/bin"
            zshenv = REPO_ROOT / "shell" / "zshenv"
            result = subprocess.run(
                [
                    zsh,
                    "-dfc",
                    (
                        f'source "{zshenv}"; '
                        f'PATH="{standalone_bin}:$PATH"; '
                        'drydock_rustup_path; rustc'
                    ),
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout, "rustup-rustc\n")

    def test_zshenv_exposes_managed_shims_in_non_login_shells(self):
        zsh = shutil.which("zsh")
        if not zsh:
            self.skipTest("zsh is not installed")

        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            local_bin = home / ".local" / "bin"
            local_bin.mkdir(parents=True)
            shim = local_bin / "rust-analyzer"
            shim.write_text("#!/bin/sh\nprintf 'managed-rust-analyzer\\n'\n")
            shim.chmod(shim.stat().st_mode | stat.S_IXUSR)

            env = os.environ.copy()
            env["HOME"] = str(home)
            env["PATH"] = "/usr/bin:/bin"
            zshenv = REPO_ROOT / "shell" / "zshenv"
            result = subprocess.run(
                [zsh, "-dfc", f'source "{zshenv}"; rust-analyzer'],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout, "managed-rust-analyzer\n")

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
