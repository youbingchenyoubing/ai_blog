from __future__ import annotations

import json
import logging
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Callable

from .device import Device, Message

logger = logging.getLogger("Webhook")


class WebhookMessageHandler(BaseHTTPRequestHandler):
    server_ref = None

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"invalid json")
            return

        device_name = data.get("device_name", "unknown")
        text = data.get("text", "")
        sender = data.get("sender", "unknown")

        msg = Message(
            rowid=int(time.time() * 1000),
            text=text,
            sender=sender,
            is_from_me=False,
            date=time.time(),
            device_name=device_name,
        )

        if self.server_ref and self.server_ref.on_message:
            self.server_ref.on_message(msg)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode())

    def log_message(self, format, *args):
        logger.debug(f"Webhook: {format % args}")


class WebhookServer:
    def __init__(self, port: int = 9876, on_message: Callable[[Message], None] | None = None):
        self.port = port
        self.on_message = on_message
        self.server: HTTPServer | None = None
        self._thread: Thread | None = None

    def start(self):
        handler = WebhookMessageHandler
        handler.server_ref = self

        self.server = HTTPServer(("0.0.0.0", self.port), handler)
        self._thread = Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

        logger.info(f"🌐 Webhook 服务器启动: http://0.0.0.0:{self.port}/")
        logger.info(f"   iPhone 快捷指令 POST 地址: http://<Mac的IP>:{self.port}/")

    def stop(self):
        if self.server:
            self.server.shutdown()
            logger.info("Webhook 服务器已停止")
