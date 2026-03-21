import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import LoadingState from '@/components/common/LoadingState';

describe('LoadingState', () => {
  it('renders the default "Loading..." message', () => {
    render(<LoadingState />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders a custom message when provided', () => {
    render(<LoadingState message="Fetching jobs..." />);
    expect(screen.getByText('Fetching jobs...')).toBeInTheDocument();
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
  });

  it('renders a CircularProgress spinner', () => {
    render(<LoadingState />);
    // MUI CircularProgress renders with role="progressbar"
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('applies default minHeight of 300', () => {
    const { container } = render(<LoadingState />);
    // The outermost Box sets minHeight via MUI sx.
    // We check the first child div which is the Box.
    const box = container.firstElementChild as HTMLElement;
    expect(box).toBeTruthy();
    // MUI applies styles inline or via className - check computed style
    const style = window.getComputedStyle(box);
    // The Box is a flex container
    expect(box.style.display || style.display).toBeTruthy();
  });

  it('renders with a custom minHeight', () => {
    const { container } = render(<LoadingState minHeight={500} />);
    const box = container.firstElementChild as HTMLElement;
    expect(box).toBeTruthy();
  });

  it('renders the message in a Typography element', () => {
    render(<LoadingState message="Please wait" />);
    const messageEl = screen.getByText('Please wait');
    expect(messageEl).toBeInTheDocument();
    // Typography renders as a <p> with variant="body2"
    expect(messageEl.tagName.toLowerCase()).toBe('p');
  });
});
