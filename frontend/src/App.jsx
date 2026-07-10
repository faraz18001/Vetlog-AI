import { useState, useEffect } from "react";
import { useChat } from "./hooks/useChat.js";
import { useAuth } from "./hooks/useAuth.js";
import ChatWindow from "./components/ChatWindow.jsx";
import InputBar from "./components/InputBar.jsx";
import Sidebar from "./components/Sidebar.jsx";
import SettingsModal from "./components/SettingsModal.jsx";
import LoginPage from "./components/LoginPage.jsx";
import { Cat, PanelLeft, LogOut } from "lucide-react";
import "./App.css";



export default function App() {
  const { user, login, register, logout, authError, setAuthError } = useAuth();
  const { messages, isLoading, sendMessage, clearChat, loadThread, sessionUsage } = useChat();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  useEffect(function () {
    if (!user) return;

    var url = "/api/conversations/?user_id=" + user.user_id;
    fetch(url)
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.length > 0) {
          loadThread(data[0].thread_id);
        } else {
          clearChat();
        }
      })
      .catch(function () {
        // ignore — sidebar will still display history
      });
  }, [user]);

  if (!user) {
    return (
      <LoginPage
        onLogin={login}
        onRegister={register}
        authError={authError}
        setAuthError={setAuthError}
      />
    );
  }

  return (
    <div className="app-shell">
      {/* Global paper-grain texture overlay */}
      <div className="grain-overlay" aria-hidden="true" />

      <Sidebar 
        isOpen={isSidebarOpen}
        onNewChat={clearChat} 
        isNewChatDisabled={messages.length === 0 && !isLoading} 
        onOpenSettings={() => setIsSettingsOpen(true)}
        onSelectThread={loadThread}
        userId={user.user_id}
      />
      
      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => setIsSettingsOpen(false)} 
        user={user}
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
            <span className="topbar-brand-mark" style={{ marginLeft: 'var(--space-2)' }}>
              <Cat size={22} strokeWidth={2.25} />
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
            <span className="topbar-user" title={user.display_name}>
              {user.display_name}
            </span>
            <button
              className="topbar-icon-btn"
              onClick={logout}
              aria-label="Log out"
              title="Log out"
            >
              <LogOut size={16} strokeWidth={2.5} />
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
    </div>
  );
}
