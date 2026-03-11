#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Terminal QOL Provisioning Script
# Targets: macOS (Homebrew) and Linux (apt/dnf + Homebrew or cargo)
# Generated iteratively by walking through setup manually
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/provision.log"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log()  { echo -e "${GREEN}[✓]${NC} $*" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[!]${NC} $*" | tee -a "$LOG_FILE"; }
err()  { echo -e "${RED}[✗]${NC} $*" | tee -a "$LOG_FILE"; }
info() { echo -e "${BLUE}[i]${NC} $*" | tee -a "$LOG_FILE"; }

# --- OS Detection ---
detect_os() {
    case "$(uname -s)" in
        Darwin) OS="macos" ;;
        Linux)
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                case "$ID" in
                    ubuntu|debian|pop) OS="debian" ;;
                    fedora|rhel|centos|rocky|alma) OS="fedora" ;;
                    arch|manjaro) OS="arch" ;;
                    *) OS="linux-unknown" ;;
                esac
            else
                OS="linux-unknown"
            fi
            ;;
        *) err "Unsupported OS: $(uname -s)"; exit 1 ;;
    esac
    log "Detected OS: $OS"
}

# --- Package Manager Detection ---
detect_pkg_manager() {
    if command -v brew &>/dev/null; then
        PKG="brew"
    elif command -v apt &>/dev/null; then
        PKG="apt"
    elif command -v dnf &>/dev/null; then
        PKG="dnf"
    elif command -v pacman &>/dev/null; then
        PKG="pacman"
    else
        PKG="none"
    fi
    log "Package manager: $PKG"
}

# --- Helper: Install via best available method ---
pkg_install() {
    local name="$1"
    local brew_name="${2:-$1}"
    local apt_name="${3:-$1}"
    local dnf_name="${4:-$1}"

    if command -v "$name" &>/dev/null; then
        log "$name already installed, skipping"
        return 0
    fi

    case "$PKG" in
        brew)   brew install "$brew_name" ;;
        apt)    sudo apt install -y "$apt_name" ;;
        dnf)    sudo dnf install -y "$dnf_name" ;;
        pacman) sudo pacman -S --noconfirm "$apt_name" ;;
        *)      err "No package manager found for $name"; return 1 ;;
    esac

    if command -v "$name" &>/dev/null; then
        log "$name installed successfully"
    else
        warn "$name may not be in PATH yet — check after shell restart"
    fi
}

# --- Helper: Install via cargo (fallback) ---
cargo_install() {
    local name="$1"
    local crate="${2:-$1}"

    if command -v "$name" &>/dev/null; then
        log "$name already installed, skipping"
        return 0
    fi

    if ! command -v cargo &>/dev/null; then
        info "Installing Rust toolchain..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source "$HOME/.cargo/env"
    fi

    cargo install "$crate" --locked
    log "$name installed via cargo"
}

