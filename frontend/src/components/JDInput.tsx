'use client';

interface JDInputProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export default function JDInput({ value, onChange, disabled }: JDInputProps) {
  return (
    <div className="glass-card jd-input-card">
      <div className="card-header">
        <span className="card-icon">📋</span>
        <h2 className="card-title">Target Job Description</h2>
        <span className="char-count">{value.length} chars</span>
      </div>
      <textarea
        id="jd-input"
        className="jd-textarea"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder="Paste the target job description here...&#10;&#10;Include the full JD text with requirements, responsibilities, and preferred qualifications for the best ATS match."
        disabled={disabled}
        rows={10}
      />
    </div>
  );
}
