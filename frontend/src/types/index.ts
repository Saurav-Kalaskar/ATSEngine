export type PipelineStatus =
  | 'idle'
  | 'analyzing'
  | 'modifying'
  | 'compiling'
  | 'verifying'
  | 'condensing'
  | 'success'
  | 'error';

export interface RefactorRequest {
  job_description: string;
  latex_code: string;
}

export interface RefactorResponse {
  thought_process: string;
  refactored_latex: string;
  pdf_base64: string;
  page_count: number;
  condensation_passes: number;
}

export interface TemplateResponse {
  latex_code: string;
}

export interface PipelineState {
  status: PipelineStatus;
  thoughtProcess: string | null;
  refactoredLatex: string | null;
  pdfUrl: string | null;
  pdfBase64: string | null;
  error: string | null;
  pageCount: number | null;
  condensationPasses: number;
}