# --- Helper: Install Homebrew if not present ---
ensure_homebrew() {
    if command -v brew &>/dev/null; then
        log "Homebrew already installed"
        return 0
    fi

    if [[ "$OS" == "macos" ]] || [[ "$OS" == "debian" ]] || [[ "$OS" == "fedora" ]]; then
        info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        # Add to PATH for this session
        if [[ "$OS" == "macos" ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
        else
            eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
        fi
        log "Homebrew installed"
    fi
}

# ============================================================
# SECTION 1: Prerequisites
# ============================================================
section_prerequisites() {
    info "=== Section 1: Prerequisites ==="
    detect_os
    ensure_homebrew
    detect_pkg_manager

    # Backup existing .zshrc if present
    if [ -f "$HOME/.zshrc" ]; then
        local backup="$HOME/.zshrc.backup.$(date +%Y%m%d%H%M%S)"
        cp "$HOME/.zshrc" "$backup"
        log "Backed up existing .zshrc to $backup"
    fi

    # Ensure ~/.config exists
    mkdir -p "$HOME/.config"
    log "Prerequisites complete"
}

# ============================================================
# SECTION 2: Terminal Emulator — Ghostty
# ============================================================
section_terminal() {
    info "=== Section 2: Terminal Emulator ==="

    case "$OS" in
        macos)
            if [ -d "/Applications/Ghostty.app" ]; then
                log "Ghostty already installed"
            else
                info "Installing Ghostty..."
                brew install --cask ghostty
                log "Ghostty installed"
            fi
            ;;
        debian)
            # Ghostty provides a .deb or can be built from source
            if command -v ghostty &>/dev/null; then
                log "Ghostty already installed"
            else
                warn "Ghostty on Linux: install from https://ghostty.org/download"
                warn "  For Ubuntu/Debian, download the .deb from the releases page"
                warn "  Or build from source: https://ghostty.org/docs/install/build"
            fi
            ;;
        fedora)
            if command -v ghostty &>/dev/null; then
                log "Ghostty already installed"
            else
                info "Installing Ghostty via dnf copr..."
                sudo dnf copr enable -y pgdev/ghostty
                sudo dnf install -y ghostty
                log "Ghostty installed"
            fi
            ;;
        arch)
            if command -v ghostty &>/dev/null; then
                log "Ghostty already installed"
            else
                sudo pacman -S --noconfirm ghostty
                log "Ghostty installed"
            fi
            ;;
        *)
            warn "Ghostty: manual install required — see https://ghostty.org/download"
            ;;
    esac
}

# ============================================================
# SECTION 3: Font — Maple Mono NF
# ============================================================
section_font() {
    info "=== Section 3: Font — Maple Mono NF ==="

    # Check if already installed
    if fc-list 2>/dev/null | grep -qi "maple mono"; then
        log "Maple Mono NF already installed"
        return 0
    fi

    case "$OS" in
        macos)
            brew install --cask font-maple-mono-nf
            ;;
        debian|fedora|arch)
            # On Linux, try brew first, fall back to manual download
            if [[ "$PKG" == "brew" ]]; then
                brew install --cask font-maple-mono-nf
            else
                info "Installing Maple Mono NF manually..."
                local font_dir="$HOME/.local/share/fonts"
                mkdir -p "$font_dir"
                local tmpdir
                tmpdir=$(mktemp -d)
                local release_url
                release_url=$(curl -s https://api.github.com/repos/subframe7536/maple-font/releases/latest \
                    | grep "browser_download_url.*MapleMono-NF.*zip" \
                    | head -1 | cut -d '"' -f 4)
                if [ -n "$release_url" ]; then
                    curl -L "$release_url" -o "$tmpdir/maple-mono-nf.zip"
                    unzip -o "$tmpdir/maple-mono-nf.zip" -d "$font_dir"
                    fc-cache -fv
                    log "Maple Mono NF installed to $font_dir"
                else
                    err "Could not find Maple Mono NF release URL"
                fi
                rm -rf "$tmpdir"
            fi
            ;;
        *)
            warn "Font: manual install required — see https://github.com/subframe7536/maple-font/releases"
            ;;
    esac
}

# ============================================================
# SECTION 4: Shell Prompt — Starship
# ============================================================
section_prompt() {
    info "=== Section 4: Prompt — Starship ==="

    if command -v starship &>/dev/null; then
        log "Starship already installed ($(starship --version))"
        return 0
    fi

    case "$PKG" in
        brew)
            brew install starship
            ;;
        *)
            # Starship provides a universal install script
            info "Installing Starship via install script..."
            curl -sS https://starship.rs/install.sh | sh -s -- -y
            ;;
    esac

    log "Starship installed ($(starship --version))"
}

