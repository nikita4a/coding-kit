---
name: mcp-repair
description: "Domain skill. MCP Repair — diagnose and fix MCP server issues. Use when MCP servers fail to connect, tools are unavailable, or config is broken. Covers connectivity, config validation, tool availability checks."
---

# MCP Repair — diagnose and fix MCP server issues

Domain skill. Systematic approach to diagnosing and repairing MCP (Model Context Protocol) server problems.

## When to use

- MCP server shows "not connected" or "disconnected"
- Tools from a specific MCP server are unavailable
- Agent reports tool errors from MCP calls
- After config changes or server restarts

## Diagnostic Workflow

### Step 1: Check connectivity
1. Verify the MCP server process is running.
2. Check the transport: stdio vs HTTP.
3. For HTTP servers, verify the port is accessible.
4. For stdio servers, verify the command and args are correct.

### Step 2: Validate config
1. Check `.mcp.json` or equivalent config file.
2. Verify the server entry has correct `command`, `args`, and `env`.
3. Check for typos in server name or tool names.
4. Ensure the config file is valid JSON.

### Step 3: Check tool availability
1. List available tools from the server.
2. Verify the expected tools are present.
3. Check tool schemas for compatibility.
4. Test a simple tool call to confirm functionality.

### Step 4: Check logs
1. Look for error messages in the MCP server output.
2. Check for authentication failures or permission errors.
3. Look for timeout or resource exhaustion errors.
4. Check the agent's own logs for MCP-related errors.

## Common Issues

| Issue | Likely Cause | Fix |
|-------|-------------|-----|
| Server not connecting | Wrong command or path | Verify the binary exists and is executable |
| Server not connecting | Port conflict (HTTP) | Check if another process uses the port |
| Tools unavailable | Server version mismatch | Update the server or agent |
| Tool returns errors | Invalid arguments | Check tool schema for correct parameter types |
| Connection timeout | Network issue (HTTP) | Verify firewall and network connectivity |
| Server crashes | Missing dependency | Check the server's runtime dependencies |

## Repair Procedures

### Stdio Server
1. Verify the binary exists: `which <command>` or check the path.
2. Test the binary manually: run it directly and check for errors.
3. Check for missing dependencies: `ldd <binary>` or equivalent.
4. Restart the agent after fixing the config.

### HTTP Server
1. Verify the server is running: `curl <url>/health` or equivalent.
2. Check the port is open: `nc -zv <host> <port>`.
3. Verify the URL in config matches the server's actual URL.
4. Check for authentication requirements.

## Anti-patterns

- Restarting everything without diagnosing the root cause
- Ignoring error messages in logs
- Editing config without understanding the schema
- Assuming a server is down when it's a config issue