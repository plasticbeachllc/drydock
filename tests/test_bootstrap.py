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
        self.assertIn("brew install --cask ghostty", commands)
        self.assertIn("brew install --cask font-maple-mono-nf", commands)
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


if __name__ == "__main__":
    unittest.main()
