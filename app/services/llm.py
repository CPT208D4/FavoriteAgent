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


def _contains_cjk(text: str) -> bool:
    # CJK Unified Ideographs + common punctuation blocks.
    for ch in text:
        code = ord(ch)
        if (
            0x4E00 <= code <= 0x9FFF  # CJK Unified Ideographs
            or 0x3400 <= code <= 0x4DBF  # CJK Unified Ideographs Extension A
            or 0x3000 <= code <= 0x303F  # CJK Symbols and Punctuation
            or 0xFF00 <= code <= 0xFFEF  # Halfwidth and Fullwidth Forms
        ):
            return True
    return False


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


def chat_completion_enforced_english(system_prompt: str, user_prompt: str) -> str:
    """
    Strongly enforce English-only output.
    - First pass: ask normally with a hardened system prompt.
    - Second pass: if output contains any CJK characters, ask for a rewrite.
    """
    hardened_system = (
        system_prompt.strip()
        + "\n\n"
        + "CRITICAL OUTPUT CONSTRAINT:\n"
        + "- Reply in ENGLISH ONLY.\n"
        + "- Do NOT output any Chinese characters (no 中文), Japanese, or Korean characters.\n"
        + "- Do NOT include bilingual text. If the question or sources are non-English, translate them.\n"
        + "- If you are about to output any non-English character, rewrite to English.\n"
    )
    def _strip_cjk_chars(text: str) -> str:
        out_chars: list[str] = []
        for ch in text:
            code = ord(ch)
            if (
                0x4E00 <= code <= 0x9FFF
                or 0x3400 <= code <= 0x4DBF
                or 0x3000 <= code <= 0x303F
                or 0xFF00 <= code <= 0xFFEF
            ):
                continue
            out_chars.append(ch)
        cleaned = "".join(out_chars)
        # normalize excessive whitespace introduced by stripping
        return " ".join(cleaned.split())

    answer = chat_completion(hardened_system, user_prompt)
    if not _contains_cjk(answer):
        return answer

    # Up to 3 rewrite attempts, then hard-strip any remaining CJK chars.
    rewrite_system = (
        "You rewrite text.\n"
        "Output MUST be English-only.\n"
        "Hard constraint: output must contain ZERO CJK characters.\n"
        "If a proper noun is in a non-English script, translate or romanize it.\n"
        "Keep meaning and keep a Sources section if present.\n"
        "Return the rewritten answer only."
    )
    for _ in range(3):
        rewrite_user = (
            "Rewrite the following into English-only. "
            "Your output must contain ZERO CJK characters:\n\n"
            + answer
        )
        answer = chat_completion(rewrite_system, rewrite_user)
        if not _contains_cjk(answer):
            return answer

    # Last-resort safety: remove any remaining CJK characters.
    return _strip_cjk_chars(answer)
