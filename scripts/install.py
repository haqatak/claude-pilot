#!/usr/bin/env python3
"""
Claude CodePro Installation & Update Script

Idempotent: Safe to run multiple times (install + update)
Supports: macOS, Linux, WSL
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import urllib.request
from pathlib import Path

# Repository configuration
REPO_URL = "https://github.com/maxritter/claude-codepro"
REPO_BRANCH = "main"

# Library modules to bootstrap
LIB_MODULES = [
    "ui.py",
    "utils.py",
    "downloads.py",
    "files.py",
    "dependencies.py",
    "shell_config.py",
    "migration.py",
    "env_setup.py",
    "devcontainer.py",
]


def bootstrap_download(
    repo_path: str, dest_path: Path, local_mode: bool, local_repo_dir: Path | None
) -> bool:
    """
    Minimal download function for bootstrapping (before lib modules are loaded).

    Args:
        repo_path: Path in repository
        dest_path: Local destination path
        local_mode: Use local files instead of downloading
        local_repo_dir: Local repository directory (if local_mode)

    Returns:
        True on success, False on failure
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if local_mode and local_repo_dir:
        source_file = local_repo_dir / repo_path
        if source_file.is_file():
            try:
                import shutil

                shutil.copy2(source_file, dest_path)
                return True
            except Exception:
                return False
        return False
    else:
        # Download from GitHub
        file_url = f"{REPO_URL}/raw/{REPO_BRANCH}/{repo_path}"
        try:
            with urllib.request.urlopen(file_url) as response:
                if response.status == 200:
                    dest_path.write_bytes(response.read())
                    return True
        except Exception:
            pass
        return False


def download_lib_modules(
    project_dir: Path, local_mode: bool, local_repo_dir: Path | None
) -> None:
    """Download all library modules before importing."""
    lib_dir = project_dir / "scripts" / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)

    for module in LIB_MODULES:
        repo_path = f"scripts/lib/{module}"
        dest_path = lib_dir / module
        if not bootstrap_download(repo_path, dest_path, local_mode, local_repo_dir):
            print(f"Warning: Failed to download lib/{module}", file=sys.stderr)


