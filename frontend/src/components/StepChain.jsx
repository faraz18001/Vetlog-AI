import { useState, useEffect } from "react";
import {
  Database,
  FileText,
  CheckCircle2,
  AlertTriangle,
  List,
  Circle,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

/* Pick an icon for a step based on its label content. */
function iconForLabel(label) {
  const l = (label || "").toLowerCase();
  if (l.includes("sql") || l.includes("query") || l.includes("database") || l.includes("row"))
    return Database;
  if (l.includes("report")) return FileText;
  if (l.includes("fail") || l.includes("error")) return AlertTriangle;
  if (l.includes("saved") || l.includes("done")) return CheckCircle2;
  return Circle;
}

/** Node chip holding an icon; state drives colour. */
function StepNode({ label, isLast, isStreaming }) {
  const l = (label || "").toLowerCase();
  const isError = l.includes("failed") || l.includes("error");
  const isDone = l === "report saved" || l.includes("rows returned") || l.includes("row returned");
  const Icon = iconForLabel(label);

  const cls = [
    "step-node",
    isError ? "step-node--error" : "",
    isDone ? "step-node--done" : "",
    isStreaming && isLast ? "step-node--live" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <span className={cls} aria-hidden>
      <span className="step-icon">
        <Icon size={12} strokeWidth={2.5} />
      </span>
    </span>
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
 *   steps       - Array of { label: string, detail?: string }
 *   isStreaming - True while the agent is still working
 */
export default function StepChain({ steps, isStreaming }) {
  const [expanded, setExpanded] = useState(false);

  if (steps.length === 0 && !isStreaming) return null;

  /* ── Collapsed summary pill ─────────────────────────────────────── */
  if (!expanded) {
    if (isStreaming) {
      const currentStatus = steps.length > 0 ? steps[steps.length - 1].label : "Thinking...";
      const l = currentStatus.toLowerCase();
      let dotColor = "var(--color-text-muted)";
      if (l.includes("fail") || l.includes("error")) {
        dotColor = "var(--color-error)";
      } else if (l.includes("sql") || l.includes("query") || l.includes("database") || l.includes("row")) {
        dotColor = "#22c55e"; // green for executing/sql tasks
      } else if (l.includes("thinking") || steps.length === 0) {
        dotColor = "var(--color-accent)"; // purple for initial thinking
      }

      return (
        <div 
          className="msg-thinking" 
          style={{ padding: 0, margin: 'var(--space-2) 0 var(--space-1)', gap: 'var(--space-2)', fontSize: 'var(--text-base)', color: 'var(--color-text)' }}
        >
          <span className="dot" style={{ width: 4, height: 4, backgroundColor: dotColor, transition: 'background-color 0.3s' }} />
          <span className="dot" style={{ width: 4, height: 4, backgroundColor: dotColor, transition: 'background-color 0.3s' }} />
          <span className="dot" style={{ width: 4, height: 4, backgroundColor: dotColor, transition: 'background-color 0.3s' }} />
          <AnimatePresence mode="wait">
            <motion.span
              key={currentStatus}
              initial={{ opacity: 0, filter: "blur(4px)" }}
              animate={{ opacity: 1, filter: "blur(0px)" }}
              exit={{ opacity: 0, filter: "blur(4px)" }}
              transition={{ duration: 0.2 }}
              style={{ marginLeft: 'var(--space-1)' }}
            >
              {currentStatus}
            </motion.span>
          </AnimatePresence>
        </div>
      );
    }

    return (
      <motion.button
        layout
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="steps-summary"
        onClick={() => setExpanded(true)}
        aria-label="Show agent steps"
      >
        <List size={12} strokeWidth={2.5} aria-hidden />
        {steps.length} step{steps.length !== 1 ? "s" : ""}
      </motion.button>
    );
  }

  /* ── Expanded vertical timeline ─────────────────────────────────── */
  return (
    <motion.div layout className="steps-chain">
      <AnimatePresence>
        {steps.map((step, i) => {
          const isLast = i === steps.length - 1;
          const showConnector = !isLast || isStreaming;
          const isError =
            step.label.includes("failed") || step.label.includes("error");

          return (
            <motion.div
              key={i}
              layout
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="step-row"
            >
              {/* Left column: node + connector line */}
              <div className="step-track">
                <StepNode label={step.label} isLast={isLast} isStreaming={false} />
                {showConnector && <span className="step-connector" />}
              </div>

              {/* Right column: label + optional detail */}
              <div className="step-label-col">
                <span
                  className={`step-label${isError ? " step-label--error" : ""}`}
                >
                  {step.label}
                </span>
                {step.detail ? (
                  <span className="step-detail">{step.detail}</span>
                ) : null}
              </div>
            </motion.div>
          );
        })}

        {/* Animated pulse node while the agent is still working */}
        {isStreaming && (
          <motion.div
            layout
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="step-row"
          >
            <div className="step-track">
              <span className="step-node step-node--live" aria-hidden>
                <span className="step-icon">
                  <Circle size={12} strokeWidth={2.5} />
                </span>
              </span>
            </div>
            <span className="step-pulse-label">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {!isStreaming && steps.length > 0 && (
        <motion.button
          layout
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="steps-collapse-btn"
          onClick={() => setExpanded(false)}
          aria-label="Collapse steps"
        >
          Collapse
        </motion.button>
      )}
    </motion.div>
  );
}
