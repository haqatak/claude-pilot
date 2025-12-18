"""Tests for config files step."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


class TestConfigFilesStep:
    """Test ConfigFilesStep class."""

    def test_config_files_step_has_correct_name(self):
        """ConfigFilesStep has name 'config_files'."""
        from installer.steps.config_files import ConfigFilesStep

        step = ConfigFilesStep()
        assert step.name == "config_files"



class TestMCPConfigBackupReplace:
    """Test MCP config backup and replace."""

    def test_backup_and_replace_creates_backup(self):
        """Replacing MCP config creates backup of existing."""
        from installer.steps.config_files import backup_and_replace_mcp_config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".mcp.json"

            # Existing config
            existing = {"mcpServers": {"existing": {"command": "existing-server"}}}
            config_file.write_text(json.dumps(existing))

            # New config
            new_config = {"mcpServers": {"new": {"command": "new-server"}}}

            backup_and_replace_mcp_config(config_file, new_config)

            # Check backup was created (with timestamp)
            backup_files = list(Path(tmpdir).glob(".mcp.json.backup.*"))
            assert len(backup_files) == 1, "Should create one timestamped backup"
            backup_file = backup_files[0]
            backup_content = json.loads(backup_file.read_text())
            assert "existing" in backup_content["mcpServers"]

            # Check new config replaced old
            result = json.loads(config_file.read_text())
            assert "new" in result["mcpServers"]
            assert "existing" not in result["mcpServers"]

    def test_backup_and_replace_creates_new(self):
        """Replacing creates new config if none exists."""
        from installer.steps.config_files import backup_and_replace_mcp_config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".mcp.json"

            new_config = {"mcpServers": {"new": {"command": "new-server"}}}

            backup_and_replace_mcp_config(config_file, new_config)

            result = json.loads(config_file.read_text())
            assert "new" in result["mcpServers"]

            # No backup should exist since there was no original
            backup_file = config_file.with_suffix(".json.backup")
            assert not backup_file.exists()


class TestDirectoryInstallation:
    """Test .qlty directory installation."""

    def test_install_qlty_directory(self):
        """ConfigFilesStep installs .qlty directory."""
        from unittest.mock import patch

        from installer.context import InstallContext
        from installer.steps.config_files import ConfigFilesStep
        from installer.ui import Console

        step = ConfigFilesStep()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            claude_dir = project_dir / ".claude"
            claude_dir.mkdir()

            # Create template
            template = {"setting": "value"}
            (claude_dir / "settings.local.template.json").write_text(json.dumps(template))

            ctx = InstallContext(
                project_dir=project_dir,
                ui=Console(non_interactive=True),
                local_mode=True,
                local_repo_dir=Path("/fake"),
            )

            # Mock download_directory to simulate installation
            with patch("installer.steps.config_files.download_directory") as mock_download:
                mock_download.return_value = 2  # 2 files installed
                step.run(ctx)

                # Should have called download_directory for .qlty
                calls = mock_download.call_args_list
                qlty_calls = [c for c in calls if ".qlty" in str(c)]
                assert len(qlty_calls) >= 1, "Should install .qlty directory"

    def test_skips_existing_directories(self):
        """ConfigFilesStep skips directories that already exist."""
        from unittest.mock import patch

        from installer.context import InstallContext
        from installer.steps.config_files import ConfigFilesStep
        from installer.ui import Console

        step = ConfigFilesStep()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            claude_dir = project_dir / ".claude"
            claude_dir.mkdir()

            # Create template
            template = {"setting": "value"}
            (claude_dir / "settings.local.template.json").write_text(json.dumps(template))

            # Pre-create directories
            (project_dir / ".qlty").mkdir()

            ctx = InstallContext(
                project_dir=project_dir,
                ui=Console(non_interactive=True),
                local_mode=True,
                local_repo_dir=Path("/fake"),
            )

            # Mock download_directory
            with patch("installer.steps.config_files.download_directory") as mock_download:
                mock_download.return_value = 0
                step.run(ctx)

                # Should NOT call download_directory for existing dirs
                calls = mock_download.call_args_list
                qlty_calls = [c for c in calls if ".qlty" in str(c)]
                assert len(qlty_calls) == 0, "Should skip existing .qlty"


class TestMCPConfigInstallation:
    """Test MCP config file installation and merging."""

    def test_installs_mcp_json(self):
        """ConfigFilesStep installs .mcp.json."""
        from unittest.mock import patch

        from installer.context import InstallContext
        from installer.steps.config_files import ConfigFilesStep
        from installer.ui import Console

        step = ConfigFilesStep()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            claude_dir = project_dir / ".claude"
            claude_dir.mkdir()

            # Create template
            template = {"setting": "value"}
            (claude_dir / "settings.local.template.json").write_text(json.dumps(template))

            ctx = InstallContext(
                project_dir=project_dir,
                ui=Console(non_interactive=True),
                local_mode=True,
                local_repo_dir=Path("/fake"),
            )

            # Mock download_file to return MCP config content
            with patch("installer.steps.config_files.download_directory") as mock_dir:
                mock_dir.return_value = 0
                with patch("installer.steps.config_files.download_file") as mock_download:
                    def fake_download(path, dest, config, progress_callback=None):
                        if ".mcp.json" in path:
                            dest.write_text(json.dumps({"mcpServers": {"new": {"command": "test"}}}))
                            return True
                        return False
                    mock_download.side_effect = fake_download
                    step.run(ctx)

                    # Should have called download_file for .mcp.json
                    mcp_calls = [c for c in mock_download.call_args_list if ".mcp.json" in str(c)]
                    assert len(mcp_calls) >= 1, "Should install .mcp.json"

    def test_installs_mcp_funnel_json(self):
        """ConfigFilesStep installs .mcp-funnel.json."""
        from unittest.mock import patch

        from installer.context import InstallContext
        from installer.steps.config_files import ConfigFilesStep
        from installer.ui import Console

        step = ConfigFilesStep()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            claude_dir = project_dir / ".claude"
            claude_dir.mkdir()

            # Create template
            template = {"setting": "value"}
            (claude_dir / "settings.local.template.json").write_text(json.dumps(template))

            ctx = InstallContext(
                project_dir=project_dir,
                ui=Console(non_interactive=True),
                local_mode=True,
                local_repo_dir=Path("/fake"),
            )

            # Mock download_file to return MCP funnel config
            with patch("installer.steps.config_files.download_directory") as mock_dir:
                mock_dir.return_value = 0
                with patch("installer.steps.config_files.download_file") as mock_download:
                    def fake_download(path, dest, config, progress_callback=None):
                        if ".mcp-funnel.json" in path:
                            dest.write_text(json.dumps({"servers": {"test": {}}}))
                            return True
                        return False
                    mock_download.side_effect = fake_download
                    step.run(ctx)

                    # Should have called download_file for .mcp-funnel.json
                    funnel_calls = [c for c in mock_download.call_args_list if ".mcp-funnel.json" in str(c)]
                    assert len(funnel_calls) >= 1, "Should install .mcp-funnel.json"

    def test_replaces_mcp_config_with_backup(self):
        """ConfigFilesStep replaces MCP config and creates backup."""
        from unittest.mock import patch

        from installer.context import InstallContext
        from installer.steps.config_files import ConfigFilesStep
        from installer.ui import Console

        step = ConfigFilesStep()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            claude_dir = project_dir / ".claude"
            claude_dir.mkdir()

            # Create template
            template = {"setting": "value"}
            (claude_dir / "settings.local.template.json").write_text(json.dumps(template))

            # Create existing MCP config
            existing_mcp = {"mcpServers": {"user-server": {"command": "my-tool"}}}
            (project_dir / ".mcp.json").write_text(json.dumps(existing_mcp))

            ctx = InstallContext(
                project_dir=project_dir,
                ui=Console(non_interactive=True),
                local_mode=False,  # Test backup creation (skipped in local_mode)
            )

            # Mock downloads
            with patch("installer.steps.config_files.download_directory") as mock_dir:
                mock_dir.return_value = 0
                with patch("installer.steps.config_files.download_file") as mock_download:
                    def fake_download(path, dest, config, progress_callback=None):
                        if ".mcp.json" in path:
                            dest.write_text(json.dumps({"mcpServers": {"new-server": {"command": "new-tool"}}}))
                            return True
                        return False
                    mock_download.side_effect = fake_download
                    step.run(ctx)

                    # Check backup was created (with timestamp)
                    backup_files = list(project_dir.glob(".mcp.json.backup.*"))
                    assert len(backup_files) == 1, "Backup should be created"
                    backup_content = json.loads(backup_files[0].read_text())
                    assert "user-server" in backup_content["mcpServers"], "Backup contains old config"

                    # Check new config replaced old
                    mcp_file = project_dir / ".mcp.json"
                    result = json.loads(mcp_file.read_text())
                    assert "new-server" in result["mcpServers"], "New server added"
                    assert "user-server" not in result["mcpServers"], "Old server replaced"
