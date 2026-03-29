'use client';

interface PDFViewerProps {
  pdfUrl: string | null;
  pageCount: number | null;
}

export default function PDFViewer({ pdfUrl, pageCount }: PDFViewerProps) {
  if (!pdfUrl) {
    return (
      <div className="glass-card pdf-viewer-card">
        <div className="card-header">
          <span className="card-icon">📄</span>
          <h2 className="card-title">PDF Preview</h2>
        </div>
        <div className="pdf-empty-state">
          <div className="empty-icon">📄</div>
          <p className="empty-text">Your refactored resume will appear here</p>
          <p className="empty-subtext">
            Paste a job description and click &quot;Refactor&quot; to generate
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card pdf-viewer-card">
      <div className="card-header">
        <span className="card-icon">📄</span>
        <h2 className="card-title">PDF Preview</h2>
        {pageCount && (
          <span className={`page-badge ${pageCount === 1 ? 'success' : 'warning'}`}>
            {pageCount} page{pageCount !== 1 ? 's' : ''}
          </span>
        )}
      </div>
      <div className="pdf-container">
        <iframe
          src={pdfUrl}
          title="Refactored Resume PDF"
          className="pdf-iframe"
        />
      </div>
    </div>
  );
}
