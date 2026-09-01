# Cua Driver Setup

Cua Driver is a computer-use agent driver that drives the host desktop: installed apps, signed-in browser sessions, local files, and the current OS user session. It connects via MCP using the `cua-driver mcp` command.

## Installation

```bash
# macOS / Linux
/bin/bash -c "$(curl -fsSL https://cua.ai/driver/install.sh)"
# Windows
irm https://cua.ai/driver/install.ps1 | iex
```

Verify: `cua-driver --version` and `cua-driver doctor`.

## MCP config

The `.mcp.json` template registers Cua Driver as:

```json
{
  "mcpServers": {
    "cua-driver": {
      "command": "cua-driver",
      "args": ["mcp"]
    }
  }
}
```

## Permission modes

| Mode | Use when |
|------|---------|
| `standard` | Normal local use. Observation, input, isolated browser, recording, file transfer without prompts. Default. |
| `bounded` | Unattended agent must stay inside a reviewed manifest of tools, apps, origins, directories. |
| `unrestricted` | Machine is disposable or fully trusted. All capabilities allowed. |

An agent cannot change the permission mode from a tool call — the mode is fixed when the daemon starts.

## macOS TCC permissions

On macOS, grant Accessibility and Screen Recording permissions:

```bash
cua-driver permissions grant
cua-driver permissions status
```

## Safety

- Cua Driver runs locally — data stays on your machine
- `standard` mode allows input against every application on the desktop
- For unattended agents, use `bounded` mode with a capability manifest
- Never use `unrestricted` mode on a machine with sensitive data
- Telemetry is content-free and can be disabled: `cua-driver telemetry disable`

## Companion skill

The `cua-driver` skill in the kit covers when to use, key tools, permission modes, installation, and antipatterns.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| No tools appear | `cua-driver doctor` — daemon running? |
| Permissions error | `cua-driver permissions status` — TCC granted? |
| Agent can't change mode | Mode is fixed at daemon start — restart with `--mode` flag |
| Command not found | `cua-driver` must be on PATH — re-run install script |