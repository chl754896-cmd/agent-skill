"""唯一的 DeepSeek AI 调用入口。"""

import json
import os


DEFAULT_MODEL = "deepseek-v4-flash"
BASE_URL = "https://api.deepseek.com"


def ai_json(prompt, client_factory=None):
    """请求 JSON；缺少 Key 或请求失败时安全返回状态，不暴露异常。"""
    model = os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL)
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return {"status": "skipped", "model": model, "data": None}
    try:
        if client_factory is None:
            from openai import OpenAI

            client_factory = OpenAI
        client = client_factory(api_key=api_key, base_url=BASE_URL)
        response = client.responses.create(model=model, input=prompt)
        return {"status": "success", "model": model, "data": json.loads(response.output_text)}
    except Exception:
        return {"status": "error", "model": model, "data": None}
