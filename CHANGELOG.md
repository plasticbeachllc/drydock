# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1] - 2026-03-14

Initial release — a complete macOS/Linux development environment provisioner
driven by symlinks, templates, and a unified theme system.

### Added

#### Bootstrap (`bootstrap.sh`)

- Platform detection (macOS vs Linux) with OS-specific install paths
- Homebrew auto-install and session activation
- macOS GUI apps: Ghostty, Maple Mono NF font, Google Chrome, 1Password, Telegram
- CLI tooling: starship, sheldon, neovim, gh, git-delta, lazygit, jj, jj-fzf,
  lazyjj, ripgrep, fd, fzf, zoxide, eza, bat, btop, dust, xh, sd, tealdeer,
  direnv, jq, bun, 1password-cli
- Rust toolchain bootstrap via `rustup-init` (idempotent)
- AI tools: Claude Code (native installer), Codex (Homebrew)
- Post-install hooks: fzf shell integration, tldr cache, sheldon lock
- Exponential-backoff retry logic for network operations
- Non-fatal failure tracking with end-of-run summary banner
- Hands off to `uv run setup.py` as final step

#### Provisioner (`setup.py`)

- Interactive identity prompts (name, email) persisted to
  `~/.config/dotfiles/identity.json`
- `--dry-run` flag to preview changes without modifying the filesystem
- `--non-interactive` / `CI=1` mode reading `DOTFILES_NAME` and
  `DOTFILES_EMAIL` from the environment
- Template rendering with longest-first placeholder substitution
- Symlink provisioning for 13 repo-owned paths into `~` and `~/.config`
- Pre-provisioning snapshots with full restore-on-error recovery
- Timestamped `.bak` backups before replacing existing files
- Claude Code integration: symlinks `statusline.sh` and merges `statusLine`
  command into `~/.claude/settings.json` without clobbering user settings
- 1Password secrets flow: account staging, interactive auth, runtime-only
  `op://` URI resolution (secrets never written to disk)
- Platform-aware SSH agent socket detection (macOS vs Linux)
- Default browser configuration (Chrome via `open` / `xdg-settings`)

#### Theme system (`themes/`)

- Three themes defined in `themes.toml`: Plastic Beach, Deep Water,
  Desert Island
- Unified color structure: base palette, accents, terminal ANSI colors, and
  preview snippets
- Color utilities: hex/rgb conversion, smooth blending/interpolation
- Generated outputs per theme:
  - Ghostty terminal theme
  - Neovim Catppuccin mocha color overrides (`theme_colors.lua`)
  - Neovim dashboard header colors (`dashboard_colors.lua`)
  - Lazygit GUI theme (`config.yml`)
  - btop system monitor theme
- Template placeholders for fzf colors, git-delta styling, starship prompt
  colors, Claude Code statusline palette, and lazyjj highlight color
- Browser-based gallery preview (`build_gallery.py` → `gallery.html`)
- Interactive theme selection with in-terminal gallery preview during setup

#### Shell (`shell/`)

- Zsh configuration with completion system, 50k shared history, and
  substring search
- Modern CLI aliases: eza, bat, ripgrep, fd, dust, btop, sd, delta, lazygit,
  lazyjj
- Jujutsu shorthand aliases (`js`, `jl`, `jd`, `jn`, `jc`, `jds`)
- Homebrew environment setup in `zprofile` (macOS and Linux paths)
- Rust toolchain sourcing in `zshenv`
- Theme-driven MOTD banner on first interactive shell

#### Git and VCS (`git/`, `jj/`)

- Templated gitconfig with delta pager, diff3 merge conflicts, and
  theme-dependent syntax highlighting
- Global gitignore (OS files, editor caches, build artifacts, jj workspaces)
- Jujutsu config with git-style diffs, delta pager, and themed lazyjj
  highlight color

#### Editor and terminal (`nvim/`, `ghostty/`)

- Full Neovim config directory symlinked to `~/.config/nvim`
- Ghostty config: Maple Mono NF 14pt, hidden titlebar, split keybindings,
  10k scrollback, dynamic theme linking

#### Prompt and plugins (`starship/`, `sheldon/`)

- Starship prompt: directory + jj-starship integration + themed character
- Sheldon plugins: zsh-completions, autosuggestions, syntax-highlighting,
  history-substring-search, fzf-tab

#### Other integrations

- GitHub CLI config with https protocol and `co` alias for `pr checkout`
- SSH config with 1Password agent socket (platform-templated)
- Claude Code statusline showing model, project, jj status, and color-coded
  context usage bar

#### Tests

- `test_setup.py`: 23 cases covering template rendering, symlink creation,
  dry-run mode, snapshots, secrets, Claude Code config, platform detection,
  non-interactive mode, and SSH config
- `test_bootstrap.py`: 5 cases covering package installation, Linux cask
  skipping, section banners, and `bash -n` syntax validation
- `test_generate.py`: 24 cases covering color utilities, theme consistency,
  WCAG AA contrast validation, and generator output correctness
