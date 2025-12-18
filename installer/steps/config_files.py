"""Config files step - installs MCP and other config files."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from installer.downloads import DownloadConfig, download_directory, download_file
from installer.steps.base import BaseStep

if TYPE_CHECKING:
    from installer.context import InstallContext


def backup_and_replace_mcp_config(config_file: Path, new_config: dict[str, Any], *, skip_backup: bool = False) -> None:
    """Backup existing MCP config and replace with new config."""
    if config_file.exists() and not skip_backup:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = config_file.with_suffix(f".json.backup.{timestamp}")
        backup_file.write_text(config_file.read_text())

    config_file.write_text(json.dumps(new_config, indent=2) + "\n")


class ConfigFilesStep(BaseStep):
    """Step that installs config files."""

    name = "config_files"

    def check(self, ctx: InstallContext) -> bool:
        """Always returns False - config files should always be updated."""
        return False

    def run(self, ctx: InstallContext) -> None:
        """Install MCP and other config files."""
        ui = ctx.ui

        config = DownloadConfig(
            repo_url="https://github.com/maxritter/claude-codepro",
            repo_branch="main",
            local_mode=ctx.local_mode,
            local_repo_dir=ctx.local_repo_dir,
        )

        nvmrc_file = ctx.project_dir / ".nvmrc"
        nvmrc_file.write_text("22\n")
        if ui:
            ui.success("Created .nvmrc for Node.js 22")

        qlty_dir = ctx.project_dir / ".qlty"
        if not qlty_dir.exists():
            if ui:
                with ui.spinner("Installing .qlty configuration..."):
                    count = download_directory(".qlty", qlty_dir, config)
                ui.success(f"Installed .qlty directory ({count} files)")
            else:
                download_directory(".qlty", qlty_dir, config)

        mcp_file = ctx.project_dir / ".mcp.json"
        if ui:
            with ui.spinner("Installing MCP configuration..."):
                with tempfile.TemporaryDirectory() as tmpdir:
                    temp_mcp = Path(tmpdir) / ".mcp.json"
                    if download_file(".mcp.json", temp_mcp, config):
                        try:
                            new_config = json.loads(temp_mcp.read_text())
                            backup_and_replace_mcp_config(mcp_file, new_config, skip_backup=ctx.local_mode)
                        except json.JSONDecodeError as e:
                            ui.warning(f"Failed to parse .mcp.json: {e}")
            ui.success("Installed .mcp.json")
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                temp_mcp = Path(tmpdir) / ".mcp.json"
                if download_file(".mcp.json", temp_mcp, config):
                    new_config = json.loads(temp_mcp.read_text())
                    backup_and_replace_mcp_config(mcp_file, new_config, skip_backup=ctx.local_mode)

        funnel_file = ctx.project_dir / ".mcp-funnel.json"
        if not funnel_file.exists():
            if ui:
                with ui.spinner("Installing MCP Funnel configuration..."):
                    with tempfile.TemporaryDirectory() as tmpdir:
                        temp_funnel = Path(tmpdir) / ".mcp-funnel.json"
                        if download_file(".mcp-funnel.json", temp_funnel, config):
                            try:
                                funnel_file.write_text(temp_funnel.read_text())
                            except Exception as e:
                                ui.warning(f"Failed to install .mcp-funnel.json: {e}")
                ui.success("Installed .mcp-funnel.json")
            else:
                with tempfile.TemporaryDirectory() as tmpdir:
                    temp_funnel = Path(tmpdir) / ".mcp-funnel.json"
                    if download_file(".mcp-funnel.json", temp_funnel, config):
                        funnel_file.write_text(temp_funnel.read_text())
        else:
            if ui:
                ui.success(".mcp-funnel.json already exists, skipping")

    def rollback(self, ctx: InstallContext) -> None:
        """Remove generated config files."""
        pass
