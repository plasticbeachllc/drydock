# Theme Infrastructure — Code Review & UAT Plan

## Part 1: Code Review

### 1.1 themes/themes.toml — Source of Truth

- [ ] All three themes define identical key sets (no missing/extra keys)
- [ ] Hex colors are valid 7-char format (`#rrggbb`)
- [ ] Terminal ANSI arrays have exactly 8 entries each (ansi, ansi_bright)
- [ ] ANSI palette order is correct: black, red, green, yellow, blue, magenta, cyan, white
- [ ] Terminal colors have sufficient contrast against their theme's bg for readability
- [ ] Accent colors are visually distinct within each theme (no two too similar)
- [ ] Preview section has all required keys (comment, module, var, var2, method, prop, string)

### 1.2 themes/generate.py — Generator Module

**Color utilities**
- [ ] `hex_to_rgb` handles both `#rrggbb` and `rrggbb` input
- [ ] `blend(c1, c2, 0.0)` returns c1, `blend(c1, c2, 1.0)` returns c2
- [ ] `ansi_rgb` produces valid `R;G;B` strings (0-255 range)

**File generators**
- [ ] `ghostty_theme()` produces valid ghostty theme format (no quotes around hex values)
- [ ] `nvim_theme_colors()` produces valid Lua that returns a table
- [ ] `nvim_dashboard_colors()` produces valid Lua
- [ ] `lazygit_config()` produces valid YAML
- [ ] `btop_theme()` produces valid btop theme format (`theme[key]="value"`)
- [ ] All generators use only keys that exist in themes.toml (no KeyError possible)

**Placeholder system**
- [ ] `theme_placeholders()` returns all `__THEME_*__` keys used across templates
- [ ] No placeholder key is a substring of another (avoid partial replacement)
- [ ] `__THEME_NAME__` doesn't collide with `__NAME__` during substitution (length-sorted replacement handles this)
- [ ] Delta block uses correct gitconfig indentation (tabs)
- [ ] FZF color string has no trailing/leading whitespace issues
- [ ] MOTD block produces valid bash
- [ ] Statusline palette uses correct `\033` escape format

### 1.3 setup.py — Provisioning Script

**Theme picker**
- [ ] Displays all themes with name + tagline
- [ ] Remembers previous selection and shows it as default
- [ ] Invalid input (non-numeric, out of range) is handled gracefully
- [ ] Theme key is persisted to identity.json under `__THEME__`

**File generation**
- [ ] Ghostty theme written to rendered dir with correct theme name
- [ ] Dynamic ghostty theme symlink is added to SYMLINK_MAP
- [ ] nvim theme_colors.lua and dashboard_colors.lua written to GENERATED_DIR
- [ ] Lazygit config.yml written to `~/.config/lazygit/`
- [ ] btop theme written to `~/.config/btop/themes/` with correct filename
- [ ] btop.conf color_theme is set (created if missing, updated if exists)

**Template rendering**
- [ ] `render_template` sorts by key length descending (avoids `__NAME__` clobbering `__THEME_NAME__`)
- [ ] `needs_templating` checks all placeholder keys including theme placeholders
- [ ] Files with both identity and theme placeholders render correctly (gitconfig, jj/config.toml)

**Symlinks**
- [ ] Existing symlinks pointing elsewhere are relinked (not duplicated)
- [ ] Existing real files are backed up before symlinking
- [ ] Missing source files are skipped with warning
- [ ] Generated file tuples `(source, target)` are handled separately from repo paths

### 1.4 Config Templates

**ghostty/config**
- [ ] `__THEME_NAME__` on the `theme =` line, no quotes

**shell/zshrc**
- [ ] `__THEME_FZF_COLORS__` inside the FZF_DEFAULT_OPTS single-quoted string
- [ ] `__THEME_MOTD__` replaces the entire MOTD block (if/fi)
- [ ] BAT_THEME set to `base16` (not theme-specific)
- [ ] No leftover hardcoded Plastic Beach colors

**git/gitconfig**
- [ ] `__THEME_DELTA__` replaces the body of the `[delta]` section
- [ ] Tab indentation preserved after substitution

**starship/starship.toml**
- [ ] `__THEME_DIR_COLOR__`, `__THEME_SUCCESS_COLOR__`, `__THEME_ERROR_COLOR__` in correct locations
- [ ] Hex colors are bare (no extra quoting) inside the starship format strings

**claude/statusline.sh**
- [ ] `__THEME_PALETTE__` replaces color variable definitions
- [ ] `RST` line is outside the placeholder (not duplicated)

**jj/config.toml**
- [ ] `__THEME_HIGHLIGHT_COLOR__` inside `[lazyjj]` section, quoted

### 1.5 Neovim Integration

**colorscheme.lua**
- [ ] `pcall(dofile, ...)` gracefully handles missing file (falls back to default catppuccin)
- [ ] Color override table maps all required catppuccin mocha keys
- [ ] Generated lua file is syntactically valid for all three themes

**dashboard.lua**
- [ ] Fallback values work when generated file is missing
- [ ] Header text matches theme name
- [ ] `SnacksDashboardHeader` highlight is set from generated color

### 1.6 Gallery (themes/build_gallery.py)

