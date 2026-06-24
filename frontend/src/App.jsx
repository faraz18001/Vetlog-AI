import { useChat } from "./hooks/useChat.js";
import ChatWindow from "./components/ChatWindow.jsx";
import InputBar from "./components/InputBar.jsx";
import "./App.css";

function PlusIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="9" cy="9" r="8" stroke="currentColor" strokeWidth="1.3" />
      <path
        d="M6 9h6M9 6v6"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </svg>
  );
}

function NewChatIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M7 1h5a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V7"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
      <path
        d="M1 5.5 5.5 1 8 3.5 3.5 8 1 9l.5-3.5Z"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function App() {
  const { messages, isLoading, sendMessage, clearChat, sessionUsage } =
    useChat();

  return (
    <div className="app-shell">
      {/* ---- Topbar ---- */}
      <header className="topbar">
        <div className="topbar-brand">
          <span className="topbar-brand-icon">
            <PlusIcon />
          </span>
          <span className="topbar-wordmark">Vetlog AI</span>
        </div>

        <div className="topbar-right">
          {sessionUsage.total_tokens > 0 && (
            <div className="topbar-usage" aria-label="Session token usage">
              <span>{sessionUsage.total_tokens.toLocaleString()} tokens</span>
              {sessionUsage.cost_usd > 0 && (
                <span className="topbar-usage-cost">
                  ${sessionUsage.cost_usd.toFixed(4)}
                </span>
              )}
            </div>
          )}
          <button
            className="topbar-new-chat"
            onClick={clearChat}
            disabled={messages.length === 0 && !isLoading}
            aria-label="Start a new chat"
          >
            <NewChatIcon />
            <span>New Chat</span>
          </button>
        </div>
      </header>

      {/* ---- Chat body ---- */}
      <main className="chat-main">
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          onPrompt={sendMessage}
        />
        <InputBar onSend={sendMessage} isLoading={isLoading} />
      </main>
    </div>
  );
}
