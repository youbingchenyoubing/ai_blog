from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from telethon.errors import FloodWaitError

from .account import AccountManager
from .ai import AIReplier, SimpleRuleReplier
from .survival import SurvivalGuard
from .telegram_client import TelegramReader, TelegramSender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Scheduler")


class MessageScheduler:
    """多账户 Telegram 调度引擎（异步）"""

    def __init__(self, config_path: str = "config.yaml"):
        self.am = AccountManager(config_path)
        self.config = self.am.config
        self.reader = TelegramReader()
        self.sender = TelegramSender()
        self.guard = SurvivalGuard(self.config)

        ai_mode = self.config.get("ai", {}).get("provider", "openai")
        if ai_mode == "openai":
            self.replier = AIReplier(self.config)
        else:
            self.replier = SimpleRuleReplier(self.config)

        self.poll_interval = self.config.get("global", {}).get("poll_interval", 5)
        self._running = False
        self._stop_event: asyncio.Event | None = None
        self._keepalive_task: asyncio.Task | None = None

    # ---------- 生命周期 ----------

    async def start(self):
        logger.info("=" * 50)
        logger.info("  Telegram 多账户 Agent 启动")
        logger.info("=" * 50)

        await self.am.start_all(interactive=True)
        online = self.am.get_online_accounts()
        logger.info(f"在线账户: {len(online)}/{len(self.am.accounts)}")
        for a in online:
            tag = f"@{a.me_username}" if a.me_username else f"id={a.me_id}"
            warmup_tag = " (养号期)" if self.guard.in_warmup(a) else ""
            logger.info(f"  ✅ {a.name} ({a.type.value}) {tag}{warmup_tag}")

        if not online:
            logger.warning("没有在线账户")
            return

        self._running = True
        self._stop_event = asyncio.Event()

        # 启动保活后台任务
        if self.guard.enabled:
            self._keepalive_task = asyncio.create_task(
                self.guard.keepalive_loop(online, self._stop_event)
            )

        broadcast_cfg = self.config.get("broadcast", {})
        auto_reply_cfg = self.config.get("auto_reply", {})

        if broadcast_cfg.get("enabled", False):
            await self._run_broadcast(broadcast_cfg)

        if auto_reply_cfg.get("enabled", False):
            await self._run_auto_reply_loop()
        else:
            logger.info("自动回复未启用，仅执行群发")

    async def stop(self):
        self._running = False
        if self._stop_event:
            self._stop_event.set()
        if self._keepalive_task:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
        await self.am.stop_all()
        logger.info("已停止")

    # ---------- 群发 ----------

    async def _run_broadcast(self, cfg: dict):
        message = cfg.get("message", "")
        recipients = cfg.get("recipients", [])
        if not message or not recipients:
            logger.warning("群发配置不完整，跳过")
            return

        logger.info(f"📢 群发消息: {message}")
        logger.info(f"   收件人: {recipients}")

        accounts = self.am.get_online_accounts()
        if not accounts:
            logger.warning("没有在线账户，跳过群发")
            return

        # 存活率检查
        for a in accounts:
            if not await self.guard.before_send(a):
                logger.warning(f"  [{a.name}] 存活率检查未通过，跳过")
                continue
            await self.guard.human_delay(2, 5)

        results = await self.sender.broadcast(accounts, recipients, message)
        for key, ok in results.items():
            icon = "✅" if ok else "❌"
            logger.info(f"  {icon} {key}")
            # 更新指标
            account_name = key.split(" -> ")[0]
            a = self.am.find_account(account_name)
            if a:
                await self.guard.after_send(a, ok)
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"群发完成: {success_count}/{len(results)} 成功")

    # ---------- 自动回复循环 ----------

    async def _run_auto_reply_loop(self):
        logger.info(f"🔄 自动回复已启用，轮询间隔: {self.poll_interval}s")
        if self.guard.enabled:
            logger.info(f"💓 保活已启用，间隔: {self.guard.keepalive_interval}s")
        logger.info("按 Ctrl+C 停止")
        try:
            while self._running:
                await self._poll_all_accounts()
                await asyncio.sleep(self.poll_interval)
        except KeyboardInterrupt:
            await self.stop()

    async def _poll_all_accounts(self):
        accounts = self.am.get_online_accounts()
        # 并发轮询所有账户
        await asyncio.gather(
            *(self._poll_account(a) for a in accounts),
            return_exceptions=True,
        )

    async def _poll_account(self, account):
        try:
            messages = await self.reader.read_new_messages(account)
        except FloodWaitError as e:
            await self.guard.on_flood_wait(account, e.seconds)
            return
        except Exception as e:
            logger.error(f"[{account.name}] 读取异常: {e}")
            return

        # 读取成功也算一次保活
        m = self.guard.get_metrics(account)
        m.last_active = datetime.now().timestamp()

        incoming = [m for m in messages if not m.is_from_me]
        if not incoming:
            return

        for msg in incoming:
            time_str = datetime.now().strftime("%H:%M:%S")
            logger.info(f"[{account.name}] {time_str} 收到消息:")
            logger.info(f"  📨 {msg.sender_name} ({msg.chat_type}): {msg.text[:50]}")
            try:
                # 回复前过存活率检查
                if not await self.guard.before_send(account):
                    continue
                await self.replier.process_message(account, msg, self.sender)
                await self.guard.after_send(account, True)
            except FloodWaitError as e:
                await self.guard.on_flood_wait(account, e.seconds)
            except Exception as e:
                logger.error(f"[{account.name}] 回复异常: {e}")
                await self.guard.after_send(account, False)

    # ---------- 手动操作 ----------

    async def send_to_all(self, text: str, recipients: list[str] | None = None):
        accounts = self.am.get_online_accounts()
        if not recipients:
            logger.error("请指定收件人")
            return
        logger.info(f"📢 发送消息到 {len(recipients)} 个收件人")

        results = {}
        for account in accounts:
            if not await self.guard.before_send(account):
                logger.warning(f"  [{account.name}] 存活率检查未通过，跳过")
                continue
            for recipient in recipients:
                key = f"{account.name} -> {recipient}"
                try:
                    ok = await self.sender.send_message(account, recipient, text)
                except FloodWaitError as e:
                    await self.guard.on_flood_wait(account, e.seconds)
                    ok = False
                results[key] = ok
                await self.guard.after_send(account, ok)
                icon = "✅" if ok else "❌"
                logger.info(f"  {icon} {key}")
                # 每条消息间模拟真人间隔
                await self.guard.human_delay(1, 3)

    async def status(self):
        await self.am.health_check()
        logger.info("=" * 60)
        logger.info("  账户状态")
        logger.info("=" * 60)
        status_icon = {
            "online": "🟢",
            "offline": "🔴",
            "need_login": "🟡",
            "error": "❌",
        }
        for a in self.am.accounts:
            icon = status_icon.get(a.status.value, "❓")
            extra = f" | @{a.me_username}" if a.me_username else ""
            extra += f" | id={a.me_id}" if a.me_id else ""
            # 附带健康分
            m = self.guard.get_metrics(a)
            health = f" | 健康={m.health_score:.0f}"
            warmup = " | 养号期" if self.guard.in_warmup(a) else ""
            logger.info(f"  {icon} {a.name} | {a.type.value}{extra}{health}{warmup}")
