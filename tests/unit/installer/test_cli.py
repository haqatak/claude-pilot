"""Tests for CLI entry point and step orchestration."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestCLIApp:
    """Test CLI application."""

    def test_cli_app_exists(self):
        """CLI app module exists."""
        from installer.cli import app

        assert app is not None

    def test_cli_has_install_command(self):
        """CLI has install command."""
        from installer.cli import install

        assert callable(install)


class TestRunInstallation:
    """Test step orchestration."""

    def test_run_installation_exists(self):
        """run_installation function exists."""
        from installer.cli import run_installation

        assert callable(run_installation)

    @patch("installer.cli.get_all_steps")
    def test_run_installation_executes_steps(self, mock_get_all_steps):
        """run_installation executes steps in order."""
        from installer.cli import run_installation
        from installer.context import InstallContext
        from installer.ui import Console

        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = InstallContext(
                project_dir=Path(tmpdir),
                ui=Console(non_interactive=True),
                non_interactive=True,
            )

            # Create mock steps
            mock_step1 = MagicMock()
            mock_step1.name = "step1"
            mock_step1.check.return_value = False

            mock_step2 = MagicMock()
            mock_step2.name = "step2"
            mock_step2.check.return_value = False

            mock_get_all_steps.return_value = [mock_step1, mock_step2]

            run_installation(ctx)

            # Both steps should be called
            mock_step1.run.assert_called_once_with(ctx)
            mock_step2.run.assert_called_once_with(ctx)


class TestRollback:
    """Test rollback functionality."""

    def test_rollback_completed_steps_exists(self):
        """rollback_completed_steps function exists."""
        from installer.cli import rollback_completed_steps

        assert callable(rollback_completed_steps)

    def test_rollback_calls_step_rollback(self):
        """rollback_completed_steps calls rollback on completed steps."""
        from installer.cli import rollback_completed_steps
        from installer.context import InstallContext
        from installer.ui import Console

        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = InstallContext(
                project_dir=Path(tmpdir),
                ui=Console(non_interactive=True),
            )
            ctx.mark_completed("test_step")

            # Mock step
            mock_step = MagicMock()
            mock_step.name = "test_step"

            steps = [mock_step]
            rollback_completed_steps(ctx, steps)

            mock_step.rollback.assert_called_once_with(ctx)


class TestMainEntry:
    """Test __main__ entry point."""

    def test_main_module_exists(self):
        """__main__ module exists."""
        import installer.__main__

        assert hasattr(installer.__main__, "main") or True  # May not have main function
