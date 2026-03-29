"""
LLM orchestration service using OpenAI-compatible API (OpenRouter/DeepSeek).
"""

import os
import logging

from openai import AsyncOpenAI
from dotenv import load_dotenv

from app.prompts.system_prompt import build_system_prompt, build_condense_prompt

load_dotenv()
logger = logging.getLogger(__name__)

# LLM client configuration
_client: AsyncOpenAI | None = None


def get_llm_client() -> AsyncOpenAI:
    """Get or create the async OpenAI client configured for OpenRouter."""
    global _client
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
    """Get the configured LLM model identifier."""
    return os.getenv("LLM_MODEL", "deepseek/deepseek-chat-v3-0324")


def get_fallback_model() -> str:
    """Get the fallback LLM model identifier."""
    return os.getenv("LLM_FALLBACK_MODEL", "qwen/qwen3-coder:free")


import json

async def call_refactor_llm(
    job_description: str,
    latex_code: str,
    bullets_map: dict,
    use_fallback: bool = False
) -> str:
    """
    Call the LLM to refactor the resume bullets based on the job description.

    Args:
        job_description: The target job description text.
        latex_code: The full LaTeX code for context reading.
        bullets_map: JSON dictionary of the extracted targeted \item bullets.
        use_fallback: If True, use the fallback model instead of primary.

    Returns:
        The raw LLM response text containing <THOUGHT_PROCESS> and <FINAL_JSON>.
    """
    client = get_llm_client()
    model = get_fallback_model() if use_fallback else get_model()
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
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=8000,
        )
        content = response.choices[0].message.content
        logger.info(f"LLM response received: {len(content)} characters")
        return content

    except Exception as e:
        if not use_fallback:
            logger.warning(f"Primary model failed ({e}), trying fallback...")
            return await call_refactor_llm(
                job_description, latex_code, bullets_map, use_fallback=True
            )
        raise


async def call_condense_llm(
    latex_code: str,
    page_count: int,
    use_fallback: bool = False
) -> str:
    """
    Call the LLM to condense the resume to fit on one page.

    Args:
        latex_code: The current LaTeX code that compiled to >1 page.
        page_count: The current number of pages.
        use_fallback: If True, use the fallback model.

    Returns:
        The raw LLM response text containing <FINAL_LATEX>.
    """
    client = get_llm_client()
    model = get_fallback_model() if use_fallback else get_model()
    system_prompt = build_condense_prompt(page_count)

    user_prompt = f"""<CURRENT_LATEX_RESUME>
{latex_code}
</CURRENT_LATEX_RESUME>

Condense this resume to fit on exactly 1 page. Return only the <FINAL_LATEX> block."""

    logger.info(f"Calling LLM ({model}) for condensation pass "
                f"(current: {page_count} pages)...")

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=8000,
        )
        content = response.choices[0].message.content
        logger.info(f"Condensation response received: {len(content)} characters")
        return content

    except Exception as e:
        if not use_fallback:
            logger.warning(f"Primary model failed for condensation ({e}), "
                          f"trying fallback...")
            return await call_condense_llm(
                latex_code, page_count, use_fallback=True
            )
        raise
