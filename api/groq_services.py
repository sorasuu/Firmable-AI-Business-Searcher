"""Utility wrappers for Groq Compound models and built-in tools."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import os
import json
import logging

logger = logging.getLogger(__name__)

try:  # pragma: no cover - import guard
    from groq import Groq  # type: ignore
except ImportError:  # pragma: no cover - handled gracefully in code
    Groq = None  # type: ignore


def _as_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _serialise_tools(tools: Any) -> Optional[List[Dict[str, Any]]]:  # pragma: no cover - simple passthrough
    if not tools:
        return None

    serialised: List[Dict[str, Any]] = []
    for tool in tools:
        # Attempt to convert dataclass-like objects to dictionaries
        if hasattr(tool, "model_dump"):
            try:
                serialised.append(tool.model_dump())  # type: ignore[arg-type]
                continue
            except Exception:  # pragma: no cover - defensive
                pass

        if hasattr(tool, "__dict__"):
            serialised.append({k: v for k, v in tool.__dict__.items() if not k.startswith("_")})
        else:
            serialised.append({"value": repr(tool)})

    return serialised


class GroqCompoundClient:
    """Lightweight helper around Groq's Compound models with Visit Website & Browser Automation."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        visit_model: Optional[str] = None,
        browser_model: Optional[str] = None,
        enable_visit: Optional[bool] = None,
        enable_browser_automation: Optional[bool] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.visit_model = visit_model or os.environ.get("GROQ_VISIT_MODEL") or os.environ.get("GROQ_COMPOUND_MODEL", "groq/compound-mini")
        self.browser_model = browser_model or os.environ.get("GROQ_BROWSER_MODEL") or self.visit_model
        self.enable_visit = enable_visit if enable_visit is not None else _as_bool(os.environ.get("ENABLE_GROQ_VISIT"), True)
        self.enable_browser_automation = (
            enable_browser_automation if enable_browser_automation is not None else _as_bool(os.environ.get("ENABLE_GROQ_BROWSER_AUTOMATION"), False)
        )
        model_version = os.environ.get("GROQ_MODEL_VERSION", "latest")

        if Groq and self.api_key:
            try:  # pragma: no cover - network client init is trivial
                self.client = Groq(api_key=self.api_key, default_headers={"Groq-Model-Version": model_version})
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to initialise Groq client: %s", exc)
                self.client = None
        else:
            if not Groq:
                logger.info("groq package not installed; live Groq tooling disabled")
            if not self.api_key:
                logger.info("GROQ_API_KEY not found; live Groq tooling disabled")
            self.client = None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    @property
    def is_available(self) -> bool:
        return self.client is not None

    def visit_website(self, url: str, instructions: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Call Groq's Visit Website tool via Compound models.

        Returns ``None`` when the feature is disabled or unavailable. Otherwise a
        dictionary containing the content, reasoning trace, executed tool details,
        and raw response metadata when accessible.
        """

        if not self.enable_visit or not self.client or not url:
            return None

        system_prompt = (
            "You are an expert business analyst. Visit the provided website and extract insights "
            "that help understand the company's positioning, offerings, and differentiators."
        )
        user_prompt_parts = [f"Website URL: {url}"]
        if instructions:
            user_prompt_parts.append("")
            user_prompt_parts.append(instructions.strip())
        else:
            user_prompt_parts.append(
                "Summarise the most important business insights, latest announcements, and any compelling calls to action from the site."
            )
        user_prompt = "\n".join(user_prompt_parts)

        try:
            completion = self.client.chat.completions.create(  # type: ignore[call-arg]
                model=self.visit_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                top_p=1.0,
            )
        except Exception as exc:
            logger.warning("Groq visit_website call failed: %s", exc)
            return {"error": str(exc), "url": url}

        message = completion.choices[0].message  # type: ignore[index]
        executed_tools = _serialise_tools(getattr(message, "executed_tools", None))

        raw_data: Optional[Dict[str, Any]] = None
        if hasattr(completion, "model_dump"):
            try:
                raw_data = completion.model_dump()  # type: ignore[call-arg]
            except Exception:  # pragma: no cover - defensive
                pass
        elif hasattr(completion, "model_dump_json"):
            try:
                raw_data = json.loads(completion.model_dump_json())  # type: ignore[call-arg]
            except Exception:  # pragma: no cover - defensive
                pass

        return {
            "url": url,
            "content": getattr(message, "content", ""),
            "reasoning": getattr(message, "reasoning", None),
            "executed_tools": executed_tools,
            "raw": raw_data,
        }

    def browser_research(self, question: str, *, focus_url: Optional[str] = None, instructions: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Run Groq browser automation for deeper research. Returns ``None`` when disabled."""

        if not self.enable_browser_automation or not self.client or not question:
            return None

        system_prompt = (
            "You are an AI research analyst. Use browser automation and web search to gather up-to-date, factual information. "
            "Return concise answers with Markdown formatting and cite key sources when available."
        )
        user_lines = []
        if focus_url:
            user_lines.append(f"Primary domain to explore: {focus_url}")
        user_lines.append(f"Research question: {question}")
        if instructions:
            user_lines.append("")
            user_lines.append(instructions.strip())
        user_prompt = "\n".join(user_lines)

        try:
            completion = self.client.chat.completions.create(  # type: ignore[call-arg]
                model=self.browser_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                top_p=1.0,
                compound_custom={
                    "tools": {
                        "enabled_tools": ["browser_automation", "web_search"],
                    }
                },
            )
        except Exception as exc:
            logger.warning("Groq browser_research call failed: %s", exc)
            return {"error": str(exc), "question": question, "focus_url": focus_url}

        message = completion.choices[0].message  # type: ignore[index]
        executed_tools = _serialise_tools(getattr(message, "executed_tools", None))

        raw_data: Optional[Dict[str, Any]] = None
        if hasattr(completion, "model_dump"):
            try:
                raw_data = completion.model_dump()  # type: ignore[call-arg]
            except Exception:  # pragma: no cover - defensive
                pass
        elif hasattr(completion, "model_dump_json"):
            try:
                raw_data = json.loads(completion.model_dump_json())  # type: ignore[call-arg]
            except Exception:  # pragma: no cover - defensive
                pass

        return {
            "question": question,
            "focus_url": focus_url,
            "content": getattr(message, "content", ""),
            "reasoning": getattr(message, "reasoning", None),
            "executed_tools": executed_tools,
            "raw": raw_data,
        }
