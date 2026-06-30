from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from telethon.errors import (
    FloodWaitError,
    UserDeactivatedError,
    AuthKeyError,
    UserBannedInChannelError,
)

from .account import Account, AccountStatus

logger = logging.getLogger("Survival")


@dataclass
class SurvivalMetrics:
    """账户存活率指标"""
    account_name: str
    last_active: float = 0.0           # 最后一次活动时间戳
    last_flood_wait: float = 0.0       # 最后一次 FloodWait 时间
    flood_wait_count: int = 0          # FloodWait 总次数
    send_count_24h: int = 0            # 24 小时内发送数
    send_window_start: float = 0.0     # 24 小时窗口起点
    health_score: float = 100.0        # 健康分（0-100）
    warnings: list[str] = field(default_factory=list)


class RateLimiter:
    """滑动窗口限流器，避免触发 Telegram 频率限制"""

    def __init__(self, max_per_minute: int = 20, max_per_hour: int = 200):
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self._minute_window: list[float] = []
        self._hour_window: list[float] = []

    def allow(self) -> tuple[bool, float]:
        """返回 (是否允许, 需等待秒数)"""
        now = time.time()
        # 清理过期记录
        self._minute_window = [t for t in self._minute_window if now - t < 60]
        self._hour_window = [t for t in self._hour_window if now - t < 3600]

        if len(self._minute_window) >= self.max_per_minute:
            wait = 60 - (now - self._minute_window[0])
            return False, max(wait, 1)
        if len(self._hour_window) >= self.max_per_hour:
            wait = 3600 - (now - self._hour_window[0])
            return False, max(wait, 1)

        self._minute_window.append(now)
        self._hour_window.append(now)
        return True, 0


