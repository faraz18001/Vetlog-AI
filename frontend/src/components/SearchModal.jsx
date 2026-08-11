import React, { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { Search, X, MessageSquare } from 'lucide-react';
import './SearchModal.css';

export default function SearchModal({ isOpen, onClose, conversations, onSelectThread }) {
  const [query, setQuery] = useState('');

  return (
    <Dialog.Root open={isOpen} onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="search-modal-overlay" />
        <Dialog.Content className="search-modal-content">
          <div className="search-modal-header">
            <div className="search-modal-input-container">
              <Search size={18} className="search-modal-icon" />
              <input
                type="text"
                className="search-modal-input"
                placeholder="Search chats..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                autoFocus
              />
            </div>
            <Dialog.Close asChild>
              <button className="search-modal-close" aria-label="Close">
                <X size={20} />
              </button>
            </Dialog.Close>
          </div>
          
          <div className="search-modal-results">
            {query.length > 0 && (
              <ul className="search-results-list">
                {(conversations || []).filter(r => r.thread_name.toLowerCase().includes(query.toLowerCase())).map((result) => (
                  <li key={result.thread_id}>
                    <button className="search-result-btn" onClick={() => {
                      onSelectThread(result.thread_id);
                      onClose(false);
                    }}>
                      <MessageSquare size={16} />
                      <span>{result.thread_name}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {query.length === 0 && (
              <div className="search-empty-state">
                <p>Type to search your previous conversations.</p>
              </div>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
