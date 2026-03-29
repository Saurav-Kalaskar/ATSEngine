'use client';

import { PIPELINE_STATUS_CONFIG } from '@/lib/constants';
import type { PipelineStatus } from '@/types';

interface PipelineStatusProps {
  status: PipelineStatus;
}

export default function PipelineStatus({ status }: PipelineStatusProps) {
  const config = PIPELINE_STATUS_CONFIG[status];

  return (
    <div className="pipeline-status">
      <div
        className={`pipeline-dot ${config.animation}`}
        style={{ backgroundColor: config.color }}
      />
      <span
        className="pipeline-label"
        style={{ color: config.color }}
      >
        {config.label}
      </span>
    </div>
  );
}
