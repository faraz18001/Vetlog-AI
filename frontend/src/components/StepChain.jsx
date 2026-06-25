import { useState, useEffect } from "react";

/**
 * Pick an appropriate SVG icon based on the step label.
 */
function StepIcon({ label }) {
  if (label === "Thinking") {
    return (
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
        <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.2" strokeDasharray="2 2" />
      </svg>
    );
  }

  if (label.startsWith("Running SQL")) {
    return (
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
        <rect x="1" y="1" width="10" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.2" />
        <path d="M3 4h6M3 6h4M3 8h5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    );
  }

  if (label.startsWith("Generating")) {
    return (
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
        <rect x="1.5" y="0.5" width="7" height="11" rx="1" stroke="currentColor" strokeWidth="1.2" />
        <path d="M3.5 3.5h5M3.5 5.5h5M3.5 7.5h3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    );
  }

  if (label === "Report saved") {
    return (
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
        <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.2" />
        <path d="M3.5 6l1.8 1.8 3-3.6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  if (label.includes("returned") || label.includes("results")) {
    return (
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
        <path d="M1 3h10M1 6h10M1 9h6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    );
  }

  if (label.includes("failed")) {
    return (
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
        <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.2" />
        <path d="M6 3.5v3M6 8h.01" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      </svg>
    );
  }

  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
      <circle cx="6" cy="6" r="2.5" fill="currentColor" />
    </svg>
  );
}

/**
 * StepChain — shows the agent's live execution steps in the chat.
 *
 * Steps arrive from the backend SSE stream as the agent actually executes them
 * (SQL queries, tool calls, row counts). While the agent is working the list
 * grows in real time. Two seconds after the final response arrives the chain
 * auto-collapses to a compact pill — the user can click it to expand again.
 *
 * Props:
 *   steps       - Array of { label: string, detail: string } from the backend.
 *   isStreaming - True while the agent is still running.
 */
export default function StepChain({ steps, isStreaming }) {
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    if (isStreaming || steps.length === 0) return;
    const timer = setTimeout(() => setExpanded(false), 2000);
    return () => clearTimeout(timer);
  }, [isStreaming, steps.length]);

  if (steps.length === 0) return null;

  if (!expanded) {
    return (
      <button
        className="steps-summary"
        onClick={() => setExpanded(true)}
        aria-label="Show agent steps"
      >
        <svg width="11" height="11" viewBox="0 0 11 11" fill="none" aria-hidden>
          <circle cx="5.5" cy="5.5" r="4.5" stroke="currentColor" strokeWidth="1.2" />
          <path d="M3.5 5.5h4M5.5 3.5v4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
        </svg>
        {steps.length} step{steps.length !== 1 ? "s" : ""}
      </button>
    );
  }

  return (
    <div className="steps-chain">
      <div className="steps-chain-items">
        {steps.map((step, index) => (
          <div
            key={index}
            className="step-item"
            style={{ animationDelay: `${index * 60}ms` }}
          >
            <span className="step-icon">
              <StepIcon label={step.label} />
            </span>

            <div className="step-body">
              <span className="step-label">{step.label}</span>
              {step.detail && (
                <span className="step-detail">{step.detail}</span>
              )}
            </div>
          </div>
        ))}

        {isStreaming && (
          <div className="step-item">
            <span className="step-icon step-icon--pulse">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </span>
          </div>
        )}
      </div>

      {!isStreaming && (
        <button
          className="steps-collapse-btn"
          onClick={() => setExpanded(false)}
          aria-label="Collapse steps"
        >
          Collapse
        </button>
      )}
    </div>
  );
}
