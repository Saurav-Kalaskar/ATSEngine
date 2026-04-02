"""
API router for resume refactoring endpoints.
"""

import os
import re
import logging

import asyncio
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


def _extract_company_name(jd_text: str) -> str:
    """
    Extract company name from a job description using common patterns.
    Returns a filesystem-safe string suitable for filenames.
    """
    jd_lower = jd_text.strip()
    
    # Pattern 1: "Company: <name>" or "Company Name: <name>"
    match = re.search(r'(?:company\s*(?:name)?)\s*[:：]\s*([^\n,;]+)', jd_lower, re.IGNORECASE)
    if match:
        return _sanitize_name(match.group(1).strip())
    
    # Pattern 2: "About <Company>" (common in JDs)
    match = re.search(r'\bAbout\s+([A-Z][A-Za-z0-9 &\-.]{1,40}?)(?:\n|,|\s+is\b|\s+was\b)', jd_text)
    if match:
        name = match.group(1).strip()
        if len(name.split()) <= 4:  # Company names are usually short
            return _sanitize_name(name)
    
    # Pattern 3: "at <Company>" near the beginning
    match = re.search(r'\bat\s+([A-Z][A-Za-z0-9 &\-.]+?)(?:\s*[,.\n!]|\s+is\b|\s+we\b)', jd_text[:500])
    if match:
        name = match.group(1).strip()
        if len(name.split()) <= 4:
            return _sanitize_name(name)
    
    # Pattern 4: "join <Company>" 
    match = re.search(r'\bjoin\s+(?:the\s+)?([A-Z][A-Za-z0-9 &\-.]+?)(?:\s*[,.\n!]|\s+team\b|\s+as\b)', jd_text[:800], re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        if len(name.split()) <= 4:
            return _sanitize_name(name)

    # Pattern 5: First line often has company or role - check if first line looks like a company
    first_line = jd_text.strip().split('\n')[0].strip()
    # If first line is short and starts with capital, it might be company or role title
    if len(first_line) < 60 and re.match(r'^[A-Z]', first_line):
        # Try to extract company from "Role at Company" pattern
        at_match = re.search(r'\bat\s+([A-Z].+)$', first_line)
        if at_match:
            return _sanitize_name(at_match.group(1).strip())
    
    # Fallback: return empty (frontend will use generic name)
    return ""


def _sanitize_name(name: str) -> str:
    """Convert a company name to a clean filename component."""
    # Remove common suffixes
    name = re.sub(r'\s*(Inc\.?|LLC|Ltd\.?|Corp\.?|Co\.?)\s*$', '', name, flags=re.IGNORECASE)
    # Replace spaces and special chars with underscores
    name = re.sub(r'[^A-Za-z0-9]+', '_', name)
    # Collapse multiple underscores and strip edges
    name = re.sub(r'_+', '_', name).strip('_')
    return name


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

    # --- Step 0: Extract company name from JD for filename ---
    company_name = _extract_company_name(request.job_description)
    logger.info(f"Detected company: '{company_name}'")

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
        
        # Strict validation loop (Character Count Baseline) - Executed Concurrently
        async def _validate_bullet(b_id, original_text, new_text):
            orig_char_count = len(original_text)
            draft_text = new_text
            retries = 0
            MAX_PARAPHRASE_RETRIES = 3

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
            
            if len(draft_text) > orig_char_count:
                logger.error(f"All {MAX_PARAPHRASE_RETRIES} paraphrase attempts failed boundary ({len(draft_text)} > {orig_char_count}). Reverting to original layout.")
                return b_id, original_text
            
            if retries > 0:
                logger.info(f"Paraphrase successful after {retries} attempt(s)! Resized to {len(draft_text)} chars. Layout protected.")
            return b_id, draft_text

        validation_tasks = []
        for b_id, original_text in bullets_map.items():
            if b_id not in updated_bullets:
                logger.warning(f"LLM dropped {b_id}. Reverting to original.")
                async def identity(k, v): return k, v
                validation_tasks.append(identity(b_id, original_text))
            else:
                validation_tasks.append(_validate_bullet(b_id, original_text, updated_bullets[b_id]))
                
        results = await asyncio.gather(*validation_tasks)
        final_valid_bullets = dict(results)

        # Step 3.5: Final Text Sanitization & Keyword Audit
        all_bolded_keywords = []
        for b_id, text in final_valid_bullets.items():
            # 1. Clean hallucinated 'extbf' anomalies. DeepSeek often token-drops the backslash 
            # or `json.loads` translates unescaped `\textbf` into `<TAB>extbf`.
            # This regex captures both braced (`extbf{AWS}`) and brace-less hallucinates (`extbfAWS`)
            # while avoiding double-escaping legitimate `\textbf{...}`.
            cleaned_text = re.sub(r'(?:\t)?(?<!\\)\bextbf\s*\{?([\w\/\-\.\+]+)\}?', r'\\textbf{\1}', text)
            
            # Normalize over-escaped backslashes: \\\\textbf -> \textbf
            cleaned_text = re.sub(r'\\{2,}textbf', r'\\textbf', cleaned_text)
            
            # Also clean up any accidental double-bracing: \textbf{{AWS}} -> \textbf{AWS}
            cleaned_text = cleaned_text.replace(r'\textbf{{', r'\textbf{')

            # 1b. Brace-balance check: strip orphan closing braces that crash \itemize
            open_count = 0
            balanced_chars = []
            for ch in cleaned_text:
                if ch == '{':
                    open_count += 1
                    balanced_chars.append(ch)
                elif ch == '}':
                    if open_count > 0:
                        open_count -= 1
                        balanced_chars.append(ch)
                    else:
                        logger.warning(f"Stripped orphan '}}' from {b_id} to prevent LaTeX crash")
                else:
                    balanced_chars.append(ch)
            cleaned_text = ''.join(balanced_chars)

            # 1c. Escape LaTeX-reserved special characters the LLM may inject as raw text
            cleaned_text = re.sub(r'(?<!\\)&', r'\\&', cleaned_text)
            cleaned_text = re.sub(r'(?<!\\)%', r'\\%', cleaned_text)
            cleaned_text = re.sub(r'(?<!\\)#', r'\\#', cleaned_text)
            # Escape underscores NOT inside LaTeX commands (e.g., data_pipeline -> data\_pipeline)
            cleaned_text = re.sub(r'(?<!\\)_', r'\\_', cleaned_text)

            final_valid_bullets[b_id] = cleaned_text
            
            # 2. Audit successful JD keyword injections
            found_keywords = re.findall(r'\\textbf\{([^}]+)\}', cleaned_text)
            all_bolded_keywords.extend(found_keywords)

        # Log exactly what the Algorithmic Recruiter achieved
        logger.info(f"ATS Keyword Bolding Audit: Converted {len(all_bolded_keywords)} high-value keywords to bold -> {all_bolded_keywords}")
        if len(all_bolded_keywords) == 0:
            logger.warning("AUDIT FAILED: The LLM failed to format any industry keywords across the entire payload. The ATS match score may degrade!")

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
                   f"Compiler log: {e.compiler_log[-1000:] if e.compiler_log else 'N/A'}"
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
        company_name=company_name,
    )
