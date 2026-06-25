import { useState, useEffect } from "react";
import { List } from "lucide-react";

/** Dot icon for each node on the timeline */
function StepDot({ label, isLast, isStreaming }) {
  const isError = label.includes("failed") || label.includes("error");
  const isDone = label === "Report saved";

  return (
    <span
      className={[
        "step-dot",
        isError ? "step-dot--error" : "",
        isDone ? "step-dot--done" : "",
        isStreaming && isLast ? "step-dot--pulse" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      aria-hidden
    />
  );
}

/**
 * StepChain — vertical timeline of agent execution steps.
 *
 * While the agent is working steps appear one-by-one with a connecting
 * line between them (like a flowchart). Two seconds after the agent
 * finishes the whole timeline collapses to a single summary pill —
 * click it to expand again.
 *
 * Props:
 *   steps       - Array of { label: string }
 *   isStreaming - True while the agent is still working
 */
export default function StepChain({ steps, isStreaming }) {
  const [expanded, setExpanded] = useState(true);

  // Auto-collapse 2 s after the agent finishes
  useEffect(() => {
    if (isStreaming || steps.length === 0) return;
    const t = setTimeout(() => setExpanded(false), 2000);
    return () => clearTimeout(t);
  }, [isStreaming, steps.length]);

  if (steps.length === 0 && !isStreaming) return null;

  /* ── Collapsed summary pill ─────────────────────────────────────── */
  if (!expanded) {
    return (
      <button
        className="steps-summary"
        onClick={() => setExpanded(true)}
        aria-label="Show agent steps"
      >
        <List size={12} strokeWidth={2.5} aria-hidden />
        {steps.length} step{steps.length !== 1 ? "s" : ""}
      </button>
    );
  }

  /* ── Expanded vertical timeline ─────────────────────────────────── */
  return (
    <div className="steps-chain">
      {steps.map((step, i) => {
        const isLast = i === steps.length - 1;
        const showConnector = !isLast || isStreaming;

        return (
          <div key={i} className="step-row" style={{ animationDelay: `${i * 60}ms` }}>
            {/* Left column: dot + connector line */}
            <div className="step-track">
              <StepDot label={step.label} isLast={isLast} isStreaming={false} />
              {showConnector && <span className="step-connector" />}
            </div>

            {/* Right column: label */}
            <span
              className={`step-label${step.label.includes("failed") || step.label.includes("error") ? " step-label--error" : ""}`}
            >
              {step.label}
            </span>
          </div>
        );
      })}

      {/* Animated pulse node while the agent is still working */}
      {isStreaming && (
        <div className="step-row">
          <div className="step-track">
            <span className="step-dot step-dot--live" aria-hidden />
          </div>
          <span className="step-pulse-label">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </span>
        </div>
      )}

      {!isStreaming && steps.length > 0 && (
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
