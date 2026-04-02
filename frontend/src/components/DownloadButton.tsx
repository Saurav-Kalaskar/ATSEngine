'use client';

interface DownloadButtonProps {
  pdfBase64: string | null;
  disabled?: boolean;
  companyName?: string;
}

export default function DownloadButton({ pdfBase64, disabled, companyName }: DownloadButtonProps) {
  const handleDownload = () => {
    if (!pdfBase64) return;

    const bytes = Uint8Array.from(atob(pdfBase64), c => c.charCodeAt(0));
    const blob = new Blob([bytes], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);

    // Build filename: Saurav_Kalaskar_Resume_CompanyName.pdf
    const companySuffix = companyName ? `_${companyName}` : '';
    const filename = `Saurav_Kalaskar_Resume${companySuffix}.pdf`;

    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
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
