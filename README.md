# dotfiles

Personal shell/editor/tooling dotfiles, provisioned from this repo via symlinks.

## What This Repo Manages

- Zsh shell config
- Git and Jujutsu config
- GitHub CLI config
- Sheldon plugins
- Starship prompt
- Ghostty config and theme
- Neovim config

The repo-owned files live here, and `setup.py` links them into `~` and `~/.config`.

## Bootstrap Flow

On a fresh macOS machine:

```bash
./bootstrap.sh
```

`bootstrap.sh` does two things:

1. Installs the core package/tooling dependencies with Homebrew.
2. Runs `uv run setup.py`.

`setup.py` then:

1. Prompts for identity values used in templated config.
2. Creates or repairs symlinks from your home directory into this repo.
3. Backs up conflicting existing files to `*.bak.<timestamp>`.
4. Offers a 1Password-backed or manual secret setup flow for `~/.zshrc.local`.

You can also run the provisioner directly:

```bash
uv run setup.py
```

## Managed Paths

These repo paths are linked into your home directory:

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
| `ghostty/themes/Plastic Beach Basic` | `~/.config/ghostty/themes/Plastic Beach Basic` |
| `nvim` | `~/.config/nvim` |

## Secrets

Runtime secrets are expected to come from one of two places:

- Preferred: 1Password CLI via the `op://...` reads in [`shell/zshrc`](/Users/tdc/worktable/dotfiles/shell/zshrc)
- Fallback: exports written to `~/.zshrc.local` by `setup.py`

This repo should not contain machine-local secrets, auth tokens, or stateful app data.

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
├── shell/
├── git/
├── jj/
├── gh/
├── ghostty/
├── nvim/
├── sheldon/
├── starship/
├── tests/
└── docs/archive/
```

## Archived Docs

Older planning and runbook material lives under `docs/archive/`. It is historical context, not the source of truth. The current workflow should be documented here in `README.md`.
