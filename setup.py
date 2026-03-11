# /// script
# requires-python = ">=3.10"
# ///
"""Dotfiles provisioning script — renders templates and creates symlinks."""

import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
RENDERED_DIR = Path.home() / ".config" / "dotfiles" / "rendered"
IDENTITY_FILE = Path.home() / ".config" / "dotfiles" / "identity.json"

# Placeholders that setup.py will substitute with real values
PLACEHOLDERS = ["__NAME__", "__EMAIL__"]

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


def main() -> None:
    print("Dotfiles provisioning\n")

    # Prompt for identity
    print("Identity (stored in ~/.config/dotfiles/identity.json):")
    identity = prompt_identity()
    print()

    # Render and symlink
    RENDERED_DIR.mkdir(parents=True, exist_ok=True)

    for repo_rel, target in SYMLINK_MAP.items():
        src = REPO_ROOT / repo_rel
        if not src.exists():
            print(f"  MISSING  {repo_rel} (skipped)")
            continue

        if needs_templating(src):
            # Render to rendered dir, symlink from there
            rendered = RENDERED_DIR / repo_rel
            rendered.parent.mkdir(parents=True, exist_ok=True)
            rendered.write_text(render_template(src, identity))
            status = create_symlink(rendered, target)
            print(f"  {status:40s} {target} -> {rendered}")
        else:
            # No placeholders — symlink directly to repo
            status = create_symlink(src, target)
            print(f"  {status:40s} {target} -> {src}")

    print("\nDone.")


if __name__ == "__main__":
    main()
