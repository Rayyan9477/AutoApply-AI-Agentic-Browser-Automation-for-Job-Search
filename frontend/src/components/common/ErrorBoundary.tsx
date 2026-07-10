import { Component } from 'react';
import type { ReactNode, ErrorInfo } from 'react';

import Icon from '@/components/ui/Icon';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Optional fallback to render instead of the default error UI. */
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * React error boundary that catches rendering errors and displays a recovery UI.
 * The one class component in the project, required by the React error boundary API.
 */
class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div style={{ minHeight: 300, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 14, padding: 32, background: 'var(--bg)', color: 'var(--text)', fontFamily: 'var(--font)' }}>
          <div style={{ display: 'grid', placeItems: 'center', width: 52, height: 52, borderRadius: 14, background: 'var(--rejected-soft)', color: 'var(--rejected)' }}>
            <Icon name="alert" size={26} />
          </div>
          <div style={{ font: '700 16px/1.2 var(--font)' }}>Something went wrong</div>
          <div style={{ font: '500 12.5px/1.4 var(--font)', color: 'var(--text-3)', textAlign: 'center', maxWidth: 380 }}>
            {this.state.error?.message ?? 'An unexpected error occurred.'}
          </div>
          <button
            onClick={this.handleReset}
            style={{ height: 36, padding: '0 16px', borderRadius: 'var(--r-md)', background: 'var(--surface-2)', border: '1px solid var(--border-2)', color: 'var(--text)', font: '700 12.5px/1 var(--font)', cursor: 'pointer' }}
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
