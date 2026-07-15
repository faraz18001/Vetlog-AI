import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Cat } from "lucide-react";
import MessageBubble from "./MessageBubble.jsx";

const SUGGESTED = [
  "Who was treated today?",
  "Show me this week's cases",
  "What medications were administered?",
  "Any animals with ongoing treatment?",
];

function EmptyState({ onPrompt }) {
  return (
    <div className="chat-empty">
      <motion.div
        className="chat-empty-icon"
        aria-hidden="true"
        initial={{ opacity: 0, scale: 0.85 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "spring", bounce: 0, duration: 0.5 }}
      >
        <Cat size={32} strokeWidth={1.75} />
      </motion.div>

      <motion.h1
        className="chat-empty-title"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.08 }}
      >
        How can I help?
      </motion.h1>

      <motion.p
        className="chat-empty-sub"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.16 }}
      >
        Ask me anything about your patients, treatments, or clinic activity.
        I query your records directly.
      </motion.p>

      <ul className="chat-prompts" role="list">
        {SUGGESTED.map((prompt, i) => (
          <motion.li
            key={prompt}
            role="listitem"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: 0.45,
              ease: [0.16, 1, 0.3, 1],
              delay: 0.24 + i * 0.07,
            }}
          >
            <button
              className="chat-prompt-btn"
              onClick={() => onPrompt(prompt)}
            >
              <span>{prompt}</span>
              <span className="chat-prompt-arrow" aria-hidden="true">
                <ArrowRight size={15} strokeWidth={2.5} />
              </span>
            </button>
          </motion.li>
        ))}
      </ul>
    </div>
  );
}

export default function ChatWindow({ messages, isLoading, onPrompt }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div
      className="chat-window"
      role="log"
      aria-live="polite"
      aria-label="Chat messages"
    >
      {messages.length === 0 ? (
        <EmptyState onPrompt={onPrompt} />
      ) : (
        <div className="chat-messages">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          <div ref={bottomRef} aria-hidden="true" />
        </div>
      )}
    </div>
  );
}
