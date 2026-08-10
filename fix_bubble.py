import sys

filepath = 'frontend/src/components/MessageBubble.jsx'
with open(filepath, 'r') as f:
    content = f.read()

# The cot_block is currently right before the first {/* Content */}
# Let's extract it.
cot_start = content.find('{/* ChainOfThought')
# The block ends before {/* Content */}
cot_end = content.find('{/* Content */}', cot_start)

if cot_start != -1 and cot_end != -1:
    cot_block = content[cot_start:cot_end]
    content = content[:cot_start] + content[cot_end:]
    
    # Now we want to insert it inside .msg-bubble
    # Let's find the second {/* Content */}
    # The first one is at content.find('{/* Content */}')
    first_marker = content.find('{/* Content */}')
    second_marker = content.find('{/* Content */}', first_marker + 1)
    
    if second_marker != -1:
        content = content[:second_marker] + cot_block + content[second_marker:]

with open(filepath, 'w') as f:
    f.write(content)

print("MessageBubble fixed!")