# ============================================================
# SECTION 5: Plugin Manager — Sheldon
# ============================================================
section_plugin_manager() {
    info "=== Section 5: Plugin Manager — Sheldon ==="

    if command -v sheldon &>/dev/null; then
        log "Sheldon already installed ($(sheldon --version))"
        return 0
    fi

    case "$PKG" in
        brew)
            brew install sheldon
            ;;
        *)
            cargo_install sheldon sheldon
            ;;
    esac

    log "Sheldon installed ($(sheldon --version))"
}

# ============================================================
# SECTION 6: CLI Tools
# ============================================================
section_cli_tools() {
    info "=== Section 6: CLI Tools ==="

    local brew_tools=(
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
    )

    # Map of binary name -> brew formula (where they differ)
    # Most match, but a few don't
    declare -A bin_to_formula=(
        [rg]=ripgrep
        [delta]=git-delta
        [tldr]=tealdeer
    )

    case "$PKG" in
        brew)
            info "Installing CLI tools via Homebrew..."
            brew install "${brew_tools[@]}"
            ;;
        apt)
            # On Debian/Ubuntu, some tools are in apt, others need cargo
            local apt_available=(bat fd-find ripgrep fzf btop direnv)
            local cargo_needed=(eza zoxide git-delta dust xh sd tealdeer lazygit)

            sudo apt update
            sudo apt install -y "${apt_available[@]}" || true

            for tool in "${cargo_needed[@]}"; do
                cargo_install "$tool" "$tool"
            done

            # Fix Debian naming: batcat -> bat, fdfind -> fd
            [ -f /usr/bin/batcat ] && ! command -v bat &>/dev/null && \
                sudo ln -sf /usr/bin/batcat /usr/local/bin/bat
            [ -f /usr/bin/fdfind ] && ! command -v fd &>/dev/null && \
                sudo ln -sf /usr/bin/fdfind /usr/local/bin/fd
            ;;
        dnf)
            local dnf_available=(bat fd-find ripgrep fzf btop direnv)
            sudo dnf install -y "${dnf_available[@]}" || true

            local cargo_needed=(eza zoxide git-delta dust xh sd tealdeer lazygit)
            for tool in "${cargo_needed[@]}"; do
                cargo_install "$tool" "$tool"
            done
            ;;
        pacman)
            sudo pacman -S --noconfirm \
                eza bat ripgrep fd zoxide fzf git-delta dust btop \
                xh sd tealdeer direnv lazygit || true
            ;;
    esac

    # fzf keybindings setup
    if [ -f "$(brew --prefix 2>/dev/null)/opt/fzf/install" ]; then
        "$(brew --prefix)/opt/fzf/install" --key-bindings --completion --no-update-rc --no-bash --no-fish
    elif [ -f /usr/share/fzf/key-bindings.zsh ]; then
        log "fzf keybindings available via system package"
    fi

    # tealdeer cache
    if command -v tldr &>/dev/null; then
        tldr --update || true
    fi

    # Verify
    local all_good=true
    for cmd in eza bat rg fd zoxide fzf delta dust btop xh sd tldr direnv lazygit; do
        if command -v "$cmd" &>/dev/null; then
            log "$cmd ✓"
        else
            warn "$cmd ✗ — not found"
            all_good=false
        fi
    done

    $all_good && log "All CLI tools installed" || warn "Some tools may need manual install"
}

