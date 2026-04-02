'use client';

import { useState, useEffect } from 'react';
import Header from '@/components/Header';
import JDInput from '@/components/JDInput';
import LaTeXEditor from '@/components/LaTeXEditor';
import PDFViewer from '@/components/PDFViewer';
import ThoughtProcess from '@/components/ThoughtProcess';
import DownloadButton from '@/components/DownloadButton';
import { useRefactorPipeline } from '@/hooks/useRefactorPipeline';
import { fetchTemplate } from '@/lib/api';

export default function Home() {
  const [jobDescription, setJobDescription] = useState('');
  const [latexCode, setLatexCode] = useState('');
  const [templateLoading, setTemplateLoading] = useState(true);
  const [templateError, setTemplateError] = useState<string | null>(null);

  const pipeline = useRefactorPipeline();

  // Fetch the base resume template on mount
  useEffect(() => {
    async function loadTemplate() {
      try {
        const template = await fetchTemplate();
        setLatexCode(template);
      } catch (err) {
        setTemplateError(
          'Could not load resume template from backend. Make sure the backend is running on port 8000.'
        );
        console.error('Failed to load template:', err);
      } finally {
        setTemplateLoading(false);
      }
    }
    loadTemplate();
  }, []);

  const isProcessing = !['idle', 'success', 'error'].includes(pipeline.status);

  const handleRefactor = () => {
    if (!jobDescription.trim() || !latexCode.trim()) return;
    pipeline.startRefactor(jobDescription, latexCode);
  };

  const canRefactor =
    jobDescription.trim().length >= 50 &&
    latexCode.trim().length >= 100 &&
    !isProcessing;

  return (
    <div className="app-container">
      <Header status={pipeline.status} />

      <main className="main-content">
        {/* Left Panel — Inputs */}
        <div className="panel left-panel">
          <JDInput
            value={jobDescription}
            onChange={setJobDescription}
            disabled={isProcessing}
          />

          {templateError && (
            <div className="error-banner">
              <span>⚠️</span> {templateError}
            </div>
          )}

          {templateLoading ? (
            <div className="glass-card latex-editor-card">
              <div className="editor-loading">
                <div className="loading-spinner" />
                <span>Loading resume template...</span>
              </div>
            </div>
          ) : (
            <LaTeXEditor
              value={latexCode}
              onChange={setLatexCode}
              disabled={isProcessing}
            />
          )}

          <div className="action-bar">
            <button
              id="refactor-btn"
              className={`refactor-btn ${isProcessing ? 'processing' : ''}`}
              onClick={handleRefactor}
              disabled={!canRefactor}
            >
              {isProcessing ? (
                <>
                  <div className="btn-spinner" />
                  Processing...
                </>
              ) : (
                <>
                  <span className="btn-icon">▶</span>
                  Refactor Resume
                </>
              )}
            </button>

            {pipeline.status === 'success' && (
              <button className="reset-btn" onClick={pipeline.reset}>
                ↺ Reset
              </button>
            )}
          </div>

          {pipeline.status === 'error' && pipeline.error && (
            <div className="error-banner">
              <span>❌</span> {pipeline.error}
            </div>
          )}
        </div>

        {/* Right Panel — Outputs */}
        <div className="panel right-panel">
          <PDFViewer
            pdfUrl={pipeline.pdfUrl}
            pageCount={pipeline.pageCount}
          />

          <ThoughtProcess
            content={pipeline.thoughtProcess}
            condensationPasses={pipeline.condensationPasses}
          />

          <DownloadButton
            pdfBase64={pipeline.pdfBase64}
            disabled={pipeline.status !== 'success'}
            companyName={pipeline.companyName}
          />
        </div>
      </main>
    </div>
  );
}
