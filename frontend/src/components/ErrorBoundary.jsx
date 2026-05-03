import { useState, useEffect } from "react";
import "./ErrorBoundary.css";

export default function ErrorBoundary({ children }) {
  const [hasError, setHasError] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const handleError = (event) => {
      console.error("Error caught:", event.error);
      setHasError(true);
      setError(event.error?.message || "An unexpected error occurred");
    };

    window.addEventListener("error", handleError);
    return () => window.removeEventListener("error", handleError);
  }, []);

  if (hasError) {
    return (
      <div className="error-boundary">
        <div className="error-content">
          <h1>⚠️ Something went wrong</h1>
          <p className="error-message">{error}</p>
          <button
            onClick={() => {
              setHasError(false);
              setError(null);
              window.location.reload();
            }}
            className="error-retry-btn"
          >
            Refresh Page
          </button>
        </div>
      </div>
    );
  }

  return children;
}
