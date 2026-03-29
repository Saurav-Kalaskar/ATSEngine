import type { PipelineStatus } from '@/types';

export const PIPELINE_STATUS_CONFIG: Record<
  PipelineStatus,
  { label: string; color: string; animation: string }
> = {
  idle: { label: 'Ready', color: 'var(--text-muted)', animation: 'none' },
  analyzing: { label: 'Analyzing JD...', color: 'var(--accent-warning)', animation: 'pulse' },
  modifying: { label: 'Refactoring LaTeX...', color: 'var(--accent-primary)', animation: 'spin' },
  compiling: { label: 'Compiling PDF...', color: 'var(--accent-success)', animation: 'spin' },
  verifying: { label: 'Verifying page count...', color: '#42a5f5', animation: 'pulse' },
  condensing: { label: 'Condensing to 1 page...', color: 'var(--accent-warning)', animation: 'spin' },
  success: { label: 'Complete ✓', color: 'var(--accent-success)', animation: 'none' },
  error: { label: 'Error', color: 'var(--accent-error)', animation: 'none' },
};
