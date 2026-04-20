from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from .ai import AIReplier, SimpleRuleReplier
from .device import Device, DeviceManager, DeviceMode, DeviceStatus, Message
from .imessage import IMessageReader, IMessageSender
from .webhook import WebhookServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Scheduler")


class MessageScheduler:
    def __init__(self, config_path: str = "config.yaml"):
        self.dm = DeviceManager(config_path)
        self.config = self.dm.config
        self.reader = IMessageReader(self.config)
        self.sender = IMessageSender()

        ai_mode = self.config.get("ai", {}).get("provider", "openai")
        if ai_mode == "openai":
            self.replier = AIReplier(self.config)
        else:
            self.replier = SimpleRuleReplier(self.config)

        self._running = False
        self._webhook: WebhookServer | None = None

    def start(self):
        logger.info("=" * 50)
        logger.info("  iMessage 群控 Agent 启动")
        logger.info("=" * 50)

        self.dm.health_check()
        online = self.dm.get_online_devices()
        logger.info(f"在线设备: {len(online)}/{len(self.dm.devices)}")
        for d in online:
            logger.info(f"  ✅ {d.name} ({d.mode.value}) - 端口 {d.local_port}")

        if not online:
            logger.warning("没有在线设备")

        self._running = True

        broadcast_cfg = self.config.get("broadcast", {})
        auto_reply_cfg = self.config.get("auto_reply", {})
        webhook_cfg = self.config.get("webhook", {})

        if broadcast_cfg.get("enabled", False):
            self._run_broadcast(broadcast_cfg)

        if webhook_cfg.get("enabled", False):
            self._start_webhook_mode(webhook_cfg)
        elif auto_reply_cfg.get("enabled", False):
            self._run_auto_reply_loop()
        else:
            logger.info("自动回复和 Webhook 均未启用，仅执行群发")

    def stop(self):
        self._running = False
        if self._webhook:
            self._webhook.stop()
        logger.info("已停止")

    def _start_webhook_mode(self, cfg: dict):
        port = cfg.get("port", 9876)
        self._webhook = WebhookServer(port=port, on_message=self._on_webhook_message)
        self._webhook.start()

        logger.info("=" * 50)
        logger.info("  📱 Webhook 模式已启用")
        logger.info("=" * 50)
        logger.info("请在每台 iPhone 上配置快捷指令：")
        logger.info(f"  1. 打开「快捷指令」→「自动化」→「创建个人自动化」")
        logger.info(f"  2. 触发条件选择「信息」→「收到信息」")
        logger.info(f"  3. 添加操作：「获取 URL 内容」")
        logger.info(f"  4. URL: http://<Mac的IP>:{port}/")
        logger.info(f"  5. 方法: POST")
        logger.info(f"  6. 请求体 JSON:")
        logger.info(f'     {{"device_name": "iPhone名称", "text": "消息内容", "sender": "发送者"}}')
        logger.info(f"  7. 关闭「运行前问询」")
        logger.info("")
        logger.info("按 Ctrl+C 停止")

        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def _on_webhook_message(self, message: Message):
        time_str = datetime.now().strftime("%H:%M:%S")
        logger.info(f"[Webhook] {time_str} 收到消息:")
        logger.info(f"  📨 [{message.device_name}] {message.sender}: {message.text[:80]}")

        device = self._find_device(message.device_name)
        if not device:
            logger.warning(f"  未找到设备: {message.device_name}，跳过回复")
            return

        reply_text = self.replier.process_message(device, message, self.sender)
        if reply_text:
            success = self.sender.send_message(device, message.sender, reply_text)
            if success:
                logger.info(f"  ✅ 已回复 {message.sender}")
            else:
                logger.warning(f"  ❌ 回复失败 {message.sender}")

    def _find_device(self, name: str) -> Device | None:
        for d in self.dm.devices:
            if d.name == name:
                return d
        if self.dm.devices:
            return self.dm.devices[0]
        return None

    def _run_broadcast(self, cfg: dict):
        message = cfg.get("message", "")
        recipients = cfg.get("recipients", [])

        if not message or not recipients:
            logger.warning("群发配置不完整，跳过")
            return

        logger.info(f"📢 群发消息: {message}")
        logger.info(f"   收件人: {recipients}")

        devices = self.dm.get_online_devices()
        if not devices:
            logger.warning("没有在线设备，跳过群发")
            return

        results = self.sender.broadcast(devices, recipients, message)

        for key, success in results.items():
            icon = "✅" if success else "❌"
            logger.info(f"  {icon} {key}")

        success_count = sum(1 for v in results.values() if v)
        logger.info(f"群发完成: {success_count}/{len(results)} 成功")

    def _run_auto_reply_loop(self):
        poll_interval = self.config.get("mac", {}).get("poll_interval", 5)
        if any(d.mode.value == "wda" for d in self.dm.devices):
            poll_interval = max(poll_interval, self.config.get("wda", {}).get("poll_interval", 10))

        logger.info(f"🔄 自动回复已启用（轮询模式），间隔: {poll_interval}s")
        logger.info("按 Ctrl+C 停止")

        try:
            while self._running:
                self._poll_all_devices()
                time.sleep(poll_interval)
        except KeyboardInterrupt:
            self.stop()

    def _poll_all_devices(self):
        devices = self.dm.get_online_devices()

        with ThreadPoolExecutor(max_workers=len(devices) or 1) as pool:
            futures = {pool.submit(self._poll_device, d): d for d in devices}
            for future in as_completed(futures):
                device = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"[{device.name}] 轮询异常: {e}")

    def _poll_device(self, device: Device):
        if device.mode == DeviceMode.MAC and device.chatdb_path:
            messages = self.reader.read_from_chatdb_path(device.chatdb_path, device)
        else:
            messages = self.reader.read_new_messages(device)

        incoming = [m for m in messages if not m.is_from_me]
        if not incoming:
            return

        for msg in incoming:
            time_str = datetime.now().strftime("%H:%M:%S")
            logger.info(f"[{device.name}] {time_str} 收到消息:")
            logger.info(f"  📨 {msg.sender}: {msg.text[:50]}")

            reply_text = self.replier.process_message(device, msg, self.sender)
            if reply_text:
                success = self.sender.send_message(device, msg.sender, reply_text)
                if success:
                    logger.info(f"  ✅ 已回复 {msg.sender}")
                else:
                    logger.warning(f"  ❌ 回复失败 {msg.sender}")

    def send_to_all(self, text: str, recipients: list[str] | None = None):
        devices = self.dm.get_online_devices()
        if not recipients:
            logger.error("请指定收件人")
            return
        logger.info(f"📢 发送消息到 {len(recipients)} 个收件人")
        results = self.sender.broadcast(devices, recipients, text)
        for key, success in results.items():
            icon = "✅" if success else "❌"
            logger.info(f"  {icon} {key}")

    def status(self):
        self.dm.health_check()
        logger.info("=" * 50)
        logger.info("  设备状态")
        logger.info("=" * 50)
        for d in self.dm.devices:
            status_icon = {"online": "🟢", "busy": "🟡", "offline": "🔴"}
            icon = status_icon.get(d.status.value, "❓")
            extra = f" | chat.db: {d.chatdb_path}" if d.chatdb_path else ""
            logger.info(f"  {icon} {d.name} | {d.mode.value} | 端口 {d.local_port}{extra}")
