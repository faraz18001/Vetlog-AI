import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble.jsx'

import { Dog } from 'lucide-react'

const SUGGESTED = [
  'Who was treated today?',
  'Show me this week\'s cases',
  'What medications were administered?',
  'Any animals with ongoing treatment?',
]

function EmptyState({ onPrompt }) {
  return (
    <div className="chat-empty">
      <div className="chat-empty-icon" aria-hidden="true">
        <Dog size={28} strokeWidth={1.5} />
      </div>
      <h1 className="chat-empty-title">How can I help?</h1>
      <p className="chat-empty-sub">
        Ask me anything about your patients, treatments, or clinic activity.
        I query your records directly.
      </p>
      <ul className="chat-prompts" role="list">
        {SUGGESTED.map(prompt => (
          <li key={prompt} role="listitem">
            <button
              className="chat-prompt-btn"
              onClick={() => onPrompt(prompt)}
            >
              {prompt}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function ChatWindow({ messages, isLoading, onPrompt }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
          {messages.map(msg => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          <div ref={bottomRef} aria-hidden="true" />
        </div>
      )}
    </div>
  )
}
