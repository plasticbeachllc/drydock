# dotfiles

Personal shell/editor/tooling dotfiles, provisioned from this repo via symlinks.

Current version: **v0.1** — see [CHANGELOG.md](CHANGELOG.md) for details.

## What This Repo Manages

- Zsh shell config
- Git and Jujutsu config
- GitHub CLI config
- Sheldon plugins
- Starship prompt
- Ghostty config and theme
- Neovim config
- Claude Code status line integration
- Generated theme outputs for Ghostty, Neovim, Lazygit, and btop

The repo-owned files live here, and `setup.py` links them into `~` and `~/.config`.

## Bootstrap Flow

On a fresh macOS machine:

```bash
./bootstrap.sh
```

On a Windows dual-boot Arch Linux laptop, boot the standard Arch ISO, connect
to the network, then run:

```bash
curl -fsSL https://raw.githubusercontent.com/plasticbeachllc/drydock/main/install/arch-live.sh | bash
```

The Arch live installer currently supports reversible dual-boot modes: it can
use an existing Linux root partition or create one partition in already-shrunk
free space. It reuses the existing EFI partition without formatting it, keeps
`/home` inside root, and uses zram instead of a swap partition. See
[install/README.md](install/README.md).

To preview the same install plan without formatting or mounting anything:

```bash
curl -fsSL https://raw.githubusercontent.com/plasticbeachllc/drydock/main/install/arch-live.sh | bash -s -- --dry-run
```

If Windows has been shrunk but no Linux partition exists yet:

```bash
curl -fsSL https://raw.githubusercontent.com/plasticbeachllc/drydock/main/install/arch-live.sh | bash -s -- dual-boot-create-partition --dry-run
```

In create-partition mode, the installer shows `parted ... print free`, asks for
which numbered free-space range to use, then creates the Linux root partition
using exact sector boundaries rather than rounded GiB values.

## Arch Linux Deployment

The current Arch path is designed for a standard Arch ISO, not a custom ISO.
Boot the USB installer, connect to the network, then fetch this repo's live
installer from GitHub.

For a Windows dual-boot machine where Windows has already been shrunk and the
installer should create the Linux partition in free space:

```bash
curl -fsSL https://raw.githubusercontent.com/plasticbeachllc/drydock/main/install/arch-live.sh | bash -s -- dual-boot-create-partition --dry-run
```

After reviewing the plan, rerun without `--dry-run`:

```bash
curl -fsSL https://raw.githubusercontent.com/plasticbeachllc/drydock/main/install/arch-live.sh | bash -s -- dual-boot-create-partition
```

For a machine where a Linux root partition already exists:

```bash
curl -fsSL https://raw.githubusercontent.com/plasticbeachllc/drydock/main/install/arch-live.sh | bash -s -- dual-boot-use-partition --dry-run
```

The live installer:

- reuses the existing EFI partition without formatting it
- creates or formats exactly one Linux root partition
- keeps `/home` inside the Linux root partition
- uses zram instead of a swap partition
- installs a GNOME/GDM first-boot system
- clones this repo to `~/worktable/drydock`

After rebooting into Arch:

```bash
cd ~/worktable/drydock
./bootstrap.sh
```

On Arch, `bootstrap.sh` uses `pacman` for official packages, initializes the
Rust stable toolchain before AUR setup, installs `paru`, installs selected AUR
packages, then runs `uv run setup.py`.

`bootstrap.sh` does three things:

1. Installs the core package/tooling dependencies with Homebrew on macOS,
   `pacman`/AUR on Arch Linux, or Homebrew on other Linux distributions.
2. Initializes the Rust toolchain.
3. Runs `uv run setup.py`.

The bootstrap install set includes:

