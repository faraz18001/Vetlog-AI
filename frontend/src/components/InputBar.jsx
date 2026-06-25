import { useState, useRef, useEffect } from 'react'
import { ArrowUp } from 'lucide-react'

const PLACEHOLDER = 'Ask about your patients, treatments, or clinic activity…'

export default function InputBar({ onSend, isLoading }) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [value])

  const canSend = value.trim().length > 0 && !isLoading

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (canSend) submit()
    }
  }

  function submit() {
    const text = value.trim()
    if (!text) return
    onSend(text)
    setValue('')
    // Reset height
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  return (
    <div className="input-bar-wrap">
      <div className="input-bar">
        <textarea
          ref={textareaRef}
          className="input-textarea"
          placeholder={PLACEHOLDER}
          value={value}
          rows={1}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          aria-label="Message input"
          disabled={isLoading}
        />
        <button
          className="input-send-btn"
          onClick={submit}
          disabled={!canSend}
          aria-label="Send message"
        >
          <ArrowUp size={16} strokeWidth={2.5} />
        </button>
      </div>
      <p className="input-hint">
        Enter to send &nbsp;·&nbsp; Shift + Enter for new line
      </p>
    </div>
  )
}
