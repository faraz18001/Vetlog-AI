import { useState, useEffect } from "react";
import { SquarePen, Search, MessageSquare, Settings, CircleUserRound, LogOut, PanelLeftClose, PanelLeftOpen, FileText, Pin } from "lucide-react";
import appLogo from "../assets/logo.png";
import { motion } from "framer-motion";
import * as Popover from "@radix-ui/react-popover";
import SearchModal from "./SearchModal.jsx";
import "./Sidebar.css";

export default function Sidebar({ isOpen, onToggle, onNewChat, isNewChatDisabled, onOpenSettings, onOpenReports, isReportsActive, onSelectThread, onBackToChat, userId, userName, onLogout }) {
  const [conversations, setConversations] = useState([]);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  useEffect(function () {
    if (!userId) {
      setConversations([]);
      return;
    }

    fetch("/api/conversations/?user_id=" + userId)
      .then(function (res) { return res.json(); })
      .then(function (data) {
        setConversations(data);
      })
      .catch(function () {
        // ignore
      });
  }, [userId]);

  return (
    <>
      <motion.aside
        className={"sidebar" + (isOpen ? "" : " sidebar--collapsed")}
        animate={{ width: isOpen ? 260 : 52 }}
        transition={{ type: "spring", bounce: 0, duration: 0.3 }}
      >
        <div className="sidebar-inner">

          <div className="sidebar-header">
            <div className="sidebar-top-row">
              {isOpen && (
                <div className="sidebar-brand">
                  <span className="sidebar-brand-mark">
                    <img src={appLogo} alt="Vetlog" style={{ width: 32, height: 32, objectFit: "contain", transform: "scale(1.7)" }} />
                  </span>
                  <span className="sidebar-wordmark">Vetlog AI</span>
                </div>
              )}
              <button
                className="sidebar-toggle-btn"
                onClick={onToggle}
                aria-label="Toggle sidebar"
                title={isOpen ? "Collapse sidebar" : "Expand sidebar"}
              >
                {isOpen ? (
                  <PanelLeftClose size={18} strokeWidth={2} />
                ) : (
                  <PanelLeftOpen size={18} strokeWidth={2} />
                )}
              </button>
            </div>

            <div className="sidebar-main-nav">
              <button
                className="sidebar-nav-btn sidebar-new-chat"
                onClick={onNewChat}
                disabled={isNewChatDisabled}
                title="New Chat"
              >
                <SquarePen size={18} strokeWidth={2} />
                {isOpen && <span>New chat</span>}
              </button>

              <button
                className="sidebar-nav-btn"
                onClick={() => setIsSearchOpen(true)}
                title="Search chats"
              >
                <Search size={18} strokeWidth={2} />
                {isOpen && <span>Search chats</span>}
              </button>

              <button
                className={"sidebar-nav-btn sidebar-reports-btn" + (isReportsActive ? " sidebar-reports-btn--active" : "")}
                onClick={onOpenReports}
                title="Reports"
              >
                <FileText size={18} strokeWidth={2} />
                {isOpen && <span>Reports</span>}
              </button>
            </div>
          </div>

          {isOpen && (
            <div className="sidebar-history">
              <div className="history-group">
                <h3 className="history-group-title">Recent</h3>
                <ul className="history-list">
                  {conversations.map(function (chat, j) {
                    return (
                      <li key={j}>
                        <button
                          className="history-item-btn"
                          onClick={function () { onSelectThread(chat.thread_id); }}
                        >
                          <span className="history-item-text">{chat.thread_name}</span>
                          <Pin size={14} className="history-item-pin" strokeWidth={2} />
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            </div>
          )}

          <div className="sidebar-footer">
            <Popover.Root>
              <Popover.Trigger asChild>
                <button className="sidebar-profile-block" title={userName || "User"}>
                  <div className="profile-avatar">
                    <span>{(userName || "U").charAt(0).toUpperCase()}</span>
                  </div>
                  {isOpen && (
                    <div className="profile-info-wrap">
                      <div className="profile-info">
                        <span className="profile-name">{userName || "User"}</span>
                        <span className="profile-role">Pro</span>
                      </div>
                      <div
                        className="profile-settings-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          onOpenSettings();
                        }}
                      >
                        <Settings size={16} strokeWidth={2} />
                      </div>
                    </div>
                  )}
                </button>
              </Popover.Trigger>
              <Popover.Portal>
                <Popover.Content className="profile-popover" side="top" align="start" sideOffset={8}>
                  <button className="profile-popover-item" onClick={onLogout}>
                    <LogOut size={14} strokeWidth={2} />
                    <span>Log out</span>
                  </button>
                </Popover.Content>
              </Popover.Portal>
            </Popover.Root>
          </div>
        </div>
      </motion.aside>

      <SearchModal isOpen={isSearchOpen} onClose={setIsSearchOpen} conversations={conversations} onSelectThread={onSelectThread} />
    </>
  );
}
