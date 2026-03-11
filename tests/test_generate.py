import math
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "themes"))

from generate import (
    ansi_rgb,
    blend,
    btop_theme,
    ghostty_theme,
    hex_to_rgb,
    lazygit_config,
    load_themes,
    nvim_dashboard_colors,
    nvim_theme_colors,
    rgb_to_hex,
    theme_placeholders,
)


class ColorUtilTests(unittest.TestCase):
    def test_hex_to_rgb_with_hash(self):
        self.assertEqual(hex_to_rgb("#ff8000"), (255, 128, 0))

    def test_hex_to_rgb_without_hash(self):
        self.assertEqual(hex_to_rgb("ff8000"), (255, 128, 0))

    def test_blend_zero_returns_c1(self):
        self.assertEqual(blend("#ff0000", "#0000ff", 0.0), "#ff0000")

    def test_blend_one_returns_c2(self):
        self.assertEqual(blend("#ff0000", "#0000ff", 1.0), "#0000ff")

    def test_blend_midpoint(self):
        result = blend("#000000", "#ffffff", 0.5)
        r, g, b = hex_to_rgb(result)
        self.assertTrue(all(126 <= c <= 130 for c in (r, g, b)))

    def test_ansi_rgb_format(self):
        result = ansi_rgb("#20e8d0")
        self.assertRegex(result, r"^\d{1,3};\d{1,3};\d{1,3}$")
        parts = [int(x) for x in result.split(";")]
        self.assertTrue(all(0 <= p <= 255 for p in parts))

    def test_ansi_rgb_values(self):
        self.assertEqual(ansi_rgb("#ff8000"), "255;128;0")


