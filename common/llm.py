"""LLM 封装模块 - 使用 OpenAI 兼容接口"""
import os
from openai import OpenAI

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("LLM_API_KEY")
        base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        if not api_key:
            raise RuntimeError("未配置 LLM_API_KEY，请在 .env 中设置")
        _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client


def chat(messages, temperature: float = 0.3, max_tokens: int = 2000) -> str:
    client = get_client()
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
    return resp.choices[0].message.content.strip()


def chat_json(messages, temperature: float = 0.2, max_tokens: int = 2000):
    import json
    sys_prompt = "你是一个严谨的数据处理助手。请只输出合法的 JSON，不要输出任何其他文字、解释或 Markdown 代码块标记。"
    full_messages = [{"role": "system", "content": sys_prompt}] + messages
    text = chat(full_messages, temperature=temperature, max_tokens=max_tokens)
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(text)
