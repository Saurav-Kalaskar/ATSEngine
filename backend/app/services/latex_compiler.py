"""
LaTeX compilation service using pdflatex with page count verification.
"""

import subprocess
import tempfile
import os
import base64
import logging

from pypdf import PdfReader

logger = logging.getLogger(__name__)


class LaTeXCompilationError(Exception):
    """Raised when pdflatex fails to compile the LaTeX code."""
    def __init__(self, message: str, compiler_log: str = ""):
        super().__init__(message)
        self.compiler_log = compiler_log


async def compile_latex(latex_code: str) -> tuple[str, int]:
    """
    Compile LaTeX code into a PDF using pdflatex.

    Args:
        latex_code: The complete LaTeX source code string.

    Returns:
        A tuple of (base64_encoded_pdf, page_count).

    Raises:
        LaTeXCompilationError: If pdflatex fails to produce a valid PDF.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "resume.tex")
        pdf_path = os.path.join(tmpdir, "resume.pdf")
        log_path = os.path.join(tmpdir, "resume.log")

        # Write LaTeX source to temp file
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_code)

        import shutil
        pdflatex_bin = shutil.which("pdflatex") or "/Library/TeX/texbin/pdflatex"
        
        # Run pdflatex with nonstopmode to prevent hanging on errors
        try:
            result = subprocess.run(
                [
                    pdflatex_bin,
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "-output-directory", tmpdir,
                    tex_path
                ],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=tmpdir
            )
        except subprocess.TimeoutExpired:
            raise LaTeXCompilationError(
                "LaTeX compilation timed out after 30 seconds."
            )
        except FileNotFoundError:
            raise LaTeXCompilationError(
                "pdflatex not found. Please install TeX Live: "
                "brew install --cask basictex"
            )

        # Check if PDF was generated
        if not os.path.exists(pdf_path):
            compiler_log = ""
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="replace") as lf:
                    full_log = lf.read()
                    # Extract the last 2000 chars which usually contain the error
                    compiler_log = full_log[-2000:]

            # Also check stderr for additional context
            error_context = result.stderr[-500:] if result.stderr else ""

            raise LaTeXCompilationError(
                "LaTeX compilation failed — no PDF output generated.",
                compiler_log=f"{compiler_log}\n\nSTDERR:\n{error_context}"
            )

        # Read and encode the PDF
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        # Get page count using pypdf
        page_count = get_page_count(pdf_bytes)

        # Base64 encode the PDF
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        logger.info(f"LaTeX compiled successfully: {page_count} page(s), "
                     f"{len(pdf_bytes)} bytes")

        return pdf_base64, page_count


def get_page_count(pdf_bytes: bytes) -> int:
    """
    Get the number of pages in a PDF from its bytes.

    Args:
        pdf_bytes: The raw PDF file bytes.

    Returns:
        The number of pages in the PDF.
    """
    import io
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return len(reader.pages)
