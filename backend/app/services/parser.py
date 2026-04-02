import json
import re

def parse_llm_response(raw_response: str) -> tuple[str, dict]:
    """
    Parse the LLM's raw output to extract the thought process and the JSON dictionary of edited bullets.

    Args:
        raw_response: The complete text response from the LLM.

    Returns:
        A tuple of (thought_process, updated_bullets_dict).

    Raises:
        ValueError: If either required block is missing or JSON is invalid.
    """
    # Extract thought process
    tp_match = re.search(
        r"<THOUGHT_PROCESS>(.*?)</THOUGHT_PROCESS>",
        raw_response,
        re.DOTALL
    )

    # Extract final JSON
    json_match = re.search(
        r"<FINAL_JSON>\s*(.*?)\s*</FINAL_JSON>",
        raw_response,
        re.DOTALL
    )

    if not tp_match:
        raise ValueError(
            "LLM response missing <THOUGHT_PROCESS> block. "
        )

    if not json_match:
        raise ValueError(
            "LLM response missing <FINAL_JSON> block. "
        )

    thought_process = tp_match.group(1).strip()
    json_code = json_match.group(1).strip()
    
    # Sometimes the LLM might wrap the JSON in ```json markdown blocks inside the tag
    json_code = re.sub(r"^```json\s*", "", json_code)
    json_code = re.sub(r"```\s*$", "", json_code)
    
    # CRITICAL: Fix unescaped LaTeX "\textbf" inside JSON strings which json.loads 
    # would incorrectly parse as a <TAB> character (\t) followed by "extbf"
    # Only escape \textbf that is NOT already double-escaped (i.e., not preceded by another backslash)
    json_code = re.sub(r'(?<!\\)\\textbf', r'\\\\textbf', json_code)
    
    try:
        updated_bullets = json.loads(json_code)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to decode <FINAL_JSON> block. Error: {str(e)}")

    return thought_process, updated_bullets


def parse_condense_response(raw_response: str) -> str:
    """
    Parse the condensation pass response (only expects <FINAL_LATEX>).

    Args:
        raw_response: The complete text response from the condensation LLM call.

    Returns:
        The condensed LaTeX code string.

    Raises:
        ValueError: If the <FINAL_LATEX> block is missing.
    """
    latex_match = re.search(
        r"<FINAL_LATEX>(.*?)</FINAL_LATEX>",
        raw_response,
        re.DOTALL
    )

    if not latex_match:
        # Fallback: try to find \documentclass directly in the response
        if r"\documentclass" in raw_response:
            # The model might have returned raw LaTeX without tags
            doc_start = raw_response.index(r"\documentclass")
            doc_end = raw_response.rfind(r"\end{document}")
            if doc_end != -1:
                return raw_response[doc_start:doc_end + len(r"\end{document}")].strip()

        raise ValueError(
            "Condensation response missing <FINAL_LATEX> block."
        )

    return latex_match.group(1).strip()
