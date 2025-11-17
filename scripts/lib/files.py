"""
File Management Functions - Install and manage Claude CodePro files

Provides file installation and configuration merging capabilities.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from . import downloads, ui


def install_directory(
    repo_dir: str,
    dest_base: Path,
    config: downloads.DownloadConfig,
) -> int:
    """
    Install all files from a repository directory.

    Args:
        repo_dir: Repository directory path (e.g., ".claude")
        dest_base: Destination base directory
        config: Download configuration

    Returns:
        Number of files installed
    """
    ui.print_status(f"Installing {repo_dir} files...")

    file_count = 0
    files = downloads.get_repo_files(repo_dir, config)

    for file_path in files:
        if not file_path:
            continue

        dest_file = dest_base / file_path

        if downloads.download_file(file_path, dest_file, config):
            file_count += 1
            print(f"   ✓ {Path(file_path).name}")

    ui.print_success(f"Installed {file_count} files")
    return file_count


def install_file(
    repo_file: str,
    dest_file: Path,
    config: downloads.DownloadConfig,
) -> bool:
    """
    Install a single file from repository.

    Args:
        repo_file: Repository file path
        dest_file: Destination file path
        config: Download configuration

    Returns:
        True on success, False on failure
    """
    if downloads.download_file(repo_file, dest_file, config):
        ui.print_success(f"Installed {repo_file}")
        return True
    else:
        ui.print_warning(f"Failed to install {repo_file}")
        return False


def merge_mcp_config(
    repo_file: str,
    dest_file: Path,
    config: downloads.DownloadConfig,
    temp_dir: Path,
) -> bool:
    """
    Merge MCP configuration files.

    Preserves existing server configurations while adding new ones.

    Args:
        repo_file: Repository file path (e.g., ".mcp.json")
        dest_file: Destination file path
        config: Download configuration
        temp_dir: Temporary directory for downloads

    Returns:
        True on success, False on failure
    """
    ui.print_status("Installing MCP configuration...")

    temp_file = temp_dir / "mcp-temp.json"

    # Download the new config
    if not downloads.download_file(repo_file, temp_file, config):
        ui.print_warning(f"Failed to download {repo_file}")
        return False

    # If destination doesn't exist, just copy it
    if not dest_file.exists():
        _ = shutil.copy2(temp_file, dest_file)
        ui.print_success(f"Created {repo_file}")
        return True

    try:
        # Load both configurations
        with open(dest_file, "r") as f:
            existing_config = json.load(f)

        with open(temp_file, "r") as f:
            new_config = json.load(f)

        # Determine which key is used for servers (.mcpServers or .servers)
        server_key = None
        if "mcpServers" in existing_config:
            server_key = "mcpServers"
        elif "servers" in existing_config:
            server_key = "servers"
        elif "mcpServers" in new_config:
            server_key = "mcpServers"
        elif "servers" in new_config:
            server_key = "servers"

        if server_key:
            # Get existing and new servers
            existing_servers = existing_config.get(server_key, {})
            new_servers = new_config.get(server_key, {})

            # Merge: new servers first, then existing (existing takes precedence)
            merged_servers = {**new_servers, **existing_servers}

            # Merge the full config
            merged_config = {**new_config, **existing_config}
            merged_config[server_key] = merged_servers
        else:
            # No servers key found, just merge dicts
            merged_config = {**new_config, **existing_config}

        # Write merged config
        with open(dest_file, "w") as f:
            json.dump(merged_config, f, indent=2)
            _ = f.write("\n")  # Add trailing newline

        ui.print_success("Merged MCP servers (preserved existing configuration)")
        return True

    except Exception as e:
        ui.print_warning(f"Failed to merge MCP configuration: {e}, preserving existing")
        return False


def merge_yaml_config(
    new_config_path: Path,
    existing_config_path: Path,
) -> bool:
    """
    Merge YAML rules config, preserving custom sections.

    This function merges config.yaml files, taking the new standard rules
    while preserving the user's custom rules.

    Args:
        new_config_path: Path to new config file
        existing_config_path: Path to existing config file to update

    Returns:
        True on success, False on failure
    """
    try:
        # Try to import YAML library (optional dependency)
        try:
            import yaml  # type: ignore[import-untyped,import-not-found]
        except ImportError:
            ui.print_warning("PyYAML not available, cannot merge YAML configs")
            return False

        # Load both configs (Any types are expected from YAML parsing)
        with open(new_config_path, "r") as f:
            new_config = yaml.safe_load(f)  # type: ignore[no-untyped-call]

        with open(existing_config_path, "r") as f:
            existing_config = yaml.safe_load(f)  # type: ignore[no-untyped-call]

        # Merge strategy: Take new config, replace custom arrays with old custom arrays
        # This preserves user's custom rules while updating standard rules
        if "commands" in new_config and "commands" in existing_config:
            for cmd_name, cmd_config in new_config["commands"].items():
                if cmd_name in existing_config["commands"]:
                    old_custom = (
                        existing_config["commands"][cmd_name]
                        .get("rules", {})
                        .get("custom", [])
                    )
                    if "rules" not in cmd_config:
                        cmd_config["rules"] = {}
                    cmd_config["rules"]["custom"] = old_custom

        # Write merged config
        with open(existing_config_path, "w") as f:
            yaml.dump(new_config, f, default_flow_style=False, sort_keys=False)

        ui.print_success("Merged config.yaml (preserved custom rules)")
        return True

    except Exception as e:
        ui.print_error(f"Failed to merge YAML config: {e}")
        return False
