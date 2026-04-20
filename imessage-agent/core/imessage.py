from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import subprocess
import time
from typing import Optional

from .device import Device, DeviceMode, Message


class IMessageReader:
    def __init__(self, config: dict):
        self.screenshot_dir = os.path.expanduser(
            config.get("wda", {}).get("screenshot_dir", "./screenshots")
        )
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def read_new_messages(self, device: Device) -> list[Message]:
        if device.mode == DeviceMode.MAC:
            return self._read_from_chatdb(device)
        else:
            return self._read_from_wda(device)

    def _read_from_chatdb(self, device: Device) -> list[Message]:
        db_path = os.path.expanduser("~/Library/Messages/chat.db")
        if not os.path.exists(db_path):
            return []

        messages = []
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
                SELECT
                    m.ROWID,
                    m.text,
                    m.is_from_me,
                    m.date,
                    m.service,
                    h.id AS sender_id,
                    cmj.chat_id
                FROM message m
                LEFT JOIN handle h ON m.handle_id = h.ROWID
                LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
                WHERE m.ROWID > ?
                AND m.text IS NOT NULL
                AND m.text != ''
                ORDER BY m.date DESC
                LIMIT 50
            """
            cursor.execute(query, (device.last_message_id,))

            for row in cursor.fetchall():
                msg = Message(
                    rowid=row["ROWID"],
                    text=row["text"] or "",
                    sender=row["sender_id"] or "unknown",
                    is_from_me=bool(row["is_from_me"]),
                    date=row["date"],
                    chat_id=row["chat_id"],
                    service=row["service"],
                    device_name=device.name,
                )
                if msg.rowid > device.last_message_id:
                    device.last_message_id = msg.rowid
                messages.append(msg)

            conn.close()
        except sqlite3.OperationalError as e:
            print(f"[{device.name}] 读取 chat.db 失败: {e}")
            print(f"  请在 系统设置 → 隐私与安全 → 完全磁盘访问权限 中添加终端/Terminal")

        return messages

    def read_from_chatdb_path(self, db_path: str, device: Device) -> list[Message]:
        expanded = os.path.expanduser(db_path)
        if not os.path.exists(expanded):
            return []

        messages = []
        try:
            conn = sqlite3.connect(f"file:{expanded}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
                SELECT
                    m.ROWID,
                    m.text,
                    m.is_from_me,
                    m.date,
                    m.service,
                    h.id AS sender_id,
                    cmj.chat_id
                FROM message m
                LEFT JOIN handle h ON m.handle_id = h.ROWID
                LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
                WHERE m.ROWID > ?
                AND m.text IS NOT NULL
                AND m.text != ''
                ORDER BY m.date DESC
                LIMIT 50
            """
            cursor.execute(query, (device.last_message_id,))

            for row in cursor.fetchall():
                msg = Message(
                    rowid=row["ROWID"],
                    text=row["text"] or "",
                    sender=row["sender_id"] or "unknown",
                    is_from_me=bool(row["is_from_me"]),
                    date=row["date"],
                    chat_id=row["chat_id"],
                    service=row["service"],
                    device_name=device.name,
                )
                if msg.rowid > device.last_message_id:
                    device.last_message_id = msg.rowid
                messages.append(msg)

            conn.close()
        except Exception as e:
            print(f"[{device.name}] 读取 {db_path} 失败: {e}")

        return messages

    def _read_from_wda(self, device: Device) -> list[Message]:
        try:
            import wda
        except ImportError:
            print(f"[{device.name}] 请安装 facebook-wda: pip install facebook-wda")
            return []

        messages = []
        try:
            c = wda.Client(device.wda_url)
            c.app_launch("com.apple.MobileSMS")
            time.sleep(2)

            source = c.source()
            messages = self._parse_messages_from_source(source, device)

        except Exception as e:
            print(f"[{device.name}] WDA 读取消息失败: {e}")

        return messages

    def _parse_messages_from_source(self, source: str, device: Device) -> list[Message]:
        messages = []

        msg_blocks = re.findall(
            r'<XCUIElementTypeStaticText[^>]*value="([^"]*)"[^>]*/>',
            source,
        )

        seen = set()
        for i, text in enumerate(msg_blocks):
            text = text.strip()
            if not text or text in seen:
                continue
            seen.add(text)

            is_from_me = False
            msg = Message(
                rowid=device.last_message_id + i + 1,
                text=text,
                sender="unknown",
                is_from_me=is_from_me,
                date=time.time(),
                device_name=device.name,
            )
            messages.append(msg)

        if messages:
            device.last_message_id = messages[-1].rowid

        return messages

    def take_screenshot(self, device: Device) -> Optional[str]:
        try:
            import wda
        except ImportError:
            return None

        try:
            c = wda.Client(device.wda_url)
            ts = int(time.time())
            path = os.path.join(self.screenshot_dir, f"{device.name}_{ts}.png")
            c.screenshot(path)

            with open(path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()

            if file_hash == device.last_screenshot_hash:
                os.remove(path)
                return None

            device.last_screenshot_hash = file_hash
            return path
        except Exception as e:
            print(f"[{device.name}] 截图失败: {e}")
            return None


class IMessageSender:
    def send_message(self, device: Device, recipient: str, text: str) -> bool:
        if device.mode == DeviceMode.MAC:
            if device.chatdb_path:
                return self._send_via_wda(device, recipient, text)
            else:
                return self._send_via_applescript(recipient, text)
        else:
            return self._send_via_wda(device, recipient, text)

    def _send_via_applescript(self, recipient: str, text: str, mac_user: str = "") -> bool:
        escaped_text = text.replace("\\", "\\\\").replace('"', '\\"')
        escaped_recipient = recipient.replace("\\", "\\\\").replace('"', '\\"')

        applescript = f'''
        tell application "Messages"
            set targetService to 1st account whose service type = iMessage
            set targetBuddy to participant "{escaped_recipient}" of targetService
            send "{escaped_text}" to targetBuddy
        end tell
        '''

        try:
            cmd = ["osascript", "-e", applescript]
            if mac_user:
                cmd = ["sudo", "-u", mac_user] + cmd

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                return True
            else:
                print(f"AppleScript 发送失败: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("AppleScript 发送超时")
            return False
        except Exception as e:
            print(f"AppleScript 发送异常: {e}")
            return False

    def _send_via_wda(self, device: Device, recipient: str, text: str) -> bool:
        try:
            import wda
        except ImportError:
            print(f"[{device.name}] 请安装 facebook-wda: pip install facebook-wda")
            return False

        try:
            c = wda.Client(device.wda_url)
            c.app_launch("com.apple.MobileSMS")
            time.sleep(2)

            new_msg_btn = c(type="Button", name="New Message")
            if new_msg_btn.exists:
                new_msg_btn.click()
                time.sleep(1)
            else:
                c.click(10, 10)
                time.sleep(0.5)
                new_msg_btn = c(type="Button", name="New Message")
                if new_msg_btn.exists:
                    new_msg_btn.click()
                    time.sleep(1)

            to_field = c(type="TextField", nameContains="To")
            if not to_field.exists:
                to_field = c(type="SearchField", index=0)
            if to_field.exists:
                to_field.click()
                time.sleep(0.3)
                to_field.set_text(recipient)
                time.sleep(1.5)

                first_result = c(type="Cell", index=0)
                if first_result.exists:
                    first_result.click()
                    time.sleep(1)

            msg_field = c(type="TextView", nameContains="iMessage")
            if not msg_field.exists:
                msg_field = c(type="TextView", nameContains="Message")
            if not msg_field.exists:
                msg_field = c(type="TextView", index=0)
            if msg_field.exists:
                msg_field.click()
                time.sleep(0.3)
                msg_field.set_text(text)
                time.sleep(0.5)

                send_btn = c(type="Button", name="Send")
                if not send_btn.exists:
                    send_btn = c(type="Button", nameContains="Send")
                if send_btn.exists:
                    send_btn.click()
                    time.sleep(1)
                    return True

            print(f"[{device.name}] 未找到消息输入框或发送按钮")
            return False
        except Exception as e:
            print(f"[{device.name}] WDA 发送消息失败: {e}")
            return False

    def broadcast(self, devices: list[Device], recipients: list[str], text: str) -> dict[str, bool]:
        results = {}
        for device in devices:
            for recipient in recipients:
                success = self.send_message(device, recipient, text)
                results[f"{device.name}->{recipient}"] = success
                time.sleep(1)
        return results
