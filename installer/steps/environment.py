"""Environment step - handles OAuth token setup for persistent authentication."""

from __future__ import annotations

import json
import os
from pathlib import Path

from installer.context import InstallContext
from installer.steps.base import BaseStep


def get_env_value(key: str, env_file: Path) -> str | None:
    """Get the value of a key from .env file, or None if not found."""
    if not env_file.exists():
        return None

    content = env_file.read_text()
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith(f"{key}="):
            value = line[len(key) + 1 :].strip()
            return value if value else None
    return None


def key_is_set(key: str, env_file: Path) -> bool:
    """Check if key exists in .env file OR is already set as environment variable."""
    if os.environ.get(key):
        return True
    return get_env_value(key, env_file) is not None


def add_env_key(key: str, value: str, env_file: Path) -> None:
    """Add or update a key in .env file."""
    env_file.parent.mkdir(parents=True, exist_ok=True)
    with open(env_file, "a") as f:
        f.write(f"{key}={value}\n")


def credentials_exist() -> bool:
    """Check if valid Claude credentials exist in ~/.claude/.credentials.json."""
    creds_path = Path.home() / ".claude" / ".credentials.json"

    try:
        if not creds_path.exists():
            return False

        content = json.loads(creds_path.read_text())
        oauth = content.get("claudeAiOauth", {})
        access_token = oauth.get("accessToken", "")
        return bool(access_token)
    except (json.JSONDecodeError, OSError):
        return False


def create_claude_credentials(token: str) -> bool:
    """Create ~/.claude/.credentials.json with OAuth token.

    Creates the ~/.claude/ directory if needed and writes credentials
    with restrictive permissions (0o600 for file, 0o700 for directory).
    """
    import time

    claude_dir = Path.home() / ".claude"
    creds_path = claude_dir / ".credentials.json"

    expires_at = int(time.time() * 1000) + (365 * 24 * 60 * 60 * 1000)

    credentials = {
        "claudeAiOauth": {
            "accessToken": token,
            "refreshToken": token,
            "expiresAt": expires_at,
            "scopes": ["user:inference", "user:profile", "user:sessions:claude_code"],
            "subscriptionType": "max",
            "rateLimitTier": "default_claude_max_20x",
        }
    }

    try:
        claude_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        creds_path.write_text(json.dumps(credentials, indent=2) + "\n")
        creds_path.chmod(0o600)
        return True
    except OSError:
        return False


def create_claude_config() -> bool:
    """Create ~/.claude.json with hasCompletedOnboarding flag."""
    config_path = Path.home() / ".claude.json"
    config = {"hasCompletedOnboarding": True}

    try:
        if config_path.exists():
            existing = json.loads(config_path.read_text())
            existing.update(config)
            config = existing

        config_path.write_text(json.dumps(config, indent=2) + "\n")
        return True
    except Exception:
        return False


class EnvironmentStep(BaseStep):
    """Step that handles OAuth token setup for persistent authentication."""

    name = "environment"

    def check(self, ctx: InstallContext) -> bool:  # noqa: ARG002
        """Skip if OAuth credentials already exist."""
        return credentials_exist()

    def run(self, ctx: InstallContext) -> None:
        """Handle OAuth token setup for persistent authentication."""
        ui = ctx.ui
        env_file = ctx.project_dir / ".env"

        token_in_env = key_is_set("CLAUDE_CODE_OAUTH_TOKEN", env_file)
        token_in_creds = credentials_exist()

        if token_in_env and not token_in_creds:
            existing_token = get_env_value("CLAUDE_CODE_OAUTH_TOKEN", env_file)
            if existing_token and ui:
                ui.status("Restoring OAuth credentials from .env...")
                if create_claude_credentials(existing_token):
                    create_claude_config()
                    ui.success("OAuth credentials restored to ~/.claude/.credentials.json")
                else:
                    ui.warning("Could not restore credentials file")

        if token_in_creds:
            if ui:
                ui.success("OAuth credentials already configured")

    def rollback(self, ctx: InstallContext) -> None:  # noqa: ARG002
        """No rollback for environment setup."""
        pass
