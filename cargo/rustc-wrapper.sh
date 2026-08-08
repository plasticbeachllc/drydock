#!/usr/bin/env bash
set -euo pipefail

if (( $# == 0 )); then
    echo "drydock-rustc-wrapper: missing rustc command" >&2
    exit 2
fi

rustc_command="$1"
shift

if command -v sccache >/dev/null 2>&1; then
    exec sccache "$rustc_command" "$@"
fi

exec "$rustc_command" "$@"
