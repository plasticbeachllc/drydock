#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="$HOME/.local/bin:$PATH"
export HOMEBREW_NO_ENV_HINTS=1

# ── OS detection ────────────────────────────────────────────
OS="$(uname -s)"
is_macos() { [[ "$OS" == "Darwin" ]]; }
is_linux() { [[ "$OS" == "Linux" ]]; }
is_arch() {
    [[ "${DRYDOCK_FORCE_ARCH:-}" == "1" ]] && return 0
    [[ "${DRYDOCK_FORCE_NON_ARCH:-}" == "1" ]] && return 1
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

brew_cmd() {
    env NONINTERACTIVE=1 HOMEBREW_NO_ENV_HINTS=1 brew "$@"
}

macos_app_installed() {
    local app_name="$1"
    local cask_name="$2"
    local applications_dir="${DRYDOCK_APPLICATIONS_DIR:-/Applications}"

    [[ -d "$applications_dir/$app_name.app" ]] && return 0
    brew_cmd list --cask "$cask_name" &>/dev/null
}

install_macos_cask() {
    local cask_name="$1"
    local app_name="$2"
    local required="${3:-0}"

    if macos_app_installed "$app_name" "$cask_name"; then
        echo "$app_name already installed."
        return 0
    fi

    echo "Installing $app_name..."
    if brew_cmd install --cask "$cask_name"; then
        return 0
    fi

    FAILED_STEPS+=("macOS cask $cask_name")
    if [[ "$required" == "1" ]]; then
        return 1
    fi
    return 0
}

ensure_macos_command_line_tools() {
    if xcode-select -p &>/dev/null && xcrun --find clang &>/dev/null; then
        echo "Xcode Command Line Tools already installed."
        return 0
    fi

    echo "Xcode Command Line Tools are not installed."
    echo "Starting Apple's installer..."
    xcode-select --install || true
    echo "After installation finishes, rerun ./bootstrap.sh."
    return 1
}

ensure_macos_sudo_access() {
    if sudo -n true 2>/dev/null; then
        echo "sudo access already available."
        return 0
    fi

    if [[ ! -t 0 ]]; then
        echo "Administrator access is required for Homebrew."
        echo "Run ./bootstrap.sh from an interactive Terminal window so sudo can prompt for your password."
        return 1
    fi

    echo "Administrator access is required for Homebrew."
    echo "Enter your macOS password at the sudo prompt below; sudo does not show a GUI dialog."
    sudo -v || {
        echo "Could not confirm sudo access."
        return 1
    }
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

configure_firewall() {
    if ! command -v ufw &>/dev/null; then
        echo "Skipping firewall setup (ufw not installed)."
        return 0
    fi
    if ! command -v iptables &>/dev/null || ! iptables --version >/dev/null 2>&1; then
        echo "Skipping firewall setup (iptables backend unavailable)."
        return 0
    fi

    sudo ufw default deny incoming || FAILED_STEPS+=("firewall default deny incoming")
    sudo ufw default allow outgoing || FAILED_STEPS+=("firewall default allow outgoing")
    sudo ufw --force enable || FAILED_STEPS+=("firewall enable")
    sudo systemctl enable --now ufw.service || FAILED_STEPS+=("service ufw.service")
}

configure_gnome_defaults() {
    if ! command -v gsettings &>/dev/null; then
        echo "Skipping GNOME defaults (gsettings not installed)."
        return 0
    fi

    local settings=(
        "org.gnome.desktop.interface color-scheme prefer-dark"
        "org.gnome.desktop.interface show-battery-percentage true"
        "org.gnome.desktop.interface clock-show-date true"
        "org.gnome.desktop.interface clock-show-weekday true"
        "org.gnome.desktop.interface enable-hot-corners false"
        "org.gnome.desktop.peripherals.touchpad tap-to-click true"
        "org.gnome.desktop.peripherals.touchpad natural-scroll true"
        "org.gnome.desktop.session idle-delay 900"
        "org.gnome.desktop.screensaver lock-delay 0"
    )

    local setting
    for setting in "${settings[@]}"; do
        # shellcheck disable=SC2086
        gsettings set $setting || FAILED_STEPS+=("GNOME setting $setting")
    done

    gsettings set org.gnome.shell favorite-apps \
        "['com.mitchellh.ghostty.desktop', 'google-chrome.desktop', 'org.gnome.Nautilus.desktop', 'org.gnome.Settings.desktop', '1password.desktop']" || \
        FAILED_STEPS+=("GNOME favorite apps")
}

configure_gnome_extensions() {
    local extension_id="appindicatorsupport@rgcjonas.gmail.com"

    if ! command -v gnome-extensions &>/dev/null; then
        echo "Skipping GNOME extension enablement (gnome-extensions not installed)."
        return 0
    fi

    if gnome-extensions list | grep -Fxq "$extension_id"; then
        gnome-extensions enable "$extension_id" || FAILED_STEPS+=("GNOME AppIndicator extension")
        return 0
    fi

    if [[ -f "/usr/share/gnome-shell/extensions/$extension_id/metadata.json" || \
          -f "$HOME/.local/share/gnome-shell/extensions/$extension_id/metadata.json" ]]; then
        echo "AppIndicator extension is installed; log out and back in, then rerun bootstrap or enable it in Extension Manager."
        return 0
    fi

    echo "Skipping AppIndicator extension enablement (extension not installed)."
}

configure_grub_boot_polish() {
    local grub_default="${DRYDOCK_GRUB_DEFAULT:-/etc/default/grub}"
    local grub_config="${DRYDOCK_GRUB_CONFIG:-/boot/grub/grub.cfg}"

    if [[ ! -f "$grub_default" ]]; then
        echo "Skipping GRUB boot polish ($grub_default not found)."
        return 0
    fi

    local current=""
    local line
    line="$(grep -E '^GRUB_CMDLINE_LINUX_DEFAULT=' "$grub_default" | tail -n 1 || true)"
    if [[ -n "$line" ]]; then
        current="${line#GRUB_CMDLINE_LINUX_DEFAULT=}"
        current="${current#\"}"
        current="${current%\"}"
        current="${current#\'}"
        current="${current%\'}"
    fi

    local arg
    for arg in logo.nologo quiet loglevel=3 rd.udev.log_level=3 systemd.show_status=auto; do
        case " $current " in
            *" $arg "*) ;;
            *) current="${current:+$current }$arg" ;;
        esac
    done

    local tmp
    tmp="$(mktemp)"
    awk -v value="$current" '
        BEGIN { written = 0 }
        /^GRUB_CMDLINE_LINUX_DEFAULT=/ {
            if (!written) {
                print "GRUB_CMDLINE_LINUX_DEFAULT=\"" value "\""
                written = 1
            }
            next
        }
        { print }
        END {
            if (!written) {
                print "GRUB_CMDLINE_LINUX_DEFAULT=\"" value "\""
            }
        }
    ' "$grub_default" >"$tmp"

    sudo install -m 0644 "$tmp" "$grub_default" || FAILED_STEPS+=("GRUB defaults")
    rm -f "$tmp"

    if command -v grub-mkconfig &>/dev/null; then
        sudo grub-mkconfig -o "$grub_config" || FAILED_STEPS+=("GRUB config")
    elif command -v grub2-mkconfig &>/dev/null; then
        sudo grub2-mkconfig -o "$grub_config" || FAILED_STEPS+=("GRUB config")
    else
        echo "Skipping GRUB config regeneration (grub-mkconfig not installed)."
    fi
}