def main() -> None:
    """Main installation flow."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Claude CodePro Installation Script")
    parser.add_argument(
        "--non-interactive", action="store_true", help="Run without interactive prompts"
    )
    parser.add_argument(
        "--skip-env", action="store_true", help="Skip environment setup (API keys)"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local files instead of downloading from GitHub",
    )
    parser.add_argument(
        "--local-repo-dir",
        type=str,
        help="Local repository directory (auto-detected if --local)",
    )

    args = parser.parse_args()

    # Determine paths
    project_dir = Path.cwd()

    # Handle local mode
    local_mode = args.local
    local_repo_dir: Path | None = None
    if local_mode:
        if args.local_repo_dir:
            local_repo_dir = Path(args.local_repo_dir).resolve()
        else:
            # Auto-detect: script is in scripts/, so parent is repo root
            script_location = Path(__file__).parent.resolve()
            local_repo_dir = script_location.parent

    # Download library modules
    download_lib_modules(project_dir, local_mode, local_repo_dir)

    # Add project scripts directory to Python path
    sys.path.insert(0, str(project_dir / "scripts"))

    # Now we can import lib modules
    from lib import (
        dependencies,
        devcontainer,
        downloads,
        env_setup,
        files,
        migration,
        shell_config,
        ui,
        utils,
    )

    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Setup download configuration
        config = downloads.DownloadConfig(
            repo_url=REPO_URL,
            repo_branch=REPO_BRANCH,
            local_mode=local_mode,
            local_repo_dir=local_repo_dir,
        )

        # Print welcome banner
        ui.print_section("Claude CodePro Installation")

        # Check required dependencies
        if not utils.check_required_dependencies():
            sys.exit(1)

        ui.print_status(f"Installing into: {project_dir}")
        print("")

        # Offer dev container setup early (exits if user chooses container)
        devcontainer.offer_devcontainer_setup(project_dir, config, args.non_interactive)

        # Run migration if needed (must be before file installation)
        migration.run_migration(project_dir, args.non_interactive)

        # Ask about Python support
        if args.non_interactive:
            install_python = "Y"
            ui.print_status(f"Non-interactive mode: Python support = {install_python}")
            print("")
        else:
            print("Do you want to install advanced Python features?")
            print(
                "This includes: uv, ruff, mypy, basedpyright, and Python quality hooks"
            )
            install_python = input("Install Python support? (Y/n): ").strip() or "Y"
            print("")
            print("")

        # Install Claude CodePro Files
        ui.print_section("Installing Claude CodePro Files")
        ui.print_status("Installing .claude files...")

        # Download .claude directory (update existing files, preserve settings.local.json and custom rules)
        file_count = 0
        claude_files = downloads.get_repo_files(".claude", config)

        for file_path in claude_files:
            if not file_path:
                continue

            # Skip custom rules (never overwrite)
            if "rules/custom/" in file_path:
                continue

            # Skip settings.local.json (will be generated from template)
            if (
                "settings.local.json" in file_path
                and "settings.local.template.json" not in file_path
            ):
                continue

            # Skip Python hook if Python not selected
            if (
                install_python.lower() not in ["y", "yes"]
                and "file_checker_python.sh" in file_path
            ):
                continue

            # Special handling for config.yaml to preserve custom rules
            if (
                "rules/config.yaml" in file_path
                and (project_dir / ".claude" / "rules" / "config.yaml").exists()
            ):
                temp_config = temp_dir / "config.yaml"
                if downloads.download_file(file_path, temp_config, config):
                    files.merge_yaml_config(
                        temp_config, project_dir / ".claude" / "rules" / "config.yaml"
                    )
                    file_count += 1
                    print("   ✓ config.yaml (merged with custom rules)")
                continue

            dest_file = project_dir / file_path
            if downloads.download_file(file_path, dest_file, config):
                file_count += 1
                print(f"   ✓ {Path(file_path).name}")

        # Create custom rules directories if they don't exist
        ui.print_status("Setting up custom rules directories...")
        for category in ["core", "extended", "workflow"]:
            custom_dir = project_dir / ".claude" / "rules" / "custom" / category
            if not custom_dir.exists():
                custom_dir.mkdir(parents=True, exist_ok=True)
                (custom_dir / ".gitkeep").touch()
                print(f"   ✓ Created custom/{category}/")

        # Generate settings.local.json from template
        ui.print_status("Generating settings.local.json from template...")
        template_file = project_dir / ".claude" / "settings.local.template.json"
        settings_file = project_dir / ".claude" / "settings.local.json"

        if template_file.exists():
            if settings_file.exists():
                if not args.non_interactive:
                    ui.print_warning("settings.local.json already exists")
                    print("This file may contain new features in this version.")
                    regen = input(
                        "Regenerate settings.local.json from template? (y/N): "
                    ).strip()
                    if regen.lower() not in ["y", "yes"]:
                        ui.print_success("Kept existing settings.local.json")
                    else:
                        template_content = template_file.read_text()
                        settings_content = template_content.replace(
                            "{{PROJECT_DIR}}", str(project_dir)
                        )
                        settings_file.write_text(settings_content)
                        ui.print_success(
                            "Regenerated settings.local.json with absolute paths"
                        )
                else:
                    ui.print_success("Kept existing settings.local.json")
            else:
                # First time installation - always generate
                template_content = template_file.read_text()
                settings_content = template_content.replace(
                    "{{PROJECT_DIR}}", str(project_dir)
                )
                settings_file.write_text(settings_content)
                ui.print_success("Generated settings.local.json with absolute paths")
        else:
            ui.print_warning(
                "settings.local.template.json not found, skipping generation"
            )

        # Make hooks executable
        hooks_dir = project_dir / ".claude" / "hooks"
        if hooks_dir.exists():
            for hook_file in hooks_dir.glob("*.sh"):
                hook_file.chmod(0o755)

        ui.print_success(f"Installed {file_count} .claude files")
        print("")

        # Install other configuration directories
        if not (project_dir / ".cipher").exists():
            files.install_directory(".cipher", project_dir, config)
            print("")

        if not (project_dir / ".qlty").exists():
            files.install_directory(".qlty", project_dir, config)
            print("")

        # Install MCP configurations
        files.merge_mcp_config(".mcp.json", project_dir / ".mcp.json", config, temp_dir)
        files.merge_mcp_config(
            ".mcp-funnel.json", project_dir / ".mcp-funnel.json", config, temp_dir
        )
        print("")

        # Install scripts
        (project_dir / "scripts" / "lib").mkdir(parents=True, exist_ok=True)
        files.install_file(
            "scripts/lib/setup-env.sh",
            project_dir / "scripts" / "lib" / "setup-env.sh",
            config,
        )
        files.install_file(
            ".claude/rules/build.sh",
            project_dir / ".claude" / "rules" / "build.sh",
            config,
        )

        # Make scripts executable
        for script_file in (project_dir / "scripts").glob("*.sh"):
            script_file.chmod(0o755)
        for lib_script in (project_dir / "scripts" / "lib").glob("*.sh"):
            lib_script.chmod(0o755)
        build_script = project_dir / ".claude" / "rules" / "build.sh"
        if build_script.exists():
            build_script.chmod(0o755)
        print("")

        # Create .nvmrc for Node.js version management
        ui.print_status("Creating .nvmrc for Node.js 22...")
        (project_dir / ".nvmrc").write_text("22\n")
        ui.print_success("Created .nvmrc")
        print("")

        # Environment Setup
        if args.skip_env or args.non_interactive:
            ui.print_section("Environment Setup")
            ui.print_status(
                "Skipping interactive environment setup (non-interactive mode)"
            )
            ui.print_warning(
                "Make sure to set up .env file manually or via environment variables"
            )
            print("")
        else:
            ui.print_section("Environment Setup")
            env_setup.setup_env_file(project_dir)

        # Install Dependencies
        ui.print_section("Installing Dependencies")

        # Install Node.js first (required for npm packages)
        dependencies.install_nodejs()
        print("")

        # Install Python tools if selected
        if install_python.lower() in ["y", "yes"]:
            dependencies.install_uv()
            print("")

            dependencies.install_python_tools()
            print("")

        dependencies.install_qlty(project_dir)
        print("")

        dependencies.install_claude_code()
        print("")

        dependencies.install_cipher()
        print("")

        dependencies.install_newman()
        print("")

        dependencies.install_dotenvx()
        print("")

        # Build Rules
        ui.print_section("Building Rules")
        build_script = project_dir / ".claude" / "rules" / "build.sh"
        if build_script.exists():
            ui.print_status("Building Claude Code commands and skills...")
            try:
                import subprocess

                subprocess.run(
                    ["bash", str(build_script)], check=True, capture_output=True
                )
                ui.print_success("Built commands and skills")
            except subprocess.CalledProcessError:
                ui.print_error("Failed to build commands and skills")
                ui.print_warning(
                    "You may need to run 'bash .claude/rules/build.sh' manually"
                )
        else:
            ui.print_warning("build.sh not found, skipping")
        print("")

        # Install Statusline Configuration
        ui.print_section("Installing Statusline Configuration")
        source_config = project_dir / ".claude" / "statusline.json"
        target_dir = Path.home() / ".config" / "ccstatusline"
        target_config = target_dir / "settings.json"

        if source_config.exists():
            ui.print_status("Installing statusline configuration...")
            target_dir.mkdir(parents=True, exist_ok=True)
            import shutil

            shutil.copy2(source_config, target_config)
            ui.print_success(
                "Installed statusline configuration to ~/.config/ccstatusline/settings.json"
            )
        else:
            ui.print_warning("statusline.json not found in .claude directory, skipping")
        print("")

        # Configure Shell
        ui.print_section("Configuring Shell")
        shell_config.add_cc_alias(project_dir)

        # Success Message
        ui.print_section("🎉 Installation Complete!")

        print("")
        print(f"{ui.GREEN}{'━' * 70}{ui.NC}")
        print(f"{ui.GREEN}  Claude CodePro has been successfully installed! 🚀{ui.NC}")
        print(f"{ui.GREEN}{'━' * 70}{ui.NC}")
        print("")
        print(f"{ui.BLUE}What's next?{ui.NC} Follow these steps to get started:")
        print("")
        print(f"{ui.YELLOW}STEP 1: Reload Your Shell{ui.NC}")
        print("   → Run: source ~/.zshrc  (or 'source ~/.bashrc' for bash)")
        print("")
        print(f"{ui.YELLOW}STEP 2: Start Claude Code{ui.NC}")
        print("   → Launch with: ccp")
        print("")
        print(f"{ui.YELLOW}STEP 3: Configure Claude Code{ui.NC}")
        print("   → In Claude Code, run: /config")
        print("   → Set 'Auto-connect to IDE' = true")
        print("   → Set 'Auto-compact' = false")
        print("")
        print(f"{ui.YELLOW}STEP 4: Verify Everything Works{ui.NC}")
        print("   → Run: /ide        (Connect to VS Code diagnostics)")
        print("   → Run: /mcp        (Verify all MCP servers are online)")
        print("   → Run: /context    (Check context usage is below 20%)")
        print("")
        print(f"{ui.YELLOW}STEP 5: Start Building!{ui.NC}")
        print("")
        print(f"   {ui.BLUE}For quick changes:{ui.NC}")
        print("   → /quick           Fast development without spec-driven planning")
        print("")
        print(f"   {ui.BLUE}For complex features:{ui.NC}")
        print("   → /plan            Create detailed spec with TDD")
        print("   → /implement       Execute spec with mandatory testing")
        print("   → /verify          Run end-to-end quality checks")
        print("")
        print(f"{ui.GREEN}{'━' * 70}{ui.NC}")
        print(f"{ui.GREEN}📚 Learn more: https://www.claude-code.pro{ui.NC}")
        print(
            f"{ui.GREEN}💬 Questions? https://github.com/maxritter/claude-codepro/issues{ui.NC}"
        )
        print(f"{ui.GREEN}{'━' * 70}{ui.NC}")
        print("")

    finally:
        # Cleanup
        utils.cleanup(temp_dir)


if __name__ == "__main__":
    main()
