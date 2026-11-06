#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日签到入口：WPS + 网易云音乐（仅每日签到），结果推送飞书自定义机器人。

配置优先级：环境变量 > 同目录 config.json。
GitHub Actions 走环境变量（Secrets），本地运行走 config.json。
"""
import datetime
import json
import os
import sys
from pathlib import Path

import notify

BASE_DIR = Path(__file__).resolve().parent


def _file_config():
    path = BASE_DIR / "config.json"
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        print(f"[配置] config.json 读取失败：{e}")
        return {}


def _pick(file_cfg, section, key, env_name):
    value = os.environ.get(env_name, "").strip()
    if value:
        return value
    return str(file_cfg.get(section, {}).get(key, "") or "").strip()


def load_config():
    file_cfg = _file_config()
    cfg = {
        "wps": {"cookie": _pick(file_cfg, "wps", "cookie", "WPS_COOKIE")},
        "netease": {"cookie": _pick(file_cfg, "netease", "cookie", "NETEASE_COOKIE")},
        "notify": {
            "type": "feishu",
            "webhook": _pick(file_cfg, "notify", "webhook", "FEISHU_WEBHOOK"),
            "secret": _pick(file_cfg, "notify", "secret", "FEISHU_SECRET"),
            "msg_type": _pick(file_cfg, "notify", "msg_type", "FEISHU_MSG_TYPE") or "interactive",
        },
    }
    if not cfg["wps"]["cookie"] and not cfg["netease"]["cookie"]:
        print("[配置] 未找到任何 Cookie。请配置 Secrets，或复制 config.json.example 为 config.json")
        sys.exit(1)
    return cfg


def save_log(message):
    try:
        with (BASE_DIR / "sign.log").open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {message}\n")
    except OSError:
        pass


def run_task(name, func, task_config):
    """单个平台失败不影响另一个平台；统一返回结构化结果。"""
    try:
        result = func(task_config)
        if not isinstance(result, dict) or "ok" not in result:
            result = {"ok": False, "message": f"模块返回值异常：{result}"}
    except Exception as e:
        result = {"ok": False, "message": f"执行异常：{type(e).__name__}: {e}"}
    flag = "成功" if result["ok"] else "失败"
    print(f"  -> [{flag}] {result['message']}")
    return {"name": name, "ok": bool(result["ok"]), "message": str(result["message"])}


def main():
    print("=" * 50)
    print("每日签到开始（WPS + 网易云音乐）")
    print("=" * 50)

    config = load_config()
    from sign import netease, wps

    results = []
    print("\n[1/2] WPS ...")
    results.append(run_task("WPS", wps.sign, config["wps"]))
    print("\n[2/2] 网易云音乐（仅每日签到）...")
    results.append(run_task("网易云音乐", netease.sign, config["netease"]))

    success = sum(1 for r in results if r["ok"])
    report = {
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": results,
        "success": success,
        "total": len(results),
    }

    text = f"【每日签到报告】{report['date']}\n"
    for r in results:
        flag = "成功" if r["ok"] else "失败"
        text += f"• {r['name']}: [{flag}] {r['message']}\n"
        save_log(f"{r['name']}: [{flag}] {r['message']}")
    text += f"成功 {success}/{len(results)}"

    print("\n" + "=" * 50)
    print(text)
    print("=" * 50)

    notify.send(config["notify"], report, text)
    return success == len(results)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