remove_gdm_login_logo() {
    local profile_dir="${DRYDOCK_DCONF_PROFILE_DIR:-/etc/dconf/profile}"
    local profile_file="$profile_dir/gdm"
    local override_dir="${DRYDOCK_GDM_DCONF_DIR:-/etc/dconf/db/gdm.d}"
    local override_file="$override_dir/00-drydock-login-screen"

    if ! command -v dconf &>/dev/null; then
        echo "Skipping GDM logo override (dconf not installed)."
        return 0
    fi

    if [[ "${DRYDOCK_GDM_DCONF_DIR:-}" == "" && ! -d /etc/dconf/db ]]; then
        echo "Skipping GDM logo override (GDM dconf database not found)."
        return 0
    fi

    if [[ ! -e "$profile_file" ]]; then
        sudo install -d -m 0755 "$profile_dir"
        printf "%s\n" \
            "user-db:user" \
            "system-db:gdm" \
            "file-db:/usr/share/gdm/greeter-dconf-defaults" | sudo tee "$profile_file" >/dev/null
    fi

    sudo install -d -m 0755 "$override_dir"
    printf "%s\n" \
        "[org/gnome/login-screen]" \
        "logo=''" | sudo tee "$override_file" >/dev/null
    sudo dconf update || FAILED_STEPS+=("GDM logo override")
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
        dconf
        ufw
        gnome-shell-extension-appindicator
        extension-manager
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
        just
        lazygit
        github-cli
        jq
        jujutsu
        lazyjj
        rustup
        nodejs
        npm
        python
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

    banner "Firewall"
    configure_firewall

    banner "GDM login screen"
    remove_gdm_login_logo

    banner "GNOME defaults"
    configure_gnome_defaults

    banner "GNOME extensions"
    configure_gnome_extensions

    banner "GRUB boot polish"
    configure_grub_boot_polish
elif is_macos || is_linux; then
    if is_macos; then
        banner "macOS preflight"
        ensure_macos_command_line_tools
        ensure_macos_sudo_access
    fi

    # ── Homebrew ────────────────────────────────────────────
    banner "Homebrew"

    if ! command -v brew &>/dev/null; then
        echo "Installing Homebrew..."
        retry 3 env NONINTERACTIVE=1 HOMEBREW_NO_ENV_HINTS=1 /bin/bash -c 'curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | /bin/bash'
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
    install_macos_cask ghostty Ghostty
    install_macos_cask font-maple-mono-nf "Maple Mono NF"
    install_macos_cask google-chrome "Google Chrome" 1
    install_macos_cask 1password 1Password 1
    install_macos_cask telegram Telegram
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
    just
    lazygit
    gh
    jq
    jj
    lazyjj
    1password-cli
    rustup-init
    node
    python
    neovim
)

