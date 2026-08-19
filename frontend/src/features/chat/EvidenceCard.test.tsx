import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';

import type { Evidence } from '../../api/types';
import { EvidenceCard } from './EvidenceCard';

test('formats monetary period comparison values and percentage units', () => {
  const evidence: Evidence = {
    tool: 'compare_periods',
    parameters: {
      metric: 'average_order_value',
      current_start: '2026-07-01',
      current_end: '2026-07-31',
      previous_start: '2026-06-01',
      previous_end: '2026-06-30',
    },
    result: {
      metric: 'average_order_value',
      current_value: 3604,
      previous_value: 3522,
      change_percent: 2.3,
      direction: 'up',
    },
    ingestion_run_id: 1,
    generated_at: '2026-08-19T12:00:00Z',
  };

  render(<EvidenceCard evidence={evidence} index={0} />);

  expect(screen.getByText('¥36.04')).toBeVisible();
  expect(screen.getByText('¥35.22')).toBeVisible();
  expect(screen.getByText('2.3%')).toBeVisible();
  expect(screen.queryByText('3604')).not.toBeInTheDocument();
});
