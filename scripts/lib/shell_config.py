"""
Shell Configuration Functions - Aliases and shell environment setup

Manages shell RC files and aliases across bash, zsh, and fish.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import ui, utils


def add_shell_alias(
    shell_file: Path,
    alias_cmd: str,
    shell_name: str,
    alias_name: str,
    project_dir: Path,
) -> None:
    """
    Add or update alias in a shell configuration file.

    Args:
        shell_file: Shell configuration file path (e.g., ~/.bashrc)
        alias_cmd: Alias command to add
        shell_name: Shell name for display (e.g., ".bashrc")
        alias_name: Alias name (e.g., "ccp")
        project_dir: Project directory path (for unique marker)
    """
    if not shell_file.exists():
        return

    content = shell_file.read_text()
    marker = f"# Claude CodePro alias - {project_dir}"
    alias_pattern = re.compile(rf"^alias {re.escape(alias_name)}=", re.MULTILINE)

    # Check if this specific project alias exists
    if marker in content:
        # Update existing alias for this project
        lines = content.split("\n")
        new_lines = []
        in_section = False

        for line in lines:
            if line == marker:
                in_section = True
                new_lines.append(marker)
                new_lines.append(alias_cmd)
            elif in_section and alias_pattern.match(line):
                in_section = False
                continue
            else:
                new_lines.append(line)

        shell_file.write_text("\n".join(new_lines))
        ui.print_success(f"Updated alias '{alias_name}' in {shell_name}")

    elif alias_pattern.search(content):
        ui.print_warning(
            f"Alias '{alias_name}' already exists in {shell_name} (skipped)"
        )

    else:
        # Add new alias
        with open(shell_file, "a") as f:
            f.write(f"\n{marker}\n{alias_cmd}\n")
        ui.print_success(f"Added alias '{alias_name}' to {shell_name}")


def ensure_nvm_in_shell(shell_file: Path, shell_name: str) -> None:
    """
    Ensure NVM initialization is present in shell configuration.

    Args:
        shell_file: Shell configuration file path
        shell_name: Shell name for display
    """
    if not shell_file.exists():
        return

    content = shell_file.read_text()

    # Check if NVM is already sourced in the shell config
    if "NVM_DIR" not in content:
        ui.print_status(f"Adding NVM initialization to {shell_name}...")

        nvm_init = """
# NVM (Node Version Manager) - flexible location detection
if [ -z "$NVM_DIR" ]; then
  if [ -s "$HOME/.nvm/nvm.sh" ]; then
    export NVM_DIR="$HOME/.nvm"
  elif [ -s "/usr/local/share/nvm/nvm.sh" ]; then
    export NVM_DIR="/usr/local/share/nvm"
  fi
fi
[ -s "$NVM_DIR/nvm.sh" ] && \\. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \\. "$NVM_DIR/bash_completion"
"""
        with open(shell_file, "a") as f:
            f.write(nvm_init)

        ui.print_success(f"Added NVM initialization to {shell_name}")


def add_cc_alias(project_dir: Path) -> None:
    """
    Add 'ccp' alias to all detected shells.

    Creates an alias that:
    - Changes to project directory
    - Loads NVM
    - Builds rules
    - Starts Claude Code with dotenvx

    Args:
        project_dir: Project directory path
    """
    alias_name = "ccp"

    ui.print_status(f"Configuring shell for NVM and '{alias_name}' alias...")

    home = Path.home()

    # Ensure NVM initialization is in shell configs
    ensure_nvm_in_shell(home / ".bashrc", ".bashrc")
    ensure_nvm_in_shell(home / ".zshrc", ".zshrc")

    # Flexible NVM detection for bash/zsh alias
    # Using single quotes in Python to avoid escaping hell
    bash_alias = (
        f"alias {alias_name}=\"cd '{project_dir}' && "
        f'([ -s \\"\\$HOME/.nvm/nvm.sh\\" ] && export NVM_DIR=\\"\\$HOME/.nvm\\" || '
        f'[ -s \\"/usr/local/share/nvm/nvm.sh\\" ] && export NVM_DIR=\\"/usr/local/share/nvm\\") && '
        f'[ -s \\"\\$NVM_DIR/nvm.sh\\" ] && . \\"\\$NVM_DIR/nvm.sh\\" && '
        f'nvm use && bash .claude/rules/build.sh &>/dev/null && clear && dotenvx run -- claude"'
    )

    # Flexible NVM detection for fish alias
    fish_alias = (
        f"alias {alias_name}='cd {project_dir}; "
        f'and begin; if test -s "$HOME/.nvm/nvm.sh"; set -x NVM_DIR "$HOME/.nvm"; '
        f'else if test -s "/usr/local/share/nvm/nvm.sh"; set -x NVM_DIR "/usr/local/share/nvm"; end; end; '
        f'and test -s "$NVM_DIR/nvm.sh"; and source "$NVM_DIR/nvm.sh"; '
        f"and nvm use; and bash .claude/rules/build.sh &>/dev/null; and clear; "
        f"and dotenvx run -- claude; end'"
    )

    add_shell_alias(home / ".bashrc", bash_alias, ".bashrc", alias_name, project_dir)
    add_shell_alias(home / ".zshrc", bash_alias, ".zshrc", alias_name, project_dir)

    # Add fish alias if fish is installed
    if utils.command_exists("fish"):
        fish_config = home / ".config/fish"
        fish_config.mkdir(parents=True, exist_ok=True)
        add_shell_alias(
            fish_config / "config.fish",
            fish_alias,
            "fish config",
            alias_name,
            project_dir,
        )

    print("")
    ui.print_success(f"Alias '{alias_name}' configured!")
    print(f"   Run '{alias_name}' from anywhere to start Claude Code for this project")
