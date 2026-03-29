'use client';

import PipelineStatusIndicator from './PipelineStatus';
import type { PipelineStatus } from '@/types';

interface HeaderProps {
  status: PipelineStatus;
}

export default function Header({ status }: HeaderProps) {
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
        <PipelineStatusIndicator status={status} />
      </div>
    </header>
  );
}
