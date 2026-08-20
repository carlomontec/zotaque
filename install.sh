#!/usr/bin/env bash
set -e

echo "=== Installing Zotaque Companion Suite for ZOTAC GAMING ZONE ==="

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOMEBREW_PLUGINS="${HOME}/homebrew/plugins"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"

# 1. Install Systemd User Services
echo "-> Installing systemd background services..."
mkdir -p "${SYSTEMD_USER_DIR}"
cp "${PROJECT_DIR}"/systemd/zotaque-*.service "${SYSTEMD_USER_DIR}/"
sed -i "s|%h/.local/bin/zotaque motion-cues|python3 ${PROJECT_DIR}/zotaque/motion_cues/server.py|g" "${SYSTEMD_USER_DIR}/zotaque-motion-cues.service"
systemctl --user daemon-reload
systemctl --user enable --now zotaque-motion-cues.service

# 2. Deploy Decky Loader Plugin
if [ -d "${HOMEBREW_PLUGINS}" ]; then
    echo "-> Deploying Zotaque plugin to Decky Loader..."
    mkdir -p "${HOMEBREW_PLUGINS}/Zotaque"
    cp -r "${PROJECT_DIR}/decky-plugin/"* "${HOMEBREW_PLUGINS}/Zotaque/"
    chmod -R 755 "${HOMEBREW_PLUGINS}/Zotaque"
    echo "-> Restarting plugin_loader.service..."
    sudo systemctl restart plugin_loader.service || true
    echo "-> Decky Plugin installed successfully!"
else
    echo "-> Note: Decky plugins folder (${HOMEBREW_PLUGINS}) not found. Skipping plugin link."
fi

echo "=== Zotaque Installation Complete! ==="
echo "Open the Quick Access Menu (...) in Gaming Mode to find the Zotaque plugin."
