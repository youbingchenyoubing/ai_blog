#!/usr/bin/env python3
"""Telegram 多账户管理 Agent — CLI 入口"""
import argparse
import asyncio
import sys


def main():
    parser = argparse.ArgumentParser(description="Telegram 多账户管理 Agent")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    sub = parser.add_subparsers(dest="command")

    # ---- 基础命令 ----
    sub.add_parser("start", help="启动 Agent (登录 + 群发 + 自动回复 + 保活)")
    sub.add_parser("status", help="查看账户状态")
    sub.add_parser("login", help="仅登录所有账户（用于首次验证码登录）")

    send_parser = sub.add_parser("send", help="发送消息")
    send_parser.add_argument("--to", nargs="+", required=True, help="收件人 (@username / user_id)")
    send_parser.add_argument("--text", required=True, help="消息内容")

    broadcast_parser = sub.add_parser("broadcast", help="群发消息")
    broadcast_parser.add_argument("--text", required=True, help="消息内容")
    broadcast_parser.add_argument("--to", nargs="+", help="收件人 (默认使用配置文件)")

    # ---- 资料管理 ----
    profile_parser = sub.add_parser("profile", help="账户资料管理")
    profile_sub = profile_parser.add_subparsers(dest="profile_cmd")

    profile_sub.add_parser("show", help="查看所有账户资料")
    profile_sub.add_parser("apply-all", help="批量应用 config.yaml 中的默认资料")

    p_name = profile_sub.add_parser("set-name", help="修改姓名")
    p_name.add_argument("--account", required=True, help="账户名称")
    p_name.add_argument("--first", required=True, help="first_name")
    p_name.add_argument("--last", default="", help="last_name")

    p_user = profile_sub.add_parser("set-username", help="修改 @username")
    p_user.add_argument("--account", required=True, help="账户名称")
    p_user.add_argument("--username", required=True, help="新用户名（不带@），传空字符串删除")

    p_about = profile_sub.add_parser("set-about", help="修改简介")
    p_about.add_argument("--account", required=True, help="账户名称")
    p_about.add_argument("--about", required=True, help="简介内容")

    p_photo = profile_sub.add_parser("set-photo", help="修改头像")
    p_photo.add_argument("--account", help="账户名称（不指定则批量从 photo_dir 加载）")
    p_photo.add_argument("--file", help="头像文件路径（批量模式忽略）")
    p_photo.add_argument("--all", action="store_true", help="批量模式：从 photo_dir 匹配 <name>.jpg")

    p_2fa = profile_sub.add_parser("set-2fa", help="设置/更新两步验证（密码+恢复邮箱）")
    p_2fa.add_argument("--account", required=True, help="账户名称")
    p_2fa.add_argument("--password", required=True, help="新密码（≥8 位）")
    p_2fa.add_argument("--email", default="", help="恢复邮箱")
    p_2fa.add_argument("--hint", default="", help="密码提示")
    p_2fa.add_argument("--current", default="", help="当前密码（修改时需要）")

    p_phone = profile_sub.add_parser("change-phone", help="换绑手机号")
    p_phone.add_argument("--account", required=True, help="账户名称")
    p_phone.add_argument("--phone", required=True, help="新手机号（带国际区号）")

    # ---- 存活率 ----
    sub.add_parser("keepalive", help="立即执行一次保活")
    sub.add_parser("health", help="查看账户健康报告")

    args = parser.parse_args()

    if args.command == "profile":
        asyncio.run(_run_profile(args))
        return

    if args.command in ("keepalive", "health"):
        asyncio.run(_run_survival(args))
        return

    # 其余命令走 scheduler
    from core.scheduler import MessageScheduler
    scheduler = MessageScheduler(config_path=args.config)

    if args.command == "start":
        asyncio.run(scheduler.start())
    elif args.command == "status":
        asyncio.run(scheduler.status())
    elif args.command == "login":
        asyncio.run(_login_only(scheduler))
    elif args.command == "send":
        asyncio.run(scheduler.send_to_all(args.text, args.to))
    elif args.command == "broadcast":
        recipients = args.to or scheduler.config.get("broadcast", {}).get("recipients", [])
        asyncio.run(scheduler.send_to_all(args.text, recipients))
    else:
        parser.print_help()


