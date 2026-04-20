#!/usr/bin/env python3
import argparse
import sys

from core.scheduler import MessageScheduler


def main():
    parser = argparse.ArgumentParser(description="iMessage 群控 Agent")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("start", help="启动 Agent (群发 + 自动回复)")
    sub.add_parser("status", help="查看设备状态")

    send_parser = sub.add_parser("send", help="发送消息")
    send_parser.add_argument("--to", nargs="+", required=True, help="收件人")
    send_parser.add_argument("--text", required=True, help="消息内容")

    broadcast_parser = sub.add_parser("broadcast", help="群发消息")
    broadcast_parser.add_argument("--text", required=True, help="消息内容")
    broadcast_parser.add_argument("--to", nargs="+", help="收件人 (默认使用配置文件)")

    args = parser.parse_args()

    scheduler = MessageScheduler(config_path=args.config)

    if args.command == "start":
        scheduler.start()
    elif args.command == "status":
        scheduler.status()
    elif args.command == "send":
        scheduler.send_to_all(args.text, args.to)
    elif args.command == "broadcast":
        recipients = args.to or scheduler.config.get("broadcast", {}).get("recipients", [])
        scheduler.send_to_all(args.text, recipients)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
