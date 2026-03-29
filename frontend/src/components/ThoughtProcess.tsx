'use client';

import { useState } from 'react';

interface ThoughtProcessProps {
  content: string | null;
  condensationPasses: number;
}

export default function ThoughtProcess({
  content,
  condensationPasses,
}: ThoughtProcessProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!content) return null;

  return (
    <div className="glass-card thought-process-card">
      <button
        className="thought-toggle"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
      >
        <span className="card-icon">🧠</span>
        <span className="thought-title">LLM Analysis & Strategy</span>
        {condensationPasses > 0 && (
          <span className="condense-badge">
            ⚡ Condensed in {condensationPasses} pass{condensationPasses > 1 ? 'es' : ''}
          </span>
        )}
        <span className={`chevron ${isOpen ? 'open' : ''}`}>▼</span>
      </button>
      {isOpen && (
        <div className="thought-content">
          <pre className="thought-pre">{content}</pre>
        </div>
      )}
    </div>
  );
}
