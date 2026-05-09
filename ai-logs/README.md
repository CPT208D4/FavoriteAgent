# AI-assisted development (vibe coding logs)

This folder holds **primary prompts** used with AI coding assistants (Cursor / ChatGPT) to generate and iterate on core parts of this project, plus **references** to the in-application LLM system prompts shipped with the backend.

| File | Contents |
|------|----------|
| [`vibe-coding-prompts.md`](vibe-coding-prompts.md) | Milestone-style dev prompts (Apr–May 2026), aligned with git history: backend, Vercel, UX, toasts, docs. |
| [`in-app-llm-system-prompts.md`](in-app-llm-system-prompts.md) | **Verbatim** strings and templates as used in code; keep in sync with `app/services/*.py` and `llm.py`. |

If prompts drift from the codebase, **source files win**—check `app/services/qa.py`, `classification.py`, `reporting.py`, and `llm.py`.
