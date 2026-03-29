"""
ATS LaTeX Refactor Engine — FastAPI Application Entry Point
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.routers import refactor

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

# Create FastAPI app
app = FastAPI(
    title="ATS LaTeX Refactor Engine",
    description=(
        "API for dynamically refactoring LaTeX resumes to maximize "
        "ATS keyword match against target job descriptions."
    ),
    version="1.0.0",
)

# CORS middleware — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Next.js dev server
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(refactor.router, prefix="/api", tags=["refactor"])


@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok", "service": "ats-latex-refactor-engine"}
