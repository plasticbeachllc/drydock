# Dotfiles Repo Plan

## Overview

Build a dotfiles repo at `~/worktable/dotfiles` that manages local machine config via symlinks, with a Python-based provisioning system bootstrapped by `uv`. The repo uses `jj` (git backend) for version control and is hosted at `github.com/<personal-account>/dotfiles` (private, already created and pushed with an initial commit on `main`).

## Current State

- Repo initialized at `~/worktable/dotfiles` with `jj git init`
- GitHub remote wired up via `gh repo create dotfiles --private --source .`
- `main` bookmark pushed with an "initial commit" (just a README.md)
- No config files copied in yet
- No scripts written yet

## Directory Structure

```
dotfiles/
├── README.md
├── bootstrap.sh          # Minimal bash bootstrapper (installs uv, kicks off Python)
├── setup.py              # Main provisioning script (run via uv)
├── shell/
│   ├── zshrc             # ~/.zshrc
│   ├── zshenv            # ~/.zshenv
│   └── zprofile          # ~/.zprofile
├── git/
│   ├── gitconfig         # ~/.gitconfig
│   └── ignore            # ~/.config/git/ignore
├── jj/
│   └── config.toml       # ~/.config/jj/config.toml
└── gh/
    └── config.yml        # ~/.config/gh/config.yml
```

File naming convention: dot prefix is dropped in the repo (e.g., `.zshrc` → `shell/zshrc`).

## Symlink Mapping

The provisioning script must create these symlinks:

| Repo path              | Symlink target               |
|------------------------|------------------------------|
| `shell/zshrc`          | `~/.zshrc`                   |
| `shell/zshenv`         | `~/.zshenv`                  |
| `shell/zprofile`       | `~/.zprofile`                |
| `git/gitconfig`        | `~/.gitconfig`               |
| `git/ignore`           | `~/.config/git/ignore`       |
| `jj/config.toml`       | `~/.config/jj/config.toml`   |
| `gh/config.yml`        | `~/.config/gh/config.yml`    |

## Phase 1: Copy Config Files Into Repo

```bash
cd ~/worktable/dotfiles
mkdir -p shell git jj gh
cp ~/.zshrc shell/zshrc
cp ~/.zshenv shell/zshenv
cp ~/.zprofile shell/zprofile
cp ~/.gitconfig git/gitconfig
cp ~/.config/git/ignore git/ignore
cp ~/.config/jj/config.toml jj/config.toml
cp ~/.config/gh/config.yml gh/config.yml
```

Verify with `jj status` to confirm jj picked up all files.

## Phase 2: Bootstrap Script (`bootstrap.sh`)

Minimal bash script. Its only job:

1. Detect OS (macOS vs Linux) — for future use
2. Install `uv` if not present (via `curl -LsSf https://astral.sh/uv/install.sh | sh`)
3. Run `uv run setup.py` to hand off to the Python provisioning script

Design constraints:
- Must work on a fresh machine with no dependencies beyond bash and curl
- Keep it short — all real logic goes in `setup.py`

## Phase 3: Provisioning Script (`setup.py`)

Python script, run via `uv run` (inline script dependencies if needed via PEP 723 metadata).

### Core behavior:

1. **Determine repo root** — resolve relative to the script's own location
2. **Read symlink mapping** — defined as a data structure in the script (the table above)
3. **For each mapping:**
   - Create parent directories if they don't exist (`mkdir -p` equivalent)
   - Check if target already exists:
     - If it's already the correct symlink → skip (idempotent)
     - If it's a regular file → back it up to `<path>.bak.<timestamp>`, then symlink
     - If it's a broken symlink → remove and re-symlink
   - Create the symlink
4. **Report** what was done (created, skipped, backed up)

### Design constraints:

- Idempotent — safe to run multiple times
- No destructive operations without backup
- Use only Python stdlib (no pip dependencies needed for symlink management)
- Print clear output showing what was linked, skipped, or backed up

### Future extensibility (don't build yet, but design with these in mind):

- OS detection (macOS vs Linux) for conditional config
- Machine-specific overrides (e.g., work laptop vs personal)
- Package installation (brew, apt)
- Config templating (e.g., inject machine-specific values into configs)

## Phase 4: Commit and Push

```bash
cd ~/worktable/dotfiles
jj describe -m "add config files and provisioning scripts"
jj new
jj bookmark set main -r @-
jj git push --bookmark main
```

## Phase 5: Replace Originals With Symlinks

After pushing (so the repo has the files safely), run the provisioning script to replace the original config files with symlinks pointing into the repo:

```bash
./bootstrap.sh
```

Verify symlinks:
```bash
ls -la ~/.zshrc ~/.zshenv ~/.zprofile ~/.gitconfig
ls -la ~/.config/git/ignore ~/.config/jj/config.toml ~/.config/gh/config.yml
```

Each should show `->` pointing into `~/worktable/dotfiles/`.

## Files to NOT Track (for .gitignore)

Create a `.gitignore` in the repo root:

```
.DS_Store
*.bak.*
__pycache__/
.jj/
```

## VCS Notes

- Use `jj` exclusively, not git directly
- Bookmark `main` tracks the primary branch
- Push workflow: `jj describe` → `jj new` → `jj bookmark set main -r @-` → `jj git push --bookmark main`
- The `.jj/` directory should be in `.gitignore` (jj handles this automatically, but be explicit)

## Sensitive Files — Do NOT Track

- `~/.npmrc` (contains auth token)
- `~/.config/gh/hosts.yml` (contains auth token)
- `~/.config/1Password/` (sensitive)
- `~/.ssh/` (keys)
- `~/.zsh_history`