#!/bin/bash
set -e

SYSTEMD_DIR="${HOME}/.config/systemd/user"
mkdir -p "${SYSTEMD_DIR}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing Zotaque user services to ${SYSTEMD_DIR}..."
cp "${SCRIPT_DIR}"/zotaque-*.service "${SYSTEMD_DIR}/"

systemctl --user daemon-reload

echo "Enabling Zotaque services..."
systemctl --user enable --now zotaque-rgb.service || true
systemctl --user enable --now zotaque-dials.service || true
systemctl --user enable --now zotaque-motion-cues.service || true

echo "Zotaque services installed and started successfully."
echo "Check status with: systemctl --user status zotaque-motion-cues.service"
