#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="$HOME/.local/bin:$PATH"

# ── OS detection ────────────────────────────────────────────
OS="$(uname -s)"
is_macos() { [[ "$OS" == "Darwin" ]]; }
is_linux() { [[ "$OS" == "Linux" ]]; }
is_arch() {
    [[ "${DRYDOCK_FORCE_ARCH:-}" == "1" ]] && return 0
    is_linux && [[ -f /etc/arch-release ]] && command -v pacman &>/dev/null
}

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

install_paru() {
    if command -v paru &>/dev/null; then
        echo "paru already installed."
        return 0
    fi

    if [[ "${DRYDOCK_SKIP_AUR:-}" == "1" ]]; then
        echo "Skipping paru install (DRYDOCK_SKIP_AUR=1)."
        return 0
    fi

    local tmp_dir
    tmp_dir="$(mktemp -d)"
    retry 3 git clone https://aur.archlinux.org/paru.git "$tmp_dir/paru"
    (
        cd "$tmp_dir/paru"
        makepkg -si --noconfirm
    )
    rm -rf "$tmp_dir"
}

install_aur_packages() {
    if [[ "${DRYDOCK_SKIP_AUR:-}" == "1" ]]; then
        echo "Skipping AUR packages (DRYDOCK_SKIP_AUR=1)."
        return 0
    fi
    if ! command -v paru &>/dev/null; then
        echo "Skipping AUR packages (paru not installed)."
        return 0
    fi

    local packages=(
        google-chrome
        1password
        1password-cli
        jj-fzf
        maplemono-nf-unhinted
    )
    for package in "${packages[@]}"; do
        paru -S --needed --noconfirm "$package" || FAILED_STEPS+=("AUR package $package")
    done
}

import_1password_signing_key() {
    if [[ "${DRYDOCK_SKIP_AUR:-}" == "1" ]]; then
        return 0
    fi
    if ! command -v gpg &>/dev/null; then
        echo "Skipping 1Password signing key import (gpg not installed)."
        return 0
    fi

    gpg --list-keys 3FEF9748469ADBE15DA7CA80AC2D62742012EA22 &>/dev/null && return 0

    curl -fsSL https://downloads.1password.com/linux/keys/1password.asc | gpg --import || \
        FAILED_STEPS+=("1Password signing key")
}

enable_user_services() {
    local services=("$@")
    for service in "${services[@]}"; do
        sudo systemctl enable --now "$service" || FAILED_STEPS+=("service $service")
    done
}

ensure_rust_toolchain() {
    if command -v rustup &>/dev/null && rustup show active-toolchain &>/dev/null; then
        echo "Rust toolchain already initialized."
        return 0
    fi

    echo "Initializing Rust toolchain..."
    if is_arch; then
        rustup default stable
    else
        rustup-init -y --no-modify-path
    fi
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

if is_arch; then
    if [[ "$EUID" -eq 0 ]]; then
        echo "Run bootstrap.sh as your normal user with sudo privileges, not as root."
        exit 1
    fi

    # ── Arch packages ──────────────────────────────────────
    banner "Arch packages"

    ARCH_PACKAGES=(
        base-devel
        procps-ng
        curl
        file
        git
        zsh
        tar
        gzip
        unzip
        ca-certificates
        gnupg
        openssh
        networkmanager
        pipewire
        pipewire-pulse
        wireplumber
        bluez
        bluez-utils
        fwupd
        tuned
        zram-generator
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
        github-cli
        jq
        jujutsu
        lazyjj
        rustup
        neovim
        fprintd
        noto-fonts
        noto-fonts-emoji
    )

    sudo pacman -Syu --needed --noconfirm "${ARCH_PACKAGES[@]}" || FAILED_STEPS+=("Arch packages")

    ARCH_OPTIONAL_PACKAGES=(
        ghostty
        bun
        ttf-jetbrains-mono-nerd
    )
    for package in "${ARCH_OPTIONAL_PACKAGES[@]}"; do
        sudo pacman -S --needed --noconfirm "$package" || FAILED_STEPS+=("optional Arch package $package")
    done

    banner "Rust toolchain"
    ensure_rust_toolchain

    banner "AUR packages"
    install_paru || FAILED_STEPS+=("paru")
    import_1password_signing_key
    install_aur_packages

    banner "Arch services"
    enable_user_services NetworkManager.service bluetooth.service tuned.service
elif is_macos || is_linux; then
    # ── Homebrew ────────────────────────────────────────────
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
    dmmulroy/tap/jj-starship
)

if ! is_arch; then
    brew install "${COMMON_TOOLS[@]}" || FAILED_STEPS+=("CLI tools (some formulae)")
fi

if is_macos; then
    brew install "${MACOS_TOOLS[@]}" || FAILED_STEPS+=("macOS-only CLI tools")
fi

# On Linux, install jj-starship via brew if available
if is_linux && ! is_arch; then
    brew install dmmulroy/tap/jj-starship 2>/dev/null || true
fi

# ── jj-fzf ──────────────────────────────────────────────────
if ! command -v jj-fzf &>/dev/null && [ ! -d "$HOME/.jj-fzf" ]; then
    banner "jj-fzf"
    if is_arch; then
        retry 3 git clone https://github.com/tim-janik/jj-fzf.git "$HOME/.jj-fzf"
    else
        brew install jj-fzf 2>/dev/null || \
        retry 3 git clone https://github.com/tim-janik/jj-fzf.git "$HOME/.jj-fzf"
    fi
fi

# ── bun ─────────────────────────────────────────────────────
if ! command -v bun &>/dev/null; then
    banner "bun"
    if is_arch; then
        sudo pacman -S --needed --noconfirm bun || FAILED_STEPS+=("bun")
    else
        brew install oven-sh/bun/bun || FAILED_STEPS+=("bun")
    fi
fi

# ── Rust toolchain ──────────────────────────────────────────
if ! is_arch; then
    banner "Rust toolchain"
    ensure_rust_toolchain
fi

# ── AI tools ───────────────────────────────────────────────
banner "AI tools"
curl -fsSL https://claude.ai/install.sh | /bin/bash 2>/dev/null || true
curl -fsSL https://chatgpt.com/codex/install.sh | CODEX_NON_INTERACTIVE=1 sh 2>/dev/null || true

# ── Post-install ────────────────────────────────────────────
banner "Post-install"

# fzf shell integration
if command -v brew &>/dev/null && [ -f "$(brew --prefix)/opt/fzf/install" ]; then
    "$(brew --prefix)/opt/fzf/install" --key-bindings --completion --no-update-rc --no-bash --no-fish
fi

# tealdeer cache
command -v tldr &>/dev/null && tldr --update || true

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

# sheldon plugin lock (must run after setup.py symlinks plugins.toml)
command -v sheldon &>/dev/null && sheldon lock || true
