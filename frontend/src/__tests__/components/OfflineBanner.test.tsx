import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';

import OfflineBanner from '@/components/ui/OfflineBanner';

function setOnline(value: boolean) {
  Object.defineProperty(navigator, 'onLine', { value, configurable: true });
  window.dispatchEvent(new Event(value ? 'online' : 'offline'));
}

afterEach(() => setOnline(true));

describe('OfflineBanner', () => {
  it('renders nothing while online', () => {
    render(<OfflineBanner />);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('shows a banner when the browser goes offline, and hides it on reconnect', () => {
    render(<OfflineBanner />);

    act(() => setOnline(false));
    expect(screen.getByRole('status')).toHaveTextContent(/offline/i);

    act(() => setOnline(true));
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });
});
