import time

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


def _client_timeout() -> httpx.Timeout:
    read = float(settings.llm_timeout_seconds)
    connect = float(settings.llm_connect_timeout_seconds)
    return httpx.Timeout(
        connect=connect,
        read=read,
        write=connect,
        pool=connect,
    )


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
    timeout = _client_timeout()
    attempts = 1 + max(0, settings.llm_retries)
    for attempt in range(attempts):
        try:
            with httpx.Client(timeout=timeout) as client:
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
        except (
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
            httpx.WriteTimeout,
            httpx.ConnectError,
        ) as exc:
            if attempt + 1 >= attempts:
                raise
            time.sleep(1.5 * (attempt + 1))
