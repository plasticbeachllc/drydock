# /// script
# requires-python = ">=3.10"
# ///
"""Dotfiles provisioning script — renders templates, creates symlinks, provisions secrets."""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
RENDERED_DIR = Path.home() / ".config" / "dotfiles" / "rendered"
IDENTITY_FILE = Path.home() / ".config" / "dotfiles" / "identity.json"

# Placeholders that setup.py will substitute with real values
PLACEHOLDERS = ["__NAME__", "__EMAIL__"]

# Secrets that can be manually provided during setup if 1Password isn't available.
# The canonical op:// URIs live in shell/zshrc (the runtime source of truth).
MANUAL_SECRETS = [
    "OPENAI_API_KEY",
]

ZSHRC_LOCAL = Path.home() / ".zshrc.local"

# Symlink mapping: repo template path -> target symlink location
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
    "ghostty/themes/Plastic Beach Basic": Path.home() / ".config" / "ghostty" / "themes" / "Plastic Beach Basic",
    "nvim":                 Path.home() / ".config" / "nvim",
    "claude/statusline.sh": Path.home() / ".claude" / "statusline.sh",
}

# Claude Code settings to merge into ~/.claude/settings.json
CLAUDE_SETTINGS_DIR = Path.home() / ".claude"
CLAUDE_SETTINGS = {
    "statusLine": {
        "type": "command",
        "command": "~/.claude/statusline.sh",
        "padding": 2,
    },
}


def load_identity() -> dict[str, str]:
    """Load saved identity or return empty dict."""
    if IDENTITY_FILE.exists():
        return json.loads(IDENTITY_FILE.read_text())
    return {}


def save_identity(identity: dict[str, str]) -> None:
    """Persist identity to disk."""
    IDENTITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    IDENTITY_FILE.write_text(json.dumps(identity, indent=2) + "\n")


def prompt_identity() -> dict[str, str]:
    """Prompt for identity values, using saved values as defaults."""
    identity = load_identity()

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


def render_template(src: Path, identity: dict[str, str]) -> str:
    """Read a template file and substitute placeholders."""
    content = src.read_text()
    for placeholder, value in identity.items():
        content = content.replace(placeholder, value)
    return content


def needs_templating(src: Path) -> bool:
    """Check if a file contains any placeholders."""
    if src.is_dir():
        return False
    content = src.read_text()
    return any(p in content for p in PLACEHOLDERS)


def create_symlink(source: Path, target: Path) -> str:
    """Create a symlink, handling existing files. Returns status string."""
    target.parent.mkdir(parents=True, exist_ok=True)

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
                return
        with ZSHRC_LOCAL.open("a") as f:
            f.write(f'export {name}="{value}"\n')
    else:
        ZSHRC_LOCAL.write_text(f'export {name}="{value}"\n')


def provision_secrets() -> None:
    """Interactive secret provisioning: 1Password auth or manual entry.

    The op:// URIs live in shell/zshrc — this step just ensures the user
    is either authenticated with `op` (so zshrc can fetch at runtime) or
    has provided manual fallback values in ~/.zshrc.local.
    """
    print("Secrets:\n")

    has_op = op_available()

    if has_op:
        print("  1Password CLI detected.")
        if op_authenticated():
            print("  Already authenticated — zshrc will fetch secrets at runtime.")
            print()
            return
        print("  Not currently signed in.\n")
        print("  [1] Sign in to 1Password now (secrets fetched live each shell session)")
        print("  [2] Enter secrets manually (written to ~/.zshrc.local)")
        print("  [3] Skip for now")
    else:
        print("  1Password CLI not installed.")
        print("  Secrets defined in zshrc will be unavailable unless set manually.\n")
        print("  [1] Enter secrets manually (written to ~/.zshrc.local)")
        print("  [2] Skip for now")

    choice = input("  choice: ").strip()

    if has_op and choice == "1":
        if op_signin():
            print("  Authenticated — zshrc will fetch secrets at runtime.")
        else:
            print("  Sign-in failed. You can re-run setup.py or set secrets in ~/.zshrc.local.")
        print()
        return

    manual = (has_op and choice == "2") or (not has_op and choice == "1")
    if manual:
        print()
        for name in MANUAL_SECRETS:
            value = input(f"  {name}: ").strip()
            if value:
                write_secret_to_zshrc_local(name, value)
                print(f"    -> written to ~/.zshrc.local")
            else:
                print(f"    -> skipped")
        print()
        return

    print("  Skipped.")
    print()


def configure_claude_code() -> None:
    """Merge managed keys into ~/.claude/settings.json without clobbering user state."""
    settings_file = CLAUDE_SETTINGS_DIR / "settings.json"
    CLAUDE_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)

    existing = {}
    if settings_file.exists():
        existing = json.loads(settings_file.read_text())

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


def main() -> None:
    print("Dotfiles provisioning\n")

    # Step 1: Identity
    print("Identity (stored in ~/.config/dotfiles/identity.json):")
    identity = prompt_identity()
    print()

    # Step 2: Symlinks
    print("Symlinks:\n")
    RENDERED_DIR.mkdir(parents=True, exist_ok=True)

    for repo_rel, target in SYMLINK_MAP.items():
        src = REPO_ROOT / repo_rel
        if not src.exists():
            print(f"  MISSING  {repo_rel} (skipped)")
            continue

        if needs_templating(src):
            rendered = RENDERED_DIR / repo_rel
            rendered.parent.mkdir(parents=True, exist_ok=True)
            rendered.write_text(render_template(src, identity))
            status = create_symlink(rendered, target)
            print(f"  {status:40s} {target} -> {rendered}")
        else:
            status = create_symlink(src, target)
            print(f"  {status:40s} {target} -> {src}")

    print()

    # Step 3: Claude Code
    print("Claude Code:\n")
    configure_claude_code()
    print()

    # Step 4: Secrets
    provision_secrets()

    print("Done.")


if __name__ == "__main__":
    main()
