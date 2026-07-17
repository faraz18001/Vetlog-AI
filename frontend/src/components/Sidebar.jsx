import { useState, useEffect } from "react";
import { MessageCirclePlus, MessageSquare, Settings, CircleUserRound, LogOut, PanelLeftClose, PanelLeftOpen, Cat } from "lucide-react";
import { motion } from "framer-motion";
import * as Popover from "@radix-ui/react-popover";
import "./Sidebar.css";

export default function Sidebar({ isOpen, onToggle, onNewChat, isNewChatDisabled, onOpenSettings, onSelectThread, userId, userName, onLogout }) {
  const [conversations, setConversations] = useState([]);

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

  function groupByDate(threads) {
    var today = new Date();
    today.setHours(0, 0, 0, 0);
    var yesterday = new Date(today.getTime() - 86400000);

    var groups = {};
    for (var i = 0; i < threads.length; i++) {
      var t = threads[i];
      var d = new Date(t.updated_at);
      d.setHours(0, 0, 0, 0);

      var key;
      if (d.getTime() === today.getTime()) {
        key = "Today";
      } else if (d.getTime() === yesterday.getTime()) {
        key = "Yesterday";
      } else if (d.getTime() >= today.getTime() - 7 * 86400000) {
        key = "Previous 7 Days";
      } else {
        key = "Older";
      }

      if (!groups[key]) {
        groups[key] = [];
      }
      groups[key].push(t);
    }

    var order = ["Today", "Yesterday", "Previous 7 Days", "Older"];
    var result = [];
    for (var j = 0; j < order.length; j++) {
      var group = order[j];
      if (groups[group]) {
        result.push({ group: group, chats: groups[group] });
      }
    }
    return result;
  }

  var groupedConversations = groupByDate(conversations);

  return (
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
                  <Cat size={22} strokeWidth={2.25} />
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

          <button
            className="sidebar-new-chat"
            onClick={onNewChat}
            disabled={isNewChatDisabled}
            aria-label="Start a new chat"
            title="New Chat"
          >
            <MessageCirclePlus size={16} strokeWidth={2} />
            {isOpen && <span>New Chat</span>}
          </button>
        </div>

        {isOpen && (
          <div className="sidebar-history">
            {groupedConversations.map(function (section, i) {
              return (
                <div key={i} className="history-group">
                  <h3 className="history-group-title">{section.group}</h3>
                  <ul className="history-list">
                    {section.chats.map(function (chat, j) {
                      return (
                        <li key={j}>
                          <button
                            className="history-item-btn"
                            onClick={function () { onSelectThread(chat.thread_id); }}
                          >
                            <MessageSquare size={14} strokeWidth={2} className="history-item-icon" />
                            <span className="history-item-text">{chat.thread_name}</span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              );
            })}
          </div>
        )}

        <div className="sidebar-footer">
          <button
            className="sidebar-footer-btn"
            onClick={onOpenSettings}
            title="Settings"
          >
            <Settings size={16} strokeWidth={2} />
            {isOpen && <span>Settings</span>}
          </button>

          <Popover.Root>
            <Popover.Trigger asChild>
              <button className="sidebar-footer-btn profile-btn" title={userName || "User"}>
                <div className="profile-avatar">
                  <CircleUserRound size={14} strokeWidth={2} />
                </div>
                {isOpen && (
                  <div className="profile-info">
                    <span className="profile-name">{userName || "User"}</span>
                    <span className="profile-role">Veterinarian</span>
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
  );
}
