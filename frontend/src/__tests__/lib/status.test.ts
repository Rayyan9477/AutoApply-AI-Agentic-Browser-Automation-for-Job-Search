import { describe, it, expect } from 'vitest';

import { atsPercent, atsColor } from '@/lib/status';

describe('atsPercent', () => {
  it('scales a 0–1 ATS score to a 0–100 integer (the scale the API returns)', () => {
    expect(atsPercent(0.91)).toBe(91);
    expect(atsPercent(0.868)).toBe(87);
    expect(atsPercent(0.78)).toBe(78);
    expect(atsPercent(1)).toBe(100);
    expect(atsPercent(0)).toBe(0);
  });

  it('treats null/undefined as 0', () => {
    expect(atsPercent(null)).toBe(0);
    expect(atsPercent(undefined)).toBe(0);
  });

  it('pairs with atsColor: a strong 0–1 score lands in the "offer" band', () => {
    // 0.91 → 91 → offer band. Before the fix, raw 0.91 fell through to the rejected band.
    expect(atsColor(atsPercent(0.91))).toBe(atsColor(91));
    expect(atsColor(atsPercent(0.91))).not.toBe(atsColor(0.91));
  });
});