# ============================================================
# SECTION 7: Version Control — jj + ecosystem
# ============================================================
section_vcs() {
    info "=== Section 7: Version Control — jj + ecosystem ==="

    # jj core
    if command -v jj &>/dev/null; then
        log "jj already installed ($(jj --version))"
    else
        case "$PKG" in
            brew)   brew install jj ;;
            *)      cargo_install jj jj-cli ;;
        esac
    fi

    # lazyjj (TUI)
    if command -v lazyjj &>/dev/null; then
        log "lazyjj already installed"
    else
        case "$PKG" in
            brew)
                brew install lazyjj 2>/dev/null || cargo_install lazyjj lazyjj
                ;;
            *)
                cargo_install lazyjj lazyjj
                ;;
        esac
    fi

    # jj-fzf (fzf-based interface)
    if command -v jj-fzf &>/dev/null || [ -d "$HOME/.jj-fzf" ]; then
        log "jj-fzf already available"
    else
        if ! brew install jj-fzf 2>/dev/null; then
            info "Installing jj-fzf via git clone..."
            git clone https://github.com/tim-janik/jj-fzf.git "$HOME/.jj-fzf"
            log "jj-fzf cloned to ~/.jj-fzf (add to PATH)"
        fi
    fi

    # gg (GUI — macOS only makes sense)
    if [[ "$OS" == "macos" ]]; then
        if [ -d "/Applications/GG.app" ] || command -v gg &>/dev/null; then
            log "gg already installed"
        else
            brew install --cask gg 2>/dev/null || cargo_install gg gg-cli
        fi
    else
        # On Linux, install CLI version
        if command -v gg &>/dev/null; then
            log "gg already installed"
        else
            cargo_install gg gg-cli
        fi
    fi
}

# ============================================================
# SECTION 8: Sheldon plugins config
# ============================================================
section_sheldon_config() {
    info "=== Section 8: Sheldon Config ==="

    mkdir -p "$HOME/.config/sheldon"

    cat > "$HOME/.config/sheldon/plugins.toml" << 'EOF'
shell = "zsh"

# --- Completions (load early) ---
[plugins.zsh-completions]
github = "zsh-users/zsh-completions"

# --- Core plugins ---
[plugins.zsh-autosuggestions]
github = "zsh-users/zsh-autosuggestions"

[plugins.zsh-syntax-highlighting]
github = "zsh-users/zsh-syntax-highlighting"

[plugins.zsh-history-substring-search]
github = "zsh-users/zsh-history-substring-search"

# --- fzf-tab (replaces default tab completion with fzf) ---
[plugins.fzf-tab]
github = "Aloxaf/fzf-tab"
EOF

    sheldon lock
    log "Sheldon plugins configured and locked"
}

# ============================================================
# SECTION 9: Starship config
# ============================================================
section_starship_config() {
    info "=== Section 9: Starship Config ==="

    mkdir -p "$HOME/.config"

    cat > "$HOME/.config/starship.toml" << 'EOF'
# Minimal, fast prompt with git + directory awareness
format = """
$directory\
$git_branch\
$git_status\
$character"""

[directory]
truncation_length = 3
truncate_to_repo = true

[git_branch]
format = "[$branch]($style) "
style = "bold purple"

[git_status]
format = '([$all_status$ahead_behind]($style) )'
style = "bold red"

[character]
success_symbol = "[❯](bold green)"
error_symbol = "[❯](bold red)"
EOF

    log "Starship config written to ~/.config/starship.toml"
}

# ============================================================
# SECTION 10: Ghostty config
# ============================================================
section_ghostty_config() {
    info "=== Section 10: Ghostty Config ==="

    mkdir -p "$HOME/.config/ghostty"

    cat > "$HOME/.config/ghostty/config" << 'EOF'
# Font
font-family = "Maple Mono NF"
font-size = 14

# Theme
theme = catppuccin-mocha

# Window
window-padding-x = 12
window-padding-y = 8
window-decoration = true

# Behavior
copy-on-select = clipboard
mouse-hide-while-typing = true
confirm-close-surface = false
shell-integration = zsh

# Scrollback
scrollback-limit = 10000
EOF

    # macOS-specific settings
    if [[ "$OS" == "macos" ]]; then
        cat >> "$HOME/.config/ghostty/config" << 'EOF'

# macOS-specific
macos-titlebar-style = hidden

# Keybindings for splits (Cmd keys — macOS only)
keybind = cmd+d=new_split:right
keybind = cmd+shift+d=new_split:down
keybind = cmd+shift+enter=toggle_split_zoom
keybind = cmd+alt+left=goto_split:left
keybind = cmd+alt+right=goto_split:right
keybind = cmd+alt+up=goto_split:top
keybind = cmd+alt+down=goto_split:bottom
EOF
    else
        cat >> "$HOME/.config/ghostty/config" << 'EOF'

# Keybindings for splits (Ctrl keys — Linux)
keybind = ctrl+shift+d=new_split:right
keybind = ctrl+shift+e=new_split:down
keybind = ctrl+shift+enter=toggle_split_zoom
keybind = ctrl+alt+left=goto_split:left
keybind = ctrl+alt+right=goto_split:right
keybind = ctrl+alt+up=goto_split:top
keybind = ctrl+alt+down=goto_split:bottom
EOF
    fi

    log "Ghostty config written to ~/.config/ghostty/config"
}

