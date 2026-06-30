from __future__ import annotations

import logging
from typing import Optional

from telethon.errors import (
    UsernameInvalidError,
    UsernameOccupiedError,
    UsernameNotModifiedError,
    PasswordHashInvalidError,
    FreshChangePhoneForbiddenError,
    PhoneNumberBannedError,
)

from .account import Account

logger = logging.getLogger("Profile")


class ProfileManager:
    """在线修改 Telegram 账户资料：用户名、姓名、简介、头像、两步验证、手机号"""

    # ---------- 资料读取 ----------

    async def get_profile(self, account: Account) -> dict:
        """读取当前账户完整资料"""
        if not account.client:
            return {}
        me = await account.client.get_me()
        full = await account.client.get_entity("me")
        return {
            "id": me.id,
            "first_name": me.first_name or "",
            "last_name": me.last_name or "",
            "username": me.username or "",
            "phone": me.phone or "",
            "photo": bool(me.photo),
            "premium": getattr(me, "premium", False),
            "about": getattr(full, "about", "") or "",
        }

    # ---------- 用户名（@username）----------

    async def update_username(self, account: Account, username: Optional[str]) -> bool:
        """修改 @username。传 None 或空字符串表示删除用户名。

        规则：
        - 长度 5-32 字符
        - 仅字母数字下划线
        - 必须以字母开头
        """
        if not account.client:
            return False
        username = (username or "").strip().lstrip("@") or None
        try:
            await account.client(functions.account.UpdateUsernameRequest(username=username))
            logger.info(f"[{account.name}] 用户名已更新: {username or '(已删除)'}")
            return True
        except UsernameInvalidError:
            logger.warning(f"[{account.name}] 用户名非法（5-32 字符，字母开头，仅字母数字下划线）")
        except UsernameOccupiedError:
            logger.warning(f"[{account.name}] 用户名已被占用: {username}")
        except UsernameNotModifiedError:
            logger.info(f"[{account.name}] 用户名未变化")
            return True
        except Exception as e:
            logger.error(f"[{account.name}] 修改用户名失败: {e}")
        return False

    # ---------- 姓名 ----------

    async def update_name(
        self,
        account: Account,
        first_name: str,
        last_name: str = "",
    ) -> bool:
        """修改 first_name / last_name"""
        if not account.client:
            return False
        first_name = (first_name or "").strip()
        if not first_name:
            logger.warning(f"[{account.name}] first_name 不能为空")
            return False
        try:
            from telethon.tl import functions
            await account.client(
                functions.account.UpdateProfileRequest(
                    first_name=first_name,
                    last_name=last_name or "",
                )
            )
            logger.info(f"[{account.name}] 姓名已更新: {first_name} {last_name}".strip())
            return True
        except Exception as e:
            logger.error(f"[{account.name}] 修改姓名失败: {e}")
        return False

    # ---------- 简介（about）----------

    async def update_about(self, account: Account, about: str) -> bool:
        """修改个人简介（about），最长 70 字符（普通账户）/ 140 字符（Premium）"""
        if not account.client:
            return False
        about = (about or "").strip()
        if len(about) > 70:
            logger.warning(f"[{account.name}] about 超过 70 字符，可能需要 Premium 才能更长")
        try:
            from telethon.tl import functions
            await account.client(
                functions.account.UpdateProfileRequest(about=about)
            )
            logger.info(f"[{account.name}] 简介已更新: {about[:30]}...")
            return True
        except Exception as e:
            logger.error(f"[{account.name}] 修改简介失败: {e}")
        return False

    # ---------- 头像 ----------

    async def update_photo(self, account: Account, file_path: str) -> bool:
        """上传新头像"""
        if not account.client:
            return False
        try:
            from telethon.tl import functions
            file = await account.client.upload_file(file_path)
            await account.client(functions.photos.UploadProfilePhotoRequest(file=file))
            logger.info(f"[{account.name}] 头像已更新: {file_path}")
            return True
        except Exception as e:
            logger.error(f"[{account.name}] 修改头像失败: {e}")
        return False

    async def delete_photo(self, account: Account) -> bool:
        """删除当前头像"""
        if not account.client:
            return False
        try:
            from telethon.tl import functions
            photos = await account.client.get_profile_photos("me")
            if not photos:
                return True
            await account.client(
                functions.photos.DeletePhotosRequest(id=[photos[0].id])
            )
            logger.info(f"[{account.name}] 头像已删除")
            return True
        except Exception as e:
            logger.error(f"[{account.name}] 删除头像失败: {e}")
        return False

    # ---------- 两步验证（密码 + 恢复邮箱）----------

    async def update_2fa(
        self,
        account: Account,
        password: str,
        hint: str = "",
        email: str = "",
        current_password: str = "",
    ) -> bool:
        """设置或更新两步验证密码与恢复邮箱。

        - 首次设置：current_password 传空
        - 修改密码：current_password 传当前密码
        - email 为恢复邮箱，Telegram 会发送验证码确认
        """
        if not account.client:
            return False
        if not password or len(password) < 8:
            logger.warning(f"[{account.name}] 密码至少 8 位")
            return False

        try:
            from telethon.password import compute_check
            from telethon.tl import functions
            from telethon.tl.functions.account import UpdatePasswordSettingsRequest
            from telethon.tl.types import (
                InputCheckPasswordSRP,
                PasswordInputSettings,
            )

            # 检查当前是否已设置两步验证
            pwd_info = await account.client.get_password_info()

            current_srp = None
            if pwd_info.has_password:
                if not current_password:
                    logger.warning(f"[{account.name}] 已设置两步验证，需提供 current_password")
                    return False
                current_srp = compute_check(pwd_info, current_password)
            else:
                logger.info(f"[{account.name}] 当前未设置两步验证，将首次设置")

            # 构造新密码设置
            new_settings = PasswordInputSettings(
                new_password=password,
                new_hint=hint or "",
                email=email or None,
            )

            await account.client(
                UpdatePasswordSettingsRequest(
                    password=current_srp,
                    new_settings=new_settings,
                )
            )
            logger.info(f"[{account.name}] 两步验证已更新（密码+邮箱）")
            return True

        except PasswordHashInvalidError:
            logger.warning(f"[{account.name}] 当前密码错误")
        except Exception as e:
            logger.error(f"[{account.name}] 更新两步验证失败: {e}")
        return False

    async def disable_2fa(self, account: Account, current_password: str) -> bool:
        """关闭两步验证"""
        if not account.client:
            return False
        try:
            from telethon.password import compute_check
            from telethon.tl.functions.account import UpdatePasswordSettingsRequest
            from telethon.tl.types import PasswordInputSettings

            pwd_info = await account.client.get_password_info()
            if not pwd_info.has_password:
                logger.info(f"[{account.name}] 未设置两步验证，无需关闭")
                return True
            current_srp = compute_check(pwd_info, current_password)
            await account.client(
                UpdatePasswordSettingsRequest(
                    password=current_srp,
                    new_settings=PasswordInputSettings(new_password=None),
                )
            )
            logger.info(f"[{account.name}] 两步验证已关闭")
            return True
        except PasswordHashInvalidError:
            logger.warning(f"[{account.name}] 当前密码错误")
        except Exception as e:
            logger.error(f"[{account.name}] 关闭两步验证失败: {e}")
        return False

    # ---------- 换绑手机号 ----------

    async def change_phone(
        self,
        account: Account,
        new_phone: str,
        code_callback=None,
    ) -> bool:
        """换绑手机号。

        流程：
        1. 调用 account.SendChangePhoneCodeRequest 发送验证码到新手机号
        2. 通过 code_callback 获取用户输入的验证码
        3. 调用 account.ChangePhoneRequest 完成换绑

        限制：
        - 新手机号不能与当前相同
        - Telegram 限制频繁换绑（通常 24 小时内只能换 1 次）
        - 新手机号必须能接收短信验证码
        """
        if not account.client:
            return False
        new_phone = (new_phone or "").strip()
        if not new_phone.startswith("+"):
            new_phone = "+" + new_phone

        try:
            from telethon.tl import functions

            # 1. 发送验证码到新号码
            await account.client(
                functions.account.SendChangePhoneCodeRequest(
                    phone_number=new_phone,
                    settings=None,
                )
            )
            logger.info(f"[{account.name}] 验证码已发送到 {new_phone}")

            # 2. 获取验证码
            if code_callback is None:
                code = input(f"[{account.name}] 请输入 {new_phone} 收到的验证码: ").strip()
            else:
                code = code_callback(account, new_phone)
            if not code:
                logger.warning(f"[{account.name}] 未提供验证码，取消换绑")
                return False

            # 3. 完成换绑
            result = await account.client(
                functions.account.ChangePhoneRequest(
                    phone_number=new_phone,
                    phone_code=code,
                )
            )
            logger.info(f"[{account.name}] 手机号已换绑到 {new_phone}")
            return True

        except FreshChangePhoneForbiddenError:
            logger.warning(f"[{account.name}] 换绑过于频繁，请 24 小时后再试")
        except PhoneNumberBannedError:
            logger.warning(f"[{account.name}] 该手机号已被 Telegram 封禁")
        except Exception as e:
            logger.error(f"[{account.name}] 换绑手机号失败: {e}")
        return False
