import httpx

from ..config import settings


def _base_and_key() -> tuple[str, str]:
    base = (settings.llm_api_base or "").rstrip("/")
    key = settings.llm_api_key or ""
    if not base or not key:
        raise RuntimeError(
            "未配置 LLM。请在 .env 设置 LLM_API_BASE 与 LLM_API_KEY，"
            "或让其继承 EMBEDDING_API_BASE / EMBEDDING_API_KEY。"
        )
    return base, key


def chat_completion(system_prompt: str, user_prompt: str) -> str:
    base, key = _base_and_key()
    url = f"{base}/chat/completions"
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": settings.llm_temperature,
    }
    with httpx.Client(timeout=float(settings.llm_timeout_seconds)) as client:
        resp = client.post(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("LLM 返回异常：缺少 choices")
    message = (choices[0].get("message") or {}).get("content")
    if not isinstance(message, str) or not message.strip():
        raise RuntimeError("LLM 返回异常：message.content 为空")
    return message.strip()
