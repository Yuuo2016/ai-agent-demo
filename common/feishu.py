"""飞书推送模块 - 使用飞书自定义机器人 Webhook"""
import os
import time
import base64
import hashlib
import hmac
import requests


def _sign(secret: str, timestamp: str) -> str:
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


def _headers(timestamp: str, sign: str) -> dict:
    return {"Content-Type": "application/json; charset=utf-8", "X-Lark-Request-Timestamp": timestamp, "X-Lark-Request-Signature": sign}


def send_text(text: str) -> dict:
    webhook = os.getenv("FEISHU_WEBHOOK")
    if not webhook:
        raise RuntimeError("未配置 FEISHU_WEBHOOK，请在 .env 中设置")
    secret = os.getenv("FEISHU_SECRET", "")
    timestamp = str(int(time.time()))
    payload = {"msg_type": "text", "content": {"text": text}}
    headers = _headers(timestamp, _sign(secret, timestamp)) if secret else {}
    return requests.post(webhook, headers=headers, json=payload, timeout=10).json()


def send_post(title: str, content: str) -> dict:
    webhook = os.getenv("FEISHU_WEBHOOK")
    if not webhook:
        raise RuntimeError("未配置 FEISHU_WEBHOOK，请在 .env 中设置")
    secret = os.getenv("FEISHU_SECRET", "")
    timestamp = str(int(time.time()))
    elements = [[{"tag": "text", "text": line}] for line in content.split("\n")]
    payload = {"msg_type": "post", "content": {"post": {"zh_cn": {"title": title, "content": elements}}}}
    headers = _headers(timestamp, _sign(secret, timestamp)) if secret else {}
    return requests.post(webhook, headers=headers, json=payload, timeout=10).json()


def send_card(title: str, markdown: str) -> dict:
    webhook = os.getenv("FEISHU_WEBHOOK")
    if not webhook:
        raise RuntimeError("未配置 FEISHU_WEBHOOK，请在 .env 中设置")
    secret = os.getenv("FEISHU_SECRET", "")
    timestamp = str(int(time.time()))
    payload = {"msg_type": "interactive", "card": {"header": {"title": {"tag": "plain_text", "content": title}}, "elements": [{"tag": "markdown", "content": markdown}]}}
    headers = _headers(timestamp, _sign(secret, timestamp)) if secret else {}
    return requests.post(webhook, headers=headers, json=payload, timeout=10).json()