- Core shell and editor tools such as `starship`, `sheldon`, `neovim`, `gh`, `jq`, and `jj`
- GUI apps and fonts such as `ghostty` and `font-maple-mono-nf`
- AI tooling such as Claude Code (via [native installer](https://claude.ai/install.sh)) and Codex (via [native installer](https://chatgpt.com/codex/install.sh))

`setup.py` then:

1. Prompts for identity values used in templated config.
2. Prompts for a theme selection and generates theme-dependent files.
3. Creates or repairs symlinks from your home directory into this repo.
4. Merges managed Claude Code settings into `~/.claude/settings.json`.
5. Backs up conflicting existing files to `*.bak.<timestamp>`.
6. Offers a 1Password-backed or manual secret setup flow for `~/.zshrc.local`.

You can also run the provisioner directly:

```bash
uv run setup.py
```

## Symlinked Paths

These repo-owned paths are linked into your home directory:

| Repo path | Target |
|---|---|
| `shell/zshrc` | `~/.zshrc` |
| `shell/zshenv` | `~/.zshenv` |
| `shell/zprofile` | `~/.zprofile` |
| `git/gitconfig` | `~/.gitconfig` |
| `git/ignore` | `~/.config/git/ignore` |
| `jj/config.toml` | `~/.config/jj/config.toml` |
| `gh/config.yml` | `~/.config/gh/config.yml` |
| `sheldon/plugins.toml` | `~/.config/sheldon/plugins.toml` |
| `starship/starship.toml` | `~/.config/starship.toml` |
| `ghostty/config` | `~/.config/ghostty/config` |
| `nvim` | `~/.config/nvim` |
| `claude/statusline.sh` | `~/.claude/statusline.sh` |
| `ssh/config` | `~/.ssh/config` |

`setup.py` also creates a dynamic symlink for the selected Ghostty theme under `~/.config/ghostty/themes/`.

## Generated Outputs

These machine-local files are generated by `setup.py` based on your selected theme and stored outside the repo:

| Generated path | Purpose |
|---|---|
| `~/.config/dotfiles/identity.json` | Stores prompted identity values and the selected theme key |
| `~/.config/dotfiles/rendered/` | Stores rendered versions of templated repo files |
| `~/.config/dotfiles/theme_colors.lua` | Neovim Catppuccin color overrides |
| `~/.config/dotfiles/dashboard_colors.lua` | Neovim dashboard header text and color |
| `~/.config/ghostty/themes/<selected theme>` | Generated Ghostty theme file |
| `~/.config/lazygit/config.yml` | Generated Lazygit theme config |
| `~/.config/btop/themes/<selected theme>.theme` | Generated btop theme file |
| `~/.config/btop/btop.conf` | Updated to point `color_theme` at the selected theme |
| `themes/gallery.html` | Local preview gallery generated from `themes.toml` |

## Claude Code

`setup.py` manages Claude Code integration in two places:

- It symlinks [`claude/statusline.sh`](/Users/tdc/worktable/drydock/claude/statusline.sh) to `~/.claude/statusline.sh`
- It merges the managed `statusLine` command into `~/.claude/settings.json` without overwriting unrelated user settings

The status line depends on `jq` and `jj`, both of which are installed by `bootstrap.sh`.

## Secrets

Secrets are resolved at runtime via the 1Password CLI — they are never written to disk in plaintext.

`setup.py` handles 1Password configuration:

1. Seeds `~/.zshrc.local` with a template comment showing the `op read` pattern
2. Prompts for and stages the team 1Password account
3. Offers to authenticate the CLI session

To add a secret, append an `op read` line to `~/.zshrc.local`:

```bash
export MY_API_KEY=$(op read "op://Vault/Item/field" --no-newline 2>/dev/null)
```

This repo should not contain machine-local secrets, auth tokens, or stateful app data.

## Non-interactive Mode

`setup.py --non-interactive` runs without prompts, reading identity from environment variables and falling back to previously saved values in `~/.config/dotfiles/identity.json`:

| Env var | Purpose |
|---|---|
| `DOTFILES_NAME` | Git author name |
| `DOTFILES_EMAIL` | Git author email |
| `DOTFILES_OP_TEAM` | 1Password team sign-in address (e.g. `myteam.1password.com`) |

Also enabled automatically when `CI=1` is set.

## Tests

The test suite focuses on `setup.py` behavior that should remain safe and idempotent.

Run it with:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Repo Layout

```text
.
├── bootstrap.sh
├── setup.py
├── claude/
├── shell/
├── git/
├── jj/
├── gh/
├── ghostty/
├── nvim/
├── sheldon/
├── ssh/
├── starship/
├── themes/
├── tests/
├── CHANGELOG.md
└── docs/archive/
```

## Archived Docs

Older planning and runbook material lives under `docs/archive/`. It is historical context, not the source of truth. The current workflow should be documented here in `README.md`.