class ThemeConsistencyTests(unittest.TestCase):
    """Validate themes.toml structure and color quality."""

    def setUp(self):
        self.themes = load_themes()

    def test_all_themes_have_identical_keys(self):
        key_sets = []
        for theme in self.themes.values():
            key_sets.append(self._flatten_keys(theme))
        for ks in key_sets[1:]:
            self.assertEqual(key_sets[0], ks)

    def test_hex_colors_valid_format(self):
        pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
        for tk, theme in self.themes.items():
            for path, val in self._walk_values(theme):
                if isinstance(val, str) and val.startswith("#"):
                    self.assertRegex(val, pattern, f"{tk}.{path}")

    def test_ansi_arrays_have_8_entries(self):
        for tk, theme in self.themes.items():
            self.assertEqual(len(theme["terminal"]["ansi"]), 8, f"{tk} ansi")
            self.assertEqual(len(theme["terminal"]["ansi_bright"]), 8, f"{tk} ansi_bright")

    def test_preview_has_required_keys(self):
        required = {"comment", "module", "var", "var2", "method", "prop", "string"}
        for tk, theme in self.themes.items():
            self.assertEqual(set(theme["preview"].keys()), required, tk)

    def test_ansi_contrast_floor_3_to_1(self):
        """All non-black ANSI colors must have >= 3.0:1 contrast against bg."""
        for tk, theme in self.themes.items():
            bg = theme["base"]["bg"]
            for label, colors in [("ansi", theme["terminal"]["ansi"]),
                                  ("ansi_bright", theme["terminal"]["ansi_bright"])]:
                for i, c in enumerate(colors):
                    if i == 0:  # skip black
                        continue
                    cr = self._contrast_ratio(c, bg)
                    self.assertGreaterEqual(
                        cr, 3.0,
                        f"{tk} {label}[{i}] {c} vs bg {bg}: {cr:.1f}:1",
                    )

    def test_dim_fg_contrast_floor_3_to_1(self):
        for tk, theme in self.themes.items():
            bg = theme["base"]["bg"]
            dim_fg = theme["base"]["dim_fg"]
            cr = self._contrast_ratio(dim_fg, bg)
            self.assertGreaterEqual(cr, 3.0, f"{tk} dim_fg {dim_fg}: {cr:.1f}:1")

    def test_fg_contrast_minimum_8_to_1(self):
        for tk, theme in self.themes.items():
            bg = theme["base"]["bg"]
            fg = theme["base"]["fg"]
            cr = self._contrast_ratio(fg, bg)
            self.assertGreaterEqual(cr, 8.0, f"{tk} fg {fg}: {cr:.1f}:1")

    # -- helpers --

    def _flatten_keys(self, d, prefix=""):
        keys = set()
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                keys |= self._flatten_keys(v, key)
            else:
                keys.add(key)
        return keys

    def _walk_values(self, d, prefix=""):
        for k, v in d.items():
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                yield from self._walk_values(v, path)
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    yield f"{path}[{i}]", item
            else:
                yield path, v

    @staticmethod
    def _srgb_to_linear(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    @classmethod
    def _luminance(cls, hex_color):
        r, g, b = hex_to_rgb(hex_color)
        return (0.2126 * cls._srgb_to_linear(r)
                + 0.7152 * cls._srgb_to_linear(g)
                + 0.0722 * cls._srgb_to_linear(b))

    @classmethod
    def _contrast_ratio(cls, c1, c2):
        l1, l2 = cls._luminance(c1), cls._luminance(c2)
        if l1 < l2:
            l1, l2 = l2, l1
        return (l1 + 0.05) / (l2 + 0.05)


class GeneratorTests(unittest.TestCase):
    """Verify each generator produces valid output for all themes."""

    def setUp(self):
        self.themes = load_themes()

    def test_ghostty_theme_no_quoted_hex(self):
        for tk, theme in self.themes.items():
            output = ghostty_theme(theme)
            for line in output.splitlines():
                if "=" in line and not line.startswith("#"):
                    self.assertNotIn('"', line, f"{tk}: {line}")
                    self.assertNotIn("'", line, f"{tk}: {line}")

    def test_nvim_theme_colors_valid_lua(self):
        for tk, theme in self.themes.items():
            output = nvim_theme_colors(theme)
            self.assertIn("return {", output)
            self.assertEqual(output.count("{"), output.count("}"), f"{tk} unbalanced braces")

    def test_nvim_dashboard_colors_valid_lua(self):
        for tk, theme in self.themes.items():
            output = nvim_dashboard_colors(theme)
            self.assertIn("return {", output)
            self.assertIn("header_color", output)
            self.assertIn("header_text", output)
            self.assertIn(theme["name"].lower(), output)

    def test_lazygit_config_valid_yaml_structure(self):
        for tk, theme in self.themes.items():
            output = lazygit_config(theme)
            self.assertIn("gui:", output)
            self.assertIn("activeBorderColor:", output)

    def test_btop_theme_format(self):
        for tk, theme in self.themes.items():
            output = btop_theme(theme)
            for line in output.splitlines():
                if line.startswith("theme["):
                    self.assertRegex(
                        line,
                        r'^theme\[\w+\]="#[0-9a-f]{6}"$',
                        f"{tk}: {line}",
                    )

    def test_btop_theme_has_required_keys(self):
        required = {
            "main_bg", "main_fg", "title", "hi_fg", "selected_bg", "selected_fg",
            "inactive_fg", "graph_text", "meter_bg", "proc_misc",
            "cpu_box", "mem_box", "net_box", "proc_box", "div_line",
            "temp_start", "temp_mid", "temp_end",
            "cpu_start", "cpu_mid", "cpu_end",
            "free_start", "free_mid", "free_end",
            "cached_start", "cached_mid", "cached_end",
            "available_start", "available_mid", "available_end",
            "used_start", "used_mid", "used_end",
            "download_start", "download_mid", "download_end",
            "upload_start", "upload_mid", "upload_end",
            "process_start", "process_mid", "process_end",
        }
        for tk, theme in self.themes.items():
            output = btop_theme(theme)
            found_keys = set()
            for line in output.splitlines():
                m = re.match(r"^theme\[(\w+)\]", line)
                if m:
                    found_keys.add(m.group(1))
            missing = required - found_keys
            self.assertFalse(missing, f"{tk} btop missing keys: {missing}")


class PlaceholderTests(unittest.TestCase):
    def setUp(self):
        self.themes = load_themes()

    def test_all_themes_produce_same_placeholder_keys(self):
        key_sets = [set(theme_placeholders(t).keys()) for t in self.themes.values()]
        for ks in key_sets[1:]:
            self.assertEqual(key_sets[0], ks)

    def test_no_placeholder_is_substring_of_another(self):
        placeholders = list(theme_placeholders(list(self.themes.values())[0]).keys())
        placeholders += ["__NAME__", "__EMAIL__"]
        for i, p1 in enumerate(placeholders):
            for j, p2 in enumerate(placeholders):
                if i != j and p1 != p2:
                    self.assertNotIn(
                        p1, p2, f'"{p1}" is substring of "{p2}"'
                    )

    def test_highlight_color_placeholder_exists(self):
        for tk, theme in self.themes.items():
            p = theme_placeholders(theme)
            self.assertIn("__THEME_HIGHLIGHT_COLOR__", p, tk)

    def test_delta_indentation(self):
        """First line no tab (template provides it), rest have tab prefix."""
        theme = list(self.themes.values())[0]
        p = theme_placeholders(theme)
        lines = p["__THEME_DELTA__"].split("\n")
        self.assertFalse(lines[0].startswith("\t"))
        for line in lines[1:]:
            if line.strip():
                self.assertTrue(line.startswith("\t"), f"missing tab: {repr(line)}")

    def test_fzf_no_trailing_whitespace(self):
        for tk, theme in self.themes.items():
            p = theme_placeholders(theme)
            for line in p["__THEME_FZF_COLORS__"].split("\n"):
                self.assertEqual(line.rstrip(), line, f"{tk} trailing ws: {repr(line)}")


if __name__ == "__main__":
    unittest.main()
