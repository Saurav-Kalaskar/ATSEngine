"""
LLM orchestration service using OpenRouter OpenAI-compatible API.
"""

import json
import os
import logging

import httpx

from openai import AsyncOpenAI
from dotenv import load_dotenv

from app.prompts.system_prompt import build_system_prompt, build_condense_prompt

load_dotenv()
logger = logging.getLogger(__name__)

# LLM client configuration
_client: AsyncOpenAI | None = None


def get_llm_provider() -> str:
    """Return the configured LLM provider."""
    return os.getenv("LLM_PROVIDER", "openrouter").strip().lower()


def get_llm_client() -> AsyncOpenAI:
    """Get or create the async OpenAI client configured for OpenRouter."""
    global _client

    if get_llm_provider() == "puter":
        raise RuntimeError("OpenAI client is not used when LLM_PROVIDER=puter")

    if _client is None:
        base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
        api_key = os.getenv("LLM_API_KEY")

        if not api_key:
            raise ValueError(
                "LLM_API_KEY environment variable is not set. "
                "Please set it in your .env file."
            )

        _client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )
    return _client


def get_model() -> str:
    """Get the configured OpenRouter model identifier from environment."""
    model = os.getenv("LLM_MODEL")
    if not model:
        raise ValueError(
            "LLM_MODEL environment variable is not set. "
            "Please set it in your .env file."
        )
    return model


def _coerce_text(value) -> str:
    """Best-effort extraction of text from mixed response payloads."""
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        parts = [_coerce_text(item) for item in value]
        return "\n".join(part for part in parts if part).strip()

    if isinstance(value, dict):
        # OpenAI-compatible structures
        if "choices" in value and isinstance(value["choices"], list) and value["choices"]:
            choice = value["choices"][0]
            if isinstance(choice, dict):
                message = choice.get("message")
                if isinstance(message, dict):
                    return _coerce_text(message.get("content"))

        # Puter-style or generic structures
        for key in ("message", "content", "text", "result"):
            if key in value:
                text = _coerce_text(value.get(key))
                if text:
                    return text

        # Some providers send multimodal content arrays
        if "content" in value and isinstance(value["content"], list):
            content_parts = []
            for item in value["content"]:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        content_parts.append(text)
            if content_parts:
                return "\n".join(content_parts).strip()

    return ""


async def _call_puter_chat(
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    puter_auth_token: str | None = None,
) -> str:
    """
    Call Puter's AI driver endpoint with a user-scoped auth token.
    """
    model = get_model()
    auth_token = puter_auth_token or os.getenv("PUTER_AUTH_TOKEN")
    if not auth_token:
        raise ValueError(
            "Missing Puter auth token. Provide X-PUTER-AUTH-TOKEN header "
            "or set PUTER_AUTH_TOKEN in the backend environment."
        )

    api_origin = os.getenv("PUTER_API_ORIGIN", "https://api.puter.com").rstrip("/")
    request_origin = os.getenv("PUTER_REQUEST_ORIGIN", "https://puter.work").rstrip("/")
    request_referer = os.getenv("PUTER_REQUEST_REFERER", f"{request_origin}/")
    timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))

    payload = {
        "interface": "puter-chat-completion",
        "driver": "ai-chat",
        "method": "complete",
        "args": {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        "auth_token": auth_token,
    }

    headers = {
        "Content-Type": "text/plain;actually=json",
        "Accept": "application/json",
        "Origin": request_origin,
        "Referer": request_referer,
        "User-Agent": "puter-js/1.0",
        "Authorization": f"Bearer {auth_token}",
    }

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.post(
            f"{api_origin}/drivers/call",
            headers=headers,
            content=json.dumps(payload),
        )

    if response.status_code == 401:
        raise ValueError("Puter authentication failed (401). Re-authenticate in the frontend.")

    if response.status_code == 403:
        raise RuntimeError(
            "Puter API call failed with HTTP 403 (Forbidden). "
            "This usually means the token is invalid/expired or request-origin checks failed. "
            "Re-authenticate in the frontend and retry."
        )

    if response.status_code >= 400:
        raise RuntimeError(
            f"Puter API call failed with HTTP {response.status_code}: {response.text[:500]}"
        )

    try:
        body = response.json()
    except ValueError as exc:
        raise ValueError("Puter returned a non-JSON response.") from exc

    if isinstance(body, dict) and body.get("success") is False:
        error_payload = body.get("error")
        error_text = _coerce_text(error_payload) or str(error_payload) or "Unknown Puter error"
        raise RuntimeError(f"Puter driver error: {error_text}")

    content = _coerce_text(body)
    if not content:
        raise ValueError("Puter provider returned an empty response payload.")
    return content


async def _call_chat(
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    puter_auth_token: str | None = None,
) -> str:
    """Dispatch chat calls to configured provider."""
    provider = get_llm_provider()
    model = get_model()

    if provider == "puter":
        return await _call_puter_chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            puter_auth_token=puter_auth_token,
        )

    client = get_llm_client()
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content or ""
    if not content:
        raise ValueError("LLM provider returned an empty response payload.")
    return content

