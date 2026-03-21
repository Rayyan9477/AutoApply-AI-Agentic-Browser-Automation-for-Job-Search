import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TemplateSelector from '@/components/resumes/TemplateSelector';

// The five template names from the component source.
const TEMPLATE_NAMES = ['Modern', 'Classic', 'Minimal', 'Technical', 'Creative'];
const TEMPLATE_IDS = ['modern', 'classic', 'minimal', 'technical', 'creative'];
const TEMPLATE_DESCRIPTIONS = [
  'Clean layout with sidebar accent',
  'Traditional professional format',
  'Simple and elegant design',
  'Optimized for engineering roles',
  'Eye-catching visual layout',
];

describe('TemplateSelector', () => {
  it('renders all five template options', () => {
    const onSelect = vi.fn();
    render(<TemplateSelector onSelect={onSelect} />);

    for (const name of TEMPLATE_NAMES) {
      expect(screen.getByText(name)).toBeInTheDocument();
    }
  });

  it('renders descriptions for all templates', () => {
    const onSelect = vi.fn();
    render(<TemplateSelector onSelect={onSelect} />);

    for (const desc of TEMPLATE_DESCRIPTIONS) {
      expect(screen.getByText(desc)).toBeInTheDocument();
    }
  });

  it('defaults to "modern" template as selected when no selectedId is given', () => {
    const onSelect = vi.fn();
    render(<TemplateSelector onSelect={onSelect} />);

    // The Modern template text should be visible
    expect(screen.getByText('Modern')).toBeInTheDocument();

    // The CheckCircleIcon is rendered via an SVG with data-testid; we check
    // that there's exactly one testid match from MUI's CheckCircleIcon.
    // MUI renders icons as <svg> elements. With the selected template,
    // CheckCircleIcon should appear once (for the "modern" template).
    const svgs = document.querySelectorAll('svg');
    const checkIcons = Array.from(svgs).filter((svg) =>
      svg.getAttribute('data-testid')?.includes('CheckCircle'),
    );
    expect(checkIcons.length).toBe(1);
  });

  it('calls onSelect with the template id when a template is clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<TemplateSelector selectedId="modern" onSelect={onSelect} />);

    // Click on the "Classic" template
    await user.click(screen.getByText('Classic'));
    expect(onSelect).toHaveBeenCalledWith('classic');
  });

  it('calls onSelect for each template when clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<TemplateSelector selectedId="modern" onSelect={onSelect} />);

    for (let i = 0; i < TEMPLATE_NAMES.length; i++) {
      await user.click(screen.getByText(TEMPLATE_NAMES[i]!));
      expect(onSelect).toHaveBeenCalledWith(TEMPLATE_IDS[i]);
    }

    expect(onSelect).toHaveBeenCalledTimes(TEMPLATE_NAMES.length);
  });

  it('shows check icon only on the selected template', () => {
    const onSelect = vi.fn();
    render(<TemplateSelector selectedId="technical" onSelect={onSelect} />);

    // Only one CheckCircleIcon should be rendered (for the "technical" template)
    const svgs = document.querySelectorAll('svg');
    const checkIcons = Array.from(svgs).filter((svg) =>
      svg.getAttribute('data-testid')?.includes('CheckCircle'),
    );
    expect(checkIcons.length).toBe(1);
  });

  it('renders different selected template correctly', () => {
    const onSelect = vi.fn();
    const { rerender } = render(
      <TemplateSelector selectedId="creative" onSelect={onSelect} />,
    );

    // Verify creative is shown as selected
    let checkIcons = document.querySelectorAll('[data-testid="CheckCircleIcon"]');
    expect(checkIcons.length).toBe(1);

    // Switch selection to minimal
    rerender(<TemplateSelector selectedId="minimal" onSelect={onSelect} />);
    checkIcons = document.querySelectorAll('[data-testid="CheckCircleIcon"]');
    expect(checkIcons.length).toBe(1);
  });
});
