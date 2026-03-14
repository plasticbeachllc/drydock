# /// script
# requires-python = ">=3.11"
# ///
"""Dotfiles provisioning script — renders templates, creates symlinks, provisions secrets."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
RENDERED_DIR = Path.home() / ".config" / "dotfiles" / "rendered"
IDENTITY_FILE = Path.home() / ".config" / "dotfiles" / "identity.json"
GENERATED_DIR = Path.home() / ".config" / "dotfiles"

# Platform detection
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

# Placeholders that setup.py will substitute with real values
PLACEHOLDERS = ["__NAME__", "__EMAIL__"]

# Secrets that can be manually provided during setup if 1Password isn't available.
# The canonical op:// URIs live in shell/zshrc (the runtime source of truth).
MANUAL_SECRETS = [
    "OPENAI_API_KEY",
]

ZSHRC_LOCAL = Path.home() / ".zshrc.local"

# 1Password team account — sign-in address (not secret, just a subdomain)
OP_TEAM_ADDRESS = "plasticbeach.1password.com"

# 1Password SSH agent socket path (platform-dependent)
if IS_MACOS:
    OP_SSH_AGENT_SOCK = (
        Path.home()
        / "Library"
        / "Group Containers"
        / "2BUA8C4S2C.com.1password"
        / "t"
        / "agent.sock"
    )
else:
    OP_SSH_AGENT_SOCK = Path.home() / ".1password" / "agent.sock"

# Symlink mapping: repo template path -> target symlink location
# (ghostty theme entry is added dynamically based on selected theme)
SYMLINK_MAP = {
    "shell/zshrc":          Path.home() / ".zshrc",
    "shell/zshenv":         Path.home() / ".zshenv",
    "shell/zprofile":       Path.home() / ".zprofile",
    "git/gitconfig":        Path.home() / ".gitconfig",
    "git/ignore":           Path.home() / ".config" / "git" / "ignore",
    "jj/config.toml":       Path.home() / ".config" / "jj" / "config.toml",
    "gh/config.yml":        Path.home() / ".config" / "gh" / "config.yml",
    "sheldon/plugins.toml": Path.home() / ".config" / "sheldon" / "plugins.toml",
    "starship/starship.toml": Path.home() / ".config" / "starship.toml",
    "ghostty/config":       Path.home() / ".config" / "ghostty" / "config",
    "nvim":                 Path.home() / ".config" / "nvim",
    "claude/statusline.sh": Path.home() / ".claude" / "statusline.sh",
    "ssh/config":           Path.home() / ".ssh" / "config",
}

# App icon overrides: {app_path: icon_source_path} — macOS only
APP_ICON_MAP = {
    "/Applications/Ghostty.app": (
        "/System/Applications/Utilities/Terminal.app"
        "/Contents/Resources/Terminal.icns"
    ),
}

# Claude Code settings to merge into ~/.claude/settings.json
CLAUDE_SETTINGS_DIR = Path.home() / ".claude"
CLAUDE_SETTINGS = {
    "statusLine": {
        "type": "command",
        "command": str(Path.home() / ".claude" / "statusline.sh"),
        "padding": 1,
    },
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Dotfiles provisioner")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        default=bool(os.environ.get("CI")),
        help="Run without prompts (reads from env vars / identity.json). "
             "Also enabled by CI=1 env var.",
    )
    return parser.parse_args(argv)


def load_identity() -> dict[str, str]:
    """Load saved identity or return empty dict."""
    if IDENTITY_FILE.exists():
        return json.loads(IDENTITY_FILE.read_text())
    return {}


def save_identity(identity: dict[str, str]) -> None:
    """Persist identity to disk."""
    IDENTITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    IDENTITY_FILE.write_text(json.dumps(identity, indent=2) + "\n")


def prompt_identity(non_interactive: bool = False) -> dict[str, str]:
    """Prompt for identity values, using saved values as defaults.

    In non-interactive mode, reads from DOTFILES_NAME / DOTFILES_EMAIL env vars
    or falls back to a previously saved identity.json.
    """
    identity = load_identity()

    if non_interactive:
        env_map = {"__NAME__": "DOTFILES_NAME", "__EMAIL__": "DOTFILES_EMAIL"}
        for key in PLACEHOLDERS:
            env_val = os.environ.get(env_map[key], "")
            if env_val:
                identity[key] = env_val
            elif key not in identity:
                print(f"Error: {env_map[key]} env var is required in non-interactive mode.")
                sys.exit(1)
        save_identity(identity)
        return identity

    for key in PLACEHOLDERS:
        label = key.strip("_").lower()
        default = identity.get(key, "")
        prompt = f"  {label}"
        if default:
            prompt += f" [{default}]"
        prompt += ": "

        value = input(prompt).strip()
        if not value:
            if default:
                value = default
            else:
                print(f"Error: {label} is required.")
                sys.exit(1)
        identity[key] = value

    save_identity(identity)
    return identity


def prompt_theme(non_interactive: bool = False) -> tuple[str, dict]:
    """Prompt for theme selection, returns (theme_key, theme_dict).

    In non-interactive mode, uses the previously saved theme or defaults to the first.
    """
    # Import here so the module isn't required at top level
    sys.path.insert(0, str(REPO_ROOT / "themes"))
    from generate import load_themes

    themes = load_themes()
    theme_keys = list(themes.keys())

    # Load previous selection
    identity = load_identity()
    prev = identity.get("__THEME__", "")
    default_idx = 0
    for i, key in enumerate(theme_keys):
        if key == prev:
            default_idx = i
            break

    if non_interactive:
        idx = default_idx
    else:
        for i, key in enumerate(theme_keys):
            t = themes[key]
            marker = "*" if key == prev else " "
            print(f"  {marker}[{i + 1}] {t['name']} — {t['tagline']}")

        prompt = f"  choice [{default_idx + 1}]: "
        choice = input(prompt).strip()
        if not choice:
            idx = default_idx
        else:
            try:
                idx = int(choice) - 1
                if not 0 <= idx < len(theme_keys):
                    raise ValueError
            except ValueError:
                print("Invalid choice.")
                sys.exit(1)

    selected_key = theme_keys[idx]
    selected = themes[selected_key]

    # Save selection
    identity["__THEME__"] = selected_key
    save_identity(identity)

    return selected_key, selected


def generate_theme_files(theme_key: str, theme: dict) -> dict[str, str]:
    """Generate all theme-dependent files. Returns placeholder dict for templates."""
    sys.path.insert(0, str(REPO_ROOT / "themes"))
    from generate import (
        btop_theme,
        ghostty_theme,
        lazygit_config,
        nvim_dashboard_colors,
        nvim_theme_colors,
        theme_placeholders,
    )

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    # Ghostty theme file — written to rendered dir, symlinked dynamically
    ghostty_theme_dir = RENDERED_DIR / "ghostty" / "themes"
    ghostty_theme_dir.mkdir(parents=True, exist_ok=True)
    ghostty_theme_path = ghostty_theme_dir / theme["name"]
    ghostty_theme_path.write_text(ghostty_theme(theme))
    print(f"  generated ghostty theme: {theme['name']}")

    # Add dynamic ghostty theme symlink
    target = Path.home() / ".config" / "ghostty" / "themes" / theme["name"]
    SYMLINK_MAP[f"__generated_ghostty_theme__"] = (ghostty_theme_path, target)

    # Neovim catppuccin colors
    nvim_colors_path = GENERATED_DIR / "theme_colors.lua"
    nvim_colors_path.write_text(nvim_theme_colors(theme))
    print(f"  generated nvim theme colors")

    # Neovim dashboard colors
    dash_path = GENERATED_DIR / "dashboard_colors.lua"
    dash_path.write_text(nvim_dashboard_colors(theme))
    print(f"  generated nvim dashboard colors")

    # Lazygit config
    lazygit_dir = Path.home() / ".config" / "lazygit"
    lazygit_dir.mkdir(parents=True, exist_ok=True)
    lazygit_path = lazygit_dir / "config.yml"
    lazygit_path.write_text(lazygit_config(theme))
    print(f"  generated lazygit config")

    # btop theme
    btop_theme_dir = Path.home() / ".config" / "btop" / "themes"
    btop_theme_dir.mkdir(parents=True, exist_ok=True)
    btop_theme_path = btop_theme_dir / f"{theme['name']}.theme"
    btop_theme_path.write_text(btop_theme(theme))
    print(f"  generated btop theme: {theme['name']}")

    # Set btop to use the theme
    btop_conf = Path.home() / ".config" / "btop" / "btop.conf"
    _set_btop_color_theme(btop_conf, theme["name"])

    # Platform-specific placeholders (SSH agent socket path)
    placeholders = theme_placeholders(theme)
    placeholders["__OP_SSH_AGENT_SOCK__"] = str(OP_SSH_AGENT_SOCK)
    return placeholders


def _set_btop_color_theme(conf_path: Path, theme_name: str) -> None:
    """Set color_theme in btop.conf, creating or updating as needed."""
    target_line = f'color_theme = "{theme_name}"'
    if conf_path.exists():
        lines = conf_path.read_text().splitlines()
        for i, line in enumerate(lines):
            if line.startswith("color_theme"):
                lines[i] = target_line
                conf_path.write_text("\n".join(lines) + "\n")
                return
        # Key not found — append
        lines.append(target_line)
        conf_path.write_text("\n".join(lines) + "\n")
    else:
        conf_path.write_text(target_line + "\n")


def render_template(src: Path, subs: dict[str, str]) -> str:
    """Read a template file and substitute placeholders."""
    content = src.read_text()
    # Sort by key length descending to avoid partial matches
    # (e.g. __THEME_NAME__ must be replaced before __NAME__)
    for placeholder, value in sorted(subs.items(), key=lambda x: -len(x[0])):
        content = content.replace(placeholder, value)
    return content


def needs_templating(src: Path, all_placeholders: list[str]) -> bool:
    """Check if a file contains any placeholders."""
    if src.is_dir():
        return False
    content = src.read_text()
    return any(p in content for p in all_placeholders)


SSH_RESTRICTED_DIRS = {Path.home() / ".ssh"}


def create_symlink(source: Path, target: Path) -> str:
    """Create a symlink, handling existing files. Returns status string."""
    target.parent.mkdir(parents=True, exist_ok=True)
    # SSH requires ~/.ssh/ to be 0700
    if target.parent in SSH_RESTRICTED_DIRS:
        target.parent.chmod(0o700)

    if target.is_symlink():
        if target.resolve() == source.resolve():
            return "skipped (already linked)"
        # Wrong symlink — remove and relink
        target.unlink()
        target.symlink_to(source)
        return "relinked (was pointing elsewhere)"

    if target.exists():
        # Back up existing file
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup = target.with_name(f"{target.name}.bak.{timestamp}")
        target.rename(backup)
        target.symlink_to(source)
        return f"linked (backed up original to {backup.name})"

    target.symlink_to(source)
    return "linked"


def op_available() -> bool:
    """Check if 1Password CLI is installed."""
    try:
        subprocess.run(["op", "--version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def op_authenticated() -> bool:
    """Check if 1Password CLI is signed in."""
    try:
        subprocess.run(["op", "whoami"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def op_signin() -> bool:
    """Interactive 1Password sign-in. Returns True if successful."""
    print("  Signing in to 1Password...")
    result = subprocess.run(["op", "signin"])
    if result.returncode == 0 and op_authenticated():
        print("  Signed in successfully.")
        return True
    print("  Sign-in failed.")
    return False


def op_account_staged() -> bool:
    """Check if the team 1Password account is already added to the CLI."""
    try:
        result = subprocess.run(
            ["op", "account", "list", "--format=json"],
            capture_output=True, text=True, check=True,
        )
        accounts = json.loads(result.stdout)
        return any(a.get("url") == OP_TEAM_ADDRESS for a in accounts)
    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError):
        return False


def op_stage_account(email: str) -> bool:
    """Pre-register the team 1Password account so signin only needs master password."""
    print(f"  Adding {OP_TEAM_ADDRESS} account for {email}...")
    result = subprocess.run([
        "op", "account", "add",
        "--address", OP_TEAM_ADDRESS,
        "--email", email,
    ])
    return result.returncode == 0


def check_op_ssh_agent() -> None:
    """Check whether the 1Password SSH agent socket is available."""
    if OP_SSH_AGENT_SOCK.exists():
        print("  1Password SSH agent: active")
    else:
        print("  1Password SSH agent: not found")
        if IS_MACOS:
            print("    -> Open 1Password > Settings > Developer > enable 'Use the SSH agent'")
        else:
            print("    -> Ensure 1Password is configured with SSH agent at ~/.1password/agent.sock")


def set_default_browser() -> None:
    """Set Chrome as default browser (platform-dependent)."""
    if IS_MACOS:
        chrome = Path("/Applications/Google Chrome.app")
        if not chrome.exists():
            print("  skipped (Chrome not installed)")
            return
        result = subprocess.run(
            ["open", "-a", "Google Chrome", "--args", "--make-default-browser"],
            capture_output=True,
        )
        if result.returncode == 0:
            print("  Chrome set as default browser (confirm in the dialog if prompted)")
        else:
            print("  failed to set default browser")
    elif IS_LINUX:
        if not shutil.which("google-chrome") and not shutil.which("google-chrome-stable"):
            print("  skipped (Chrome not installed)")
            return
        if not shutil.which("xdg-settings"):
            print("  skipped (xdg-settings not available)")
            return
        result = subprocess.run(
            ["xdg-settings", "set", "default-web-browser", "google-chrome.desktop"],
            capture_output=True,
        )
        if result.returncode == 0:
            print("  Chrome set as default browser")
        else:
            print("  failed to set default browser")
    else:
        print(f"  skipped (unsupported platform: {sys.platform})")


def _ensure_zshrc_local_permissions() -> None:
    """Ensure ~/.zshrc.local has restrictive permissions (0600)."""
    if ZSHRC_LOCAL.exists():
        ZSHRC_LOCAL.chmod(0o600)


def write_secret_to_zshrc_local(name: str, value: str) -> None:
    """Write an export line to ~/.zshrc.local, replacing if it already exists."""
    marker = f"export {name}="
    if ZSHRC_LOCAL.exists():
        content = ZSHRC_LOCAL.read_text()
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if line.startswith(marker):
                lines[i] = f'export {name}="{value}"'
                ZSHRC_LOCAL.write_text("\n".join(lines) + "\n")
                _ensure_zshrc_local_permissions()
                return
        with ZSHRC_LOCAL.open("a") as f:
            f.write(f'export {name}="{value}"\n')
    else:
        ZSHRC_LOCAL.write_text(f'export {name}="{value}"\n')
    _ensure_zshrc_local_permissions()


def provision_secrets(identity: dict[str, str]) -> None:
    """Interactive secret provisioning: 1Password account staging + auth.

    Stages the team 1Password account so the user only needs their master
    password (or Touch ID) to authenticate. Falls back to manual entry
    for environments without 1Password.
    """
    print("1Password:\n")

    has_op = op_available()

    if not has_op:
        print("  1Password CLI not installed.")
        print("  Secrets defined in zshrc will be unavailable unless set manually.\n")
        print("  [1] Enter secrets manually (written to ~/.zshrc.local)")
        print("  [2] Skip for now")
        choice = input("  choice: ").strip()
        if choice == "1":
            print()
            for name in MANUAL_SECRETS:
                value = input(f"  {name}: ").strip()
                if value:
                    write_secret_to_zshrc_local(name, value)
                    print(f"    -> written to ~/.zshrc.local")
                else:
                    print(f"    -> skipped")
        else:
            print("  Skipped.")
        print()
        return

    print("  1Password CLI detected.")

    # Stage team account if not already added
    if not op_account_staged():
        email = identity.get("__EMAIL__", "")
        if email:
            op_stage_account(email)
        else:
            print("  warning: no email in identity, skipping account staging")

    # Authenticate if needed
    if op_authenticated():
        print("  Already authenticated — zshrc will fetch secrets at runtime.")
    else:
        print("  No active CLI session.\n")
        print("  [1] Authenticate now (Touch ID if 1Password app is open, or master password)")
        print("  [2] Enter secrets manually (written to ~/.zshrc.local)")
        print("  [3] Skip for now")
        choice = input("  choice: ").strip()

        if choice == "1":
            if op_signin():
                print("  Authenticated — secrets will be fetched live via op:// URIs.")
            else:
                print("  Auth failed. Re-run setup.py or set secrets in ~/.zshrc.local.")
        elif choice == "2":
            print()
            for name in MANUAL_SECRETS:
                value = input(f"  {name}: ").strip()
                if value:
                    write_secret_to_zshrc_local(name, value)
                    print(f"    -> written to ~/.zshrc.local")
                else:
                    print(f"    -> skipped")
        else:
            print("  Skipped.")

    # Check SSH agent status
    print()
    check_op_ssh_agent()
    print()


def configure_claude_code() -> None:
    """Merge managed keys into ~/.claude/settings.json without clobbering user state."""
    settings_file = CLAUDE_SETTINGS_DIR / "settings.json"
    CLAUDE_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)

    existing = {}
    if settings_file.exists():
        try:
            existing = json.loads(settings_file.read_text())
        except json.JSONDecodeError:
            print(f"  warning: {settings_file} contains invalid JSON, overwriting")
            existing = {}

    changed = False
    for key, value in CLAUDE_SETTINGS.items():
        if existing.get(key) != value:
            existing[key] = value
            changed = True

    if changed:
        settings_file.write_text(json.dumps(existing, indent=2) + "\n")
        print("  updated ~/.claude/settings.json")
    else:
        print("  ~/.claude/settings.json already up to date")


def configure_app_icons() -> None:
    """Set custom app icons declaratively using fileicon (macOS only)."""
    if not IS_MACOS:
        print("  skipped (macOS only)")
        return

    if not shutil.which("fileicon"):
        print("  skipped (fileicon not installed — run bootstrap.sh first)")
        return

    changed = False
    for app_path, icon_path in APP_ICON_MAP.items():
        app = Path(app_path)
        icon = Path(icon_path)
        label = app.stem

        if not app.exists():
            print(f"  {label:20s} skipped (not installed)")
            continue

        if not icon.exists():
            print(f"  {label:20s} skipped (icon source missing: {icon})")
            continue

        result = subprocess.run(
            ["fileicon", "test", str(app)],
            capture_output=True,
        )
        if result.returncode == 0:
            print(f"  {label:20s} skipped (custom icon already set)")
            continue

        result = subprocess.run(
            ["fileicon", "set", str(app), str(icon)],
            capture_output=True,
        )
        if result.returncode == 0:
            print(f"  {label:20s} set ({icon.name})")
            changed = True
        else:
            stderr = result.stderr.decode().strip()
            print(f"  {label:20s} failed ({stderr})")

    if changed:
        subprocess.run(["killall", "Dock"], capture_output=True)


def open_url(path: str) -> None:
    """Open a file or URL using the platform-appropriate command."""
    if IS_MACOS:
        subprocess.run(["open", path])
    elif IS_LINUX:
        subprocess.run(["xdg-open", path], stderr=subprocess.DEVNULL)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    non_interactive = args.non_interactive

    print("Dotfiles provisioning\n")
    if non_interactive:
        print("  (non-interactive mode)\n")

    # Step 1: Identity
    print("Identity (stored in ~/.config/dotfiles/identity.json):")
    identity = prompt_identity(non_interactive=non_interactive)
    print()

    # Step 2: Theme
    print("Theme:\n")
    if not non_interactive:
        gallery_script = REPO_ROOT / "themes" / "build_gallery.py"
        gallery_html = REPO_ROOT / "themes" / "gallery.html"
        if gallery_script.exists():
            subprocess.run([sys.executable, str(gallery_script)], capture_output=True)
            if gallery_html.exists():
                choice = input("  press p to preview theme gallery in browser, or Enter to skip: ").strip().lower()
                if choice == "p":
                    open_url(str(gallery_html))
                print()
    theme_key, theme = prompt_theme(non_interactive=non_interactive)
    print(f"\n  Selected: {theme['name']}\n")
    print("Generating theme configs:\n")
    theme_subs = generate_theme_files(theme_key, theme)
    print()

    # Merge all substitutions: identity + theme placeholders
    all_subs = {**identity, **theme_subs}
    all_placeholder_keys = list(all_subs.keys())

    # Step 3: Symlinks
    print("Symlinks:\n")
    RENDERED_DIR.mkdir(parents=True, exist_ok=True)

    for repo_rel, target_or_tuple in SYMLINK_MAP.items():
        # Handle dynamically generated files (stored as tuples)
        if isinstance(target_or_tuple, tuple):
            source, target = target_or_tuple
            status = create_symlink(source, target)
            print(f"  {status:40s} {target} -> {source}")
            continue

        target = target_or_tuple
        src = REPO_ROOT / repo_rel
        if not src.exists():
            print(f"  MISSING  {repo_rel} (skipped)")
            continue

        if needs_templating(src, all_placeholder_keys):
            rendered = RENDERED_DIR / repo_rel
            rendered.parent.mkdir(parents=True, exist_ok=True)
            rendered.write_text(render_template(src, all_subs))
            # Preserve executable bit from source
            src_mode = src.stat().st_mode
            rendered.chmod(src_mode & 0o7777)
            status = create_symlink(rendered, target)
            print(f"  {status:40s} {target} -> {rendered}")
        else:
            status = create_symlink(src, target)
            print(f"  {status:40s} {target} -> {src}")

    print()

    # Step 4: Claude Code
    print("Claude Code:\n")
    configure_claude_code()
    print()

    # Step 5: App Icons (macOS only)
    print("App Icons:\n")
    configure_app_icons()
    print()

    # Step 6: Default Browser
    print("Default Browser:\n")
    set_default_browser()
    print()

    # Step 7: 1Password & Secrets
    if non_interactive:
        print("1Password:\n")
        print("  skipped (non-interactive mode)\n")
    else:
        provision_secrets(identity)

    print("Done.")


if __name__ == "__main__":
    main()
