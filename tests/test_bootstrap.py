import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_PATH = REPO_ROOT / "bootstrap.sh"


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.bin_dir = self.root / "bin"
        self.home_dir = self.root / "home"
        self.brew_prefix = self.root / "fakebrew"
        self.log_file = self.root / "commands.log"

        self.bin_dir.mkdir()
        self.home_dir.mkdir()
        (self.brew_prefix / "opt" / "fzf").mkdir(parents=True)

        self._write_executable(
            self.bin_dir / "brew",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'brew %s\\n' "$*" >> "{self.log_file}"
if [ "${{1:-}}" = "--prefix" ]; then
  echo "{self.brew_prefix}"
  exit 0
fi
if [ "${{1:-}}" = "install" ]; then
  exit 0
fi
exit 0
""",
        )
        self._write_executable(
            self.bin_dir / "uv",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'uv %s\\n' "$*" >> "{self.log_file}"
exit 0
""",
        )
        self._write_executable(
            self.bin_dir / "git",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'git %s\\n' "$*" >> "{self.log_file}"
exit 0
""",
        )
        self._write_executable(
            self.bin_dir / "bun",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'bun %s\\n' "$*" >> "{self.log_file}"
exit 0
""",
        )
        self._write_executable(
            self.bin_dir / "rustup-init",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'rustup-init %s\\n' "$*" >> "{self.log_file}"
exit 0
""",
        )
        self._write_executable(
            self.brew_prefix / "opt" / "fzf" / "install",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'fzf-install %s\\n' "$*" >> "{self.log_file}"
exit 0
""",
        )
        # uname stub that returns Linux (since we're testing on Linux)
        self._write_executable(
            self.bin_dir / "uname",
            f"""#!/usr/bin/env bash
if [ "${{1:-}}" = "-s" ]; then
  echo "Linux"
else
  /usr/bin/uname "$@"
fi
""",
        )

    def _write_executable(self, path: Path, content: str) -> None:
        path.write_text(textwrap.dedent(content))
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def test_bootstrap_installs_packages_and_hands_off_to_setup(self):
        env = os.environ.copy()
        env["HOME"] = str(self.home_dir)
        env["PATH"] = f"{self.bin_dir}:/usr/bin:/bin"

        result = subprocess.run(
            ["bash", str(BOOTSTRAP_PATH)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)

        commands = self.log_file.read_text()
        # CLI tools are installed (no casks on Linux)
        self.assertIn("brew install starship", commands)
        self.assertIn("gh", commands)
        self.assertIn("jq", commands)
        self.assertIn("rustup-init", commands)
        self.assertIn("brew install jj-fzf", commands)
        self.assertIn("rustup-init -y --no-modify-path", commands)
        self.assertIn(
            "fzf-install --key-bindings --completion --no-update-rc --no-bash --no-fish",
            commands,
        )
        self.assertIn(f"uv run {REPO_ROOT / 'setup.py'}", commands)
        self.assertNotIn("git clone", commands)

    def test_bootstrap_skips_casks_on_linux(self):
        """On Linux, GUI casks should not be installed."""
        env = os.environ.copy()
        env["HOME"] = str(self.home_dir)
        env["PATH"] = f"{self.bin_dir}:/usr/bin:/bin"

        result = subprocess.run(
            ["bash", str(BOOTSTRAP_PATH)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)

        commands = self.log_file.read_text()
        self.assertNotIn("--cask ghostty", commands)
        self.assertNotIn("--cask font-maple-mono-nf", commands)
        self.assertNotIn("--cask google-chrome", commands)
        self.assertNotIn("--cask 1password", commands)

    def test_bootstrap_shows_section_banners(self):
        """Output should include section banners for clarity."""
        env = os.environ.copy()
        env["HOME"] = str(self.home_dir)
        env["PATH"] = f"{self.bin_dir}:/usr/bin:/bin"

        result = subprocess.run(
            ["bash", str(BOOTSTRAP_PATH)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("==> Homebrew", result.stdout)
        self.assertIn("==> CLI tools", result.stdout)
        self.assertIn("==> Rust toolchain", result.stdout)
        self.assertIn("==> Running setup.py", result.stdout)

    def test_bootstrap_skips_fileicon_on_linux(self):
        """fileicon is macOS-only, should not appear in Linux installs."""
        env = os.environ.copy()
        env["HOME"] = str(self.home_dir)
        env["PATH"] = f"{self.bin_dir}:/usr/bin:/bin"

        result = subprocess.run(
            ["bash", str(BOOTSTRAP_PATH)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        commands = self.log_file.read_text()
        # fileicon is in MACOS_TOOLS, not COMMON_TOOLS
        # On Linux, the MACOS_TOOLS array should not be installed
        self.assertNotIn("fileicon", commands)

    def test_bootstrap_syntax_valid(self):
        """bootstrap.sh should pass bash -n syntax check."""
        result = subprocess.run(
            ["bash", "-n", str(BOOTSTRAP_PATH)],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr.decode())


if __name__ == "__main__":
    unittest.main()
