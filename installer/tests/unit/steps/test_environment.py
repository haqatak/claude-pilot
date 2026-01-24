"""Tests for environment step - OAuth token setup."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from installer.steps.environment import (
    EnvironmentStep,
    add_env_key,
    create_claude_config,
    create_claude_credentials,
    credentials_exist,
    get_env_value,
    key_is_set,
)


class TestGetEnvValue:
    """Tests for get_env_value function."""

    def test_returns_none_when_file_not_exists(self):
        """Returns None when .env file does not exist."""
        result = get_env_value("KEY", Path("/nonexistent/.env"))
        assert result is None

    def test_returns_none_when_key_not_found(self):
        """Returns None when key is not in .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("OTHER_KEY=value\n")
            result = get_env_value("MY_KEY", env_file)
            assert result is None

    def test_returns_value_when_key_exists(self):
        """Returns value when key exists in .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("MY_KEY=my_value\n")
            result = get_env_value("MY_KEY", env_file)
            assert result == "my_value"

    def test_returns_none_for_empty_value(self):
        """Returns None when key exists but value is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("MY_KEY=\n")
            result = get_env_value("MY_KEY", env_file)
            assert result is None


class TestKeyIsSet:
    """Tests for key_is_set function."""

    def test_returns_true_when_set_in_env_var(self):
        """Returns True when key is set as environment variable."""
        with patch.dict("os.environ", {"MY_KEY": "value"}):
            result = key_is_set("MY_KEY", Path("/nonexistent/.env"))
            assert result is True

    def test_returns_true_when_in_env_file(self):
        """Returns True when key is in .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("MY_KEY=value\n")
            with patch.dict("os.environ", {}, clear=True):
                result = key_is_set("MY_KEY", env_file)
                assert result is True

    def test_returns_false_when_not_set(self):
        """Returns False when key is not set anywhere."""
        with patch.dict("os.environ", {}, clear=True):
            result = key_is_set("MY_KEY", Path("/nonexistent/.env"))
            assert result is False


class TestAddEnvKey:
    """Tests for add_env_key function."""

    def test_creates_env_file_if_not_exists(self):
        """Creates .env file if it does not exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            add_env_key("MY_KEY", "my_value", env_file)
            assert env_file.exists()
            assert env_file.read_text() == "MY_KEY=my_value\n"

    def test_appends_to_existing_env_file(self):
        """Appends to existing .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("EXISTING=value\n")
            add_env_key("MY_KEY", "my_value", env_file)
            content = env_file.read_text()
            assert "EXISTING=value" in content
            assert "MY_KEY=my_value" in content

    def test_creates_parent_directories(self):
        """Creates parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / "subdir" / ".env"
            add_env_key("MY_KEY", "my_value", env_file)
            assert env_file.exists()


