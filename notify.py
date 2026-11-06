#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""飞书群自定义机器人通知。

Webhook 形如 https://open.feishu.cn/open-apis/bot/v2/hook/<token>
安全设置开启「签名校验」时需同时配置 secret：
  string_to_sign = f"{timestamp}\\n{secret}"
  sign = base64(hmac_sha256(key=string_to_sign.encode(), msg=b""))
"""
import base64
import hashlib
import hmac
import os
import time

import requests

TIMEOUT = 10


def gen_sign(secret, timestamp):
    """飞书官方签名算法：以 timestamp + 换行 + secret 作为 HMAC 密钥。"""
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def _template(report):
    if report["success"] == report["total"]:
        return "green"
    if report["success"] == 0:
        return "red"
    return "orange"


def _card(report):
    lines = []
    for item in report["results"]:
        flag = "[成功]" if item["ok"] else "[失败]"
        lines.append(f"**{item['name']}**　{flag}　{item['message']}")
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {
                "tag": "plain_text",
                "content": f"每日签到报告 · {report['success']}/{report['total']} 成功",
            },
            "template": _template(report),
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(lines)}},
            {"tag": "hr"},
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": f"执行时间 {report['date']} | WPS + 网易云音乐",
                    }
                ],
            },
        ],
    }


def send(config, report, text):
    """推送签到报告。config: webhook / secret / msg_type；失败不影响签到主流程。"""
    webhook = (config.get("webhook") or os.environ.get("FEISHU_WEBHOOK") or "").strip()
    if not webhook:
        print("  [通知] 未配置 FEISHU_WEBHOOK，跳过推送")
        return False

    msg_type = (config.get("msg_type") or "interactive").lower()
    if msg_type == "text":
        payload = {"msg_type": "text", "content": {"text": text}}
    else:
        payload = {"msg_type": "interactive", "card": _card(report)}

    secret = (config.get("secret") or os.environ.get("FEISHU_SECRET") or "").strip()
    if secret:
        timestamp = str(int(time.time()))
        payload["timestamp"] = timestamp
        payload["sign"] = gen_sign(secret, timestamp)

    try:
        response = requests.post(webhook, json=payload, timeout=TIMEOUT)
        data = response.json()
        if data.get("code") == 0 or data.get("StatusCode") == 0:
            print("  [通知] 飞书机器人推送成功")
            return True
        print(f"  [通知] 飞书机器人返回错误：{data}")
    except Exception as e:
        print(f"  [通知] 飞书机器人推送失败：{type(e).__name__}: {e}")
    return False
