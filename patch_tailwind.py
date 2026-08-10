import sys

filepath = 'frontend/tailwind.config.js'
with open(filepath, 'r') as f:
    content = f.read()

content = content.replace('["DM Sans", "sans-serif"]', '["var(--font-display)", "sans-serif"]')
content = content.replace('["Nunito Sans", "sans-serif"]', '["var(--font-body)", "sans-serif"]')

with open(filepath, 'w') as f:
    f.write(content)

print("Tailwind config updated!")
