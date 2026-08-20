"""
Async WebSocket & HTTP Server for Zotaque Motion Cues.
Broadcasts realtime filtered 2D motion cues vectors to overlays and Decky plugins.
"""

import asyncio
import json
import logging
import time
from typing import Set

try:
    import websockets
except ImportError:
    websockets = None

from zotaque.motion_cues.filter import MotionCuesFilter
from zotaque.motion_cues.overlay_html import OVERLAY_HTML
from zotaque.motion_cues.sensor import IIOIMUSensor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zotaque.motion_cues")


class MotionCuesServer:
    """Streams sensor motion vectors to WebSocket clients at 50Hz."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.sensor = IIOIMUSensor()
        self.filter = MotionCuesFilter(cutoff_hz=1.5, sample_rate_hz=50.0, sensitivity=1.3)
        self.connected_clients: Set[any] = set()
        self.running = False

    async def _handle_http(self, path: str, request_headers: dict) -> tuple:
        """Serves the transparent canvas overlay directly over HTTP."""
        if path == "/" or path == "/index.html":
            return (
                200,
                [
                    ("Content-Type", "text/html; charset=utf-8"),
                    ("Content-Length", str(len(OVERLAY_HTML.encode("utf-8")))),
                    ("Access-Control-Allow-Origin", "*"),
                ],
                OVERLAY_HTML.encode("utf-8"),
            )
        return None

    async def _ws_handler(self, websocket):
        """Registers connected WebSocket clients."""
        self.connected_clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address} (Total: {len(self.connected_clients)})")
        try:
            async for message in websocket:
                # Can accept runtime sensitivity or config tweaks from client
                pass
        except Exception:
            pass
        finally:
            self.connected_clients.remove(websocket)
            logger.info(f"Client disconnected (Total: {len(self.connected_clients)})")

    async def _sensor_sampling_loop(self):
        """Samples IIO sensor at 50Hz and broadcasts filtered coordinates."""
        interval = 1.0 / 50.0
        while self.running:
            start_time = time.time()
            sample = self.sensor.read_sample()
            vec = self.filter.process_imu_sample(
                sample["accel_x"],
                sample["accel_y"],
                sample["accel_z"],
                timestamp=sample["timestamp"]
            )

            if self.connected_clients:
                payload = json.dumps(vec)
                # Broadcast to all active clients
                await asyncio.gather(
                    *[client.send(payload) for client in list(self.connected_clients)],
                    return_exceptions=True
                )

            elapsed = time.time() - start_time
            sleep_time = max(0.001, interval - elapsed)
            await asyncio.sleep(sleep_time)

    async def start(self):
        """Starts WebSocket server and sampling loop."""
        if websockets is None:
            raise RuntimeError("websockets package required. Install with: pip install websockets")

        self.running = True
        logger.info(f"Starting Motion Cues Server on ws://{self.host}:{self.port}/ws")
        logger.info(f"Overlay available at http://{self.host}:{self.port}/")

        async with websockets.serve(
            self._ws_handler,
            self.host,
            self.port,
            process_request=self._handle_http
        ):
            await self._sensor_sampling_loop()


def run_server(host: str = "0.0.0.0", port: int = 8765):
    """Entrypoint to run the async motion cues daemon."""
    server = MotionCuesServer(host=host, port=port)
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Motion cues server stopped.")
