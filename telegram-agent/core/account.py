from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import yaml
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneNumberUnoccupiedError,
)


class AccountType(Enum):
    USER = "user"
    BOT = "bot"


class AccountStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    NEED_LOGIN = "need_login"
    ERROR = "error"


@dataclass
class Account:
    """单个 Telegram 账户的数据模型"""
    name: str
    type: AccountType
    session: str                 # .session 文件路径（不含扩展名）
    api_id: int
    api_hash: str
    phone: str = ""              # 用户账户需要
    bot_token: str = ""          # 机器人账户需要
    proxy: Optional[list] = None
    enabled: bool = True

    # 运行时状态
    status: AccountStatus = AccountStatus.OFFLINE
    client: Optional[TelegramClient] = None
    me_id: Optional[int] = None        # 当前账户的 user_id
    me_username: str = ""
    last_message_id: int = 0           # 增量读取的游标
    current_task: Optional[str] = None

    @property
    def is_user(self) -> bool:
        return self.type == AccountType.USER

    @property
    def is_bot(self) -> bool:
        return self.type == AccountType.BOT


class AccountManager:
    """管理多个 Telegram 账户：加载配置、创建客户端、登录、健康检查"""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.accounts: list[Account] = []
        self._init_accounts()

    def _init_accounts(self):
        session_dir = self.config.get("global", {}).get("session_dir", "./sessions")
        os.makedirs(session_dir, exist_ok=True)

        for a in self.config.get("accounts", []):
            if not a.get("enabled", True):
                continue
            account = Account(
                name=a["name"],
                type=AccountType(a.get("type", "user")),
                session=a["session"],
                api_id=int(a["api_id"]),
                api_hash=a["api_hash"],
                phone=a.get("phone", ""),
                bot_token=a.get("bot_token", ""),
                proxy=a.get("proxy"),
                enabled=a.get("enabled", True),
            )
            # 自动补齐会话目录
            session_dir_name = os.path.dirname(account.session)
            if session_dir_name and not os.path.exists(session_dir_name):
                os.makedirs(session_dir_name, exist_ok=True)
            self.accounts.append(account)

    # ---------- 客户端创建 ----------

    def _build_client(self, account: Account) -> TelegramClient:
        proxy = tuple(account.proxy) if account.proxy else None

        # 设备指纹：从配置读取或使用随机主流设备参数
        survival_cfg = self.config.get("survival", {})
        device_params = {}
        if survival_cfg.get("device_fingerprint", True):
            from .survival import SurvivalGuard
            device_params = SurvivalGuard.recommended_device_params()

        client = TelegramClient(
            account.session,
            account.api_id,
            account.api_hash,
            proxy=proxy,
            connection_retries=self.config.get("global", {}).get("request_retry", 3),
            device_model=device_params.get("device_model", "Unknown"),
            system_version=device_params.get("system_version", "Unknown"),
            app_version=device_params.get("app_version", "1.0"),
        )
        return client

    # ---------- 登录 ----------

    async def login(self, account: Account, interactive: bool = True) -> bool:
        """登录账户。机器人用 bot_token，用户账户用手机号。

        interactive=True 时会在终端询问验证码/两步密码。
        已有有效 session 文件时直接复用。
        """
        if account.client and account.client.is_connected():
            return True

        client = self._build_client(account)
        await client.connect()

        try:
            if account.is_bot:
                await client.start(bot_token=account.bot_token)
            else:
                # 已登录则直接返回
                if await client.is_user_authorized():
                    pass
                elif interactive:
                    await self._interactive_user_login(client, account)
                else:
                    account.status = AccountStatus.NEED_LOGIN
                    return False

            me = await client.get_me()
            account.me_id = me.id
            account.me_username = me.username or ""
            account.client = client
            account.status = AccountStatus.ONLINE
            return True

        except SessionPasswordNeededError:
            account.status = AccountStatus.NEED_LOGIN
            if interactive:
                print(f"[{account.name}] 需要两步验证密码，请在终端输入：")
                import getpass
                pwd = getpass.getpass("密码: ")
                await client.sign_in(password=pwd)
                me = await client.get_me()
                account.me_id = me.id
                account.me_username = me.username or ""
                account.client = client
                account.status = AccountStatus.ONLINE
                return True
            return False
        except Exception as e:
            account.status = AccountStatus.ERROR
            print(f"[{account.name}] 登录失败: {e}")
            return False

    async def _interactive_user_login(self, client: TelegramClient, account: Account):
        await client.send_code_request(account.phone)
        code = input(f"[{account.name}] 请输入收到的验证码: ").strip()
        try:
            await client.sign_in(account.phone, code)
        except PhoneCodeInvalidError:
            raise RuntimeError("验证码错误")
        except PhoneNumberUnoccupiedError:
            raise RuntimeError("该手机号未注册 Telegram")

    # ---------- 健康检查 ----------

    async def health_check(self):
        """检查所有账户的连接状态"""
        for account in self.accounts:
            if not account.client:
                account.status = AccountStatus.OFFLINE
                continue
            try:
                if not account.client.is_connected():
                    await account.client.connect()
                if await account.client.is_user_authorized():
                    account.status = AccountStatus.ONLINE
                else:
                    account.status = AccountStatus.NEED_LOGIN
            except Exception:
                account.status = AccountStatus.ERROR

    def get_online_accounts(self) -> list[Account]:
        return [a for a in self.accounts if a.status == AccountStatus.ONLINE]

    # ---------- 生命周期 ----------

    async def start_all(self, interactive: bool = True):
        """启动所有启用的账户"""
        for account in self.accounts:
            ok = await self.login(account, interactive=interactive)
            tag = "✅" if ok else "❌"
            print(f"  {tag} {account.name} ({account.type.value})")

    async def stop_all(self):
        """断开所有账户连接"""
        for account in self.accounts:
            if account.client and account.client.is_connected():
                await account.client.disconnect()
                account.status = AccountStatus.OFFLINE

    def find_account(self, name: str) -> Optional[Account]:
        for a in self.accounts:
            if a.name == name:
                return a
        return None
