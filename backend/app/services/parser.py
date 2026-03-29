"""
Parser for extracting structured blocks from LLM responses.
Extracts <THOUGHT_PROCESS> and <FINAL_LATEX> sections.
"""

import re


def parse_llm_response(raw_response: str) -> tuple[str, str]:
    """
    Parse the LLM's raw output to extract the thought process and LaTeX code.

    Args:
        raw_response: The complete text response from the LLM.

    Returns:
        A tuple of (thought_process, latex_code).

    Raises:
        ValueError: If either required block is missing from the response.
    """
    # Extract thought process
    tp_match = re.search(
        r"<THOUGHT_PROCESS>(.*?)</THOUGHT_PROCESS>",
        raw_response,
        re.DOTALL
    )

    # Extract final LaTeX
    latex_match = re.search(
        r"<FINAL_LATEX>(.*?)</FINAL_LATEX>",
        raw_response,
        re.DOTALL
    )

    if not tp_match:
        raise ValueError(
            "LLM response missing <THOUGHT_PROCESS> block. "
            "The model may have deviated from the expected output format."
        )

    if not latex_match:
        raise ValueError(
            "LLM response missing <FINAL_LATEX> block. "
            "The model may have deviated from the expected output format."
        )

    thought_process = tp_match.group(1).strip()
    latex_code = latex_match.group(1).strip()

    # Basic validation: LaTeX should contain \documentclass
    if r"\documentclass" not in latex_code:
        raise ValueError(
            "Extracted LaTeX code does not contain \\documentclass. "
            "The output may be malformed or incomplete."
        )

    return thought_process, latex_code


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
