#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""网易云音乐 —— 仅每日签到。

不含刷歌、等级查询、任务领取等任何额外动作。

接口 /weapi/point/dailySignin 要求 weapi 加密（原仓库明文 POST 无法签到）：
  params    = Base64(AES(Base64(AES(json, NONCE)), secKey))
  encSecKey = RSA(逆序 secKey)
依赖 pycryptodome。若依赖缺失或 weapi 请求失败，自动降级尝试旧版明文接口，
两条路径都指向同一个「每日签到」动作，不会执行其他业务。
"""
import base64
import json
import os
import re

import requests

API_URL = "https://music.163.com"
WEAPI_SIGNIN = f"{API_URL}/weapi/point/dailySignin"
LEGACY_SIGNIN = f"{API_URL}/api/point/dailySignin"

NONCE = b"0CoJUm6Qyw8W8jud"
IV = b"0102030405060708"
PUBKEY = 0x10001
MODULUS = int(
    "00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b"
    "725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280"
    "104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932"
    "575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b"
    "3ece0462db0a22b8e7",
    16,
)


def _headers(cookie):
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
        ),
        "Cookie": cookie,
        "Referer": "https://music.163.com/",
        "Origin": "https://music.163.com",
        "Content-Type": "application/x-www-form-urlencoded",
    }


def _csrf_token(cookie):
    match = re.search(r"(?:^|;\s*)__csrf=([^;]+)", cookie)
    return match.group(1) if match else ""


def _aes_b64(text, key):
    """AES-128-CBC + PKCS7，返回 Base64 字符串。"""
    from Crypto.Cipher import AES

    pad_len = 16 - len(text.encode("utf-8")) % 16
    padded = (text + chr(pad_len) * pad_len).encode("utf-8")
    cipher = AES.new(key, AES.MODE_CBC, IV)
    return base64.b64encode(cipher.encrypt(padded)).decode("ascii")


def weapi(data):
    """生成 weapi 所需的 params / encSecKey。"""
    sec_key = os.urandom(8).hex().encode("ascii")  # 16 字节随机密钥
    plain = json.dumps(data, separators=(",", ":"), ensure_ascii=True)
    params = _aes_b64(_aes_b64(plain, NONCE), sec_key)
    reversed_key = sec_key[::-1]
    enc_sec_key = format(pow(int.from_bytes(reversed_key, "big"), PUBKEY, MODULUS), "x").zfill(256)
    return {"params": params, "encSecKey": enc_sec_key}


def _interpret(data):
    code = data.get("code")
    if code == 200:
        point = data.get("point")
        return {"ok": True, "message": "签到成功" + (f"（+{point} 积分）" if point else "")}
    if code == 301:
        return {"ok": True, "message": "今日已签到（无需重复）"}
    detail = data.get("msg") or data.get("message") or "未知响应"
    return {"ok": False, "message": f"code={code}: {detail}"}


def sign(config):
    """只执行一次每日签到，返回 {"ok": bool, "message": str}。"""
    cookie = (config.get("cookie") or "").strip()
    if not cookie:
        return {"ok": False, "message": "未配置 NETEASE_COOKIE"}

    headers = _headers(cookie)
    csrf = _csrf_token(cookie)
    payload = {"type": 0, "csrf_token": csrf}
    errors = []

    try:
        response = requests.post(WEAPI_SIGNIN, headers=headers, data=weapi(payload), timeout=15)
        result = _interpret(response.json())
        if result["ok"]:
            return result
        errors.append(f"weapi: {result['message']}")
    except ImportError:
        errors.append("weapi: 缺少 pycryptodome，已降级")
    except Exception as e:
        errors.append(f"weapi: 请求异常 {type(e).__name__}: {e}")

    # 降级：旧版明文签到接口（仅在上面未成功时尝试）
    try:
        response = requests.post(
            LEGACY_SIGNIN,
            headers=headers,
            data={"type": 0, "csrf_token": csrf},
            timeout=15,
        )
        result = _interpret(response.json())
        if result["ok"]:
            result["message"] += "（明文接口）"
            return result
        errors.append(f"legacy: {result['message']}")
    except Exception as e:
        errors.append(f"legacy: 请求异常 {type(e).__name__}: {e}")

    return {"ok": False, "message": "；".join(errors)}
