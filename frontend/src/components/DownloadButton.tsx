'use client';

interface DownloadButtonProps {
  pdfBase64: string | null;
  disabled?: boolean;
}

export default function DownloadButton({ pdfBase64, disabled }: DownloadButtonProps) {
  const handleDownload = () => {
    if (!pdfBase64) return;

    const bytes = Uint8Array.from(atob(pdfBase64), c => c.charCodeAt(0));
    const blob = new Blob([bytes], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);

    const timestamp = new Date().toISOString().slice(0, 10);
    const a = document.createElement('a');
    a.href = url;
    a.download = `resume_refactored_${timestamp}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <button
      className="download-btn"
      onClick={handleDownload}
      disabled={disabled || !pdfBase64}
    >
      <span className="download-icon">⬇</span>
      Download PDF
    </button>
  );
}
