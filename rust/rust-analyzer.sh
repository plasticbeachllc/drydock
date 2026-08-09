#!/usr/bin/env bash
set -euo pipefail

rustup_command=""
if command -v rustup >/dev/null 2>&1; then
    rustup_command="$(command -v rustup)"
elif [[ -x "$HOME/.cargo/bin/rustup" ]]; then
    rustup_command="$HOME/.cargo/bin/rustup"
elif [[ -x /opt/homebrew/opt/rustup/bin/rustup ]]; then
    rustup_command="/opt/homebrew/opt/rustup/bin/rustup"
elif [[ -x /usr/local/opt/rustup/bin/rustup ]]; then
    rustup_command="/usr/local/opt/rustup/bin/rustup"
elif [[ -x /home/linuxbrew/.linuxbrew/opt/rustup/bin/rustup ]]; then
    rustup_command="/home/linuxbrew/.linuxbrew/opt/rustup/bin/rustup"
fi

if [[ -z "$rustup_command" ]]; then
    echo "rust-analyzer: rustup is not installed or discoverable" >&2
    exit 1
fi

if ! analyzer_command="$("$rustup_command" which rust-analyzer)"; then
    echo "rust-analyzer: install the component with 'rustup component add rust-analyzer'" >&2
    exit 1
fi

exec "$analyzer_command" "$@"
