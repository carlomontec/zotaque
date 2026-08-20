"""
Zero-Dependency HTTP & Server-Sent Events (SSE) Server for Zotaque Motion Cues.
Streams realtime IMU motion vectors at 50Hz and saves GUI calibration preferences.
"""

import json
import logging
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

# Ensure project root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from zotaque.core.config import load_config, save_config
from zotaque.motion_cues.filter import MotionCuesFilter
from zotaque.motion_cues.overlay_html import OVERLAY_HTML
from zotaque.motion_cues.sensor import IIOIMUSensor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("zotaque.motion_cues")

# Global instances
SENSOR = IIOIMUSensor()
FILTER = MotionCuesFilter()


class MotionCuesHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests, SSE stream, and configuration updates."""

    def log_message(self, format, *args):
        # Suppress noisy HTTP access logs during continuous SSE streaming
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            content = OVERLAY_HTML.encode("utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        elif self.path == "/events":
            # Server-Sent Events stream
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            interval = 1.0 / 50.0  # 50 Hz
            try:
                while True:
                    start_t = time.time()
                    sample = SENSOR.read_sample()
                    vec = FILTER.process_imu_sample(
                        sample["accel_x"],
                        sample["accel_y"],
                        sample["accel_z"],
                        timestamp=sample["timestamp"]
                    )
                    payload = f"data: {json.dumps(vec)}\n\n"
                    self.wfile.write(payload.encode("utf-8"))
                    self.wfile.flush()

                    elapsed = time.time() - start_t
                    sleep_time = max(0.001, interval - elapsed)
                    time.sleep(sleep_time)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/config":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                new_cfg = json.loads(body)

                # Update live filter
                FILTER.update_parameters(new_cfg)

                # Persist to disk
                cfg = load_config()
                cfg.setdefault("motion_cues", {}).update(new_cfg)
                save_config(cfg)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"status":"saved"}')
            except Exception as ex:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f'{{"error":"{ex}"}}'.encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()


def run_server(host: str = "0.0.0.0", port: int = 8765):
    """Starts the zero-dependency Motion Cues HTTP + SSE server."""
    # Load initial config into filter
    cfg = load_config().get("motion_cues", {})
    FILTER.update_parameters(cfg)

    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, MotionCuesHandler)
    logger.info(f"Zotaque Motion Cues Server listening on http://{host}:{port}/")
    logger.info(f"Open http://localhost:{port} in your browser or Steam Game Mode overlay.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping Motion Cues server...")
        httpd.shutdown()


if __name__ == "__main__":
    run_server()