- [ ] Reads the same themes.toml as generate.py (consistent source)
- [ ] HTML-escapes preview text content
- [ ] Generated gallery.html renders all three themes
- [ ] Swatch layout doesn't overflow at 380px card width


## Part 2: Manual UAT

### Prerequisites

```bash
# Fresh state: no rendered configs, no saved identity
rm -rf ~/.config/dotfiles/rendered
# Back up identity if you want to preserve it
cp ~/.config/dotfiles/identity.json ~/.config/dotfiles/identity.json.bak
```

### 2.1 Setup Flow — Theme Selection

1. Run `python3 setup.py`
2. Enter identity (name, email)
3. Verify all three themes are listed with `[1] [2] [3]`
4. Select **Plastic Beach Basic** (option 1)
5. Verify output shows:
   - `generated ghostty theme: Plastic Beach Basic`
   - `generated nvim theme colors`
   - `generated nvim dashboard colors`
   - `generated lazygit config`
   - `generated btop theme: Plastic Beach Basic`
6. Verify symlinks are created/updated
7. Complete secrets step (skip is fine)

### 2.2 Setup Flow — Theme Switching

1. Run `python3 setup.py` again
2. Verify previous theme is marked with `*` and shown as default
3. Select **Deep Water** (option 2)
4. Verify all generated files are updated
5. Run a third time, select **Desert Island**
6. Verify the `*` marker now shows Desert Island

### 2.3 Ghostty Verification

For each theme:
1. Open Ghostty (or reload config with Cmd+,)
2. Verify background color matches theme's `base.bg`
3. Verify text color matches theme's `base.fg`
4. Verify cursor color matches theme's `terminal.cursor`
5. Run `echo -e "\033[31mred \033[32mgreen \033[33myellow \033[34mblue \033[35mmagenta \033[36mcyan\033[0m"` — verify ANSI colors match theme

### 2.4 Shell Verification

For each theme:
1. Open a new terminal tab (sources fresh zshrc)
2. Verify MOTD displays with correct theme name, icon, and colors
3. Run `fzf` in a directory — verify border, selection, and highlight colors
4. Run `bat --theme` — verify it reports `base16`
5. Run `cat somefile` (aliased to bat) — verify syntax colors use terminal palette

### 2.5 Starship Prompt

For each theme:
1. Open new shell
2. Verify directory path is colored with theme's secondary color
3. Run a failing command (e.g., `false`) — verify `❯` turns to error color
4. Successful command — verify `❯` shows primary/success color

### 2.6 Git Delta

For each theme:
1. Make a small change to a tracked file
2. Run `git diff` (uses delta)
3. Verify minus lines have a dark red-tinted background
4. Verify plus lines have a dark green-tinted background
5. Verify file headers use theme's pink color
6. Verify line numbers use theme's purple (minus) and primary (plus)

### 2.7 Neovim

For each theme:
1. Open `nvim`
2. Verify dashboard shows correct theme header text (e.g., `░▒▓  deep water  ▓▒░`)
3. Verify dashboard header color matches theme's primary
4. Open a source file — verify syntax colors align with theme palette
5. Verify background matches theme's base.bg
6. Verify `:hi Normal` shows expected fg/bg

### 2.8 Lazygit

For each theme:
1. Run `lg` (lazygit alias)
2. Verify active border color matches theme's primary
3. Verify inactive border uses theme's dim_fg
4. Verify selected line background matches theme's accent

### 2.9 Lazyjj

For each theme:
1. Run `lj` (lazyjj alias) in a jj repo
2. Verify highlight color matches theme's primary

### 2.10 btop

For each theme:
1. Run `btop`
2. Verify it loads the correct theme (check top-right theme indicator if visible)
3. Verify box borders use distinct theme colors (cpu=primary, mem=success, net=secondary, proc=purple)
4. Verify graph gradients use theme accent colors
5. Verify background matches theme's bg

### 2.11 Claude Code Statusline

For each theme:
1. Open Claude Code in a jj repo
2. Verify statusline shows model name, project, bookmark, context bar
3. Verify colors correspond to theme palette (primary for teal, secondary for blue, etc.)

### 2.12 Gallery

1. Run `python3 themes/build_gallery.py`
2. Open `themes/gallery.html` in a browser
3. Verify all three themes render with correct swatches
4. Verify code preview uses the same accent colors defined in themes.toml
5. Verify swatch labels are readable and don't overflow

### 2.13 Cross-Theme Consistency

1. Switch between all three themes via `python3 setup.py`
2. After each switch, spot-check at least: Ghostty bg, fzf colors, starship prompt, nvim syntax
3. Verify no stale colors leak from the previous theme (especially check delta and fzf)
4. Verify identity placeholders (__NAME__, __EMAIL__) are still correctly rendered in gitconfig and jj/config.toml after theme switch

### 2.14 Edge Cases

- [ ] Run setup.py with no prior identity.json — verify clean first-run
- [ ] Delete `~/.config/dotfiles/theme_colors.lua` and open nvim — verify graceful fallback
- [ ] Delete `~/.config/dotfiles/dashboard_colors.lua` and open nvim — verify fallback header
- [ ] Run setup.py and press Enter at theme prompt without typing — verify default selection works
- [ ] Add a 4th theme to themes.toml — verify setup.py picks it up, gallery renders it, all generators work
