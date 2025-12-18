"""Tests for finalize step."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestFinalizeStep:
    """Test FinalizeStep class."""

    def test_finalize_step_has_correct_name(self):
        """FinalizeStep has name 'finalize'."""
        from installer.steps.finalize import FinalizeStep

        step = FinalizeStep()
        assert step.name == "finalize"

    def test_check_always_returns_false(self):
        """check() always returns False (always runs)."""
        from installer.context import InstallContext
        from installer.steps.finalize import FinalizeStep
        from installer.ui import Console

        step = FinalizeStep()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            ctx = InstallContext(
                project_dir=project_dir,
                ui=Console(non_interactive=True),
            )

            # Finalize always runs
            assert step.check(ctx) is False


class TestStatuslineConfig:
    """Test statusline configuration installation."""

    def test_run_installs_statusline_config(self):
        """run() copies statusline.json to config dir."""
        from installer.context import InstallContext
        from installer.steps.finalize import FinalizeStep
        from installer.ui import Console

        step = FinalizeStep()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            claude_dir = project_dir / ".claude"
            claude_dir.mkdir()

            # Create statusline.json
            statusline_config = {"status": "enabled"}
            import json
            (claude_dir / "statusline.json").write_text(json.dumps(statusline_config))

            ctx = InstallContext(
                project_dir=project_dir,
                ui=Console(non_interactive=True),
            )

            # Mock home directory
            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path(tmpdir) / "home"
                (Path(tmpdir) / "home").mkdir()

                step.run(ctx)

                # Check config was installed
                target_config = Path(tmpdir) / "home" / ".config" / "ccstatusline" / "settings.json"
                assert target_config.exists()
                assert json.loads(target_config.read_text()) == statusline_config

    def test_run_skips_statusline_if_no_source(self):
        """run() skips statusline if no source file."""
        from installer.context import InstallContext
        from installer.steps.finalize import FinalizeStep
        from installer.ui import Console

        step = FinalizeStep()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / ".claude").mkdir()

            ctx = InstallContext(
                project_dir=project_dir,
                ui=Console(non_interactive=True),
            )

            # Should not raise even without statusline.json
            step.run(ctx)


class TestFinalSuccessPanel:
    """Test final success panel display."""

    def test_run_displays_success_message(self):
        """run() displays success panel."""
        from installer.context import InstallContext
        from installer.steps.finalize import FinalizeStep
        from installer.ui import Console

        step = FinalizeStep()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / ".claude").mkdir()

            console = Console(non_interactive=True)
            ctx = InstallContext(
                project_dir=project_dir,
                ui=console,
            )

            # Mock to capture output
            with patch.object(console, "success_box") as mock_success_box:
                with patch.object(console, "next_steps") as mock_next_steps:
                    step.run(ctx)

                    # Should display success box and next steps
                    mock_success_box.assert_called()
                    mock_next_steps.assert_called()
