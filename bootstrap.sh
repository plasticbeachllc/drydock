#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── OS detection ────────────────────────────────────────────
OS="$(uname -s)"
is_macos() { [[ "$OS" == "Darwin" ]]; }
is_linux() { [[ "$OS" == "Linux" ]]; }

# ── Helpers ─────────────────────────────────────────────────

FAILED_STEPS=()

# Retry a command with exponential backoff (for network operations).
# Usage: retry <max_attempts> <command...>
retry() {
    local max="$1"; shift
    local attempt=1
    local delay=2
    while true; do
        if "$@"; then
            return 0
        fi
        if (( attempt >= max )); then
            echo "  ✗ failed after $max attempts: $*"
            return 1
        fi
        echo "  retrying in ${delay}s (attempt $((attempt+1))/$max)..."
        sleep "$delay"
        (( attempt++ ))
        (( delay *= 2 ))
    done
}

banner() {
    echo ""
    echo "==> $1"
    echo ""
}

# Trap: print summary on exit
finish() {
    local exit_code=$?
    echo ""
    if (( ${#FAILED_STEPS[@]} > 0 )); then
        echo "Warning: the following steps had failures:"
        for step in "${FAILED_STEPS[@]}"; do
            echo "  - $step"
        done
        echo ""
        echo "Re-run bootstrap.sh to retry failed steps."
    fi
    if (( exit_code == 0 )); then
        echo "Bootstrap complete."
    else
        echo "Bootstrap exited with errors (code $exit_code)."
    fi
}
trap finish EXIT

# ── Homebrew ────────────────────────────────────────────────
banner "Homebrew"

if ! command -v brew &>/dev/null; then
    echo "Installing Homebrew..."
    retry 3 /bin/bash -c 'curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | /bin/bash'
    # Activate brew in this session
    if is_macos; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -d /home/linuxbrew/.linuxbrew ]; then
        eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
    fi
else
    echo "Homebrew already installed."
fi

# ── Casks (GUI apps — macOS only) ──────────────────────────
if is_macos; then
    banner "Casks (GUI apps)"
    brew install --cask ghostty 2>/dev/null || true
    brew install --cask font-maple-mono-nf 2>/dev/null || true
    brew install --cask google-chrome 2>/dev/null || true
    brew install --cask 1password 2>/dev/null || true
    brew install --cask telegram 2>/dev/null || true
fi

# ── CLI tools ───────────────────────────────────────────────
banner "CLI tools"

# Common tools available via Homebrew on both macOS and Linux
COMMON_TOOLS=(
    starship
    sheldon
    eza
    bat
    ripgrep
    fd
    zoxide
    fzf
    git-delta
    dust
    btop
    xh
    sd
    tealdeer
    direnv
    lazygit
    gh
    jq
    jj
    lazyjj
    1password-cli
    rustup-init
    neovim
)

# macOS-only brew formulae
MACOS_TOOLS=(
    fileicon
    dmmulroy/tap/jj-starship
)

brew install "${COMMON_TOOLS[@]}" || FAILED_STEPS+=("CLI tools (some formulae)")

if is_macos; then
    brew install "${MACOS_TOOLS[@]}" || FAILED_STEPS+=("macOS-only CLI tools")
fi

# On Linux, install jj-starship via brew if available
if is_linux; then
    brew install dmmulroy/tap/jj-starship 2>/dev/null || true
fi

# ── jj-fzf ──────────────────────────────────────────────────
if ! command -v jj-fzf &>/dev/null && [ ! -d "$HOME/.jj-fzf" ]; then
    banner "jj-fzf"
    brew install jj-fzf 2>/dev/null || \
        retry 3 git clone https://github.com/tim-janik/jj-fzf.git "$HOME/.jj-fzf"
fi

# ── bun ─────────────────────────────────────────────────────
if ! command -v bun &>/dev/null; then
    banner "bun"
    brew install oven-sh/bun/bun || FAILED_STEPS+=("bun")
fi

# ── Rust toolchain ──────────────────────────────────────────
banner "Rust toolchain"

if [ ! -f "$HOME/.cargo/env" ]; then
    echo "Initializing Rust toolchain..."
    rustup-init -y --no-modify-path
else
    echo "Rust toolchain already initialized."
fi

# ── AI tools ───────────────────────────────────────────────
banner "AI tools"
curl -fsSL https://claude.ai/install.sh | /bin/bash 2>/dev/null || true
brew install codex 2>/dev/null || true

# ── Post-install ────────────────────────────────────────────
banner "Post-install"

# fzf shell integration
if [ -f "$(brew --prefix)/opt/fzf/install" ]; then
    "$(brew --prefix)/opt/fzf/install" --key-bindings --completion --no-update-rc --no-bash --no-fish
fi

# tealdeer cache
command -v tldr &>/dev/null && tldr --update || true

# sheldon plugin lock
command -v sheldon &>/dev/null && sheldon lock || true

# ── uv (for setup.py) ──────────────────────────────────────
if ! command -v uv &>/dev/null; then
    banner "uv"
    retry 3 bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh' || FAILED_STEPS+=("uv")
else
    echo "uv already installed."
fi

# ── Hand off to Python provisioner ──────────────────────────
banner "Running setup.py"
uv run "$SCRIPT_DIR/setup.py"
