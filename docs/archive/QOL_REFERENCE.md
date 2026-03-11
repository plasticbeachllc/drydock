# Terminal QOL Dotfiles Reference

> Comprehensive provisioning guide for macOS and Linux.
> Verified on macOS Tahoe 26.3 (arm64) on 2026-03-10.
> All packages installed and tested unless noted otherwise.

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Package Inventory](#2-package-inventory)
3. [Installation: Package Manager](#3-installation-package-manager)
4. [Installation: Homebrew Casks (GUI apps)](#4-installation-homebrew-casks)
5. [Installation: Homebrew Formulae (CLI tools)](#5-installation-homebrew-formulae)
6. [Installation: Cargo Fallbacks (Linux without Homebrew)](#6-installation-cargo-fallbacks)
7. [Installation: Git-cloned tools](#7-installation-git-cloned-tools)
8. [Post-install Steps](#8-post-install-steps)
9. [Config: Sheldon (plugin manager)](#9-config-sheldon)
10. [Config: Starship (prompt)](#10-config-starship)
11. [Config: Ghostty (terminal)](#11-config-ghostty)
12. [Config: .zshrc](#12-config-zshrc)
13. [Config: Git + Delta](#13-config-git--delta)
14. [Config: jj (Jujutsu)](#14-config-jj)
15. [Config: bat](#15-config-bat)
16. [Verification](#16-verification)
17. [Dotfiles Structure Suggestion](#17-dotfiles-structure-suggestion)
18. [Cross-platform Notes](#18-cross-platform-notes)

---

## 1. System Requirements

| Requirement | macOS | Linux |
|---|---|---|
| OS | macOS 15+ (Sequoia/Tahoe) | Ubuntu 22.04+, Fedora 39+, Arch |
| Architecture | arm64 or x86_64 | x86_64 or arm64 |
| Shell | zsh (default since Catalina) | zsh (install if needed) |
| Package manager | Homebrew | Homebrew, apt, dnf, or pacman |
| Rust toolchain | Optional (only if cargo fallbacks needed) | Recommended |

### Bootstrap: Homebrew

```bash
# macOS + Linux
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Post-install PATH (macOS arm64)
eval "$(/opt/homebrew/bin/brew shellenv)"

# Post-install PATH (Linux)
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
```

### Bootstrap: Rust (only if needed for cargo installs)

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"
```

### Bootstrap: zsh on Linux (if not default)

```bash
# Debian/Ubuntu
sudo apt install -y zsh
chsh -s $(which zsh)

# Fedora
sudo dnf install -y zsh
chsh -s $(which zsh)
```

---

## 2. Package Inventory

### GUI Applications (casks)

| Package | Brew cask name | Verified version | Purpose |
|---|---|---|---|
| Ghostty | `ghostty` | 1.3.0 | Terminal emulator (GPU-rendered, native macOS) |
| Maple Mono NF | `font-maple-mono-nf` | — | Monospace font with Nerd Font icons built in |

### CLI Tools (formulae)

| Binary name | Brew formula | Verified version | Purpose | Replaces |
|---|---|---|---|---|
| `starship` | `starship` | 1.24.2 | Cross-shell prompt | default zsh prompt |
| `sheldon` | `sheldon` | 0.8.5 | Zsh plugin manager (Rust, TOML config) | oh-my-zsh |
| `eza` | `eza` | 0.23.4 | File listing with icons/git | `ls` |
| `bat` | `bat` | 0.26.1 | Syntax-highlighted cat | `cat` |
| `rg` | `ripgrep` | 15.1.0 | Fast grep | `grep` |
| `fd` | `fd` | 10.4.2 | Fast find | `find` |
| `zoxide` | `zoxide` | 0.9.9 | Smart cd (frecency) | `cd` |
| `fzf` | `fzf` | 0.70.0 | Fuzzy finder (files, history, etc.) | — |
| `delta` | `git-delta` | 0.18.2 | Beautiful git diffs | `diff` / git's pager |
| `dust` | `dust` | 1.2.4 | Visual disk usage | `du` |
| `btop` | `btop` | 1.4.6 | Resource monitor | `top` / `htop` |
| `xh` | `xh` | 0.25.3 | HTTP client (Rust) | `curl` |
| `sd` | `sd` | 1.1.0 | Simpler sed | `sed` |
| `tldr` | `tealdeer` | 1.8.1 | Community cheat sheets | `man` |
| `direnv` | `direnv` | 2.37.1 | Per-directory env vars | — |
| `lazygit` | `lazygit` | 0.60.0 | TUI git client | — |
| `jj` | `jj` | 0.39.0 | Jujutsu VCS (Git-compatible) | `git` (local workflow) |
| `lazyjj` | `lazyjj` | 0.6.1 | TUI for jj | — |
| `jj-fzf` | `jj-fzf` | — | fzf-based jj interface | — |

### Zsh Plugins (managed by Sheldon)

| Plugin | GitHub repo | Purpose |
|---|---|---|
| zsh-completions | `zsh-users/zsh-completions` | Extended completion definitions |
| zsh-autosuggestions | `zsh-users/zsh-autosuggestions` | Fish-like inline history suggestions |
| zsh-syntax-highlighting | `zsh-users/zsh-syntax-highlighting` | Live command colorization |
| zsh-history-substring-search | `zsh-users/zsh-history-substring-search` | Up/down arrow history filtering |
| fzf-tab | `Aloxaf/fzf-tab` | Replace default tab completion with fzf |

---

## 3. Installation: Package Manager

Ensure Homebrew is available (see Section 1), then proceed.

---

## 4. Installation: Homebrew Casks

```bash
brew install --cask ghostty
brew install --cask font-maple-mono-nf
```

### Linux alternatives

**Ghostty:**
- Fedora: `sudo dnf copr enable -y pgdev/ghostty && sudo dnf install -y ghostty`
- Arch: `sudo pacman -S ghostty`
- Debian/Ubuntu: Download .deb from https://ghostty.org/download or build from source

**Maple Mono NF (without Homebrew):**
```bash
mkdir -p ~/.local/share/fonts
RELEASE_URL=$(curl -s https://api.github.com/repos/subframe7536/maple-font/releases/latest \
  | grep "browser_download_url.*MapleMono-NF.*zip" \
  | head -1 | cut -d '"' -f 4)
curl -L "$RELEASE_URL" -o /tmp/maple-mono-nf.zip
unzip -o /tmp/maple-mono-nf.zip -d ~/.local/share/fonts
fc-cache -fv
rm /tmp/maple-mono-nf.zip
```

## 5. Installation: Homebrew Formulae

All CLI tools in a single command:

```bash
brew install \
  starship \
  sheldon \
  eza \
  bat \
  ripgrep \
  fd \
  zoxide \
  fzf \
  git-delta \
  dust \
  btop \
  xh \
  sd \
  tealdeer \
  direnv \
  lazygit \
  jj \
  lazyjj
```

**Note:** `jj-fzf` may not be in Homebrew — see Section 7 for git-clone fallback.

---

## 6. Installation: Cargo Fallbacks

For Linux distros without Homebrew, or when a formula isn't available:

| Binary | Cargo crate | Install command |
|---|---|---|
| `eza` | `eza` | `cargo install eza --locked` |
| `bat` | `bat` | `cargo install bat --locked` |
| `rg` | `ripgrep` | `cargo install ripgrep --locked` |
| `fd` | `fd-find` | `cargo install fd-find --locked` |
| `zoxide` | `zoxide` | `cargo install zoxide --locked` |
| `delta` | `git-delta` | `cargo install git-delta --locked` |
| `dust` | `du-dust` | `cargo install du-dust --locked` |
| `xh` | `xh` | `cargo install xh --locked` |
| `sd` | `sd` | `cargo install sd --locked` |
| `tldr` | `tealdeer` | `cargo install tealdeer --locked` |
| `lazygit` | — | Not on crates.io; use `go install` or distro pkg |
| `jj` | `jj-cli` | `cargo install jj-cli --locked` |
| `lazyjj` | `lazyjj` | `cargo install lazyjj --locked` |
| `sheldon` | `sheldon` | `cargo install sheldon --locked` |

**Starship** has a universal installer (no cargo needed):
```bash
curl -sS https://starship.rs/install.sh | sh -s -- -y
```

**fzf** and **btop** are best installed via system package manager:
```bash
# Debian/Ubuntu
sudo apt install -y fzf btop direnv

# Fedora
sudo dnf install -y fzf btop direnv
```

### Debian/Ubuntu binary name quirks

On Debian-based systems, some tools install under different binary names:
- `bat` installs as `batcat` → symlink: `sudo ln -sf /usr/bin/batcat /usr/local/bin/bat`
- `fd` installs as `fdfind` → symlink: `sudo ln -sf /usr/bin/fdfind /usr/local/bin/fd`

---

## 7. Installation: Git-cloned Tools

### jj-fzf

```bash
git clone https://github.com/tim-janik/jj-fzf.git ~/.jj-fzf
# Add to PATH in .zshrc: export PATH="$HOME/.jj-fzf:$PATH"
```

---

## 8. Post-install Steps

### fzf shell integration

```bash
# macOS (Homebrew)
$(brew --prefix)/opt/fzf/install --key-bindings --completion --no-update-rc --no-bash --no-fish

# Linux (system package)
# fzf keybindings are typically at /usr/share/fzf/key-bindings.zsh
# Source in .zshrc instead
```

This generates `~/.fzf.zsh` which is sourced in the .zshrc below.

### tealdeer cache

```bash
tldr --update
```

### Sheldon plugin lock

```bash
sheldon lock
```

---

## 9. Config: Sheldon

**File:** `~/.config/sheldon/plugins.toml`

```toml
shell = "zsh"

# --- Completions (load early) ---
[plugins.zsh-completions]
github = "zsh-users/zsh-completions"

# --- Core plugins ---
[plugins.zsh-autosuggestions]
github = "zsh-users/zsh-autosuggestions"

[plugins.zsh-syntax-highlighting]
github = "zsh-users/zsh-syntax-highlighting"

[plugins.zsh-history-substring-search]
github = "zsh-users/zsh-history-substring-search"

# --- fzf-tab (replaces default tab completion with fzf) ---
[plugins.fzf-tab]
github = "Aloxaf/fzf-tab"
```

After writing this file, run `sheldon lock` to download plugins.

---

## 10. Config: Starship

**File:** `~/.config/starship.toml`

```toml
# Minimal, fast prompt with git + directory awareness
format = """
$directory\
$git_branch\
$git_status\
$character"""

[directory]
truncation_length = 3
truncate_to_repo = true

[git_branch]
format = "[$branch]($style) "
style = "bold purple"

[git_status]
format = '([$all_status$ahead_behind]($style) )'
style = "bold red"

[character]
success_symbol = "[❯](bold green)"
error_symbol = "[❯](bold red)"
```

---

## 11. Config: Ghostty

**File:** `~/.config/ghostty/config`

Ghostty uses a flat key-value format (not TOML/JSON).

### Shared (all platforms)

```
# Font
font-family = "Maple Mono NF"
font-size = 14

# Theme
theme = catppuccin-mocha

# Window
window-padding-x = 12
window-padding-y = 8
window-decoration = true

# Behavior
copy-on-select = clipboard
mouse-hide-while-typing = true
confirm-close-surface = false
shell-integration = zsh

# Scrollback
scrollback-limit = 10000
```

### macOS-specific (append to above)

```
# macOS-specific
macos-titlebar-style = hidden

# Keybindings for splits
keybind = cmd+d=new_split:right
keybind = cmd+shift+d=new_split:down
keybind = cmd+shift+enter=toggle_split_zoom
keybind = cmd+alt+left=goto_split:left
keybind = cmd+alt+right=goto_split:right
keybind = cmd+alt+up=goto_split:top
keybind = cmd+alt+down=goto_split:bottom
```

### Linux-specific (append instead)

```
# Keybindings for splits
keybind = ctrl+shift+d=new_split:right
keybind = ctrl+shift+e=new_split:down
keybind = ctrl+shift+enter=toggle_split_zoom
keybind = ctrl+alt+left=goto_split:left
keybind = ctrl+alt+right=goto_split:right
keybind = ctrl+alt+up=goto_split:top
keybind = ctrl+alt+down=goto_split:bottom
```

### Ghostty keybindings cheat sheet

| Action | macOS | Linux |
|---|---|---|
| Split right | `Cmd+D` | `Ctrl+Shift+D` |
| Split down | `Cmd+Shift+D` | `Ctrl+Shift+E` |
| Navigate splits | `Cmd+Alt+Arrow` | `Ctrl+Alt+Arrow` |
| Zoom split | `Cmd+Shift+Enter` | `Ctrl+Shift+Enter` |
| New tab | `Cmd+T` | `Ctrl+Shift+T` |
| Close tab/split | `Cmd+W` | `Ctrl+Shift+W` |

---

## 12. Config: .zshrc

**File:** `~/.zshrc`

This is the main shell configuration. It should be **assembled** from your dotfiles, not pasted monolithically. Below is the complete contents organized by concern, so you can split into separate sourced files if your dotfiles framework supports it.

### Pre-existing config (preserve from current system)

```bash
# --- Bun ---
[ -f "$HOME/.local/bin/env" ] && . "$HOME/.local/bin/env"
[ -s "$HOME/.bun/_bun" ] && source "$HOME/.bun/_bun"
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# --- Antigravity ---
export PATH="$HOME/.antigravity/antigravity/bin:$PATH"

# --- Homebrew ---
export HOMEBREW_NO_ENV_HINTS=1
```

### PATH additions

```bash
# Cargo
[ -d "$HOME/.cargo/bin" ] && export PATH="$HOME/.cargo/bin:$PATH"

# jj-fzf
[ -d "$HOME/.jj-fzf" ] && export PATH="$HOME/.jj-fzf:$PATH"
```

### Tool initialization (order matters)

```bash
# Sheldon (plugin manager) — must be before prompt
eval "$(sheldon source)"

# Starship prompt
eval "$(starship init zsh)"

# Zoxide (smart cd)
eval "$(zoxide init zsh)"

# direnv
eval "$(direnv hook zsh)"

# fzf
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
```

### fzf configuration

```bash
export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'
export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
export FZF_ALT_C_COMMAND='fd --type d --hidden --follow --exclude .git'
export FZF_DEFAULT_OPTS='
  --height 40%
  --layout=reverse
  --border
  --color=bg+:#313244,bg:#1e1e2e,spinner:#f5e0dc,hl:#f38ba8
  --color=fg:#cdd6f4,header:#f38ba8,info:#cba6f7,pointer:#f5e0dc
  --color=marker:#b4befe,fg+:#cdd6f4,prompt:#cba6f7,hl+:#f38ba8
'
```

### History

```bash
HISTSIZE=50000
SAVEHIST=50000
HISTFILE=~/.zsh_history
setopt EXTENDED_HISTORY
setopt HIST_EXPIRE_DUPS_FIRST
setopt HIST_IGNORE_DUPS
setopt HIST_IGNORE_SPACE
setopt HIST_VERIFY
setopt SHARE_HISTORY
setopt INC_APPEND_HISTORY
```

### Key bindings

```bash
# History substring search (requires zsh-history-substring-search plugin)
bindkey '^[[A' history-substring-search-up
bindkey '^[[B' history-substring-search-down
```

### Aliases: CLI tool replacements

```bash
alias ls='eza --icons --group-directories-first'
alias ll='eza --icons --group-directories-first -la'
alias lt='eza --icons --tree --level=2'
alias cat='bat --paging=never'
alias grep='rg'
alias find='fd'
alias du='dust'
alias top='btop'
alias sed='sd'
alias diff='delta'
alias lg='lazygit'
alias lj='lazyjj'
```

**Note on aliasing coreutils:** The aliases for `grep`, `find`, `sed`, `du`, and `top` shadow the originals. Access originals via `\grep`, `\find`, `\sed`, `\du`, `\top` or full path (`/usr/bin/grep`, etc.). Some scripts may depend on the originals, so be aware.

### Aliases: jj (Jujutsu)

```bash
alias js='jj status'
alias jl='jj log'
alias jd='jj diff'
alias jn='jj new'
alias jc='jj commit'
alias jds='jj describe'
```

### Environment: delta and bat

```bash
export DELTA_PAGER="less -R"
export BAT_THEME="Catppuccin Mocha"
```

---

## 13. Config: Git + Delta

These are `git config --global` settings. They can also be expressed as a `~/.gitconfig` file.

### As git commands

```bash
git config --global core.pager delta
git config --global interactive.diffFilter "delta --color-only"
git config --global delta.navigate true
git config --global delta.dark true
git config --global delta.syntax-theme "Catppuccin Mocha"
git config --global delta.side-by-side true
git config --global delta.line-numbers true
git config --global merge.conflictstyle diff3
git config --global diff.colorMoved default
```

### As ~/.gitconfig (equivalent)

```ini
[core]
    pager = delta

[interactive]
    diffFilter = delta --color-only

[delta]
    navigate = true
    dark = true
    syntax-theme = Catppuccin Mocha
    side-by-side = true
    line-numbers = true

[merge]
    conflictstyle = diff3

[diff]
    colorMoved = default
```

**Note:** If your dotfiles manage `~/.gitconfig` declaratively, use the file approach. If you use `[include]` directives in gitconfig, you can put the delta config in a separate file like `~/.config/git/delta.gitconfig` and include it.

---

## 14. Config: jj

**File:** `~/.config/jj/config.toml`

```toml
[user]
name = "Taylor"
email = "YOUR_EMAIL_HERE"

[ui]
default-command = "log"
diff.format = "git"
pager = "delta"

[git]
auto-local-bookmark = false
```

### Initializing jj on existing git repos

jj works alongside git via colocated repos. To try jj on an existing project:

```bash
cd ~/worktable/keel
jj git init --colocate
```

This creates a `.jj` directory alongside `.git`. Both tools work on the same repo. To revert: `rm -rf .jj`.

### jj ecosystem tools

| Tool | Launch command | Purpose |
|---|---|---|
| jj CLI | `jj` | Core VCS operations |
| lazyjj | `lazyjj` or `lj` (alias) | TUI for jj (log, files, bookmarks) |
| jj-fzf | `jj-fzf` | fzf-based interactive jj interface |

---

## 15. Config: bat

bat uses Catppuccin Mocha theme via the `BAT_THEME` env var set in `.zshrc`. To verify available themes:

```bash
bat --list-themes | grep -i catppuccin
```

If the theme isn't available, install it:

```bash
mkdir -p "$(bat --config-dir)/themes"
curl -L https://github.com/catppuccin/bat/raw/main/themes/Catppuccin%20Mocha.tmTheme \
  -o "$(bat --config-dir)/themes/Catppuccin Mocha.tmTheme"
bat cache --build
```

---

## 16. Verification

Run this after all installation and configuration is complete:

```bash
echo "=== Terminal QOL Verification ==="
echo ""

echo "--- System ---"
echo "OS:    $(uname -s) $(uname -r)"
echo "Shell: $SHELL ($(zsh --version))"
echo "Brew:  $(brew --version | head -1)"
echo ""

echo "--- Tools ---"
for cmd in eza bat rg fd zoxide fzf delta dust btop xh sd tldr direnv lazygit jj lazyjj; do
  printf "  %-10s " "$cmd"
  if command -v "$cmd" &>/dev/null; then
    echo "✓"
  else
    echo "✗ NOT FOUND"
  fi
done
echo ""

echo "--- jj-fzf ---"
if [ -x "$HOME/.jj-fzf/jj-fzf" ] || command -v jj-fzf &>/dev/null; then
  echo "  jj-fzf    ✓"
else
  echo "  jj-fzf    ✗ NOT FOUND"
fi
echo ""

echo "--- Configs ---"
for f in \
  "$HOME/.config/sheldon/plugins.toml" \
  "$HOME/.config/starship.toml" \
  "$HOME/.config/ghostty/config" \
  "$HOME/.config/jj/config.toml" \
  "$HOME/.zshrc"; do
  printf "  %-45s " "$f"
  [ -f "$f" ] && echo "✓" || echo "✗ MISSING"
done
echo ""

echo "--- Sheldon Plugins ---"
sheldon lock --check 2>/dev/null && echo "  Plugins locked ✓" || echo "  Run: sheldon lock"
echo ""

echo "--- Font ---"
if fc-list 2>/dev/null | grep -qi "maple mono" || \
   system_profiler SPFontsDataType 2>/dev/null | grep -qi "maple mono"; then
  echo "  Maple Mono NF ✓"
else
  echo "  Maple Mono NF ✗ NOT FOUND"
fi
echo ""

echo "=== Verification complete ==="
```

---

## 17. Dotfiles Structure Suggestion

Here's one way to organize these files in a dotfiles repo:

```
dotfiles/
├── install.sh              # Main provisioning script
├── Brewfile                # Homebrew bundle (declarative)
├── config/
│   ├── ghostty/
│   │   └── config
│   ├── starship.toml
│   ├── sheldon/
│   │   └── plugins.toml
│   ├── jj/
│   │   └── config.toml
│   └── git/
│       └── delta.gitconfig
├── zsh/
│   ├── .zshrc              # Main entry point
│   ├── aliases.zsh         # CLI tool aliases
│   ├── history.zsh         # History config
│   ├── keybindings.zsh     # Key bindings
│   ├── tools.zsh           # Tool init (sheldon, starship, zoxide, etc.)
│   ├── fzf.zsh             # fzf configuration
│   ├── path.zsh            # PATH additions
│   └── local.zsh           # Machine-specific (gitignored)
├── git/
│   └── .gitconfig          # Or just the delta portion
└── scripts/
    └── verify.sh           # Verification script from Section 16
```

### Brewfile (declarative alternative to install commands)

```ruby
# Taps
tap "homebrew/cask-fonts"

# Casks (GUI apps)
cask "ghostty"
cask "font-maple-mono-nf"

# Formulae (CLI tools)
brew "starship"
brew "sheldon"
brew "eza"
brew "bat"
brew "ripgrep"
brew "fd"
brew "zoxide"
brew "fzf"
brew "git-delta"
brew "dust"
brew "btop"
brew "xh"
brew "sd"
brew "tealdeer"
brew "direnv"
brew "lazygit"
brew "jj"
brew "lazyjj"
```

Install everything from Brewfile:

```bash
brew bundle --file=Brewfile
```

### Symlink strategy

Most dotfiles managers (stow, chezmoi, dotbot, bare git repo) symlink config files from the repo into their expected locations:

| Repo path | Symlink target |
|---|---|
| `config/ghostty/config` | `~/.config/ghostty/config` |
| `config/starship.toml` | `~/.config/starship.toml` |
| `config/sheldon/plugins.toml` | `~/.config/sheldon/plugins.toml` |
| `config/jj/config.toml` | `~/.config/jj/config.toml` |
| `zsh/.zshrc` | `~/.zshrc` |
| `git/.gitconfig` | `~/.gitconfig` (or use `[include]`) |

---

## 18. Cross-platform Notes

### macOS vs Linux differences

| Concern | macOS | Linux |
|---|---|---|
| Ghostty install | `brew install --cask ghostty` | Distro-specific (see Section 4) |
| Font install | `brew install --cask font-maple-mono-nf` | Manual download to `~/.local/share/fonts` + `fc-cache -fv` |
| Font verification | `system_profiler SPFontsDataType` | `fc-list` |
| fzf keybindings | `$(brew --prefix)/opt/fzf/install` | Source `/usr/share/fzf/key-bindings.zsh` or use brew path |
| Ghostty keybindings | `Cmd+...` | `Ctrl+Shift+...` |
| Ghostty titlebar | `macos-titlebar-style = hidden` | Not applicable |
| Homebrew path | `/opt/homebrew/` (arm64) or `/usr/local/` (x86) | `/home/linuxbrew/.linuxbrew/` |
| bat binary name | `bat` | `bat` (brew) or `batcat` (apt) |
| fd binary name | `fd` | `fd` (brew) or `fdfind` (apt) |

### Secrets management

The current setup has `OPENAI_API_KEY` in `.zshrc`. Better approach with direnv:

```bash
# In project directory, e.g. ~/worktable/keel/
echo 'export OPENAI_API_KEY="sk-proj-..."' > .envrc
direnv allow
```

Add `.envrc` to your global gitignore:

```bash
echo ".envrc" >> ~/.config/git/ignore
```

This keeps secrets out of your dotfiles repo and scoped to the projects that need them.

---

## Quick Start (Fresh Machine)

For the impatient — the minimum commands to go from zero to working on a fresh Mac:

```bash
# 1. Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
eval "$(/opt/homebrew/bin/brew shellenv)"

# 2. Clone dotfiles
git clone https://github.com/YOU/dotfiles.git ~/dotfiles

# 3. Install packages
brew bundle --file=~/dotfiles/Brewfile

# 4. Symlink configs (example with stow)
cd ~/dotfiles && stow config zsh git

# 5. Post-install
$(brew --prefix)/opt/fzf/install --key-bindings --completion --no-update-rc --no-bash --no-fish
sheldon lock
tldr --update
git clone https://github.com/tim-janik/jj-fzf.git ~/.jj-fzf

# 6. Set git + delta config
git config --global core.pager delta
git config --global interactive.diffFilter "delta --color-only"
git config --global delta.navigate true
git config --global delta.dark true
git config --global delta.syntax-theme "Catppuccin Mocha"
git config --global delta.side-by-side true
git config --global delta.line-numbers true
git config --global merge.conflictstyle diff3
git config --global diff.colorMoved default

# 7. Open Ghostty and enjoy
open /Applications/Ghostty.app
```
