# Provisioning Framework Improvement Plan

Concrete improvements to make this framework more resilient and
cross-platform (macOS + Linux).

---

## 1. Add Linux support to bootstrap.sh

**Problem:** `bootstrap.sh` assumes macOS/Homebrew exclusively.
Homebrew path is hardcoded to `/opt/homebrew/bin/brew`, and there is no
package-manager abstraction for Linux.

**Fix:**

- Detect OS at the top of the script (`uname -s`).
- On Linux, install packages via the native package manager (apt, dnf,
  or pacman) where equivalents exist, falling back to Homebrew on Linux
  for tools not in distro repos.
- Gate macOS-only casks (Ghostty DMG, fonts, Chrome, 1Password desktop)
  behind an `is_macos` guard.
- Use `/home/linuxbrew/.linuxbrew/bin/brew` on Linux when Homebrew is
  the chosen path.

---

## 2. Add Linux support to setup.py

**Problem:** Several setup.py stages are macOS-only with no guards or
Linux alternatives.

**Fix:**

- Add `IS_LINUX = sys.platform.startswith("linux")` /
  `IS_MACOS = sys.platform == "darwin"` constants.
- **1Password SSH agent socket:** Use
  `~/.1password/agent.sock` on Linux instead of the macOS
  `~/Library/Group Containers/...` path.
- **App icons:** Skip `configure_app_icons()` on Linux (no `fileicon`
  equivalent; desktop files handle icons differently).
- **Default browser:** Use `xdg-settings set default-web-browser
  google-chrome.desktop` on Linux instead of `open -a`.
- **ssh/config:** Template the `IdentityAgent` path so it resolves
  correctly per platform.

---

## 3. Add a `--non-interactive` / `--ci` mode

**Problem:** Every run requires interactive input (name, email, theme),
which makes automated testing and CI impossible.

**Fix:**

- Accept `--non-interactive` flag (or `CI=1` env var).
- In this mode, require identity values from env vars
  (`DOTFILES_NAME`, `DOTFILES_EMAIL`) or a pre-existing
  `identity.json`.
- Default to the first theme if none is persisted.
- Skip secret provisioning entirely.
- Exit non-zero if required values are missing instead of prompting.

---

## 4. Make bootstrap.sh more resilient

**Problem:** A network hiccup mid-install leaves the machine in a
partially-provisioned state with no easy way to resume.

**Fix:**

- **Idempotent guards:** Wrap each package install in an `is_installed`
  check (e.g., `command -v jq` or `brew list --formula | grep -q jq`)
  so re-runs skip already-installed packages.
- **Retry with backoff:** Add a `retry()` helper for network-dependent
  commands (brew install, curl, bun install).
- **Section markers:** Print clear `==> Installing CLI tools` /
  `==> Installing Rust toolchain` banners so users can see where a
  failure occurred.
- **Trap handler:** Add `trap cleanup EXIT` to print a summary of what
  succeeded and what failed, rather than silently stopping at the first
  `set -e` failure.

---

## 5. Add a `--check` / dry-run mode to setup.py

**Problem:** No way to validate the current machine state without
making changes. Useful for CI and for debugging drift.

**Fix:**

- Add `--check` flag that walks through every stage but only reports
  what *would* change.
- Exit 0 if everything is in sync, exit 1 if drift is detected.
- Print a summary: symlinks OK/stale/missing, templates
  rendered/outdated, secrets present/absent.

---

## 6. Improve error reporting in setup.py

**Problem:** Errors during symlink creation, template rendering, or
subprocess calls produce bare tracebacks or silent failures.

**Fix:**

- Add a lightweight `log(level, msg)` helper (info / warn / error)
  with colored output.
- Wrap each stage in a try/except that logs the stage name and error,
  then continues to the next stage (fail-open for non-critical stages,
  fail-closed for identity).
- At the end, print a summary: `7/7 stages completed` or
  `6/7 stages completed (1 warning)`.

---

## 7. Add integration tests for the full provisioning pipeline

**Problem:** `test_bootstrap.py` mocks everything, so it can't catch
real integration issues. There are no tests for the end-to-end flow.

**Fix:**

- Add a test that runs `setup.py --non-interactive --check` (from
  improvement 3 + 5) in a temp home directory with a pre-seeded
  `identity.json`.
- Verify: all symlinks created, all templates rendered, no placeholder
  strings remain in output files.
- Run in CI on both macOS and Linux runners.

---

## 8. Pin tool versions

**Problem:** `brew install <tool>` installs whatever is latest, which
can break configs (e.g., a starship format change, a delta flag
rename).

**Fix:**

- Add a `Brewfile` (or `tool-versions` / `mise.toml`) that pins major
  versions for critical tools (starship, delta, sheldon, bat).
- Use `brew bundle` instead of individual `brew install` calls.
- This also makes the package list declarative and diffable.

---

## 9. Validate rendered output

**Problem:** Template rendering can silently produce broken configs if
a placeholder is misspelled or a theme key is missing.

**Fix:**

- After rendering, validate critical outputs:
  - `gitconfig`: `git config --file <rendered> --list` exits 0.
  - `starship.toml`: `starship config` or TOML parse check.
  - `jj/config.toml`: TOML parse check.
  - Lua files: `luac -p` syntax check (if available).
- Add a `validate_rendered_files()` stage to setup.py.

---

## 10. Add shell config for Linux differences

**Problem:** `zprofile` and `zshenv` assume macOS Homebrew paths.
`ssh/config` hardcodes the macOS 1Password agent socket.

**Fix:**

- Make `zprofile` conditional:
  ```zsh
  # Homebrew
  if [[ -f /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -f /home/linuxbrew/.linuxbrew/bin/brew ]]; then
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
  fi
  ```
- Template `ssh/config` with `__OP_SSH_AGENT_SOCK__` placeholder
  instead of a hardcoded path.
- Add a Linux-appropriate `.desktop` file or XDG setup if needed.

---

## Priority order

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| 1 | OS detection + Linux guards (items 2, 10) | Medium | High |
| 2 | bootstrap.sh resilience (item 4) | Small | High |
| 3 | Non-interactive mode (item 3) | Small | High |
| 4 | Linux bootstrap support (item 1) | Medium | High |
| 5 | Dry-run / check mode (item 5) | Small | Medium |
| 6 | Error reporting (item 6) | Small | Medium |
| 7 | Pin tool versions (item 8) | Small | Medium |
| 8 | Validate rendered output (item 9) | Small | Medium |
| 9 | Integration tests (item 7) | Medium | Medium |
