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
        self.dconf_profile_dir = self.root / "etc" / "dconf" / "profile"
        self.gdm_dconf_dir = self.root / "etc" / "dconf" / "db" / "gdm.d"
        self.grub_default = self.root / "etc" / "default" / "grub"
        self.grub_config = self.root / "boot" / "grub" / "grub.cfg"

        self.bin_dir.mkdir()
        self.home_dir.mkdir()
        self.dconf_profile_dir.mkdir(parents=True)
        self.gdm_dconf_dir.mkdir(parents=True)
        self.grub_default.parent.mkdir(parents=True)
        self.grub_config.parent.mkdir(parents=True)
        (self.brew_prefix / "opt" / "fzf").mkdir(parents=True)
        self.grub_default.write_text('GRUB_CMDLINE_LINUX_DEFAULT="quiet"\n')

        self._write_executable(
            self.bin_dir / "brew",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'brew %s\\n' "$*" >> "{self.log_file}"
if [ "${{NONINTERACTIVE:-}}" != "1" ]; then
  echo "brew called without NONINTERACTIVE=1" >&2
  exit 2
fi
if [ "${{HOMEBREW_NO_ENV_HINTS:-}}" != "1" ]; then
  echo "brew called without HOMEBREW_NO_ENV_HINTS=1" >&2
  exit 2
fi
if [ "${{1:-}}" = "--prefix" ]; then
  echo "{self.brew_prefix}"
  exit 0
fi
if [ "${{1:-}}" = "list" ] && [ "${{2:-}}" = "--cask" ]; then
  exit 1
fi
if [ "${{1:-}}" = "install" ] && [ "${{2:-}}" = "--cask" ] && [ "${{3:-}}" = "${{DRYDOCK_FAIL_BREW_CASK:-}}" ]; then
  exit 1
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
            self.bin_dir / "curl",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{self.log_file}"
cat <<'SCRIPT'
#!/usr/bin/env bash
exit 0
SCRIPT
""",
        )
        self._write_executable(
            self.bin_dir / "xcode-select",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'xcode-select %s\\n' "$*" >> "{self.log_file}"
if [ "${{1:-}}" = "-p" ]; then
  if [ "${{DRYDOCK_XCODE_SELECT_MISSING:-}}" = "1" ]; then
    exit 1
  fi
  echo "/Library/Developer/CommandLineTools"
  exit 0
fi
if [ "${{1:-}}" = "--install" ]; then
  exit 0
fi
exit 0
""",
        )
        self._write_executable(
            self.bin_dir / "xcrun",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'xcrun %s\\n' "$*" >> "{self.log_file}"
if [ "${{1:-}}" = "--find" ] && [ "${{2:-}}" = "clang" ]; then
  if [ "${{DRYDOCK_XCRUN_CLANG_MISSING:-}}" = "1" ]; then
    exit 1
  fi
  echo "/Library/Developer/CommandLineTools/usr/bin/clang"
  exit 0
fi
exit 0
""",
        )
        self._write_executable(
            self.bin_dir / "rustup",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'rustup %s\\n' "$*" >> "{self.log_file}"
if [ "${{1:-}}" = "show" ] && [ "${{2:-}}" = "active-toolchain" ]; then
  exit 1
fi
exit 0
""",
        )
        self._write_executable(
            self.bin_dir / "sudo",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'sudo %s\\n' "$*" >> "{self.log_file}"
if [ "${{1:-}}" = "-n" ] && [ "${{2:-}}" = "true" ]; then
  if [ "${{DRYDOCK_SUDO_CACHE_MISSING:-}}" = "1" ]; then
    exit 1
  fi
  exit 0
fi
if [ "${{1:-}}" = "-v" ]; then
  if [ "${{DRYDOCK_SUDO_VALIDATE_FAIL:-}}" = "1" ]; then
    exit 1
  fi
  exit 0
fi
exit 0
""",
        )
        self._write_executable(
            self.bin_dir / "pacman",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'pacman %s\\n' "$*" >> "{self.log_file}"
exit 0
""",
        )
        self._write_executable(
            self.bin_dir / "systemctl",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'systemctl %s\\n' "$*" >> "{self.log_file}"
exit 0
""",
        )
        self._write_executable(
            self.bin_dir / "ufw",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'ufw %s\\n' "$*" >> "{self.log_file}"
exit 0
""",
        )
        self._write_executable(
            self.bin_dir / "iptables",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'iptables %s\\n' "$*" >> "{self.log_file}"
if [ "${{1:-}}" = "--version" ]; then
  echo "iptables v1.8.13 (nf_tables)"
fi
exit 0
""",
        )
        self._write_executable(
            self.bin_dir / "dconf",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'dconf %s\\n' "$*" >> "{self.log_file}"
exit 0
""",
        )
        self._write_executable(
            self.bin_dir / "gsettings",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'gsettings %s\\n' "$*" >> "{self.log_file}"
exit 0
""",
        )
        self._write_executable(
            self.bin_dir / "gnome-extensions",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'gnome-extensions %s\\n' "$*" >> "{self.log_file}"
if [ "${{1:-}}" = "list" ]; then
  echo "appindicatorsupport@rgcjonas.gmail.com"
fi
exit 0
""",
        )
        self._write_executable(
            self.bin_dir / "grub-mkconfig",
            f"""#!/usr/bin/env bash
set -euo pipefail
printf 'grub-mkconfig %s\\n' "$*" >> "{self.log_file}"
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

    def _stub_uname(self, os_name: str) -> None:
        self._write_executable(
            self.bin_dir / "uname",
            f"""#!/usr/bin/env bash
if [ "${{1:-}}" = "-s" ]; then
  echo "{os_name}"
else
  /usr/bin/uname "$@"
fi
""",
        )

    def test_bootstrap_installs_packages_and_hands_off_to_setup(self):
        env = os.environ.copy()
        env["HOME"] = str(self.home_dir)
        env["PATH"] = f"{self.bin_dir}:/usr/bin:/bin"
        env["DRYDOCK_FORCE_NON_ARCH"] = "1"
        env["DRYDOCK_FORCE_JJ_FZF_INSTALL"] = "1"

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
        self.assertIn("just", commands)
        self.assertIn("rustup", commands)
        self.assertIn("cargo-nextest", commands)
        self.assertIn("cargo-llvm-cov", commands)
        self.assertIn("cargo-deny", commands)
        self.assertIn("sccache", commands)
        self.assertIn("bacon", commands)
        self.assertIn("brew install jj-fzf", commands)
        self.assertIn("rustup toolchain install stable", commands)
        self.assertIn("rustup default stable", commands)
        self.assertIn(
            "rustup component add --toolchain stable clippy rust-analyzer rust-src rustfmt llvm-tools-preview",
            commands,
        )
        self.assertNotIn("rustup-init", commands)
        self.assertIn(
            "fzf-install --key-bindings --completion --no-update-rc --no-bash --no-fish",
            commands,
        )
        self.assertIn("curl -fsSL https://claude.ai/install.sh", commands)
        self.assertIn("curl -fsSL https://chatgpt.com/codex/install.sh", commands)
        self.assertNotIn("brew install codex", commands)
        self.assertIn(f"uv run {REPO_ROOT / 'setup.py'}", commands)
        self.assertNotIn("git clone", commands)

    def test_bootstrap_uses_stable_when_run_from_toolchain_override(self):
        """A project override must not change bootstrap's machine toolchain."""
        project_dir = self.root / "project"
        project_dir.mkdir()
        (project_dir / "rust-toolchain.toml").write_text(
            '[toolchain]\nchannel = "nightly"\n'
        )
        env = os.environ.copy()
        env["HOME"] = str(self.home_dir)
        env["PATH"] = f"{self.bin_dir}:/usr/bin:/bin"
        env["DRYDOCK_FORCE_NON_ARCH"] = "1"

        result = subprocess.run(
            ["bash", str(BOOTSTRAP_PATH)],
            cwd=project_dir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        commands = self.log_file.read_text()
        self.assertIn("rustup toolchain install stable", commands)
        self.assertIn("rustup default stable", commands)
        self.assertIn(
            "rustup component add --toolchain stable clippy rust-analyzer rust-src rustfmt llvm-tools-preview",
            commands,
        )
        self.assertNotIn("rustup show active-toolchain", commands)

    def test_bootstrap_skips_casks_on_linux(self):
        """On Linux, GUI casks should not be installed."""
        env = os.environ.copy()
        env["HOME"] = str(self.home_dir)
        env["PATH"] = f"{self.bin_dir}:/usr/bin:/bin"
        env["DRYDOCK_FORCE_NON_ARCH"] = "1"

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

    def test_bootstrap_installs_required_macos_casks_when_missing(self):
        """On macOS, Chrome and 1Password should be installed when absent."""
        self._stub_uname("Darwin")
        applications_dir = self.root / "Applications"
        applications_dir.mkdir()

        env = os.environ.copy()
        env["HOME"] = str(self.home_dir)
        env["PATH"] = f"{self.bin_dir}:/usr/bin:/bin"
        env["DRYDOCK_APPLICATIONS_DIR"] = str(applications_dir)

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
        self.assertIn("brew install --cask google-chrome", commands)
        self.assertIn("brew install --cask 1password", commands)

    def test_bootstrap_starts_xcode_tools_installer_when_missing(self):
        """On macOS, missing Command Line Tools should launch installer and stop."""
        self._stub_uname("Darwin")

        env = os.environ.copy()
        env["HOME"] = str(self.home_dir)
        env["PATH"] = f"{self.bin_dir}:/usr/bin:/bin"
        env["DRYDOCK_XCODE_SELECT_MISSING"] = "1"

        result = subprocess.run(
            ["bash", str(BOOTSTRAP_PATH)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("After installation finishes, rerun ./bootstrap.sh.", result.stdout)

        commands = self.log_file.read_text()
        self.assertIn("xcode-select -p", commands)
        self.assertIn("xcode-select --install", commands)
        self.assertNotIn("brew install", commands)

    def test_bootstrap_starts_xcode_tools_installer_when_clang_missing(self):
        """macOS preflight should verify CLT tools, not just xcode-select."""
        self._stub_uname("Darwin")

        env = os.environ.copy()
        env["HOME"] = str(self.home_dir)
        env["PATH"] = f"{self.bin_dir}:/usr/bin:/bin"
        env["DRYDOCK_XCRUN_CLANG_MISSING"] = "1"

        result = subprocess.run(
            ["bash", str(BOOTSTRAP_PATH)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("After installation finishes, rerun ./bootstrap.sh.", result.stdout)

        commands = self.log_file.read_text()
        self.assertIn("xcode-select -p", commands)
        self.assertIn("xcrun --find clang", commands)
        self.assertIn("xcode-select --install", commands)
        self.assertNotIn("brew install", commands)

    def test_bootstrap_fails_before_homebrew_without_interactive_sudo(self):
        """macOS preflight should not let Homebrew discover missing sudo first."""
        self._stub_uname("Darwin")

        env = os.environ.copy()
        env["HOME"] = str(self.home_dir)
        env["PATH"] = f"{self.bin_dir}:/usr/bin:/bin"
        env["DRYDOCK_SUDO_CACHE_MISSING"] = "1"

        result = subprocess.run(
            ["bash", str(BOOTSTRAP_PATH)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Run ./bootstrap.sh from an interactive Terminal", result.stdout)

        commands = self.log_file.read_text()
        self.assertIn("sudo -n true", commands)
        self.assertNotIn("brew install", commands)

    def test_bootstrap_fails_when_required_macos_cask_fails(self):
        """Required macOS apps should not be silently skipped on install failure."""
        self._stub_uname("Darwin")
        applications_dir = self.root / "Applications"
        applications_dir.mkdir()

        env = os.environ.copy()
        env["HOME"] = str(self.home_dir)
        env["PATH"] = f"{self.bin_dir}:/usr/bin:/bin"
        env["DRYDOCK_APPLICATIONS_DIR"] = str(applications_dir)
        env["DRYDOCK_FAIL_BREW_CASK"] = "google-chrome"

        result = subprocess.run(
            ["bash", str(BOOTSTRAP_PATH)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("macOS cask google-chrome", result.stdout)

    def test_bootstrap_shows_section_banners(self):
        """Output should include section banners for clarity."""
        env = os.environ.copy()
        env["HOME"] = str(self.home_dir)
        env["PATH"] = f"{self.bin_dir}:/usr/bin:/bin"
        env["DRYDOCK_FORCE_NON_ARCH"] = "1"

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

    def test_bootstrap_uses_pacman_on_arch(self):
        """Arch Linux should use pacman/AUR instead of Linuxbrew."""
        env = os.environ.copy()
        env["HOME"] = str(self.home_dir)
        env["PATH"] = f"{self.bin_dir}:/usr/bin:/bin"
        env["DRYDOCK_FORCE_ARCH"] = "1"
        env["DRYDOCK_SKIP_AUR"] = "1"
        env["DRYDOCK_DCONF_PROFILE_DIR"] = str(self.dconf_profile_dir)
        env["DRYDOCK_GDM_DCONF_DIR"] = str(self.gdm_dconf_dir)
        env["DRYDOCK_GRUB_DEFAULT"] = str(self.grub_default)
        env["DRYDOCK_GRUB_CONFIG"] = str(self.grub_config)

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
        self.assertIn("sudo pacman -Syu --needed --noconfirm", commands)
        self.assertIn("jujutsu", commands)
        self.assertIn("lazyjj", commands)
        self.assertIn("nodejs", commands)
        self.assertIn("npm", commands)
        self.assertIn("python", commands)
        self.assertIn("dconf", commands)
        self.assertIn("ufw", commands)
        self.assertIn("gnome-shell-extension-appindicator", commands)
        self.assertIn("extension-manager", commands)
        self.assertIn("just", commands)
        self.assertIn("rustup toolchain install stable", commands)
        self.assertIn("rustup default stable", commands)
        self.assertIn("cargo-nextest", commands)
        self.assertIn("cargo-llvm-cov", commands)
        self.assertIn("cargo-deny", commands)
        self.assertIn("sccache", commands)
        self.assertIn("bacon", commands)
        self.assertIn(
            "rustup component add --toolchain stable clippy rust-analyzer rust-src rustfmt llvm-tools-preview",
            commands,
        )
        self.assertIn("sudo systemctl enable --now NetworkManager.service", commands)
        self.assertIn("sudo ufw default deny incoming", commands)
        self.assertIn("sudo ufw default allow outgoing", commands)
        self.assertIn("sudo ufw --force enable", commands)
        self.assertIn("sudo systemctl enable --now ufw.service", commands)
        self.assertIn(f"sudo install -d -m 0755 {self.dconf_profile_dir}", commands)
        self.assertIn(f"sudo tee {self.dconf_profile_dir / 'gdm'}", commands)
        self.assertIn(f"sudo install -d -m 0755 {self.gdm_dconf_dir}", commands)
        self.assertIn(
            f"sudo tee {self.gdm_dconf_dir / '00-drydock-login-screen'}",
            commands,
        )
        self.assertIn("sudo dconf update", commands)
        self.assertIn(
            "gsettings set org.gnome.desktop.interface color-scheme prefer-dark",
            commands,
        )
        self.assertIn(
            "gsettings set org.gnome.desktop.interface show-battery-percentage true",
            commands,
        )
        self.assertIn(
            "gsettings set org.gnome.desktop.peripherals.touchpad tap-to-click true",
            commands,
        )
        self.assertIn(
            "gsettings set org.gnome.shell favorite-apps "
            "['com.mitchellh.ghostty.desktop', 'google-chrome.desktop', "
            "'org.gnome.Nautilus.desktop', 'org.gnome.Settings.desktop', "
            "'1password.desktop']",
            commands,
        )
        self.assertIn(
            "gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com",
            commands,
        )
        self.assertIn(f"sudo install -m 0644", commands)
        self.assertIn(str(self.grub_default), commands)
        self.assertIn(f"sudo grub-mkconfig -o {self.grub_config}", commands)
        self.assertNotIn("brew install starship", commands)

    def test_bootstrap_syntax_valid(self):
        """bootstrap.sh should pass bash -n syntax check."""
        result = subprocess.run(
            ["bash", "-n", str(BOOTSTRAP_PATH)],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr.decode())

    def test_arch_live_syntax_valid(self):
        """Arch live installer should pass bash -n syntax check."""
        result = subprocess.run(
            ["bash", "-n", str(REPO_ROOT / "install" / "arch-live.sh")],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr.decode())


if __name__ == "__main__":
    unittest.main()
