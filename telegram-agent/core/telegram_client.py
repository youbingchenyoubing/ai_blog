from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from telethon.errors import FloodWaitError
from telethon.tl.types import (
    User,
    Chat,
    Channel,
    PeerUser,
    PeerChat,
    PeerChannel,
)

from .account import Account

logger = logging.getLogger("TelegramClient")


@dataclass
class TGMessage:
    """统一的 Telegram 消息数据模型"""
    msg_id: int                       # 消息 ID（Telethon message.id）
    text: str                         # 消息文本
    sender_id: int                    # 发送者 user_id
    sender_name: str                  # 发送者展示名（first_name + last_name / title）
    is_from_me: bool                  # 是否是我发送的
    date: float                       # 时间戳
    chat_id: int                      # 会话 ID
    chat_type: str                    # user / group / channel
    chat_title: str                   # 会话名称
    account_name: str = ""            # 来自哪个账户
    reply_to: Optional[int] = None    # 被回复消息 ID


class TelegramReader:
    """从 Telegram 账户读取新消息（增量轮询）"""

    async def read_new_messages(self, account: Account, limit: int = 50) -> list[TGMessage]:
        """读取所有未处理的新消息，返回 TGMessage 列表。

        - 用户账户：遍历最近活跃的对话（dialogs），从每个对话拉取新消息
        - 机器人账户：仅遍历最近对话
        - 使用 account.last_message_id 作为游标（全局最大消息 ID）
        """
        if not account.client or not account.client.is_connected():
            return []

        messages: list[TGMessage] = []
        try:
            async for dialog in account.client.iter_dialogs(limit=30):
                msgs = await self._read_dialog(account, dialog, limit=limit)
                messages.extend(msgs)
        except FloodWaitError as e:
            logger.warning(f"[{account.name}] FloodWait: 需等待 {e.seconds}s")
            return []
        except Exception as e:
            logger.error(f"[{account.name}] 读取消息异常: {e}")
            return []

        # 按时间排序
        messages.sort(key=lambda m: m.date)
        # 更新游标
        if messages:
            account.last_message_id = max(account.last_message_id, max(m.msg_id for m in messages))
        return messages

    async def _read_dialog(self, account: Account, dialog, limit: int) -> list[TGMessage]:
        result: list[TGMessage] = []
        try:
            async for msg in account.client.iter_messages(
                dialog.entity,
                limit=limit,
                min_id=account.last_message_id,
            ):
                tg = await self._convert_message(account, msg, dialog)
                if tg:
                    result.append(tg)
        except FloodWaitError as e:
            logger.warning(f"[{account.name}] 读取 {dialog.name} FloodWait: {e.seconds}s")
        except Exception as e:
            logger.debug(f"[{account.name}] 读取 {dialog.name} 失败: {e}")
        return result

    async def _convert_message(self, account: Account, msg, dialog) -> Optional[TGMessage]:
        if not msg or not msg.text:
            return None

        # 会话类型
        entity = dialog.entity
        if isinstance(entity, User):
            chat_type = "user"
            chat_title = (entity.first_name or "") + (entity.last_name or "")
            chat_title = chat_title.strip() or entity.username or str(entity.id)
        elif isinstance(entity, Channel):
            chat_type = "channel"
            chat_title = entity.title or "Channel"
        elif isinstance(entity, Chat):
            chat_type = "group"
            chat_title = entity.title or "Group"
        else:
            chat_type = "unknown"
            chat_title = dialog.name or "Unknown"

        # 发送者信息
        sender_id = msg.sender_id or 0
        sender_name = ""
        is_from_me = (sender_id == account.me_id) if account.me_id else False
        try:
            sender = await msg.get_sender()
            if sender:
                if isinstance(sender, User):
                    sender_name = ((sender.first_name or "") + " " + (sender.last_name or "")).strip()
                    if not sender_name:
                        sender_name = sender.username or str(sender.id)
                else:
                    sender_name = getattr(sender, "title", str(sender_id))
        except Exception:
            sender_name = str(sender_id)

        return TGMessage(
            msg_id=msg.id,
            text=msg.text or "",
            sender_id=sender_id,
            sender_name=sender_name,
            is_from_me=is_from_me,
            date=msg.date.timestamp() if msg.date else datetime.now().timestamp(),
            chat_id=msg.chat_id or dialog.id,
            chat_type=chat_type,
            chat_title=chat_title,
            account_name=account.name,
            reply_to=getattr(msg.reply_to, "reply_to_msg_id", None) if msg.reply_to else None,
        )


class TelegramSender:
    """通过 Telegram 账户发送消息"""

    async def send_message(self, account: Account, recipient: str, text: str) -> bool:
        """向指定收件人发送消息。

        recipient 支持：
        - @username
        - user_id 数字字符串
        - 聊天链接 t.me/...
        """
        if not account.client or not account.client.is_connected():
            return False

        try:
            entity = await self._resolve_recipient(account, recipient)
            if not entity:
                logger.warning(f"[{account.name}] 无法解析收件人: {recipient}")
                return False
            await account.client.send_message(entity, text)
            return True
        except FloodWaitError as e:
            logger.warning(f"[{account.name}] 发送到 {recipient} FloodWait: {e.seconds}s")
            return False
        except Exception as e:
            logger.error(f"[{account.name}] 发送到 {recipient} 失败: {e}")
            return False

    async def _resolve_recipient(self, account: Account, recipient: str):
        recipient = recipient.strip()
        # user_id 纯数字
        if recipient.isdigit():
            try:
                return await account.client.get_entity(int(recipient))
            except Exception:
                return None
        # @username
        if recipient.startswith("@"):
            try:
                return await account.client.get_entity(recipient)
            except Exception:
                return None
        # t.me/...
        if "t.me/" in recipient:
            username = recipient.split("t.me/")[-1].split("/")[0]
            if username:
                return await self._resolve_recipient(account, f"@{username}")
        # 直接当 username 试一次
        try:
            return await account.client.get_entity(recipient)
        except Exception:
            return None

    async def reply_message(self, account: Account, chat_id: int, reply_to_id: int, text: str) -> bool:
        """在指定会话中回复某条消息"""
        if not account.client or not account.client.is_connected():
            return False
        try:
            await account.client.send_message(
                chat_id,
                text,
                reply_to=reply_to_id,
            )
            return True
        except Exception as e:
            logger.error(f"[{account.name}] 回复消息失败: {e}")
            return False

    async def broadcast(self, accounts: list[Account], recipients: list[str], text: str) -> dict:
        """矩阵式群发：N 个账户 × M 个收件人"""
        results: dict[str, bool] = {}
        for account in accounts:
            for recipient in recipients:
                key = f"{account.name} -> {recipient}"
                ok = await self.send_message(account, recipient, text)
                results[key] = ok
        return results
