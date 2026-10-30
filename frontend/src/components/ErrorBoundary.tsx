import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('ErrorBoundary caught:', error, info.componentStack);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="page" style={{ textAlign: 'center', paddingTop: '80px' }}>
          <div className="card" style={{ padding: '32px 24px' }}>
            <h1 style={{ fontSize: '1.4rem', marginBottom: '12px' }}>
              Etwas ist schiefgelaufen
            </h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '20px' }}>
              Ein unerwarteter Fehler ist aufgetreten. Bitte versuche es erneut.
            </p>
            {this.state.error && (
              <pre style={{
                background: 'var(--bg-input)',
                borderRadius: 'var(--radius)',
                padding: '12px',
                fontSize: '0.75rem',
                color: 'var(--danger)',
                marginBottom: '20px',
                overflow: 'auto',
                maxHeight: '120px',
                textAlign: 'left',
              }}>
                {this.state.error.message}
              </pre>
            )}
            <button className="btn-primary" onClick={this.handleRetry}>
              Erneut versuchen
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
