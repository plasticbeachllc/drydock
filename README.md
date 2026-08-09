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
- Rust toolchain, build-cache, test, coverage, and dependency-audit tooling
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
packages, applies the baseline GNOME/system defaults, then runs `uv run setup.py`.

`bootstrap.sh` does three things:

1. Installs the core package/tooling dependencies with Homebrew on macOS,
   `pacman`/AUR on Arch Linux, or Homebrew on other Linux distributions.
2. Installs and selects the stable Rust toolchain, independent of any project
   toolchain override in the launch directory.
3. Runs `uv run setup.py`.

The bootstrap install set includes:

- Core shell and editor tools such as `starship`, `sheldon`, `neovim`, `gh`, `flyctl`, `jq`, and `jj`
- Rustup plus `rust-analyzer`, `rust-src`, Clippy, rustfmt, and LLVM tools
- Rust feedback tools: `cargo-nextest`, `cargo-llvm-cov`, `cargo-deny`, `sccache`, and `bacon`
- GUI apps and fonts such as `ghostty` and `font-maple-mono-nf`
- Arch desktop/system defaults such as UFW firewall policy, GNOME dark mode, AppIndicator support, and quieter GRUB boot output
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
| `cargo/rustc-wrapper.sh` | `~/.local/bin/drydock-rustc-wrapper` |
| `rust/rust-analyzer.sh` | `~/.local/bin/rust-analyzer` |
| `claude/statusline.sh` | `~/.claude/statusline.sh` |
| `codex/rust-fast.config.toml` | `~/.codex/rust-fast.config.toml` |
| `codex/skills/sync-branch` | `~/.codex/skills/sync-branch` |
| `ssh/config` | `~/.ssh/config` |

`setup.py` also creates a dynamic symlink for the selected Ghostty theme under `~/.config/ghostty/themes/`.
It merges Drydock's `build.rustc-wrapper` setting into Cargo's active home
config (`~/.cargo/config` when present, otherwise `~/.cargo/config.toml`)
instead of replacing the rest of your Cargo configuration. For safety, it
refuses to follow an unmanaged config symlink; replace that link with a local
file before rerunning setup. It also refuses to replace an existing
`build.rustc-wrapper` that points somewhere else; retain that wrapper or remove
it explicitly before enabling Drydock's wrapper. When `CARGO_HOME` is set,
setup manages the active config under that directory instead of `~/.cargo`.

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

## AI-enabled Rust Development

Rustup is the source of truth for the compiler, Cargo, standard-library source,
formatting, linting, and language-server components. On Homebrew systems,
`.zshenv` puts the keg-only rustup proxy directory ahead of a standalone
Homebrew Rust installation for both login and non-login shells. `.zprofile`
reapplies that ordering after `brew shellenv`. This makes interactive terminals,
Neovim, and AI agent shells resolve the same toolchain. `.zshenv` also exposes
the managed `~/.local/bin` shims to non-login shells.

The managed Cargo config uses a repo-owned compiler wrapper. It enables
`sccache` when the command is installed so dependencies can be reused across
repositories and isolated jj workspaces, and invokes rustc directly when
`sccache` is unavailable. This keeps direct `setup.py` runs and partial package
installs usable. A failing installed `sccache` is reported as a build failure so
that normal compiler diagnostics and exit status are not run twice. Build
artifacts remain inside each project's own `target/` directory; this repo does
not set a shared `CARGO_TARGET_DIR`.

Neovim enables LazyVim's Rust and test extras. Rustup supplies `rust-analyzer`,
and a repo-owned `~/.local/bin/rust-analyzer` shim resolves the executable from
the active rustup toolchain. Neovim explicitly includes that shim directory and
the discovered Homebrew rustup proxy directory in its environment even when
launched outside a login shell. LazyVim supplies the Rust-specific editor
integration, Cargo.toml support, debugger integration, and test adapter rather
than installing a second rust-analyzer through Mason; its LSP command explicitly
uses the managed shim.

For a new Rust repository, copy the files from `rust/project-template/` into
the project root and rename `AGENTS.md.example` to `AGENTS.md`. Review feature
combinations and project-specific instructions before using the defaults. The
template provides these standard commands:

```bash
just check
just lint
just test
just coverage
just dependencies
just verify
```

`cargo-nextest` does not run doctests, so `just verify` includes a separate
`cargo test --doc` step.

For routine, low-latency Codex iterations, use the managed profile:

```bash
codex --profile rust-fast
```

It inherits the model from the base Codex config and lowers only the reasoning
effort to `medium`. Current Codex versions load this sibling profile file and
overlay its top-level keys on `~/.codex/config.toml`; they do not use a
`[profiles.rust-fast]` table. Continue using the default high-reasoning profile
for broad design, debugging, or review work.

If an older machine already has the standalone Homebrew `rust` formula, first
check whether anything still requires it and remove it only when the command
prints no dependents:

```bash
brew uses --installed rust
brew uninstall rust
```

Then rerun `./bootstrap.sh` and verify the unified environment:

```bash
type -a rustc cargo rust-analyzer
rustup show active-toolchain
rustup component list --installed
sccache --show-stats
```

## Claude Code

`setup.py` manages Claude Code integration in two places:

- It symlinks [`claude/statusline.sh`](/Users/tdc/worktable/drydock/claude/statusline.sh) to `~/.claude/statusline.sh`
- It merges the managed `statusLine` command into `~/.claude/settings.json` without overwriting unrelated user settings

The status line depends on `jq` and `jj`, both of which are installed by `bootstrap.sh`.

## Secrets

Secrets are resolved at runtime via the 1Password CLI — they are never written to disk in plaintext.
Prefer project-scoped `direnv` files or `op run` commands so local AI agents
inherit only the credentials required for the active project.

`setup.py` handles 1Password configuration:

1. Seeds `~/.zshrc.local` with a template comment showing the `op read` pattern
2. Prompts for and stages the team 1Password account
3. Offers to authenticate the CLI session

For a secret that genuinely must be global, append an `op read` line to
`~/.zshrc.local`:

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

`setup.py --dry-run` reports intended identity, theme, and provisioning changes
without writing generated files or saved selections.

## Repo Layout

```text
.
├── bootstrap.sh
├── setup.py
├── cargo/
├── claude/
├── codex/
├── shell/
├── git/
├── jj/
├── gh/
├── ghostty/
├── nvim/
├── sheldon/
├── ssh/
├── starship/
├── rust/
├── themes/
├── tests/
├── CHANGELOG.md
└── docs/archive/
```

## Archived Docs

Older planning and runbook material lives under `docs/archive/`. It is historical context, not the source of truth. The current workflow should be documented here in `README.md`.
