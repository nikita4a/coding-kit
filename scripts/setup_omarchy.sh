#!/bin/bash
set -euo pipefail

# =============================================================================
# Omarchy PC Setup Script
# Reproduces the full coding-kit + MCP + Obsidian + memory setup from scratch
# Generated: 2026-09-02
# PC: Omarchy 4.0.2 (Arch Linux), AMD Ryzen 7 5800X, NVIDIA GTX 1660 SUPER
# =============================================================================

echo "=== Omarchy Setup Script ==="
echo "Starting at $(date)"
echo

# ---------------------------------------------------------------------------
# 1. Clone coding-kit
# ---------------------------------------------------------------------------
echo "--- [1/12] Cloning coding-kit ---"
if [ ! -d /tmp/coding-kit ]; then
  git clone --depth 1 https://github.com/nikita4a/coding-kit.git /tmp/coding-kit
else
  echo "  /tmp/coding-kit already exists, pulling latest"
  cd /tmp/coding-kit && git pull
fi
cd /tmp/coding-kit

# ---------------------------------------------------------------------------
# 2. Install memory engine
# ---------------------------------------------------------------------------
echo "--- [2/12] Installing memory engine ---"
python scripts/install.py

# ---------------------------------------------------------------------------
# 3. Deploy skills to all harnesses
# ---------------------------------------------------------------------------
echo "--- [3/12] Deploying skills ---"
python scripts/tools/deploy.py

# ---------------------------------------------------------------------------
# 4. Install Cua Driver
# ---------------------------------------------------------------------------
echo "--- [4/12] Installing Cua Driver ---"
if ! command -v cua-driver &>/dev/null; then
  /bin/bash -c "$(curl -fsSL https://cua.ai/driver/install.sh)"
  echo "  Cua Driver installed: $(cua-driver --version 2>/dev/null || echo 'version check failed')"
else
  echo "  Cua Driver already installed: $(cua-driver --version 2>/dev/null)"
fi

echo "  Installing Cua Driver skills..."
cua-driver skills install 2>&1 || echo "  WARNING: skills install failed (may need auth)"

# ---------------------------------------------------------------------------
# 5. Cua Driver systemd autostart (unrestricted mode)
# ---------------------------------------------------------------------------
echo "--- [5/12] Setting up Cua Driver systemd autostart ---"
mkdir -p ~/.config/systemd/user/

cat > ~/.config/systemd/user/cua-driver.service << 'CUASERVICE'
[Unit]
Description=cua-driver background daemon (unrestricted)
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=%h/.local/bin/cua-driver serve --dangerously-bypass-approvals
Restart=on-failure
RestartSec=2
Environment="DISPLAY=:0"
Environment="WAYLAND_DISPLAY=wayland-1"

[Install]
WantedBy=graphical-session.target
CUASERVICE

systemctl --user daemon-reload
systemctl --user enable --now cua-driver.service 2>&1 || echo "  WARNING: could not enable systemd service"
echo "  Cua Driver autostart configured (unrestricted mode)"

# ---------------------------------------------------------------------------
# 6. Install BrowserMCP and SearchMCP
# ---------------------------------------------------------------------------
echo "--- [6/12] Installing BrowserMCP and SearchMCP ---"
mkdir -p ~/mcps

# Try to copy from AGGG4ks-dist archive
AGGG_SRC="/home/nikita/Downloads/Telegram Desktop/AGGG4ks-dist-2026-09-01/AGGG4ks-dist/mcps"
if [ -d "$AGGG_SRC" ]; then
  echo "  Copying MCPs from $AGGG_SRC"
  cp -r "$AGGG_SRC/BrowserMCP" ~/mcps/ 2>/dev/null || echo "  WARNING: BrowserMCP copy failed"
  cp -r "$AGGG_SRC/SearchMCP" ~/mcps/ 2>/dev/null || echo "  WARNING: SearchMCP copy failed"
else
  echo "  AGGG4ks-dist not found at $AGGG_SRC"
  echo "  Clone manually:"
  echo "    git clone <browsermcp-repo> ~/mcps/BrowserMCP"
  echo "    git clone <searchmcp-repo> ~/mcps/SearchMCP"
fi

# Install dependencies
if [ -d ~/mcps/BrowserMCP ]; then
  echo "  Installing BrowserMCP dependencies..."
  cd ~/mcps/BrowserMCP && uv sync 2>&1 || echo "  WARNING: uv sync failed for BrowserMCP"