async def _login_only(scheduler):
    """仅执行登录流程，便于首次输入验证码"""
    from core.account import AccountStatus
    print("=" * 50)
    print("  Telegram 账户登录")
    print("=" * 50)
    await scheduler.am.start_all(interactive=True)
    print("\n登录结果：")
    for a in scheduler.am.accounts:
        icon = "✅" if a.status == AccountStatus.ONLINE else "❌"
        print(f"  {icon} {a.name} ({a.type.value}) -> {a.status.value}")
    await scheduler.am.stop_all()


# ---------- 资料管理 ----------

async def _run_profile(args):
    from core.account import AccountManager
    from core.profile import ProfileManager

    am = AccountManager(args.config)
    pm = ProfileManager()

    await am.start_all(interactive=False)
    online = am.get_online_accounts()
    if not online:
        print("没有在线账户")
        await am.stop_all()
        return

    try:
        if args.profile_cmd == "show":
            print("=" * 60)
            print("  账户资料")
            print("=" * 60)
            for a in online:
                info = await pm.get_profile(a)
                print(f"\n[{a.name}]")
                for k, v in info.items():
                    print(f"  {k:12}: {v}")

        elif args.profile_cmd == "apply-all":
            defaults = am.config.get("profile", {}).get("defaults", {})
            for a in online:
                if defaults.get("first_name"):
                    await pm.update_name(a, defaults["first_name"], defaults.get("last_name", ""))
                if defaults.get("about"):
                    await pm.update_about(a, defaults["about"])
                if defaults.get("username"):
                    await pm.update_username(a, defaults["username"])

        elif args.profile_cmd == "set-name":
            a = am.find_account(args.account)
            if a:
                await pm.update_name(a, args.first, args.last)

        elif args.profile_cmd == "set-username":
            a = am.find_account(args.account)
            if a:
                await pm.update_username(a, args.username)

        elif args.profile_cmd == "set-about":
            a = am.find_account(args.account)
            if a:
                await pm.update_about(a, args.about)

        elif args.profile_cmd == "set-photo":
            if args.all:
                # 批量从 photo_dir 加载 <account_name>.jpg
                import os
                photo_dir = am.config.get("profile", {}).get("photo_dir", "./avatars")
                for a in online:
                    path = os.path.join(photo_dir, f"{a.name}.jpg")
                    if os.path.exists(path):
                        await pm.update_photo(a, path)
                    else:
                        print(f"[{a.name}] 未找到头像: {path}")
            else:
                a = am.find_account(args.account)
                if a and args.file:
                    await pm.update_photo(a, args.file)

        elif args.profile_cmd == "set-2fa":
            a = am.find_account(args.account)
            if a:
                await pm.update_2fa(
                    a,
                    password=args.password,
                    email=args.email,
                    hint=args.hint,
                    current_password=args.current,
                )

        elif args.profile_cmd == "change-phone":
            a = am.find_account(args.account)
            if a:
                await pm.change_phone(a, args.phone)
    finally:
        await am.stop_all()


# ---------- 存活率 ----------

async def _run_survival(args):
    from core.account import AccountManager
    from core.survival import SurvivalGuard

    am = AccountManager(args.config)
    guard = SurvivalGuard(am.config)

    await am.start_all(interactive=False)
    online = am.get_online_accounts()

    try:
        if args.command == "keepalive":
            print("=" * 50)
            print("  执行保活")
            print("=" * 50)
            for a in online:
                ok = await guard.keepalive_once(a)
                icon = "✅" if ok else "❌"
                print(f"  {icon} {a.name}")
        elif args.command == "health":
            print("=" * 70)
            print("  账户健康报告")
            print("=" * 70)
            report = guard.health_report(online)
            for r in report:
                print(f"\n[{r['name']}] status={r['status']} score={r['health_score']}")
                print(f"  24h 发送: {r['send_count_24h']}  FloodWait: {r['flood_wait_count']}  养号期: {r['in_warmup']}")
                print(f"  最后活动: {r['last_active']}")
                if r["warnings"]:
                    print(f"  ⚠ 警告: {', '.join(r['warnings'])}")
    finally:
        await am.stop_all()


if __name__ == "__main__":
    main()
