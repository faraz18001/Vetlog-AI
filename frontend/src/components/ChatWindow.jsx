import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Cat } from "lucide-react";
import appLogo from "../assets/logo.png";
import MessageBubble from "./MessageBubble.jsx";
import InputBar from "./InputBar.jsx";

const SUGGESTED = [
  "Who was treated today?",
  "Show me this week's cases",
  "What medications were administered?",
  "Any animals with ongoing treatment?",
];

function EmptyState({ onSend, isLoading }) {
  return (
    <div className="chat-empty">
      <motion.div
        className="chat-empty-icon"
        aria-hidden="true"
        initial={{ opacity: 0, scale: 0.85 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "spring", bounce: 0, duration: 0.5 }}
      >
        <img src={appLogo} alt="Vetlog AI" style={{ width: 64, height: 64, objectFit: "contain", transform: "scale(1.5)" }} />
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
        style={{ marginBottom: "2rem" }}
      >
        Ask me anything about your patients, treatments, or clinic activity.
        I query your records directly.
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.24 }}
        style={{ width: "100%", maxWidth: "800px" }}
      >
        <InputBar onSend={onSend} isLoading={isLoading} />
      </motion.div>
    </div>
  );
}

export default function ChatWindow({ messages, isLoading, onPrompt, onSend }) {
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
        <EmptyState onSend={onSend} isLoading={isLoading} />
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