# ============================================================
# SECTION 11: .zshrc
# ============================================================
section_zshrc() {
    info "=== Section 11: .zshrc ==="

    cat > "$HOME/.zshrc" << 'ZSHRC'
# ============================================================
# ZSH Config — Terminal QOL Setup
# ============================================================

# --- Bun ---
[ -f "$HOME/.local/bin/env" ] && . "$HOME/.local/bin/env"
[ -s "$HOME/.bun/_bun" ] && source "$HOME/.bun/_bun"
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# --- Homebrew ---
export HOMEBREW_NO_ENV_HINTS=1

# --- Cargo ---
[ -d "$HOME/.cargo/bin" ] && export PATH="$HOME/.cargo/bin:$PATH"

# --- jj-fzf ---
[ -d "$HOME/.jj-fzf" ] && export PATH="$HOME/.jj-fzf:$PATH"

# --- Sheldon (plugin manager) ---
eval "$(sheldon source)"

# --- Starship prompt ---
eval "$(starship init zsh)"

# --- Zoxide (smart cd) ---
eval "$(zoxide init zsh)"

# --- direnv ---
eval "$(direnv hook zsh)"

# --- fzf ---
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# --- fzf config ---
export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'
export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
export FZF_ALT_C_COMMAND='fd --type d --hidden --follow --exclude .git'
export FZF_DEFAULT_OPTS='
  --height 40%
  --layout=reverse
  --border
  --color=bg+:#313244,bg:#1e1e2e,spinner:#f5e0dc,hl:#f38ba8
  --color=fg:#cdd6f4,header:#f38ba8,info:#cba6f7,pointer:#f5e0dc
  --color=marker:#b4befe,fg+:#cdd6f4,prompt:#cba6f7,hl+:#f38ba8
'

# --- History ---
HISTSIZE=50000
SAVEHIST=50000
HISTFILE=~/.zsh_history
setopt EXTENDED_HISTORY
setopt HIST_EXPIRE_DUPS_FIRST
setopt HIST_IGNORE_DUPS
setopt HIST_IGNORE_SPACE
setopt HIST_VERIFY
setopt SHARE_HISTORY
setopt INC_APPEND_HISTORY

# --- Key bindings ---
bindkey '^[[A' history-substring-search-up
bindkey '^[[B' history-substring-search-down

# --- Aliases: CLI tool replacements ---
alias ls='eza --icons --group-directories-first'
alias ll='eza --icons --group-directories-first -la'
alias lt='eza --icons --tree --level=2'
alias cat='bat --paging=never'
alias grep='rg'
alias find='fd'
alias du='dust'
alias top='btop'
alias sed='sd'
alias diff='delta'
alias lg='lazygit'
alias lj='lazyjj'

# --- jj aliases ---
alias js='jj status'
alias jl='jj log'
alias jd='jj diff'
alias jn='jj new'
alias jc='jj commit'
alias jds='jj describe'

# --- delta / bat theme ---
export DELTA_PAGER="less -R"
export BAT_THEME="Catppuccin Mocha"

# --- Machine-local config (not in dotfiles repo) ---
[ -f "$HOME/.zshrc.local" ] && source "$HOME/.zshrc.local"
ZSHRC

    log ".zshrc written (put secrets/machine-specific config in ~/.zshrc.local)"
}