async def call_refactor_llm(
    job_description: str,
    latex_code: str,
    bullets_map: dict,
    puter_auth_token: str | None = None,
) -> str:
    """
    Call the LLM to refactor the resume bullets based on the job description.

    Args:
        job_description: The target job description text.
        latex_code: The full LaTeX code for context reading.
        bullets_map: JSON dictionary of the extracted targeted \\item bullets.

    Returns:
        The raw LLM response text containing <THOUGHT_PROCESS> and <FINAL_JSON>.
    """
    model = get_model()
    system_prompt = build_system_prompt()

    user_prompt = f"""<TARGET_JD>
{job_description}
</TARGET_JD>

<CURRENT_LATEX_RESUME>
{latex_code}
</CURRENT_LATEX_RESUME>

<BULLETS_TO_EDIT>
{json.dumps(bullets_map, indent=2)}
</BULLETS_TO_EDIT>"""

    logger.info(f"Calling LLM ({model}) for resume refactoring...")

    try:
        content = await _call_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=8000,
            puter_auth_token=puter_auth_token,
        )
        logger.info(f"LLM response received: {len(content)} characters")
        return content

    except Exception:
        raise


async def call_condense_llm(
    latex_code: str,
    page_count: int,
    puter_auth_token: str | None = None,
) -> str:
    """
    Call the LLM to condense the resume to fit on one page.

    Args:
        latex_code: The current LaTeX code that compiled to >1 page.
        page_count: The current number of pages.
    Returns:
        The raw LLM response text containing <FINAL_LATEX>.
    """
    model = get_model()
    system_prompt = build_condense_prompt(page_count)

    user_prompt = f"""<CURRENT_LATEX_RESUME>
{latex_code}
</CURRENT_LATEX_RESUME>

Condense this resume to fit on exactly 1 page. Return only the <FINAL_LATEX> block."""

    logger.info(f"Calling LLM ({model}) for condensation pass "
                f"(current: {page_count} pages)...")

    try:
        content = await _call_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=8000,
            puter_auth_token=puter_auth_token,
        )
        logger.info(f"Condensation response received: {len(content)} characters")
        return content

    except Exception:
        raise

async def call_paraphrase_bullet_llm(
    original_bullet: str,
    draft_bullet: str,
    max_chars: int,
    puter_auth_token: str | None = None,
) -> str:
    """
    Call the LLM to aggressively paraphrase a single bullet point to fit within a strict character limit,
    without losing the newly inserted \\textbf{} keywords.
    """
    model = get_model()
    
    system_prompt = (
        "You are an absolute precision editor. Your only job is to shorten the provided text "
        f"so it is STRICTLY LESS THAN {max_chars} characters.\n\n"
        "RULES:\n"
        "1. You MUST retain EVERY \\textbf{keyword} present in the draft.\n"
        "2. Do NOT remove any LaTeX grammar (like \\textbf).\n"
        "3. Rewrite the surrounding filler words to be maximally concise.\n"
        f"4. The final string MUST be <= {max_chars} characters.\n"
        "5. Output ONLY the raw shortened LaTeX string. No `<FINAL_LATEX>`, no markdown, no quotes."
    )
    
    user_prompt = f"Original Bullet: {original_bullet}\nDraft Bullet (Too Long): {draft_bullet}\nTarget Max Length: {max_chars} chars.\nShorten the Draft Bullet."
    
    logger.info(f"Calling LLM ({model}) to micro-paraphrase bullet down to {max_chars} chars...")
    
    try:
        content = await _call_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=600,
            puter_auth_token=puter_auth_token,
        )
        content = content.strip()
        if not content:
            raise ValueError("LLM provider returned an empty response payload.")
        # Clean up possible markdown tags around the string just in case
        content = content.removeprefix("```latex").removeprefix("```").removesuffix("```").strip()
        return content

    except Exception:
        raise