fi

if [ -d ~/mcps/SearchMCP ]; then
  echo "  Installing SearchMCP dependencies..."
  cd ~/mcps/SearchMCP && uv sync 2>&1 || echo "  WARNING: uv sync failed for SearchMCP"
fi

# ---------------------------------------------------------------------------
# 7. Camoufox binary download instructions
# ---------------------------------------------------------------------------
echo "--- [7/12] Camoufox ---"
echo "  Camoufox binary must be downloaded manually from GitHub:"
echo "    https://github.com/daijro/camoufox/releases"
echo "  Place at: ~/.cache/camoufox/browsers/official/"
echo "  Then run:"
echo "    cd ~/mcps/BrowserMCP && uv run python -m camoufox fetch"
echo

# ---------------------------------------------------------------------------
# 8. Configure .mcp.json
# ---------------------------------------------------------------------------
echo "--- [8/12] Configuring MCP servers ---"

# OMP .mcp.json
OMP_MCP_DIR=~/.omp/agent
mkdir -p "$OMP_MCP_DIR"

cat > "$OMP_MCP_DIR/.mcp.json" << 'MCPJSON'
{
  "mcpServers": {
    "cua-driver": {
      "command": "cua-driver",
      "args": ["mcp"]
    },
    "browsermcp": {
      "command": "uv",
      "args": ["run", "--project", "$HOME/mcps/BrowserMCP", "browsermcp", "mcp"]
    },
    "searchmcp": {
      "command": "uv",
      "args": ["run", "--project", "$HOME/mcps/SearchMCP", "searchmcp", "mcp"]
    }
  }
}
MCPJSON

# Claude Desktop .mcp.json
mkdir -p ~/.claude
cp "$OMP_MCP_DIR/.mcp.json" ~/.claude/.mcp.json 2>/dev/null || echo "  WARNING: could not copy to ~/.claude/.mcp.json"

echo "  MCP servers configured in $OMP_MCP_DIR/.mcp.json"

# ---------------------------------------------------------------------------
# 9. Install Obsidian
# ---------------------------------------------------------------------------
echo "--- [9/12] Installing Obsidian ---"
if command -v obsidian &>/dev/null; then
  echo "  Obsidian already installed: $(obsidian --version 2>/dev/null || echo 'version check failed')"
else
  if command -v pacman &>/dev/null; then
    sudo pacman -S --noconfirm obsidian 2>&1 || echo "  WARNING: pacman install failed, install manually"
  elif command -v yay &>/dev/null; then
    yay -S --noconfirm obsidian 2>&1 || echo "  WARNING: yay install failed, install manually"
  else
    echo "  Install Obsidian manually: https://obsidian.md/download"
  fi
fi

# ---------------------------------------------------------------------------
# 10. Set up Obsidian vault on disk C
# ---------------------------------------------------------------------------
echo "--- [10/12] Setting up Obsidian vault ---"
OBSIDIAN_VAULT="/mnt/disk_c/ObsidianVault"
mkdir -p "$OBSIDIAN_VAULT/.obsidian"

# Symlink memory directories into vault
ln -sf ~/.memory/Wiki "$OBSIDIAN_VAULT/memory-wiki" 2>/dev/null || echo "  WARNING: could not link Wiki"
ln -sf ~/.memory/db "$OBSIDIAN_VAULT/memory-db" 2>/dev/null || echo "  WARNING: could not link db"
ln -sf ~/.memory/db-tools "$OBSIDIAN_VAULT/memory-db-tools" 2>/dev/null || echo "  WARNING: could not link db-tools"
ln -sf ~/.memory/scripts "$OBSIDIAN_VAULT/memory-scripts" 2>/dev/null || echo "  WARNING: could not link scripts"

echo "  Obsidian vault ready at $OBSIDIAN_VAULT"
echo "  Open with: obsidian $OBSIDIAN_VAULT"

# ---------------------------------------------------------------------------
# 11. Improve internet (DNS, BBR, buffers, mirrors)
# ---------------------------------------------------------------------------
echo "--- [11/12] Optimizing network ---"

