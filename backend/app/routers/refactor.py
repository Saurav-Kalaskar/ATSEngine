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
from app.services.llm_service import call_refactor_llm, call_condense_llm
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
    1. Call LLM to refactor LaTeX based on JD
    2. Parse the response for thought process + LaTeX code
    3. Compile LaTeX to PDF
    4. Verify page count (must be 1)
    5. If >1 page: condense and retry (max 2 times)
    6. Return result
    """
    condensation_passes = 0

    # --- Step 1: Call LLM for refactoring ---
    try:
        logger.info("Step 1: Calling LLM for resume refactoring...")
        raw_response = await call_refactor_llm(
            job_description=request.job_description,
            latex_code=request.latex_code,
        )
    except Exception as e:
        logger.error(f"LLM API call failed: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"LLM API call failed: {str(e)}"
        )

    # --- Step 2: Parse LLM response ---
    try:
        logger.info("Step 2: Parsing LLM response...")
        thought_process, refactored_latex = parse_llm_response(raw_response)
    except ValueError as e:
        logger.error(f"Failed to parse LLM response: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to parse LLM response: {str(e)}"
        )

    # --- Step 3: Compile LaTeX to PDF ---
    try:
        logger.info("Step 3: Compiling LaTeX to PDF...")
        pdf_base64, page_count = await compile_latex(refactored_latex)
    except LaTeXCompilationError as e:
        logger.error(f"LaTeX compilation failed: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"LaTeX compilation failed: {str(e)}. "
                   f"Compiler log: {e.compiler_log[:500] if e.compiler_log else 'N/A'}"
        )

    # --- Step 4: One-page verification loop ---
    while page_count > 1 and condensation_passes < MAX_CONDENSE_RETRIES:
        condensation_passes += 1
        logger.info(
            f"Step 4: Page count is {page_count}, running condensation pass "
            f"{condensation_passes}/{MAX_CONDENSE_RETRIES}..."
        )

        # Call LLM to condense
        try:
            condense_response = await call_condense_llm(
                latex_code=refactored_latex,
                page_count=page_count,
            )
            refactored_latex = parse_condense_response(condense_response)
        except (ValueError, Exception) as e:
            logger.warning(f"Condensation pass {condensation_passes} failed: {e}")
            break

        # Recompile
        try:
            pdf_base64, page_count = await compile_latex(refactored_latex)
        except LaTeXCompilationError as e:
            logger.error(f"Recompilation after condensation failed: {e}")
            raise HTTPException(
                status_code=422,
                detail=f"LaTeX recompilation after condensation failed: {str(e)}"
            )

    # Log final result
    if page_count > 1:
        logger.warning(
            f"Resume still {page_count} pages after {condensation_passes} "
            f"condensation passes. Returning as-is."
        )

    logger.info(
        f"Pipeline complete: {page_count} page(s), "
        f"{condensation_passes} condensation pass(es)"
    )

    return RefactorResponse(
        thought_process=thought_process,
        refactored_latex=refactored_latex,
        pdf_base64=pdf_base64,
        page_count=page_count,
        condensation_passes=condensation_passes,
    )
