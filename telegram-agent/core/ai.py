from __future__ import annotations

import logging
import random
import time
from typing import Optional

from openai import OpenAI

from .account import Account
from .telegram_client import TGMessage, TelegramSender

logger = logging.getLogger("AIReplier")


class AIReplier:
    """基于 OpenAI（或兼容 API）的智能回复"""

    def __init__(self, config: dict):
        ai_cfg = config.get("ai", {})
        self.client = OpenAI(
            api_key=ai_cfg.get("api_key", ""),
            base_url=ai_cfg.get("base_url", "https://api.openai.com/v1"),
        )
        self.model = ai_cfg.get("model", "gpt-4o-mini")
        self.system_prompt = ai_cfg.get("system_prompt", "你是一个智能消息助手。")

        reply_cfg = config.get("auto_reply", {})
        self.reply_delay_min = reply_cfg.get("reply_delay_min", 3)
        self.reply_delay_max = reply_cfg.get("reply_delay_max", 8)
        self.keyword_filters = reply_cfg.get("keyword_filters", [])
        self.blocked_senders = set(reply_cfg.get("blocked_senders", []))
        self.private_only = reply_cfg.get("private_only", True)

        # 每个联系人的对话历史（最近 10 轮）
        self._history: dict[str, list[dict]] = {}

    def should_reply(self, account: Account, message: TGMessage) -> bool:
        if message.is_from_me:
            return False
        if self.private_only and message.chat_type != "user":
            return False
        sender_key = str(message.sender_id) if message.sender_id else message.sender_name
        if sender_key in self.blocked_senders:
            return False
        for kw in self.keyword_filters:
            if kw in message.text:
                return False
        return True

    def generate_reply(self, account: Account, message: TGMessage) -> Optional[str]:
        try:
            history = self._history.get(message.sender_name, [])
            history.append({"role": "user", "content": message.text})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *history[-10:],
                ],
            )
            reply = response.choices[0].message.content.strip()
            history.append({"role": "assistant", "content": reply})
            self._history[message.sender_name] = history
            return reply
        except Exception as e:
            logger.error(f"[{account.name}] AI 生成回复失败: {e}")
            return None

    async def process_message(
        self,
        account: Account,
        message: TGMessage,
        sender: TelegramSender,
    ) -> Optional[str]:
        """完整流程：判断 → 延迟 → 生成 → 回复"""
        if not self.should_reply(account, message):
            return None

        delay = random.uniform(self.reply_delay_min, self.reply_delay_max)
        time.sleep(delay)

        reply_text = self.generate_reply(account, message)
        if not reply_text:
            return None

        # 优先用 reply_message（在原会话回复）
        ok = await sender.reply_message(account, message.chat_id, message.msg_id, reply_text)
        if not ok:
            # 兜底：直接发给发送者
            ok = await sender.send_message(account, str(message.sender_id), reply_text)
        return reply_text if ok else None


class SimpleRuleReplier:
    """规则引擎：无需 AI 调用，关键词匹配"""

    def __init__(self, config: dict):
        reply_cfg = config.get("auto_reply", {})
        self.reply_delay_min = reply_cfg.get("reply_delay_min", 3)
        self.reply_delay_max = reply_cfg.get("reply_delay_max", 8)
        self.keyword_filters = reply_cfg.get("keyword_filters", [])
        self.blocked_senders = set(reply_cfg.get("blocked_senders", []))
        self.private_only = reply_cfg.get("private_only", True)
        self.rules: dict[str, str] = {
            "你好": "你好呀～",
            "在吗": "在的，有什么可以帮你？",
            "谢谢": "不客气～",
        }
        self.fallback = "收到，我看到你的消息了！"

    def should_reply(self, account: Account, message: TGMessage) -> bool:
        if message.is_from_me:
            return False
        if self.private_only and message.chat_type != "user":
            return False
        sender_key = str(message.sender_id) if message.sender_id else message.sender_name
        if sender_key in self.blocked_senders:
            return False
        for kw in self.keyword_filters:
            if kw in message.text:
                return False
        return True

    def generate_reply(self, account: Account, message: TGMessage) -> str:
        for kw, reply in self.rules.items():
            if kw in message.text:
                return reply
        if message.text.endswith("?") or message.text.endswith("？"):
            return "这个问题我还不太确定，让我想想～"
        return self.fallback

    async def process_message(
        self,
        account: Account,
        message: TGMessage,
        sender: TelegramSender,
    ) -> Optional[str]:
        if not self.should_reply(account, message):
            return None

        delay = random.uniform(self.reply_delay_min, self.reply_delay_max)
        time.sleep(delay)

        reply_text = self.generate_reply(account, message)
        ok = await sender.reply_message(account, message.chat_id, message.msg_id, reply_text)
        if not ok:
            ok = await sender.send_message(account, str(message.sender_id), reply_text)
        return reply_text if ok else None