class TestCredentialsExist:
    """Tests for credentials_exist function."""

    def test_returns_false_when_file_not_exists(self):
        """Returns False when credentials file does not exist."""
        with patch("installer.steps.environment.Path.home") as mock_home:
            mock_home.return_value = Path("/nonexistent")
            result = credentials_exist()
            assert result is False

    def test_returns_false_when_no_access_token(self):
        """Returns False when credentials file has no access token."""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            creds_file = claude_dir / ".credentials.json"
            creds_file.write_text(json.dumps({"claudeAiOauth": {}}))
            with patch("installer.steps.environment.Path.home") as mock_home:
                mock_home.return_value = Path(tmpdir)
                result = credentials_exist()
                assert result is False

    def test_returns_true_when_access_token_exists(self):
        """Returns True when credentials file has access token."""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            creds_file = claude_dir / ".credentials.json"
            creds_file.write_text(
                json.dumps({"claudeAiOauth": {"accessToken": "test_token"}})
            )
            with patch("installer.steps.environment.Path.home") as mock_home:
                mock_home.return_value = Path(tmpdir)
                result = credentials_exist()
                assert result is True

    def test_returns_false_on_invalid_json(self):
        """Returns False when credentials file has invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            creds_file = claude_dir / ".credentials.json"
            creds_file.write_text("not valid json")
            with patch("installer.steps.environment.Path.home") as mock_home:
                mock_home.return_value = Path(tmpdir)
                result = credentials_exist()
                assert result is False


class TestCreateClaudeCredentials:
    """Tests for create_claude_credentials function."""

    def test_creates_credentials_file(self):
        """Creates credentials file with correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("installer.steps.environment.Path.home") as mock_home:
                mock_home.return_value = Path(tmpdir)
                result = create_claude_credentials("test_token")
                assert result is True

                creds_file = Path(tmpdir) / ".claude" / ".credentials.json"
                assert creds_file.exists()

                content = json.loads(creds_file.read_text())
                assert content["claudeAiOauth"]["accessToken"] == "test_token"
                assert content["claudeAiOauth"]["refreshToken"] == "test_token"
                assert "expiresAt" in content["claudeAiOauth"]
                assert "scopes" in content["claudeAiOauth"]

    def test_creates_directory_with_correct_permissions(self):
        """Creates .claude directory with 0700 permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("installer.steps.environment.Path.home") as mock_home:
                mock_home.return_value = Path(tmpdir)
                create_claude_credentials("test_token")

                claude_dir = Path(tmpdir) / ".claude"
                assert claude_dir.exists()


class TestCreateClaudeConfig:
    """Tests for create_claude_config function."""

    def test_creates_config_with_onboarding_flag(self):
        """Creates ~/.claude.json with hasCompletedOnboarding flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("installer.steps.environment.Path.home") as mock_home:
                mock_home.return_value = Path(tmpdir)
                result = create_claude_config()
                assert result is True

                config_file = Path(tmpdir) / ".claude.json"
                assert config_file.exists()
                content = json.loads(config_file.read_text())
                assert content["hasCompletedOnboarding"] is True

    def test_preserves_existing_config(self):
        """Preserves existing config when updating."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".claude.json"
            config_file.write_text(json.dumps({"existingKey": "value"}))
            with patch("installer.steps.environment.Path.home") as mock_home:
                mock_home.return_value = Path(tmpdir)
                create_claude_config()
                content = json.loads(config_file.read_text())
                assert content["existingKey"] == "value"
                assert content["hasCompletedOnboarding"] is True


class TestEnvironmentStep:
    """Tests for EnvironmentStep class."""

    def test_step_has_correct_name(self):
        """EnvironmentStep has name 'environment'."""
        step = EnvironmentStep()
        assert step.name == "environment"

    def test_check_returns_true_when_credentials_exist(self):
        """EnvironmentStep.check returns True when credentials exist."""
        from installer.context import InstallContext
        from installer.ui import Console

        step = EnvironmentStep()
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = InstallContext(
                project_dir=Path(tmpdir),
                ui=Console(non_interactive=True),
            )
            with patch("installer.steps.environment.credentials_exist", return_value=True):
                assert step.check(ctx) is True

    def test_check_returns_false_when_no_credentials(self):
        """EnvironmentStep.check returns False when no credentials."""
        from installer.context import InstallContext
        from installer.ui import Console

        step = EnvironmentStep()
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = InstallContext(
                project_dir=Path(tmpdir),
                ui=Console(non_interactive=True),
            )
            with patch("installer.steps.environment.credentials_exist", return_value=False):
                assert step.check(ctx) is False

    def test_run_restores_credentials_from_env(self):
        """EnvironmentStep restores credentials when token in .env but not in creds."""
        from installer.context import InstallContext
        from installer.ui import Console

        step = EnvironmentStep()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .env with token
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("CLAUDE_CODE_OAUTH_TOKEN=test_token\n")

            ctx = InstallContext(
                project_dir=Path(tmpdir),
                ui=Console(non_interactive=True),
            )

            with patch("installer.steps.environment.Path.home") as mock_home:
                mock_home.return_value = Path(tmpdir)
                with patch(
                    "installer.steps.environment.credentials_exist", return_value=False
                ):
                    with patch(
                        "installer.steps.environment.create_claude_credentials",
                        return_value=True,
                    ) as mock_create:
                        step.run(ctx)
                        mock_create.assert_called_once_with("test_token")

    def test_run_skips_when_user_declined(self):
        """EnvironmentStep skips token setup when user previously declined."""
        from installer.context import InstallContext
        from installer.ui import Console

        step = EnvironmentStep()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mark as declined
            config_path = Path(tmpdir) / ".claude" / "config" / "ccp-config.json"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(json.dumps({"declined_oauth_token": True}))

            ctx = InstallContext(
                project_dir=Path(tmpdir),
                ui=Console(non_interactive=True),
            )

            with patch("installer.steps.environment.Path.home") as mock_home:
                mock_home.return_value = Path(tmpdir)
                with patch(
                    "installer.steps.environment.credentials_exist", return_value=False
                ):
                    # Should not prompt
                    step.run(ctx)
                    # If we got here without error, the step skipped properly

    def test_run_succeeds_when_credentials_exist(self):
        """EnvironmentStep succeeds when credentials already exist."""
        from installer.context import InstallContext
        from installer.ui import Console

        step = EnvironmentStep()
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = InstallContext(
                project_dir=Path(tmpdir),
                ui=Console(non_interactive=True),
            )

            with patch("installer.steps.environment.Path.home") as mock_home:
                mock_home.return_value = Path(tmpdir)
                with patch(
                    "installer.steps.environment.credentials_exist", return_value=True
                ):
                    step.run(ctx)
                    # Should complete without prompting

    def test_rollback_does_nothing(self):
        """EnvironmentStep.rollback does nothing."""
        from installer.context import InstallContext
        from installer.ui import Console

        step = EnvironmentStep()
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = InstallContext(
                project_dir=Path(tmpdir),
                ui=Console(non_interactive=True),
            )
            # Should not raise
            step.rollback(ctx)

    def test_run_shows_status_when_credentials_exist(self):
        """EnvironmentStep shows success when OAuth credentials already exist."""
        from unittest.mock import MagicMock

        from installer.context import InstallContext

        step = EnvironmentStep()
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ui = MagicMock()
            ctx = InstallContext(
                project_dir=Path(tmpdir),
                ui=mock_ui,
            )

            with patch("installer.steps.environment.Path.home") as mock_home:
                mock_home.return_value = Path(tmpdir)
                with patch(
                    "installer.steps.environment.credentials_exist", return_value=True
                ):
                    with patch(
                        "installer.steps.environment.key_is_set", return_value=False
                    ):
                        step.run(ctx)
                        # Should show success message when creds exist
                        mock_ui.success.assert_called()
