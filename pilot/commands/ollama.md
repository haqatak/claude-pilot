---
description: Configure Ollama integration for Claude Code
user-invocable: true
model: sonnet
---

# /ollama - Configure Ollama Integration

**Guides the user to configure Ollama integration for Claude Code.** Checks if Ollama is running, asks for model selection, and updates the configuration.

---

## TABLE OF CONTENTS

| Phase       | Description                                            | Steps   |
| ----------- | ------------------------------------------------------ | ------- |
| **Phase 1** | Check Ollama Status                                    | 1.1–1.2 |
| **Phase 2** | Configuration                                          | 2.1–2.2 |
| **Phase 3** | Verify & Restart                                       | 3.1     |

---

## Phase 1: Check Ollama Status

### Step 1.1: Check if Ollama is running

Check if Ollama is reachable at the default URL.

```bash
curl -s http://localhost:11434/api/tags > /dev/null && echo "Ollama is running" || echo "Ollama is NOT running"
```

If NOT running:
- Inform the user that Ollama needs to be running.
- Ask if they want to proceed anyway (maybe they use a remote server).
- If they proceed, ask for the Base URL.

### Step 1.2: List available models

If running locally:
List available models to help the user choose.

```bash
curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | cut -d'"' -f4
```

---

## Phase 2: Configuration

### Step 2.1: Ask for Model

Ask the user if they want to **Enable** or **Disable** Ollama integration.

If **Enable**:
1. Ask for the **Base URL** (default: `http://localhost:11434`).
2. Ask for the **Model Name** (e.g., `qwen2.5-coder`, `deepseek-coder-v2`, `llama3.1`).
   - Suggest models found in Step 1.2.
   - Mention the recommended context window (64k).

If **Disable**:
- Proceed to remove the configuration.

### Step 2.2: Update Configuration

Update `~/.claude/settings.json` (or the project specific configuration) with the environment variables.

**Use Python to safely update the JSON file:**

```python
import json
import os
from pathlib import Path

# INPUT VARIABLES (Set these based on user input)
ACTION = "ENABLE" # or "DISABLE"
BASE_URL = "http://localhost:11434"
MODEL_NAME = "qwen2.5-coder:latest"

settings_path = Path.home() / ".claude" / "settings.json"

if settings_path.exists():
    try:
        with open(settings_path, "r") as f:
            config = json.load(f)

        env = config.get("env", {})

        if ACTION == "ENABLE":
            env["ANTHROPIC_AUTH_TOKEN"] = "ollama"
            env["ANTHROPIC_BASE_URL"] = BASE_URL
            env["ANTHROPIC_API_KEY"] = ""
            if MODEL_NAME:
                env["ANTHROPIC_MODEL"] = MODEL_NAME
            print(f"Enabling Ollama with model {MODEL_NAME} at {BASE_URL}")

        elif ACTION == "DISABLE":
            env.pop("ANTHROPIC_AUTH_TOKEN", None)
            env.pop("ANTHROPIC_BASE_URL", None)
            env.pop("ANTHROPIC_API_KEY", None)
            env.pop("ANTHROPIC_MODEL", None)
            print("Disabling Ollama integration")

        config["env"] = env

        with open(settings_path, "w") as f:
            json.dump(config, f, indent=2)

        print(f"Updated {settings_path}")

    except Exception as e:
        print(f"Error updating settings: {e}")
else:
    print(f"Settings file not found at {settings_path}")
```

---

## Phase 3: Verify & Restart

### Step 3.1: Instructions

Tell the user that the configuration has been updated.
**They need to restart `pilot` for the changes to take effect.**

```bash
pilot --restart
```
(Or just `pilot` if they are already out)
