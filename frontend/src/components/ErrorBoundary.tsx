import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return <div className="error-page">
        <h1>Something went wrong.</h1>
        <p>{this.state.error?.message || 'An unexpected error occurred.'}</p>
        <button onClick={() => window.location.reload()}>Reload Page</button>
      </div>;
    }

    return this.props.children;
  }
}

export default ErrorBoundary;