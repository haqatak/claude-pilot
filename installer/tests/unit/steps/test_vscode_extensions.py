"""Tests for VS Code extensions step."""

from unittest.mock import MagicMock, patch

from installer.steps.vscode_extensions import (
    CONTAINER_EXTENSIONS,
    OPTIONAL_EXTENSIONS,
    VSCodeExtensionsStep,
)


class TestVSCodeExtensionsStep:
    """Test VSCodeExtensionsStep class."""

    def test_step_has_correct_name(self):
        """VSCodeExtensionsStep has name 'vscode_extensions'."""
        step = VSCodeExtensionsStep()
        assert step.name == "vscode_extensions"

    def test_container_extensions_list_not_empty(self):
        """CONTAINER_EXTENSIONS list contains extensions."""
        assert len(CONTAINER_EXTENSIONS) > 0
        assert all(isinstance(ext, str) for ext in CONTAINER_EXTENSIONS)

    def test_optional_extensions_list_exists(self):
        """OPTIONAL_EXTENSIONS list exists and contains strings."""
        assert isinstance(OPTIONAL_EXTENSIONS, list)
        assert all(isinstance(ext, str) for ext in OPTIONAL_EXTENSIONS)

    def test_kaleidoscope_is_optional(self):
        """Kaleidoscope extension is in optional list, not required."""
        assert "kaleidoscope-app.vscode-ksdiff" in OPTIONAL_EXTENSIONS
        assert "kaleidoscope-app.vscode-ksdiff" not in CONTAINER_EXTENSIONS

    @patch("installer.steps.vscode_extensions._get_ide_cli")
    def test_no_cli_shows_warning(self, mock_get_cli):
        """When no IDE CLI found, shows warning message."""
        mock_get_cli.return_value = None
        ctx = MagicMock()
        ctx.ui = MagicMock()

        step = VSCodeExtensionsStep()
        step.run(ctx)

        ctx.ui.warning.assert_called()

    @patch("installer.steps.vscode_extensions._get_ide_cli")
    @patch("installer.steps.vscode_extensions._get_installed_extensions")
    def test_all_installed_shows_success(self, mock_installed, mock_cli):
        """When all extensions installed, shows success without installing."""
        mock_cli.return_value = "code"
        all_extensions = CONTAINER_EXTENSIONS + OPTIONAL_EXTENSIONS
        mock_installed.return_value = {ext.lower() for ext in all_extensions}

        ctx = MagicMock()
        ctx.ui = MagicMock()
        ctx.config = {}

        step = VSCodeExtensionsStep()
        step.run(ctx)

        ctx.ui.success.assert_called()
        assert ctx.config["installed_extensions"] == 0
        assert ctx.config["failed_extensions"] == []

    @patch("installer.steps.vscode_extensions._get_ide_cli")
    @patch("installer.steps.vscode_extensions._get_installed_extensions")
    @patch("installer.steps.vscode_extensions._install_extension")
    def test_optional_extension_failure_not_in_failed_list(
        self, mock_install, mock_installed, mock_cli
    ):
        """Optional extension failure doesn't add to failed list."""
        mock_cli.return_value = "code"
        mock_installed.return_value = {ext.lower() for ext in CONTAINER_EXTENSIONS}
        mock_install.return_value = False

        ctx = MagicMock()
        ctx.ui = MagicMock()
        ctx.config = {}

        step = VSCodeExtensionsStep()
        step.run(ctx)

        assert "kaleidoscope-app.vscode-ksdiff" not in ctx.config["failed_extensions"]

    @patch("installer.steps.vscode_extensions._get_ide_cli")
    @patch("installer.steps.vscode_extensions._get_installed_extensions")
    @patch("installer.steps.vscode_extensions._install_extension")
    def test_required_extension_failure_in_failed_list(
        self, mock_install, mock_installed, mock_cli
    ):
        """Required extension failure adds to failed list."""
        mock_cli.return_value = "code"
        mock_installed.return_value = set()

        def install_side_effect(_cli, ext):
            return ext != "anthropic.claude-code"

        mock_install.side_effect = install_side_effect

        ctx = MagicMock()
        ctx.ui = MagicMock()
        ctx.config = {}

        step = VSCodeExtensionsStep()
        step.run(ctx)

        assert "anthropic.claude-code" in ctx.config["failed_extensions"]

    def test_check_always_returns_false(self):
        """check() always returns False to ensure step runs."""
        ctx = MagicMock()
        step = VSCodeExtensionsStep()
        assert step.check(ctx) is False
