import { MessageCirclePlus, ClipboardList, Settings, CircleUserRound } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import "./Sidebar.css";

const DUMMY_HISTORY = [
  {
    group: "Today",
    chats: [
      "Bailey (Dog) - Skin Allergy",
      "Bella - Blood Work Results",
    ],
  },
  {
    group: "Yesterday",
    chats: [
      "Chloe - Follow-up Check",
      "Inventory: Amoxicillin Restock",
    ],
  },
  {
    group: "Previous 7 Days",
    chats: [
      "Donation: Paws Welfare Trust",
      "Luna (Cat) - Vaccination",
      "Max - Post-op Recovery",
    ],
  },
];

export default function Sidebar({ isOpen, onNewChat, isNewChatDisabled, onOpenSettings }) {
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
        {DUMMY_HISTORY.map((section, i) => (
          <div key={i} className="history-group">
            <h3 className="history-group-title">{section.group}</h3>
            <ul className="history-list">
              {section.chats.map((chat, j) => (
                <li key={j}>
                  <button className="history-item-btn">
                    <ClipboardList size={14} strokeWidth={2} className="history-item-icon" />
                    <span className="history-item-text">{chat}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
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
