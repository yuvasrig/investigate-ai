import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  message: string;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error: unknown): State {
    const message = error instanceof Error ? error.message : String(error);
    return { hasError: true, message };
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-4 px-6">
            <p className="text-bear font-semibold text-lg">Something went wrong</p>
            <p className="text-muted-foreground text-sm max-w-md text-center">{this.state.message}</p>
            <button
              onClick={() => window.location.replace("/")}
              className="mt-4 text-sm font-medium text-accent hover:text-accent/80 transition-colors"
            >
              ← Go home
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
