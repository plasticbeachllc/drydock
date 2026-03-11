#!/usr/bin/env python3
"""Generate theme-gallery.html from themes.toml."""

import html as html_mod
import tomllib
from pathlib import Path

DIR = Path(__file__).parent
TOML_PATH = DIR / "themes.toml"
OUT_PATH = DIR / "gallery.html"

CSS = """\
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #111; color: #ccc; font-family: "Maple Mono NF", "SF Mono", monospace; padding: 40px; }
  h1 { text-align: center; margin-bottom: 40px; font-size: 14px; letter-spacing: 4px; text-transform: uppercase; color: #666; }
  .themes { display: flex; gap: 32px; justify-content: center; flex-wrap: wrap; }
  .theme { width: 380px; border-radius: 12px; overflow: hidden; }
  .theme-header { padding: 20px 24px 12px; font-size: 13px; letter-spacing: 2px; text-transform: uppercase; }
  .theme-body { padding: 0 24px 24px; }
  .section-label { font-size: 10px; letter-spacing: 1px; text-transform: uppercase; margin: 16px 0 8px; opacity: 0.5; }
  .swatches { display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 18px; }
  .swatch { width: 36px; height: 36px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 8px; letter-spacing: 0.5px; position: relative; }
  .swatch span { position: absolute; bottom: -14px; font-size: 8px; white-space: nowrap; opacity: 0.6; }
  .preview { margin-top: 20px; border-radius: 8px; padding: 16px; font-size: 12px; line-height: 1.8; }
  .preview .keyword { font-weight: bold; }
  .preview .cursor { display: inline-block; width: 8px; height: 16px; vertical-align: text-bottom; animation: blink 1s step-end infinite; }
  @keyframes blink { 50% { opacity: 0; } }"""


def swatch(bg: str, label: str, label_color: str, border: str | None = None) -> str:
    style = f"background:{bg};"
    if border:
        style += f" border: 1px solid {border};"
    return f'<div class="swatch" style="{style}"><span style="color:{label_color}">{label}</span></div>'


def preview(base: dict, acc: dict, pv: dict) -> str:
    kw = acc["purple"]
    fg = base["fg"]
    sec = acc["secondary"]
    s = acc["success"]
    w = acc["warn"]
    e = acc["error"]
    p = acc["primary"]
    y = acc["yellow"]
    dim = base["dim_fg"]

    def sp(color, text, cls=""):
        text = html_mod.escape(text)
        attr = f'style="color:{color};"'
        if cls:
            attr = f'class="{cls}" ' + attr
        return f"<span {attr}>{text}</span>"

    lines = [
        sp(dim, f'-- {pv["comment"]}'),
        (
            sp(kw, "local", "keyword") + " " +
            sp(sec, pv["var"]) + " " +
            sp(fg, "=") + " " +
            sp(kw, "require", "keyword") +
            sp(fg, "(") +
            sp(s, f'"{pv["module"]}"') +
            sp(fg, ")")
        ),
        (
            sp(kw, "local", "keyword") + " " +
            sp(fg, f'{pv["var2"]} =') + " " +
            sp(sec, pv["var"]) +
            sp(fg, ".") +
            sp(w, pv["method"]) +
            sp(fg, "(") +
            sp(y, "42") +
            sp(fg, ")")
        ),
        (
            sp(kw, "if", "keyword") + " " +
            sp(fg, f'{pv["var2"]}.') +
            sp(e, pv["prop"]) + " " +
            sp(kw, "then", "keyword")
        ),
        (
            sp(fg, "  ") +
            sp(p, "print") +
            sp(fg, "(") +
            sp(s, f'"{pv["string"]}"') +
            sp(fg, ")")
        ),
        sp(kw, "end", "keyword") + f'<span class="cursor" style="background:{p};"></span>',
    ]
    return "<br>\n        ".join(lines)


def render_theme(theme: dict) -> str:
    base = theme["base"]
    acc = theme["accents"]
    pv = theme["preview"]
    dim_fg = base["dim_fg"]

    base_swatches = [
        swatch(base["bg"], "bg", dim_fg, border=base["sel"]),
        swatch(base["dim"], "dim", dim_fg),
        swatch(base["accent"], "accent", dim_fg),
        swatch(base["sel"], "sel", dim_fg),
        swatch(base["fg"], "fg", dim_fg),
        swatch(base["dim_fg"], "dim", dim_fg),
        swatch(base["bright"], "bright", dim_fg),
    ]

    accent_swatches = [
        swatch(acc[k], k, dim_fg)
        for k in ("primary", "secondary", "warn", "error", "success", "purple", "pink", "yellow")
    ]

    return f"""\
  <!-- {theme["name"].upper()} -->
  <div class="theme" style="background: {base["bg"]};">
    <div class="theme-header" style="color: {acc["primary"]};">
      ░▒▓ {theme["name"]} ▓▒░
    </div>
    <div class="theme-body">
      <div class="section-label" style="color: {dim_fg};">base</div>
      <div class="swatches">
        {"".join(base_swatches)}
      </div>
      <div class="section-label" style="color: {dim_fg};">accents</div>
      <div class="swatches">
        {"".join(accent_swatches)}
      </div>
      <div class="preview" style="background: {base["dim"]};">
        {preview(base, acc, pv)}
      </div>
    </div>
  </div>"""


def main():
    raw = TOML_PATH.read_text()
    themes = tomllib.loads(raw)

    theme_blocks = "\n\n".join(render_theme(t) for t in themes.values())

    html = f"""\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Dotfiles Theme Gallery</title>
<style>
{CSS}
</style>
</head>
<body>
<h1>dotfiles theme gallery</h1>
<div class="themes">

{theme_blocks}

</div>
</body>
</html>
"""
    OUT_PATH.write_text(html)
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
