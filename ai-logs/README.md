# AI-assisted development (vibe coding logs)

This folder holds **primary prompts** used with AI coding assistants (Cursor / ChatGPT-style tools) to generate and iterate on core parts of this project, plus **references** to the in-application LLM system prompts shipped with the backend.

| File | Contents |
|------|----------|
| [`vibe-coding-prompts.md`](vibe-coding-prompts.md) | High-level development prompts (architecture, RAG, uploads, reports). |
| [`in-app-llm-system-prompts.md`](in-app-llm-system-prompts.md) | **Verbatim** strings and templates as used in code (plus `llm.chat_completion_enforced_english`); keep in sync with `app/services/*.py` and `llm.py`. |

If prompts drift from the codebase, **source files win**—check `app/services/qa.py`, `classification.py`, `reporting.py`, and `llm.py`.
