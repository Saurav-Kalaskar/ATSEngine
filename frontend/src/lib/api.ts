import type { RefactorResponse, TemplateResponse } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Fetch the base resume LaTeX template from the backend.
 */
export async function fetchTemplate(): Promise<string> {
  const res = await fetch(`${API_BASE}/api/template`);
  if (!res.ok) {
    throw new Error(`Failed to fetch template: ${res.statusText}`);
  }
  const data: TemplateResponse = await res.json();
  return data.latex_code;
}

/**
 * Submit a job description and LaTeX code for ATS refactoring.
 */
export async function refactorResume(
  jobDescription: string,
  latexCode: string
): Promise<RefactorResponse> {
  const res = await fetch(`${API_BASE}/api/refactor`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      job_description: jobDescription,
      latex_code: latexCode,
    }),
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || `Refactoring failed: ${res.statusText}`);
  }

  return res.json();
}
