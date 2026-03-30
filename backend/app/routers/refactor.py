"""
API router for resume refactoring endpoints.
"""

import os
import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    RefactorRequest,
    RefactorResponse,
    TemplateResponse,
    ErrorResponse,
)
from app.services.llm_service import call_refactor_llm, call_condense_llm, call_paraphrase_bullet_llm
from app.services.latex_compiler import compile_latex, LaTeXCompilationError
from app.services.parser import parse_llm_response, parse_condense_response

logger = logging.getLogger(__name__)

router = APIRouter()

# Maximum number of condensation retries
MAX_CONDENSE_RETRIES = 2

# Path to the base resume template
TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "templates",
    "base_resume.tex"
)


@router.get("/template", response_model=TemplateResponse)
async def get_template():
    """
    Returns the base resume LaTeX template stored on the backend.
    Frontend fetches this on mount to populate the Monaco Editor.
    """
    try:
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            latex_code = f.read()
        return TemplateResponse(latex_code=latex_code)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Base resume template not found on server."
        )


from app.services.latex_parser import extract_and_templatize_bullets, reconstruct_latex

@router.post(
    "/refactor",
    response_model=RefactorResponse,
    responses={
        422: {"model": ErrorResponse, "description": "LaTeX compilation error"},
        502: {"model": ErrorResponse, "description": "LLM API error"},
    }
)
async def refactor_resume(request: RefactorRequest):
    """
    Main refactoring pipeline:
    1. Parse and extract target bullet points
    2. Call LLM to output updated JSON for those bullets
    3. Programmatically validate structural lengths (length diff must be <= 0 and >= -1 word)
    4. Reconstruct and Compile LaTeX to PDF
    """
    condensation_passes = 0

    # --- Step 1: Parse Bullet Points ---
    logger.info("Step 1: Parsing and extracting targeted bullet points...")
    bullets_map, templated_latex = extract_and_templatize_bullets(request.latex_code)
    
    if not bullets_map:
        raise HTTPException(status_code=400, detail="Could not find any bullet points in Professional Experience or Projects sections.")

    # --- Step 2: Call LLM for refactoring ---
    try:
        logger.info(f"Step 2: Calling LLM for resume refactoring ({len(bullets_map)} bullets)...")
        raw_response = await call_refactor_llm(
            job_description=request.job_description,
            latex_code=request.latex_code,
            bullets_map=bullets_map
        )
    except Exception as e:
        logger.error(f"LLM API call failed: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"LLM API call failed: {str(e)}"
        )

    # --- Step 3: Parse and Validate LLM response ---
    try:
        logger.info("Step 3: Parsing and strictly validating LLM JSON response...")
        thought_process, updated_bullets = parse_llm_response(raw_response)
        
        # Strict validation loop (Character Count Baseline)
        final_valid_bullets = {}
        for b_id, original_text in bullets_map.items():
            if b_id not in updated_bullets:
                logger.warning(f"LLM dropped {b_id}. Reverting to original.")
                final_valid_bullets[b_id] = original_text
                continue
                
            orig_char_count = len(original_text)
            
            draft_text = updated_bullets[b_id]
            retries = 0
            MAX_PARAPHRASE_RETRIES = 3

            # Constraint: new_char_count MUST be <= orig_char_count to guarantee it won't trigger a new line wrap
            while len(draft_text) > orig_char_count and retries < MAX_PARAPHRASE_RETRIES:
                logger.warning(
                    f"Validation failed for {b_id}: Original={orig_char_count} chars, Draft={len(draft_text)} chars. "
                    f"Triggering micro-paraphrase (Attempt {retries + 1}/{MAX_PARAPHRASE_RETRIES})..."
                )
                try:
                    draft_text = await call_paraphrase_bullet_llm(
                        original_bullet=original_text,
                        draft_bullet=draft_text,
                        max_chars=orig_char_count
                    )
                except Exception as e:
                    logger.error(f"Micro-paraphrase exception on attempt {retries + 1}: {e}")
                
                retries += 1
            
            # Post-retry evaluation
            if len(draft_text) > orig_char_count:
                logger.error(f"All {MAX_PARAPHRASE_RETRIES} paraphrase attempts failed boundary ({len(draft_text)} > {orig_char_count}). Reverting to original layout to protect 1-page compliance.")
                final_valid_bullets[b_id] = original_text
            else:
                if retries > 0:
                    logger.info(f"Paraphrase successful after {retries} attempt(s)! Resized to {len(draft_text)} chars. Layout protected.")
                final_valid_bullets[b_id] = draft_text

        # Reconstruct the LaTeX using only perfectly validated bullets
        refactored_latex = reconstruct_latex(templated_latex, final_valid_bullets)
        
    except ValueError as e:
        logger.error(f"Failed to parse LLM response: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to parse LLM response: {str(e)}"
        )

    # --- Step 4: Compile LaTeX to PDF ---
    try:
        logger.info("Step 4: Compiling LaTeX to PDF...")
        pdf_base64, page_count = await compile_latex(refactored_latex)
    except LaTeXCompilationError as e:
        logger.error(f"LaTeX compilation failed: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"LaTeX compilation failed: {str(e)}. "
                   f"Compiler log: {e.compiler_log[:500] if e.compiler_log else 'N/A'}"
        )

    # --- Step 5: Absolute worst-case fallback ---
    while page_count > 1 and condensation_passes < MAX_CONDENSE_RETRIES:
        condensation_passes += 1
        logger.info(
            f"Step 5: Emergency condensation pass (page count {page_count}) "
            f"{condensation_passes}/{MAX_CONDENSE_RETRIES}..."
        )

        try:
            condense_response = await call_condense_llm(
                latex_code=refactored_latex,
                page_count=page_count,
            )
            refactored_latex = parse_condense_response(condense_response)
        except (ValueError, Exception) as e:
            logger.warning(f"Condensation pass {condensation_passes} failed: {e}")
            break

        try:
            pdf_base64, page_count = await compile_latex(refactored_latex)
        except LaTeXCompilationError as e:
            logger.error(f"Recompilation after condensation failed: {e}")
            raise HTTPException(
                status_code=422,
                detail=f"LaTeX recompilation after condensation failed: {str(e)}"
            )

    logger.info(f"Pipeline complete: {page_count} page(s), {condensation_passes} condensation pass(es)")

    return RefactorResponse(
        thought_process=thought_process,
        refactored_latex=refactored_latex,
        pdf_base64=pdf_base64,
        page_count=page_count,
        condensation_passes=condensation_passes,
    )
