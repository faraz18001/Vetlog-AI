import { memo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Cat, Check, Copy, UserRound, Loader2 } from "lucide-react";
import appLogo from "../assets/logo.png";
import { motion } from "framer-motion";
import ReportCard from "./ReportCard.jsx";
import InlineTableCard from "./InlineTableCard.jsx";
import {
  ChainOfThought,
  ChainOfThoughtStep,
  ChainOfThoughtTrigger,
  ChainOfThoughtContent,
  ChainOfThoughtItem
} from "./ChainOfThought.jsx";

function fmt(n) {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

function UsageBadge({ usage }) {
  const hasCost = usage.cost_usd > 0;
  return (
    <div className="usage-badge" aria-label="Token usage">
      <span title="Input tokens">↑{fmt(usage.input_tokens)}</span>
      <span className="usage-sep">/</span>
      <span title="Output tokens">↓{fmt(usage.output_tokens)}</span>
      {hasCost && (
        <>
          <span className="usage-sep">·</span>
          <span title="Estimated cost" className="usage-cost">
            ${usage.cost_usd < 0.001 ? "<0.001" : usage.cost_usd.toFixed(4)}
          </span>
        </>
      )}
    </div>
  );
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard unavailable — silently ignore */
    }
  }

  return (
    <button
      type="button"
      className={`msg-copy-btn${copied ? " msg-copy-btn--done" : ""}`}
      onClick={handleCopy}
      aria-label={copied ? "Copied" : "Copy message"}
      title={copied ? "Copied" : "Copy message"}
    >
      {copied ? (
        <Check size={14} strokeWidth={2.5} />
      ) : (
        <Copy size={14} strokeWidth={2.25} />
      )}
    </button>
  );
}

/** Individual message row — user or assistant */
function MessageBubble({ message }) {
  const { role, content, isStreaming, isError, timestamp, steps } = message;
  const isUser = role === "user";

  const timeLabel = timestamp
    ? timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : null;

  const showCopy =
    !isUser && !isStreaming && !isError && content && content.trim().length > 0;

  return (
    <motion.div
      layout={!isStreaming}
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", bounce: 0, duration: 0.4 }}
      className={`msg-row ${isUser ? "msg-row--user" : "msg-row--ai"}`}
    >
      {/* Avatar */}
      <div
        className={`msg-avatar ${isUser ? "msg-avatar--user" : "msg-avatar--ai"}`}
        aria-hidden="true"
      >
        {isUser ? (
          <UserRound size={12} strokeWidth={2.5} />
        ) : (
          <img src={appLogo} alt="AI" style={{ width: "100%", height: "100%", objectFit: "contain", transform: "scale(1.7)" }} />
        )}
      </div>

      {/* Content */}
      <div
        className={`msg-bubble ${isUser ? "msg-bubble--user" : "msg-bubble--ai"}`}
      >
        {/* ChainOfThought — shown for AI messages that triggered tool calls, or initially while thinking */}
        {!isUser && (steps?.length > 0 || (isStreaming && !content)) && (
          <ChainOfThought>
            {(steps ?? []).map((step, i) => (
              <ChainOfThoughtStep key={i} defaultOpen={isStreaming && i === (steps ?? []).length - 1}>
                <ChainOfThoughtTrigger>
                  {step.label}
                </ChainOfThoughtTrigger>
                {step.detail && (
                  <ChainOfThoughtContent>
                    <ChainOfThoughtItem>
                      {step.detail}
                    </ChainOfThoughtItem>
                  </ChainOfThoughtContent>
                )}
              </ChainOfThoughtStep>
            ))}
            {isStreaming && (
              <div className="chain-of-thought-step">
                <div className="chain-of-thought-timeline">
                  <div className="chain-of-thought-dot" style={{ display: 'none' }} />
                  <Loader2 size={14} className="spin" style={{ color: 'var(--color-accent)', marginTop: '8px' }} />
                </div>
                <div className="chain-of-thought-trigger" style={{ cursor: 'default' }}>
                  <span className="chain-of-thought-trigger-text" style={{ color: 'var(--color-text-muted)' }}>Thinking...</span>
                </div>
              </div>
            )}
          </ChainOfThought>
        )}

        
        {/* Content */}
        {(content || isUser || isError) ? (
          <div
            className={[
              "msg-content",
              isUser ? "msg-content--user" : "msg-content--ai",
              isStreaming && !isError ? "msg-content--streaming" : "",
              isError ? "msg-content--error" : "",
            ]
              .join(" ")
              .trim()}
          >
            {isUser || isError ? (
              <p>{content}</p>
            ) : (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content}
              </ReactMarkdown>
            )}
          </div>
        ) : null}

        {showCopy && <CopyButton text={content} />}

        {timeLabel && !isStreaming && (
          <span className="msg-ts" aria-hidden="true">
            {timeLabel}
          </span>
        )}

        {/* Report card — shown when the agent generated a report this turn */}
        {!isUser && !isStreaming && !isError && message.reportPath && (
          <ReportCard reportPath={message.reportPath} />
        )}

        {/* Inline table — shown when the agent ran query_to_inline_table */}
        {!isUser && !isStreaming && !isError && message.tablePath && (
          <InlineTableCard path={message.tablePath} />
        )}

        {/* Token usage badge — AI messages only, after streaming ends */}
        {!isUser && !isStreaming && !isError && message.usage && (
          <UsageBadge usage={message.usage} />
        )}
      </div>
    </motion.div>
  );
}

export default memo(MessageBubble);
