#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WPS —— 每日签到 + 每日任务（保留原仓库行为）。"""
import requests

API_URL = "https://vip.wps.cn"


def sign(config):
    """返回 {"ok": bool, "message": str}。"""
    cookie = (config.get("cookie") or "").strip()
    if not cookie:
        return {"ok": False, "message": "未配置 WPS_COOKIE"}

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
        ),
        "Cookie": cookie,
        "Referer": "https://vip.wps.cn/",
    }

    results = []
    ok = False

    # 每日签到
    try:
        response = requests.get(f"{API_URL}/sign/api/signin", headers=headers, timeout=15)
        data = response.json()
        detail = str(data.get("msg") or data.get("message") or "")
        if data.get("ok") or data.get("code") == 0 or "已签到" in detail:
            ok = True
            results.append("签到成功" if "已签到" not in detail else "今日已签到")
            reward = (data.get("data") or {}).get("reward")
            if reward:
                results.append(f"获得 {reward} 积分")
        else:
            results.append(f"签到: {detail or '未知错误'}")
    except Exception as e:
        results.append(f"签到失败: {type(e).__name__}: {e}")

    # 每日任务（原仓库逻辑，接口可用性由 WPS 侧决定，失败不影响签到结论）
    try:
        response = requests.get(f"{API_URL}/sign/api/daily", headers=headers, timeout=15)
        data = response.json()
        if data.get("ok") or data.get("code") == 0:
            results.append("每日任务接口正常")
    except Exception:
        pass

    return {"ok": ok, "message": " | ".join(results) if results else "签到完成"}
