import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router-dom';

import CommandPalette from '@/components/ui/CommandPalette';
import { useUiStore } from '@/store/useUiStore';

function LocationDisplay() {
  const loc = useLocation();
  return <div>path:{loc.pathname}</div>;
}

function renderPalette(initial = '/dashboard') {
  return render(
    <MemoryRouter initialEntries={[initial]}>
      <CommandPalette />
      <LocationDisplay />
    </MemoryRouter>,
  );
}

describe('CommandPalette', () => {
  beforeEach(() => useUiStore.setState({ paletteOpen: true, theme: 'dark' }));

  it('lists navigation commands when open', () => {
    renderPalette();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Jobs')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('renders nothing when closed', () => {
    useUiStore.setState({ paletteOpen: false });
    renderPalette();
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
  });

  it('filters commands by the typed query', async () => {
    renderPalette();
    await userEvent.type(screen.getByPlaceholderText(/type a command/i), 'jobs');
    expect(screen.getByText('Jobs')).toBeInTheDocument();
    expect(screen.queryByText('Settings')).not.toBeInTheDocument();
  });

  it('navigates and closes when a command is chosen', async () => {
    renderPalette('/dashboard');
    await userEvent.click(screen.getByText('Jobs'));
    expect(screen.getByText('path:/jobs')).toBeInTheDocument();
    expect(useUiStore.getState().paletteOpen).toBe(false);
  });

  it('runs an action command (toggle theme) and closes', async () => {
    renderPalette();
    await userEvent.click(screen.getByText(/toggle theme/i));
    expect(useUiStore.getState().theme).toBe('light');
    expect(useUiStore.getState().paletteOpen).toBe(false);
  });

  it('closes on Escape', async () => {
    renderPalette();
    await userEvent.keyboard('{Escape}');
    expect(useUiStore.getState().paletteOpen).toBe(false);
  });
});
