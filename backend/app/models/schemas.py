from pydantic import BaseModel, Field


class RefactorRequest(BaseModel):
    """Request body for the resume refactoring endpoint."""
    job_description: str = Field(
        ...,
        min_length=50,
        description="The target job description text to match against"
    )
    latex_code: str = Field(
        ...,
        min_length=100,
        description="The raw LaTeX resume code to refactor"
    )


class RefactorResponse(BaseModel):
    """Response body containing the refactored resume data."""
    thought_process: str = Field(
        ...,
        description="The LLM's analysis and keyword mapping strategy"
    )
    refactored_latex: str = Field(
        ...,
        description="The complete refactored LaTeX code"
    )
    pdf_base64: str = Field(
        ...,
        description="Base64-encoded PDF of the compiled resume"
    )
    page_count: int = Field(
        ...,
        description="Number of pages in the compiled PDF (should always be 1)"
    )
    condensation_passes: int = Field(
        default=0,
        description="Number of condensation passes needed (0 = fit first try)"
    )


class TemplateResponse(BaseModel):
    """Response body for the resume template endpoint."""
    latex_code: str = Field(
        ...,
        description="The default base resume LaTeX code"
    )


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    error_type: str = "general"
    compiler_log: str | None = None
