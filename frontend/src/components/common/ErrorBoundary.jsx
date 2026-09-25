import { Component } from "react";
import Icon from "./Icon.jsx";
import Button from "./Button.jsx";

/**
 * Catches render-time errors in whatever it wraps so one broken surface
 * doesn't blank the whole app. Must be a class component — React has no
 * hook equivalent for getDerivedStateFromError/componentDidCatch.
 */
export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("Unhandled error in surface:", error, info);
  }

  componentDidUpdate(prevProps) {
    // Recover automatically when the caller swaps to a different surface
    // (e.g. App.jsx remounts on tab change) rather than staying stuck.
    if (this.state.error && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ error: null });
    }
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="flex flex-col items-center gap-3.5 rounded-xl border border-error/30 bg-error-container/6 px-6 py-10 text-center">
        <Icon name="error" size={28} className="text-error" />
        <div>
          <p className="font-display text-[15px] font-semibold text-error">Something went wrong on this screen</p>
          <p className="mt-1.5 max-w-md text-[13.5px] leading-relaxed text-on-surface-variant">
            {this.state.error?.message || "An unexpected error occurred."} You can try another tab, or reload the
            page if this keeps happening.
          </p>
        </div>
        <Button variant="ghost" icon="refresh" onClick={() => this.setState({ error: null })}>
          Try again
        </Button>
      </div>
    );
  }
}
