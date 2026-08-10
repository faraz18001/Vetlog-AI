import sys

filepath = 'frontend/src/components/MessageBubble.jsx'
with open(filepath, 'r') as f:
    content = f.read()

# Replace import
content = content.replace(
    'import StepChain from "./StepChain.jsx";',
    'import {\n  ChainOfThought,\n  ChainOfThoughtStep,\n  ChainOfThoughtTrigger,\n  ChainOfThoughtContent,\n  ChainOfThoughtItem\n} from "./ChainOfThought.jsx";'
)

# Replace usage
old_usage = """        {/* Step chain — shown for AI messages that triggered tool calls, or initially while thinking */}
        {!isUser && (steps?.length > 0 || (isStreaming && !content)) && (
          <StepChain steps={steps ?? []} isStreaming={isStreaming} />
        )}"""

new_usage = """        {/* ChainOfThought — shown for AI messages that triggered tool calls, or initially while thinking */}
        {!isUser && (steps?.length > 0 || (isStreaming && !content)) && (
          <ChainOfThought>
            {(steps ?? []).map((step, i) => (
              <ChainOfThoughtStep key={i} defaultOpen={isStreaming && i === (steps ?? []).length - 1}>
                <ChainOfThoughtTrigger>
                  {step.label}
                </ChainOfThoughtTrigger>
                {step.detail && (
                  <ChainOfThoughtContent>
                    <ChainOfThoughtItem>
                      {step.detail}
                    </ChainOfThoughtItem>
                  </ChainOfThoughtContent>
                )}
              </ChainOfThoughtStep>
            ))}
            {isStreaming && (
              <div className="msg-thinking" style={{ padding: 'var(--space-2) 0', color: 'var(--color-text-muted)' }}>
                <span className="dot" style={{ backgroundColor: 'var(--color-accent)' }} />
                <span className="dot" style={{ backgroundColor: 'var(--color-accent)' }} />
                <span className="dot" style={{ backgroundColor: 'var(--color-accent)' }} />
                <span style={{ marginLeft: 'var(--space-2)' }}>Thinking...</span>
              </div>
            )}
          </ChainOfThought>
        )}"""

content = content.replace(old_usage, new_usage)

with open(filepath, 'w') as f:
    f.write(content)

print("MessageBubble patched!")
