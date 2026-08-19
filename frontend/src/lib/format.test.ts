import { formatCompactMoney, formatMoney, formatPercent } from './format';

describe('business formatting', () => {
  it('uses the backend-formatted money as the display authority', () => {
    expect(formatMoney({ cents: 4200, formatted: '¥42.00' })).toBe('¥42.00');
  });

  it('formats large cent values compactly without losing the currency unit', () => {
    expect(formatCompactMoney(1_234_500)).toBe('¥1.23万');
  });

  it('distinguishes missing comparison baselines from a flat zero change', () => {
    expect(formatPercent(null)).toBe('暂无对比');
    expect(formatPercent(0)).toBe('0.0%');
    expect(formatPercent(12.34)).toBe('+12.3%');
    expect(formatPercent(-8.25)).toBe('-8.3%');
  });
});
