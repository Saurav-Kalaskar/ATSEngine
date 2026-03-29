'use client';

import { useState, useCallback, useRef } from 'react';
import type { PipelineState, PipelineStatus } from '@/types';
import { refactorResume } from '@/lib/api';

const INITIAL_STATE: PipelineState = {
  status: 'idle',
  thoughtProcess: null,
  refactoredLatex: null,
  pdfUrl: null,
  pdfBase64: null,
  error: null,
  pageCount: null,
  condensationPasses: 0,
};

/**
 * Core hook managing the entire refactoring pipeline.
 * Handles API calls, status transitions, and result state.
 */
export function useRefactorPipeline() {
  const [state, setState] = useState<PipelineState>(INITIAL_STATE);
  const abortRef = useRef<AbortController | null>(null);

  const setStatus = useCallback((status: PipelineStatus) => {
    setState(prev => ({ ...prev, status }));
  }, []);

  const startRefactor = useCallback(
    async (jobDescription: string, latexCode: string) => {
      // Reset state
      setState({
        ...INITIAL_STATE,
        status: 'analyzing',
      });

      // Revoke old PDF URL if exists
      if (state.pdfUrl) {
        URL.revokeObjectURL(state.pdfUrl);
      }

      try {
        // Simulate analyzing phase (1 second)
        await delay(1000);
        setStatus('modifying');

        // Simulate modifying phase transition (0.5s) then make the API call
        await delay(500);

        const result = await refactorResume(jobDescription, latexCode);

        // Brief compiling state for UX
        setStatus('compiling');
        await delay(800);

        // Check if condensation happened
        if (result.condensation_passes > 0) {
          setStatus('condensing');
          await delay(600);
        }

        // Convert base64 PDF to Blob URL
        const pdfBytes = Uint8Array.from(atob(result.pdf_base64), c =>
          c.charCodeAt(0)
        );
        const pdfBlob = new Blob([pdfBytes], { type: 'application/pdf' });
        const pdfUrl = URL.createObjectURL(pdfBlob);

        // Success!
        setState({
          status: 'success',
          thoughtProcess: result.thought_process,
          refactoredLatex: result.refactored_latex,
          pdfUrl,
          pdfBase64: result.pdf_base64,
          error: null,
          pageCount: result.page_count,
          condensationPasses: result.condensation_passes,
        });
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'An unknown error occurred';
        setState(prev => ({
          ...prev,
          status: 'error',
          error: message,
        }));
      }
    },
    [state.pdfUrl, setStatus]
  );

  const reset = useCallback(() => {
    if (state.pdfUrl) {
      URL.revokeObjectURL(state.pdfUrl);
    }
    setState(INITIAL_STATE);
  }, [state.pdfUrl]);

  return {
    ...state,
    startRefactor,
    reset,
  };
}

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
