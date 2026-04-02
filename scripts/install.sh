#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_CONFIG_DIR="${HOME}/.config/nyxplay"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"

echo "[nyxplay] Installing package..."
python -m pip install --user "${PROJECT_DIR}"

echo "[nyxplay] Installing user config if missing..."
mkdir -p "${USER_CONFIG_DIR}"
if [[ ! -f "${USER_CONFIG_DIR}/config.toml" ]]; then
  cp "${PROJECT_DIR}/src/nyxplay/data/default_config.toml" "${USER_CONFIG_DIR}/config.toml"
fi

echo "[nyxplay] Installing systemd user service..."
mkdir -p "${SYSTEMD_USER_DIR}"
cp "${PROJECT_DIR}/systemd/nyxplay.service" "${SYSTEMD_USER_DIR}/nyxplay.service"

echo "[nyxplay] Reloading systemd user daemon..."
systemctl --user daemon-reload

echo "[nyxplay] Done."
echo
echo "To enable the service:"
echo "  systemctl --user enable --now nyxplay.service"
echo
echo "To inspect logs:"
echo "  journalctl --user -u nyxplay.service -f"