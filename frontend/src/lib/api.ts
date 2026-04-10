import type { RefactorResponse, TemplateResponse } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const LLM_PROVIDER = (process.env.NEXT_PUBLIC_LLM_PROVIDER || 'openrouter').toLowerCase();
const PUTER_SCRIPT_SRC = 'https://js.puter.com/v2/';

let puterScriptPromise: Promise<void> | null = null;

function loadPuterScript(): Promise<void> {
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('Puter requires a browser environment.'));
  }

  if (window.puter) {
    return Promise.resolve();
  }

  if (puterScriptPromise) {
    return puterScriptPromise;
  }

  puterScriptPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${PUTER_SCRIPT_SRC}"]`
    );

    if (existing) {
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener(
        'error',
        () => reject(new Error('Failed to load Puter SDK script.')),
        { once: true }
      );
      return;
    }

    const script = document.createElement('script');
    script.src = PUTER_SCRIPT_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load Puter SDK script.'));
    document.head.appendChild(script);
  });

  return puterScriptPromise;
}

async function ensurePuterAuthToken(): Promise<string> {
  await loadPuterScript();

  if (!window.puter) {
    throw new Error('Puter SDK is unavailable after script load.');
  }

  await window.puter.ui.authenticateWithPuter();

  const token = window.puter.authToken;
  if (!token) {
    throw new Error('Puter authentication succeeded but no auth token was found.');
  }

  return token;
}

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
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (LLM_PROVIDER === 'puter') {
    const puterToken = await ensurePuterAuthToken();
    headers['X-PUTER-AUTH-TOKEN'] = puterToken;
  }

  const res = await fetch(`${API_BASE}/api/refactor`, {
    method: 'POST',
    headers,
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
