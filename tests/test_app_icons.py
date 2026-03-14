"""Tests for configure_app_icons()."""

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[1]
SETUP_PATH = REPO_ROOT / "setup.py"


import sys


def load_setup_module():
    spec = importlib.util.spec_from_file_location("dotfiles_setup", SETUP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["dotfiles_setup"] = module
    spec.loader.exec_module(module)
    return module


setup = load_setup_module()
configure_app_icons = setup.configure_app_icons
APP_ICON_MAP = setup.APP_ICON_MAP


def _force_macos(func):
    """Decorator to patch IS_MACOS=True so icon tests run on any platform."""
    return patch.object(setup, "IS_MACOS", True)(func)


class TestConfigureAppIcons(unittest.TestCase):
    """Tests for the configure_app_icons function."""

    def test_skips_on_non_macos(self):
        """Should skip entirely on Linux."""
        with (
            patch.object(setup, "IS_MACOS", False),
            patch("builtins.print") as mock_print,
        ):
            configure_app_icons()
        mock_print.assert_called_once()
        assert "macOS only" in mock_print.call_args[0][0]

    @_force_macos
    @patch("dotfiles_setup.shutil.which", return_value=None)
    def test_skips_when_fileicon_not_installed(self, mock_which):
        """Should skip gracefully if fileicon binary is missing."""
        with patch("builtins.print") as mock_print:
            configure_app_icons()
        mock_print.assert_called_once()
        assert "fileicon not installed" in mock_print.call_args[0][0]

    @_force_macos
    @patch("dotfiles_setup.shutil.which", return_value="/opt/homebrew/bin/fileicon")
    def test_skips_when_app_not_installed(self, mock_which):
        """Should skip if the target app doesn't exist."""
        with (
            patch.object(Path, "exists", return_value=False),
            patch("builtins.print") as mock_print,
        ):
            configure_app_icons()
        output = " ".join(call[0][0] for call in mock_print.call_args_list)
        assert "not installed" in output

    @_force_macos
    @patch("dotfiles_setup.shutil.which", return_value="/opt/homebrew/bin/fileicon")
    @patch("dotfiles_setup.subprocess.run")
    def test_skips_when_icon_source_missing(self, mock_run, mock_which):
        """Should skip if the icon source file doesn't exist."""
        orig_exists = Path.exists

        def selective_exists(self):
            s = str(self)
            if s.endswith(".app"):
                return True
            if s.endswith(".icns"):
                return False
            return orig_exists(self)

        with (
            patch.object(Path, "exists", selective_exists),
            patch("builtins.print") as mock_print,
        ):
            configure_app_icons()
        output = " ".join(call[0][0] for call in mock_print.call_args_list)
        assert "icon source missing" in output
        mock_run.assert_not_called()

    @_force_macos
    @patch("dotfiles_setup.shutil.which", return_value="/opt/homebrew/bin/fileicon")
    @patch("dotfiles_setup.subprocess.run")
    def test_skips_when_icon_already_set(self, mock_run, mock_which):
        """Should skip if fileicon test reports icon already present."""
        mock_run.return_value = MagicMock(returncode=0)
        with (
            patch.object(Path, "exists", return_value=True),
            patch("builtins.print") as mock_print,
        ):
            configure_app_icons()
        # fileicon test was called but fileicon set was not
        calls = mock_run.call_args_list
        assert len(calls) == 1
        assert "test" in calls[0][0][0]
        output = " ".join(call[0][0] for call in mock_print.call_args_list)
        assert "already set" in output

    @_force_macos
    @patch("dotfiles_setup.shutil.which", return_value="/opt/homebrew/bin/fileicon")
    @patch("dotfiles_setup.subprocess.run")
    def test_sets_icon_when_not_present(self, mock_run, mock_which):
        """Should call fileicon set when no custom icon is present."""
        mock_run.side_effect = [
            MagicMock(returncode=1),  # fileicon test -> no icon
            MagicMock(returncode=0),  # fileicon set -> success
            MagicMock(returncode=0),  # killall Dock
        ]
        with (
            patch.object(Path, "exists", return_value=True),
            patch("builtins.print") as mock_print,
        ):
            configure_app_icons()
        # fileicon test + fileicon set + killall Dock = 3 calls
        assert mock_run.call_count == 3
        set_call = mock_run.call_args_list[1][0][0]
        assert "set" in set_call

    @_force_macos
    @patch("dotfiles_setup.shutil.which", return_value="/opt/homebrew/bin/fileicon")
    @patch("dotfiles_setup.subprocess.run")
    def test_reports_failure(self, mock_run, mock_which):
        """Should report failure when fileicon set fails."""
        mock_run.side_effect = [
            MagicMock(returncode=1),  # fileicon test -> no icon
            MagicMock(returncode=1, stderr=b"permission denied"),  # set -> fail
        ]
        with (
            patch.object(Path, "exists", return_value=True),
            patch("builtins.print") as mock_print,
        ):
            configure_app_icons()
        output = " ".join(call[0][0] for call in mock_print.call_args_list)
        assert "failed" in output
        assert "permission denied" in output


if __name__ == "__main__":
    unittest.main()
