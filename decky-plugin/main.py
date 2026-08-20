import json
import os
import socket
import sys
from pathlib import Path
import decky_plugin

PLUGIN_DIR = Path(__file__).resolve().parent
SOCKET_PATH = "/tmp/zotaque.sock"


def send_ipc_cmd(cmd_dict: dict) -> dict:
    """Sends a JSON command to the native Rust overlay daemon."""
    if not os.path.exists(SOCKET_PATH):
        return {"status": "daemon_not_running"}
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(0.5)
        client.connect(SOCKET_PATH)
        payload = json.dumps(cmd_dict) + "\n"
        client.sendall(payload.encode("utf-8"))
        data = client.recv(1024).decode("utf-8")
        client.close()
        return json.loads(data)
    except Exception as e:
        return {"status": "error", "error": str(e)}


class Plugin:
    async def _main(self):
        decky_plugin.logger.info("Zotaque Decky Plugin Initialized")

    async def _unload(self):
        decky_plugin.logger.info("Zotaque Decky Plugin Unloaded")

    async def toggle_motion_cues(self, enabled: bool):
        """Toggles native Rust overlay on/off."""
        cmd = {"cmd": "enable"} if enabled else {"cmd": "disable"}
        return send_ipc_cmd(cmd)

    async def update_motion_config(self, tilt_sensitivity: float = 1.0, dot_color_hex: str = "#00e5ff"):
        """Sends updated sliders to the native Rust overlay."""
        return send_ipc_cmd({
            "cmd": "set_config",
            "tilt_sensitivity": float(tilt_sensitivity),
            "dot_color_hex": dot_color_hex
        })

    async def get_overlay_status(self):
        """Checks if native Rust daemon is running."""
        return send_ipc_cmd({"cmd": "get_status"})