# macOS-only brew formulae
MACOS_TOOLS=(
    dmmulroy/tap/jj-starship
)

if ! is_arch; then
    brew_cmd install "${COMMON_TOOLS[@]}" || FAILED_STEPS+=("CLI tools (some formulae)")
fi

if is_macos; then
    brew_cmd install "${MACOS_TOOLS[@]}" || FAILED_STEPS+=("macOS-only CLI tools")
fi

# On Linux, install jj-starship via brew if available
if is_linux && ! is_arch; then
    brew_cmd install dmmulroy/tap/jj-starship 2>/dev/null || true
fi

# ── jj-fzf ──────────────────────────────────────────────────
if [[ "${DRYDOCK_FORCE_JJ_FZF_INSTALL:-}" == "1" ]] || \
    { ! command -v jj-fzf &>/dev/null && [ ! -d "$HOME/.jj-fzf" ]; }; then
    banner "jj-fzf"
    if is_arch; then
        retry 3 git clone https://github.com/tim-janik/jj-fzf.git "$HOME/.jj-fzf"
    else
        brew_cmd install jj-fzf 2>/dev/null || \
        retry 3 git clone https://github.com/tim-janik/jj-fzf.git "$HOME/.jj-fzf"
    fi
fi

# ── bun ─────────────────────────────────────────────────────
if ! command -v bun &>/dev/null; then
    banner "bun"
    if is_arch; then
        sudo pacman -S --needed --noconfirm bun || FAILED_STEPS+=("bun")
    else
        brew_cmd install oven-sh/bun/bun || FAILED_STEPS+=("bun")
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
if command -v brew &>/dev/null && [ -f "$(brew_cmd --prefix)/opt/fzf/install" ]; then
    "$(brew_cmd --prefix)/opt/fzf/install" --key-bindings --completion --no-update-rc --no-bash --no-fish
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