# ============================================================
# SECTION 12: Git + Delta config
# ============================================================
section_git_config() {
    info "=== Section 12: Git + Delta Config ==="

    git config --global core.pager delta
    git config --global interactive.diffFilter "delta --color-only"
    git config --global delta.navigate true
    git config --global delta.dark true
    git config --global delta.syntax-theme "Catppuccin Mocha"
    git config --global delta.side-by-side true
    git config --global delta.line-numbers true
    git config --global merge.conflictstyle diff3
    git config --global diff.colorMoved default

    log "Git configured to use delta"
}

# ============================================================
# SECTION 13: jj config
# ============================================================
section_jj_config() {
    info "=== Section 13: jj Config ==="

    mkdir -p "$HOME/.config/jj"

    # Only write if not already configured (preserve user's email)
    if [ ! -f "$HOME/.config/jj/config.toml" ]; then
        local jj_name jj_email
        jj_name=$(git config --global user.name 2>/dev/null || echo "")
        jj_email=$(git config --global user.email 2>/dev/null || echo "")

        cat > "$HOME/.config/jj/config.toml" << EOF
[user]
name = "${jj_name}"
email = "${jj_email}"

[ui]
default-command = "log"
diff.format = "git"
pager = "delta"

[git]
auto-local-bookmark = false
EOF
        log "jj config written (using git user: $jj_name <$jj_email>)"
    else
        log "jj config already exists, skipping"
    fi
}

# ============================================================
# SECTION 14: Verify
# ============================================================
section_verify() {
    info "=== Section 14: Verification ==="

    local failures=0

    for cmd in eza bat rg fd zoxide fzf delta dust btop xh sd tldr direnv lazygit jj lazyjj; do
        if command -v "$cmd" &>/dev/null; then
            log "$cmd ✓"
        else
            warn "$cmd ✗ — not found"
            ((failures++)) || true
        fi
    done

    # jj-fzf (not a standard binary)
    if [ -x "$HOME/.jj-fzf/jj-fzf" ] || command -v jj-fzf &>/dev/null; then
        log "jj-fzf ✓"
    else
        warn "jj-fzf ✗ — not found"
        ((failures++)) || true
    fi

    # Config files
    for f in \
        "$HOME/.config/sheldon/plugins.toml" \
        "$HOME/.config/starship.toml" \
        "$HOME/.config/ghostty/config" \
        "$HOME/.config/jj/config.toml" \
        "$HOME/.zshrc"; do
        if [ -f "$f" ]; then
            log "Config: $f ✓"
        else
            warn "Config: $f ✗ — missing"
            ((failures++)) || true
        fi
    done

    # Font
    if fc-list 2>/dev/null | grep -qi "maple mono" || \
       system_profiler SPFontsDataType 2>/dev/null | grep -qi "maple mono"; then
        log "Font: Maple Mono NF ✓"
    else
        warn "Font: Maple Mono NF ✗ — not found"
        ((failures++)) || true
    fi

    if [ "$failures" -eq 0 ]; then
        log "All checks passed!"
    else
        warn "$failures check(s) failed — review warnings above"
    fi
}

# ============================================================
# Main
# ============================================================
main() {
    echo ""
    info "Terminal QOL Provisioning Script"
    info "================================"
    echo ""

    section_prerequisites
    section_terminal
    section_font
    section_prompt
    section_plugin_manager
    section_cli_tools
    section_vcs
    section_sheldon_config
    section_starship_config
    section_ghostty_config
    section_zshrc
    section_git_config
    section_jj_config
    section_verify

    echo ""
    log "Provisioning complete! Open Ghostty and enjoy."
    log "Log saved to: $LOG_FILE"
}

main "$@"