# DNS: set Cloudflare on active connection
ACTIVE_CONN=$(nmcli -t -f NAME connection show --active 2>/dev/null | head -1)
if [ -n "$ACTIVE_CONN" ]; then
  echo "  Setting DNS on active connection: $ACTIVE_CONN"
  nmcli connection modify "$ACTIVE_CONN" ipv4.dns "1.1.1.1 1.0.0.1" 2>/dev/null || echo "  WARNING: DNS set failed"
  nmcli connection modify "$ACTIVE_CONN" ipv4.ignore-auto-dns yes 2>/dev/null || true
  nmcli connection up "$ACTIVE_CONN" 2>/dev/null || echo "  WARNING: connection restart failed"
else
  echo "  No active nmcli connection found, skipping DNS config"
fi

# BBR congestion control
echo "  Enabling BBR congestion control..."
echo "net.core.default_qdisc=fq" | sudo tee /etc/sysctl.d/99-bbr.conf >/dev/null
echo "net.ipv4.tcp_congestion_control=bbr" | sudo tee -a /etc/sysctl.d/99-bbr.conf >/dev/null
sudo sysctl -p /etc/sysctl.d/99-bbr.conf 2>&1 || echo "  WARNING: BBR sysctl apply failed"

# Buffer sizes
echo "  Setting TCP buffer sizes..."
cat << 'NETEOF' | sudo tee /etc/sysctl.d/99-network.conf >/dev/null
net.core.rmem_max=16777216
net.core.wmem_max=16777216
net.ipv4.tcp_rmem=4096 87380 16777216
net.ipv4.tcp_wmem=4096 65536 16777216
net.ipv4.tcp_window_scaling=1
net.ipv4.tcp_fastopen=3
NETEOF
sudo sysctl -p /etc/sysctl.d/99-network.conf 2>&1 || echo "  WARNING: network sysctl apply failed"

# Pacman mirrors (best effort)
echo "  Updating pacman mirrors..."
if command -v reflector &>/dev/null; then
  sudo reflector --latest 50 --sort rate --protocol https --number 20 --save /etc/pacman.d/mirrorlist 2>&1 || echo "  WARNING: reflector failed"
else
  echo "  reflector not installed, skipping mirror update"
fi

echo "  Network optimization complete"

# ---------------------------------------------------------------------------
# 12. Verify everything
# ---------------------------------------------------------------------------
echo "--- [12/12] Verification ---"
echo

# Cua Driver
echo ">>> Cua Driver status:"
cua-driver status 2>&1 || echo "  FAILED"
echo

echo ">>> Cua Driver doctor:"
cua-driver doctor 2>&1 || echo "  FAILED"
echo

# coding-kit checks
echo ">>> coding-kit doctor:"
cd /tmp/coding-kit && python scripts/doctor.py 2>&1 || echo "  FAILED"
echo

echo ">>> coding-kit validate skills:"
python scripts/validate_skills.py 2>&1 || echo "  FAILED"
echo

echo ">>> coding-kit scan secrets:"
python scripts/scan_secrets.py 2>&1 || echo "  FAILED"
echo

# MCP server configs
echo ">>> MCP configs:"
ls -la ~/.omp/agent/.mcp.json 2>&1
ls -la ~/.claude/.mcp.json 2>&1
echo

# Obsidian
echo ">>> Obsidian:"
if command -v obsidian &>/dev/null; then
  echo "  Installed: $(obsidian --version 2>/dev/null || echo 'yes')"
else
  echo "  NOT INSTALLED (install manually)"
fi
echo

# Network
echo ">>> Network:"
echo "  Congestion control: $(sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null || echo 'unknown')"
echo "  DNS: $(nmcli -t -f IP4.DNS connection show \"$ACTIVE_CONN\" 2>/dev/null | head -1 || echo 'unknown')"
echo "  BBR: $(sysctl -n net.core.default_qdisc 2>/dev/null || echo 'unknown')"
echo

echo "=== Setup Complete ==="
echo "Finished at $(date)"
echo
echo "Post-setup manual steps:"
echo "  1. Open Obsidian vault: obsidian $OBSIDIAN_VAULT"
echo "  2. Download Camoufox: cd ~/mcps/BrowserMCP && uv run python -m camoufox fetch"
echo "  3. Cua Driver running in unrestricted mode (--dangerously-bypass-approvals is set)"
echo "     - click, type_text, press_key need delivery_mode: 'foreground' on Wayland"
echo "     - screenshot tool not available in v0.23.2; use 'zoom' instead"
echo "     - get_window_state works with pid + window_id"
echo "  4. Reboot to apply all systemd/services"