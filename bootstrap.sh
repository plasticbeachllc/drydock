#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- Homebrew ---
if ! command -v brew &>/dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    echo "Homebrew already installed."
fi

# --- Casks (GUI apps) ---
echo "Installing casks..."
brew install --cask ghostty 2>/dev/null || true
brew install --cask font-maple-mono-nf 2>/dev/null || true

# --- Formulae (CLI tools) ---
echo "Installing CLI tools..."
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
  lazyjj \
  dmmulroy/tap/jj-starship \
  1password-cli \
  neovim

# --- jj-fzf (git clone if not in brew) ---
if ! command -v jj-fzf &>/dev/null && [ ! -d "$HOME/.jj-fzf" ]; then
    echo "Installing jj-fzf..."
    brew install jj-fzf 2>/dev/null || \
        git clone https://github.com/tim-janik/jj-fzf.git "$HOME/.jj-fzf"
fi

# --- bun (needed for AI tool installs) ---
if ! command -v bun &>/dev/null; then
    echo "Installing bun..."
    brew install oven-sh/bun/bun
fi

# --- AI tools (via bun for auto-updates) ---
echo "Installing AI tools..."
bun install -g @anthropic-ai/claude-code 2>/dev/null || true
bun install -g @openai/codex 2>/dev/null || true

# --- Post-install ---
echo "Running post-install steps..."

# fzf shell integration
if [ -f "$(brew --prefix)/opt/fzf/install" ]; then
    "$(brew --prefix)/opt/fzf/install" --key-bindings --completion --no-update-rc --no-bash --no-fish
fi

# tealdeer cache
command -v tldr &>/dev/null && tldr --update || true

# sheldon plugin lock
command -v sheldon &>/dev/null && sheldon lock || true

# --- uv (for setup.py) ---
if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
else
    echo "uv already installed."
fi

# --- Hand off to Python provisioner ---
echo ""
echo "Package installation complete. Running setup.py..."
echo ""
uv run "$SCRIPT_DIR/setup.py"
