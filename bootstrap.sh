#!/usr/bin/env bash
set -euo pipefail

# Detect OS
OS="$(uname -s)"
case "$OS" in
    Darwin) echo "Detected macOS" ;;
    Linux)  echo "Detected Linux" ;;
    *)      echo "Unsupported OS: $OS"; exit 1 ;;
esac

# Install uv if not present
if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "uv installed."
else
    echo "uv already installed."
fi

# Hand off to Python provisioning script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
uv run "$SCRIPT_DIR/setup.py"
