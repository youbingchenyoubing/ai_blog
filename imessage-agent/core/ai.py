from __future__ import annotations

import random
import time

from openai import OpenAI

from .device import Device, Message


class AIReplier:
    def __init__(self, config: dict):
        ai_config = config.get("ai", {})
        self.client = OpenAI(
            base_url=ai_config.get("base_url", "https://api.openai.com/v1"),
            api_key=ai_config.get("api_key", ""),
        )
        self.model = ai_config.get("model", "gpt-4o-mini")
        self.system_prompt = ai_config.get(
            "system_prompt",
            "你是一个智能消息助手。请根据收到的消息内容，生成一条简短、自然、友好的回复。",
        )

        reply_config = config.get("auto_reply", {})
        self.reply_delay_min = reply_config.get("reply_delay_min", 3)
        self.reply_delay_max = reply_config.get("reply_delay_max", 8)
        self.keyword_filters = reply_config.get("keyword_filters", [])
        self.blocked_senders = set(reply_config.get("blocked_senders", []))

    def should_reply(self, message: Message) -> bool:
        if message.is_from_me:
            return False

        if message.sender in self.blocked_senders:
            return False

        for keyword in self.keyword_filters:
            if keyword in message.text:
                print(f"  ⏭️  关键词过滤: [{keyword}]")
                return False

        return True

    def generate_reply(self, message: Message) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {
                        "role": "user",
                        "content": f"对方发来: {message.text}\n请生成回复:",
                    },
                ],
                temperature=0.8,
                max_tokens=100,
            )
            reply = response.choices[0].message.content.strip()
            return reply
        except Exception as e:
            print(f"  ❌ AI 回复生成失败: {e}")
            return "收到，稍后回复您~"

    def process_message(self, device: Device, message: Message, sender) -> str | None:
        if not self.should_reply(message):
            return None

        delay = random.uniform(self.reply_delay_min, self.reply_delay_max)
        print(f"  ⏳ 等待 {delay:.1f}s 后回复...")
        time.sleep(delay)

        reply_text = self.generate_reply(message)
        print(f"  🤖 AI 回复: {reply_text}")

        return reply_text


class SimpleRuleReplier:
    def __init__(self, config: dict):
        rules_config = config.get("auto_reply", {})
        self.keyword_filters = rules_config.get("keyword_filters", [])
        self.blocked_senders = set(rules_config.get("blocked_senders", []))
        self.rules = config.get("rules", {})

    def should_reply(self, message: Message) -> bool:
        if message.is_from_me:
            return False
        if message.sender in self.blocked_senders:
            return False
        for keyword in self.keyword_filters:
            if keyword in message.text:
                return False
        return True

    def generate_reply(self, message: Message) -> str:
        text_lower = message.text.lower().strip()

        for trigger, response in self.rules.items():
            if trigger in text_lower:
                return response

        greetings = ["你好", "嗨", "hi", "hello"]
        if any(g in text_lower for g in greetings):
            return random.choice(["你好呀！", "嗨～有什么可以帮你的？", "你好！"])

        questions = ["?", "？", "怎么", "什么", "吗"]
        if any(q in text_lower for q in questions):
            return "这个问题我需要确认一下，稍后回复你哦"

        return "收到，我看到你的消息了！"
