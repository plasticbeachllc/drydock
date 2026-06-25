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


if __name__ == "__main__":
    unittest.main()
