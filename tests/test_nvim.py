import os
import shutil
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class NeovimConfigTests(unittest.TestCase):
    def test_mason_ensure_installed_is_assigned(self):
        lsp_config = REPO_ROOT / "nvim" / "lua" / "plugins" / "lsp.lua"
        content = lsp_config.read_text()

        self.assertIn(
            "opts.ensure_installed = vim.list_extend(opts.ensure_installed or {},",
            content,
        )

    def test_lazyvim_rust_and_test_extras_are_enabled(self):
        lazy_config = REPO_ROOT / "nvim" / "lua" / "config" / "lazy.lua"
        content = lazy_config.read_text()

        self.assertIn('import = "lazyvim.plugins.extras.lang.rust"', content)
        self.assertIn('import = "lazyvim.plugins.extras.test.core"', content)

    def test_rust_analyzer_is_not_managed_twice(self):
        lsp_config = REPO_ROOT / "nvim" / "lua" / "plugins" / "lsp.lua"
        self.assertNotIn("servers.rust_analyzer", lsp_config.read_text())

    @unittest.skipUnless(shutil.which("nvim"), "Neovim is not installed")
    def test_rust_lsp_uses_managed_shim_and_disables_mason(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            (home / ".local" / "bin").mkdir(parents=True)
            env = os.environ.copy()
            env["HOME"] = str(home)
            lsp_config = REPO_ROOT / "nvim" / "lua" / "plugins" / "lsp.lua"
            result = subprocess.run(
                [
                    shutil.which("nvim"),
                    "--headless",
                    "-u",
                    "NONE",
                    "-c",
                    (
                        f'lua local specs = dofile("{lsp_config}"); '
                        'assert(specs[1].opts.servers.rust_analyzer == nil); '
                        'local opts = { ensure_installed = { "rust-analyzer", "pyright" } }; '
                        'specs[2].opts(nil, opts); '
                        'assert(not vim.tbl_contains(opts.ensure_installed, "rust-analyzer")); '
                        'local rustacean = specs[3].opts(nil, {}); '
                        'assert(rustacean.server.cmd[1] == vim.fn.expand("~/.local/bin/rust-analyzer"))'
                    ),
                    "-c",
                    "qa",
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)

    @unittest.skipUnless(shutil.which("nvim"), "Neovim is not installed")
    def test_neovim_resolves_managed_rust_analyzer_shim(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            local_bin = home / ".local" / "bin"
            local_bin.mkdir(parents=True)
            toolchain_bin = home / "toolchain" / "bin"
            toolchain_bin.mkdir(parents=True)
            command_bin = home / "command-bin"
            command_bin.mkdir()

            analyzer = toolchain_bin / "rust-analyzer"
            analyzer.write_text(
                "#!/usr/bin/env bash\n"
                "printf 'stub-rust-analyzer 1.2.3\\n'\n"
            )
            analyzer.chmod(analyzer.stat().st_mode | stat.S_IXUSR)

            rustup = command_bin / "rustup"
            rustup.write_text(textwrap.dedent(f"""\
                #!/usr/bin/env bash
                if [[ "$1" == "which" && "$2" == "rust-analyzer" ]]; then
                    printf '%s\\n' "{analyzer}"
                    exit 0
                fi
                exit 2
                """))
            rustup.chmod(rustup.stat().st_mode | stat.S_IXUSR)

            (local_bin / "rust-analyzer").symlink_to(
                REPO_ROOT / "rust" / "rust-analyzer.sh"
            )

            env = os.environ.copy()
            env["HOME"] = str(home)
            env["PATH"] = f"{command_bin}:/usr/bin:/bin"
            result = subprocess.run(
                [
                    shutil.which("nvim"),
                    "--headless",
                    "-u",
                    "NONE",
                    "-c",
                    f"luafile {REPO_ROOT / 'nvim' / 'lua' / 'config' / 'options.lua'}",
                    "-c",
                    (
                        'lua local output = vim.fn.system({"rust-analyzer", "--version"}); '
                        'assert(vim.v.shell_error == 0, output); '
                        'assert(output == "stub-rust-analyzer 1.2.3\\n", output)'
                    ),
                    "-c",
                    "qa",
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)

    @unittest.skipUnless(shutil.which("nvim"), "Neovim is not installed")
    def test_neovim_does_not_add_current_directory_when_path_is_empty(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            (home / ".local" / "bin").mkdir(parents=True)
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["PATH"] = ""
            local_bin = home / ".local" / "bin"

            result = subprocess.run(
                [
                    shutil.which("nvim"),
                    "--headless",
                    "-u",
                    "NONE",
                    "-c",
                    f"luafile {REPO_ROOT / 'nvim' / 'lua' / 'config' / 'options.lua'}",
                    "-c",
                    f'lua assert(vim.env.PATH == "{local_bin}", vim.env.PATH)',
                    "-c",
                    "qa",
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)

    @unittest.skipUnless(shutil.which("nvim"), "Neovim is not installed")
    def test_neovim_prefers_homebrew_rustup_proxies_for_gui_commands(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home = root / "home"
            (home / ".local" / "bin").mkdir(parents=True)
            command_bin = root / "command-bin"
            command_bin.mkdir()
            brew_rustup_bin = root / "brew" / "opt" / "rustup" / "bin"
            brew_rustup_bin.mkdir(parents=True)

            (command_bin / "cargo").write_text("#!/bin/sh\nprintf 'standalone-cargo\\n'\n")
            (brew_rustup_bin / "cargo").write_text("#!/bin/sh\nprintf 'rustup-cargo\\n'\n")
            for cargo in (command_bin / "cargo", brew_rustup_bin / "cargo"):
                cargo.chmod(cargo.stat().st_mode | stat.S_IXUSR)

            env = os.environ.copy()
            env["HOME"] = str(home)
            env["HOMEBREW_PREFIX"] = str(root / "brew")
            env["PATH"] = f"{command_bin}:/usr/bin:/bin"
            result = subprocess.run(
                [
                    shutil.which("nvim"),
                    "--headless",
                    "-u",
                    "NONE",
                    "-c",
                    f"luafile {REPO_ROOT / 'nvim' / 'lua' / 'config' / 'options.lua'}",
                    "-c",
                    (
                        'lua local output = vim.fn.system({"cargo", "--version"}); '
                        'assert(vim.v.shell_error == 0, output); '
                        'assert(output == "rustup-cargo\\n", output)'
                    ),
                    "-c",
                    "qa",
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)


if __name__ == "__main__":
    unittest.main()