class SurvivalGuard:
    """账户存活率优化：行为模拟、频率控制、保活、健康监测"""

    def __init__(self, config: dict):
        survival_cfg = config.get("survival", {})
        self.enabled = survival_cfg.get("enabled", True)
        self.warmup_days = survival_cfg.get("warmup_days", 3)          # 新号养号期
        self.keepalive_interval = survival_cfg.get("keepalive_interval", 1800)  # 保活间隔（秒）
        self.active_hours = survival_cfg.get("active_hours", [8, 23])  # 活跃时段
        self.jitter_max = survival_cfg.get("jitter_max", 5)            # 操作抖动（秒）

        # 频率限制（保守值，低于 Telegram 阈值）
        rate_cfg = survival_cfg.get("rate_limit", {})
        self.limiters: dict[str, RateLimiter] = {}
        self.default_limiter = RateLimiter(
            max_per_minute=rate_cfg.get("per_minute", 15),
            max_per_hour=rate_cfg.get("per_hour", 150),
        )

        # 每个账户的指标
        self.metrics: dict[str, SurvivalMetrics] = {}

        # 账户注册时间（用于判断养号期）—— 从 session 文件首次创建推算
        self._account_birth: dict[str, float] = {}

    # ---------- 指标 ----------

    def get_metrics(self, account: Account) -> SurvivalMetrics:
        if account.name not in self.metrics:
            self.metrics[account.name] = SurvivalMetrics(account_name=account.name)
        return self.metrics[account.name]

    def get_limiter(self, account: Account) -> RateLimiter:
        """每个账户独立限流器"""
        if account.name not in self.limiters:
            self.limiters[account.name] = RateLimiter(
                max_per_minute=self.default_limiter.max_per_minute,
                max_per_hour=self.default_limiter.max_per_hour,
            )
        return self.limiters[account.name]

    # ---------- 行为模拟 ----------

    def is_active_hours(self) -> bool:
        """当前是否在活跃时段"""
        if not self.active_hours or len(self.active_hours) != 2:
            return True
        hour = datetime.now().hour
        return self.active_hours[0] <= hour < self.active_hours[1]

    async def human_delay(self, min_s: float = 1.0, max_s: float = 3.0):
        """模拟真人操作间隔"""
        delay = random.uniform(min_s, max_s) + random.uniform(0, self.jitter_max)
        await asyncio.sleep(delay)

    def in_warmup(self, account: Account) -> bool:
        """是否在养号期内"""
        birth = self._account_birth.get(account.name)
        if not birth:
            return False
        return (time.time() - birth) < self.warmup_days * 86400

    def set_account_birth(self, account: Account, ts: float):
        self._account_birth[account.name] = ts

    # ---------- 操作前检查 ----------

    async def before_send(self, account: Account) -> bool:
        """发送消息前的检查"""
        if not self.enabled:
            return True

        m = self.get_metrics(account)

        # 1. 活跃时段限制（非活跃时段降低操作频率）
        if not self.is_active_hours():
            # 非活跃时段仅允许 1/3 的操作
            if random.random() > 0.3:
                logger.debug(f"[{account.name}] 非活跃时段，跳过本次操作")
                return False

        # 2. 养号期内严格限制
        if self.in_warmup(account):
            limiter = self.get_limiter(account)
            limiter.max_per_minute = min(limiter.max_per_minute, 5)
            limiter.max_per_hour = min(limiter.max_per_hour, 30)

        # 3. 健康分过低
        if m.health_score < 30:
            logger.warning(f"[{account.name}] 健康分过低({m.health_score:.0f})，暂停操作")
            return False

        # 4. 限流
        limiter = self.get_limiter(account)
        allowed, wait = limiter.allow()
        if not allowed:
            logger.info(f"[{account.name}] 限流，需等待 {wait:.0f}s")
            await asyncio.sleep(min(wait, 30))  # 最多等 30s
            return False

        # 5. FloodWait 后冷却
        if m.last_flood_wait and time.time() - m.last_flood_wait < 300:
            logger.info(f"[{account.name}] FloodWait 冷却中")
            return False

        return True

    async def after_send(self, account: Account, success: bool):
        """发送消息后的状态更新"""
        m = self.get_metrics(account)
        m.last_active = time.time()
        if success:
            m.send_count_24h += 1
            m.health_score = min(100, m.health_score + 0.1)
        else:
            m.health_score = max(0, m.health_score - 2)

    async def on_flood_wait(self, account: Account, seconds: int):
        """收到 FloodWait 时的处理"""
        m = self.get_metrics(account)
        m.last_flood_wait = time.time()
        m.flood_wait_count += 1
        # 惩罚健康分
        m.health_score = max(0, m.health_score - min(seconds / 10, 20))
        logger.warning(
            f"[{account.name}] FloodWait {seconds}s，健康分降至 {m.health_score:.0f}"
        )

    # ---------- 保活 ----------

    async def keepalive_once(self, account: Account) -> bool:
        """单次保活操作：读取对话列表 + 标记已读 + 获取自身资料

        保活逻辑：
        - iter_dialogs 拉取最近对话（模拟打开 App）
        - 标记所有对话已读（模拟查看消息）
        - 读取自身资料（心跳）
        """
        if not account.client or not account.client.is_connected():
            return False
        try:
            count = 0
            async for dialog in account.client.iter_dialogs(limit=10):
                count += 1
                # 标记已读
                try:
                    await dialog.mark_read()
                except Exception:
                    pass
                await self.human_delay(0.5, 1.5)

            # 心跳：获取自身资料
            await account.client.get_me()

            m = self.get_metrics(account)
            m.last_active = time.time()
            m.health_score = min(100, m.health_score + 0.5)
            logger.debug(f"[{account.name}] 保活完成，读取 {count} 个对话")
            return True
        except FloodWaitError as e:
            await self.on_flood_wait(account, e.seconds)
            return False
        except (UserDeactivatedError, AuthKeyError):
            logger.error(f"[{account.name}] 账户已被停用或登录态失效")
            account.status = AccountStatus.ERROR
            return False
        except Exception as e:
            logger.error(f"[{account.name}] 保活失败: {e}")
            return False

    async def keepalive_loop(self, accounts: list[Account], stop_event: asyncio.Event):
        """持续保活循环"""
        if not self.enabled:
            return
        logger.info(f"💓 保活已启用，间隔: {self.keepalive_interval}s")
        while not stop_event.is_set():
            for account in accounts:
                if account.status != AccountStatus.ONLINE:
                    continue
                # 活跃时段才保活
                if not self.is_active_hours():
                    continue
                await self.keepalive_once(account)
                await self.human_delay(5, 15)  # 账户间间隔
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self.keepalive_interval)
            except asyncio.TimeoutError:
                pass

    # ---------- 健康检查 ----------

    def health_report(self, accounts: list[Account]) -> list[dict]:
        """生成所有账户的健康报告"""
        report = []
        for a in accounts:
            m = self.get_metrics(a)
            warnings = []
            if m.health_score < 50:
                warnings.append("健康分过低")
            if m.flood_wait_count > 3:
                warnings.append(f"FloodWait 次数过多({m.flood_wait_count})")
            if m.last_active and time.time() - m.last_active > 86400:
                warnings.append("超过 24 小时无活动")
            m.warnings = warnings
            report.append({
                "name": a.name,
                "status": a.status.value,
                "health_score": round(m.health_score, 1),
                "send_count_24h": m.send_count_24h,
                "flood_wait_count": m.flood_wait_count,
                "last_active": datetime.fromtimestamp(m.last_active).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ) if m.last_active else "never",
                "in_warmup": self.in_warmup(a),
                "warnings": warnings,
            })
        return report

    # ---------- 设备指纹 ----------

    @staticmethod
    def recommended_device_params() -> dict:
        """返回推荐的设备参数（用于创建客户端时模拟常见设备）

        Telegram 客户端的 device_model / system_version / app_version 不会直接
        导致封号，但保持与真实移动客户端一致能降低风控异常概率。
        """
        presets = [
            {"device_model": "iPhone 14 Pro", "system_version": "iOS 17.4.1", "app_version": "10.8.2"},
            {"device_model": "iPhone 13", "system_version": "iOS 16.7.4", "app_version": "10.6.0"},
            {"device_model": "Pixel 7", "system_version": "Android 14", "app_version": "10.8.2"},
            {"device_model": "Samsung Galaxy S23", "system_version": "Android 14", "app_version": "10.8.2"},
        ]
        return random.choice(presets)
