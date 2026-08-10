import sys

filepath = 'frontend/src/components/MessageBubble.jsx'
with open(filepath, 'r') as f:
    content = f.read()

# 1. Update lucide-react imports to include Loader2
content = content.replace(
    'import { Cat, Check, Copy, UserRound } from "lucide-react";',
    'import { Cat, Check, Copy, UserRound, Loader2 } from "lucide-react";'
)

# 2. Extract ChainOfThought block
cot_start = content.find('{/* ChainOfThought')
cot_end = content.find('{/* Report card')

if cot_start != -1 and cot_end != -1:
    cot_block = content[cot_start:cot_end]
    content = content[:cot_start] + content[cot_end:]
    
    # Update the thinking indicator in cot_block
    old_thinking = """            {isStreaming && (
              <div className="msg-thinking" style={{ padding: 'var(--space-2) 0', color: 'var(--color-text-muted)' }}>
                <span className="dot" style={{ backgroundColor: 'var(--color-accent)' }} />
                <span className="dot" style={{ backgroundColor: 'var(--color-accent)' }} />
                <span className="dot" style={{ backgroundColor: 'var(--color-accent)' }} />
                <span style={{ marginLeft: 'var(--space-2)' }}>Thinking...</span>
              </div>
            )}"""
            
    new_thinking = """            {isStreaming && (
              <div className="chain-of-thought-step">
                <div className="chain-of-thought-timeline">
                  <div className="chain-of-thought-dot" style={{ display: 'none' }} />
                  <Loader2 size={14} className="spin" style={{ color: 'var(--color-accent)', marginTop: '8px' }} />
                </div>
                <div className="chain-of-thought-trigger" style={{ cursor: 'default' }}>
                  <span className="chain-of-thought-trigger-text" style={{ color: 'var(--color-text-muted)' }}>Thinking...</span>
                </div>
              </div>
            )}"""
            
    cot_block = cot_block.replace(old_thinking, new_thinking)

    # Move cot_block to before Content
    content_marker = '{/* Content */}'
    insert_pos = content.find(content_marker)
    
    if insert_pos != -1:
        content = content[:insert_pos] + cot_block + '\n        ' + content[insert_pos:]

with open(filepath, 'w') as f:
    f.write(content)

print("Layout patched!")
