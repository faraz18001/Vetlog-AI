import { useState, useEffect } from "react";
import { MessageCirclePlus, ClipboardList, Settings, CircleUserRound } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import "./Sidebar.css";

export default function Sidebar({ isOpen, onNewChat, isNewChatDisabled, onOpenSettings, onSelectThread, userId }) {
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
    <AnimatePresence initial={false}>
      {isOpen && (
        <motion.aside
          className="sidebar"
          initial={{ width: 0 }}
          animate={{ width: 260 }}
          exit={{ width: 0 }}
          transition={{ type: "spring", bounce: 0, duration: 0.3 }}
        >
          <div className="sidebar-inner">
            {/* Top Action */}
            <div className="sidebar-header">
              <button
                className="sidebar-new-chat"
                onClick={onNewChat}
                disabled={isNewChatDisabled}
                aria-label="Start a new chat"
              >
                <MessageCirclePlus size={16} strokeWidth={2} />
                <span>New Chat</span>
              </button>
            </div>

            {/* Chat History */}
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
                              <ClipboardList size={14} strokeWidth={2} className="history-item-icon" />
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

            {/* Bottom Profile / Settings */}
            <div className="sidebar-footer">
              <button
                className="sidebar-footer-btn"
                onClick={onOpenSettings}
              >
                <Settings size={16} strokeWidth={2} />
                <span>Settings</span>
              </button>
              <button className="sidebar-footer-btn profile-btn">
                <div className="profile-avatar">
                  <CircleUserRound size={14} strokeWidth={2} />
                </div>
                <div className="profile-info">
                  <span className="profile-name">Dr. Faraz</span>
                  <span className="profile-role">Veterinarian</span>
                </div>
              </button>
            </div>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
