import os
import shutil
import stat
import subprocess
import tempfile
import textwrap
import tomllib
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class RustDevelopmentConfigTests(unittest.TestCase):
    def test_managed_rust_wrappers_are_executable(self):
        for path in (
            REPO_ROOT / "cargo" / "rustc-wrapper.sh",
            REPO_ROOT / "rust" / "rust-analyzer.sh",
        ):
            self.assertTrue(os.access(path, os.X_OK), msg=f"{path} is not executable")

    def test_global_cargo_config_uses_safe_managed_wrapper(self):
        config = tomllib.loads((REPO_ROOT / "cargo" / "config.toml").read_text())
        self.assertEqual(
            config["build"]["rustc-wrapper"],
            "__HOME__/.local/bin/drydock-rustc-wrapper",
        )

    def test_project_toolchain_has_required_components(self):
        path = REPO_ROOT / "rust" / "project-template" / "rust-toolchain.toml"
        toolchain = tomllib.loads(path.read_text())["toolchain"]
        self.assertEqual(toolchain["channel"], "stable")
        self.assertTrue(
            {"clippy", "llvm-tools-preview", "rust-analyzer", "rust-src", "rustfmt"}
            <= set(toolchain["components"])
        )

    def test_project_verification_contract_covers_core_checks(self):
        justfile = (REPO_ROOT / "rust" / "project-template" / "justfile").read_text()
        for command in (
            "cargo fmt",
            "cargo check",
            "cargo clippy",
            "cargo nextest",
            "cargo test --doc",
            "cargo llvm-cov",
            "cargo deny",
        ):
            self.assertIn(command, justfile)


class RustToolWrapperTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()

    def _write_executable(self, name: str, content: str) -> Path:
        path = self.bin_dir / name
        path.write_text(textwrap.dedent(content))
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def _path_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PATH"] = f"{self.bin_dir}:/usr/bin:/bin"
        return env

    def test_rustc_wrapper_falls_back_when_sccache_is_missing(self):
        rustc = self._write_executable(
            "fake-rustc",
            """\
            #!/usr/bin/env bash
            printf 'rustc:%s\\n' "$*"
            """,
        )

        result = subprocess.run(
            [REPO_ROOT / "cargo" / "rustc-wrapper.sh", rustc, "--version"],
            env=self._path_env(),
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "rustc:--version")

    def test_rustc_wrapper_uses_sccache_when_available(self):
        rustc = self._write_executable("fake-rustc", "#!/usr/bin/env bash\nexit 9\n")
        self._write_executable(
            "sccache",
            """\
            #!/usr/bin/env bash
            printf 'sccache:%s\\n' "$*"
            """,
        )

        result = subprocess.run(
            [REPO_ROOT / "cargo" / "rustc-wrapper.sh", rustc, "--version"],
            env=self._path_env(),
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(f"sccache:{rustc} --version", result.stdout)

    def test_rustc_wrapper_propagates_sccache_failure_without_retrying_rustc(self):
        rustc = self._write_executable(
            "fake-rustc",
            "#!/usr/bin/env bash\nprintf 'rustc:%s\\n' \"$*\"\n",
        )
        self._write_executable(
            "sccache",
            "#!/usr/bin/env bash\nprintf 'sccache failed\\n' >&2\nexit 1\n",
        )

        result = subprocess.run(
            [REPO_ROOT / "cargo" / "rustc-wrapper.sh", rustc, "--version"],
            env=self._path_env(),
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("sccache failed", result.stderr)

    def test_rust_analyzer_shim_resolves_active_rustup_toolchain(self):
        analyzer = self._write_executable(
            "toolchain-rust-analyzer",
            """\
            #!/usr/bin/env bash
            printf 'rust-analyzer:%s\\n' "$*"
            """,
        )
        self._write_executable(
            "rustup",
            f"""\
            #!/usr/bin/env bash
            if [[ "$1" == "which" && "$2" == "rust-analyzer" ]]; then
                printf '%s\\n' "{analyzer}"
                exit 0
            fi
            exit 2
            """,
        )

        result = subprocess.run(
            [REPO_ROOT / "rust" / "rust-analyzer.sh", "--version"],
            env=self._path_env(),
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "rust-analyzer:--version")


class CodexProfileIntegrationTests(unittest.TestCase):
    def test_rust_fast_profile_uses_supported_sibling_config_layout(self):
        profile_path = REPO_ROOT / "codex" / "rust-fast.config.toml"
        profile = tomllib.loads(profile_path.read_text())

        self.assertEqual(profile_path.name, "rust-fast.config.toml")
        self.assertEqual(profile["model_reasoning_effort"], "medium")
        self.assertIn("developer_instructions", profile)
        self.assertNotIn("profiles", profile)

    @unittest.skipUnless(shutil.which("codex"), "Codex CLI is not installed")
    def test_codex_cli_discovers_rust_fast_profile_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            codex_home = Path(temp_dir)
            shutil.copy2(
                REPO_ROOT / "codex" / "rust-fast.config.toml",
                codex_home / "rust-fast.config.toml",
            )
            env = os.environ.copy()
            env["CODEX_HOME"] = str(codex_home)
            result = subprocess.run(
                [
                    shutil.which("codex"),
                    "--profile",
                    "rust-fast",
                    "debug",
                    "prompt-input",
                    "profile discovery test",
                ],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("For routine Rust work, prefer narrow checks", result.stdout)


if __name__ == "__main__":
    unittest.main()
