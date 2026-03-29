'use client';

import { useRef, useCallback } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';

interface LaTeXEditorProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export default function LaTeXEditor({ value, onChange, disabled }: LaTeXEditorProps) {
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleMount: OnMount = useCallback((editor: any, monaco: any) => {
    editorRef.current = editor;

    // Define custom dark theme
    monaco.editor.defineTheme('ats-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [
        { token: 'comment', foreground: '5a5a72', fontStyle: 'italic' },
        { token: 'keyword', foreground: 'a29bfe' },
        { token: 'string', foreground: '00e676' },
      ],
      colors: {
        'editor.background': '#12121a',
        'editor.foreground': '#e8e8f0',
        'editor.lineHighlightBackground': '#1a1a2e',
        'editorCursor.foreground': '#6c5ce7',
        'editor.selectionBackground': '#6c5ce740',
        'editorLineNumber.foreground': '#5a5a72',
        'editorLineNumber.activeForeground': '#a29bfe',
        'editorWidget.background': '#0a0a0f',
        'editorWidget.border': '#ffffff10',
      },
    });

    monaco.editor.setTheme('ats-dark');
  }, []);

  return (
    <div className="glass-card latex-editor-card">
      <div className="card-header">
        <span className="card-icon">⟨/⟩</span>
        <h2 className="card-title">Base Resume LaTeX</h2>
      </div>
      <div className="editor-wrapper">
        <Editor
          height="100%"
          language="latex"
          value={value}
          onChange={(v: string | undefined) => onChange(v || '')}
          onMount={handleMount}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            wordWrap: 'on',
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            fontSize: 13,
            lineHeight: 20,
            padding: { top: 12, bottom: 12 },
            scrollBeyondLastLine: false,
            renderLineHighlight: 'gutter',
            cursorBlinking: 'smooth',
            cursorSmoothCaretAnimation: 'on',
            smoothScrolling: true,
            readOnly: disabled,
            bracketPairColorization: { enabled: true },
          }}
          loading={
            <div className="editor-loading">
              <div className="loading-spinner" />
              <span>Loading editor...</span>
            </div>
          }
        />
      </div>
    </div>
  );
}
