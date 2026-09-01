---
name: cua-driver
description: 'Domain skill. Computer-use agent driver: drive the host desktop — installed apps, signed-in browser sessions, local files, OS session. Connects via MCP (cua-driver mcp). Use when the agent needs to interact with native desktop applications, take screenshots, click, type text, or read window state.'
---

# Cua Driver — computer-use agent driver

Domain skill. Cua Driver lets an agent drive the host desktop: installed apps, signed-in browser sessions, local files opened in apps, and the current OS user session.

## When to use

- Agent needs to interact with native desktop applications (not just browser)
- Agent needs to take screenshots of the desktop or specific windows
- Agent needs to click, type text, or read window state from native apps
- Agent needs to drive signed-in browser sessions that require native browser (not headless)
- User says "use cua", "drive the desktop", "control my apps"

## How it works

Cua Driver runs as a local daemon (`cua-driver serve`) and exposes tools via MCP (`cua-driver mcp`). The agent connects through the MCP config in `.mcp.json`.

### Key tools
- `list_apps` — enumerate running applications
- `click` — click at coordinates or on a UI element
- `type_text` — type text into the focused window
- `get_window_state` — read window title, position, size
- `screenshot` — capture the screen or a specific window

### Permission modes

| Mode | Use when |
|------|---------|
| `standard` | Normal local use. Observation, input, isolated browser, recording, file transfer without prompts. Default. |
| `bounded` | Unattended agent must stay inside a reviewed manifest of tools, apps, origins, directories. |
| `unrestricted` | Machine is disposable or fully trusted. All capabilities allowed. |

An agent cannot change the permission mode from a tool call. The mode is fixed when the daemon starts.

## Installation

```bash
# macOS
/bin/bash -c "$(curl -fsSL https://cua.ai/driver/install.sh)"
# Windows
irm https://cua.ai/driver/install.ps1 | iex
# Linux
/bin/bash -c "$(curl -fsSL https://cua.ai/driver/install.sh)"
```

Verify: `cua-driver --version` and `cua-driver doctor`.

On macOS, grant Accessibility and Screen Recording permissions:
```bash
cua-driver permissions grant
cua-driver permissions status
```

## MCP config

The `.mcp.json` already includes:
```json
"cua-driver": {
  "command": "cua-driver",
  "args": ["mcp"]
}
```

## Safety

- Cua Driver runs locally — data stays on your machine
- `standard` mode allows input against every application on the desktop
- For unattended agents, use `bounded` mode with a capability manifest
- Never use `unrestricted` mode on a machine with sensitive data
- Telemetry is content-free and can be disabled: `cua-driver telemetry disable`

## Antipatterns

- Using `unrestricted` mode on production machines
- Skipping `cua-driver doctor` after installation
- Not granting macOS TCC permissions before first use
- Assuming the agent can change permission mode at runtime (it cannot)