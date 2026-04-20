from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import yaml


class DeviceMode(Enum):
    MAC = "mac"
    WDA = "wda"


class DeviceStatus(Enum):
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass
class Device:
    name: str
    udid: str
    local_port: int
    mode: DeviceMode = DeviceMode.WDA
    apple_id: str = ""
    chatdb_path: str = ""
    status: DeviceStatus = DeviceStatus.OFFLINE
    current_task: Optional[str] = None
    last_message_id: int = 0
    last_screenshot_hash: str = ""

    @property
    def wda_url(self) -> str:
        return f"http://localhost:{self.local_port}"

    def check_online(self) -> bool:
        if self.mode == DeviceMode.WDA:
            try:
                import urllib.request
                resp = urllib.request.urlopen(f"{self.wda_url}/status", timeout=3)
                self.status = DeviceStatus.ONLINE if resp.status == 200 else DeviceStatus.OFFLINE
            except Exception:
                self.status = DeviceStatus.OFFLINE
        else:
            self.status = DeviceStatus.ONLINE
        return self.status == DeviceStatus.ONLINE


@dataclass
class Message:
    rowid: int
    text: str
    sender: str
    is_from_me: bool
    date: float
    chat_id: Optional[int] = None
    service: Optional[str] = None
    device_name: str = ""


class DeviceManager:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.devices: list[Device] = []
        self._init_devices()

    def _init_devices(self):
        for d in self.config.get("devices", []):
            device = Device(
                name=d["name"],
                udid=d["udid"],
                local_port=d["local_port"],
                mode=DeviceMode(d.get("mode", "wda")),
                apple_id=d.get("apple_id", ""),
                chatdb_path=d.get("chatdb_path", ""),
            )
            self.devices.append(device)

    def get_online_devices(self) -> list[Device]:
        return [d for d in self.devices if d.status == DeviceStatus.ONLINE]

    def health_check(self):
        for device in self.devices:
            device.check_online()

    def start_iproxy(self):
        for device in self.devices:
            if device.mode == DeviceMode.WDA:
                subprocess.Popen(
                    ["iproxy", str(device.local_port), "8100", "-u", device.udid],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                time.sleep(0.5)
