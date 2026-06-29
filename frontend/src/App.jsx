import { useState } from "react";
import { useChat } from "./hooks/useChat.js";
import ChatWindow from "./components/ChatWindow.jsx";
import InputBar from "./components/InputBar.jsx";
import Sidebar from "./components/Sidebar.jsx";
import SettingsModal from "./components/SettingsModal.jsx";
import { HeartPulse, PanelLeft } from "lucide-react";
import "./App.css";



export default function App() {
  const { messages, isLoading, sendMessage, clearChat, sessionUsage } = useChat();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  return (
    <div className="app-shell">
      <Sidebar 
        isOpen={isSidebarOpen}
        onNewChat={clearChat} 
        isNewChatDisabled={messages.length === 0 && !isLoading} 
        onOpenSettings={() => setIsSettingsOpen(true)}
      />
      
      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => setIsSettingsOpen(false)} 
      />
      
      <div className="app-content">
        {/* ---- Topbar ---- */}
        <header className="topbar">
          <div className="topbar-brand">
            <button 
              className="topbar-icon-btn" 
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              aria-label="Toggle sidebar"
            >
              <PanelLeft size={20} strokeWidth={2.5} />
            </button>
            <span className="topbar-brand-icon" style={{ marginLeft: 'var(--space-2)' }}>
              <HeartPulse size={20} strokeWidth={2.5} />
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
    </div>
  );
}
