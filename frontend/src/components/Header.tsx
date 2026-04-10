'use client';

import PipelineStatusIndicator from './PipelineStatus';
import type { PipelineStatus } from '@/types';

interface HeaderProps {
  status: PipelineStatus;
}

export default function Header({ status }: HeaderProps) {
  const provider = (process.env.NEXT_PUBLIC_LLM_PROVIDER || 'openrouter').toLowerCase();
  const providerLabel = provider === 'puter' ? 'Puter' : 'OpenRouter';

  return (
    <header className="app-header">
      <div className="header-left">
        <div className="header-logo">
          <span className="logo-icon">◆</span>
          <h1 className="header-title">
            ATS LaTeX <span className="accent">Refactor Engine</span>
          </h1>
        </div>
        <p className="header-subtitle">
          Surgically refactor your resume for 100% ATS keyword match
        </p>
      </div>
      <div className="header-right">
        <div className="provider-indicator" title="Active LLM provider">
          <span className="provider-key">Provider</span>
          <span className={`provider-value ${provider === 'puter' ? 'puter' : 'openrouter'}`}>
            {providerLabel}
          </span>
        </div>
        <PipelineStatusIndicator status={status} />
      </div>
    </header>
  );
}
