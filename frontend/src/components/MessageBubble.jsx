import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Individual message row — user or assistant */
export default function MessageBubble({ message }) {
  const { role, content, isStreaming, isError, timestamp } = message;
  const isUser = role === "user";

  const timeLabel = timestamp
    ? timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <div className={`msg-row ${isUser ? "msg-row--user" : "msg-row--ai"}`}>
      {/* Avatar */}
      <div
        className={`msg-avatar ${isUser ? "msg-avatar--user" : "msg-avatar--ai"}`}
        aria-hidden="true"
      >
        {isUser ? (
          "You"
        ) : (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle
              cx="8"
              cy="8"
              r="7"
              stroke="currentColor"
              strokeWidth="1.3"
            />
            <path
              d="M5 8h6M8 5v6"
              stroke="currentColor"
              strokeWidth="1.3"
              strokeLinecap="round"
            />
          </svg>
        )}
      </div>

      {/* Content */}
      <div
        className={`msg-bubble ${isUser ? "msg-bubble--user" : "msg-bubble--ai"}`}
      >
        {/* Thinking dots — no content yet but still streaming */}
        {!isUser && isStreaming && !content ? (
          <span
            className="msg-thinking"
            role="status"
            aria-label="Vetlog AI is thinking"
          >
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </span>
        ) : (
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
              // User bubbles and errors stay as plain text
              <p>{content}</p>
            ) : (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content}
              </ReactMarkdown>
            )}
          </div>
        )}

        {timeLabel && !isStreaming && (
          <span className="msg-ts" aria-hidden="true">
            {timeLabel}
          </span>
        )}
      </div>
    </div>
  );
}
