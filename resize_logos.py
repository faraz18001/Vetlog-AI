import sys

def replace_in_file(filepath, old, new):
    with open(filepath, 'r') as f:
        content = f.read()
    if old in content:
        content = content.replace(old, new)
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False

# 1. ChatWindow.jsx
cw = 'frontend/src/components/ChatWindow.jsx'
replace_in_file(cw, 
                '<img src={pusheenCat} alt="Vetlog AI" style={{ width: 32, height: 32, objectFit: "contain" }} />', 
                '<img src={pusheenCat} alt="Vetlog AI" style={{ width: 64, height: 64, objectFit: "contain", transform: "scale(1.5)" }} />')

# 2. MessageBubble.jsx
mb = 'frontend/src/components/MessageBubble.jsx'
replace_in_file(mb,
                '<img src={pusheenCat} alt="AI" style={{ width: 20, height: 20, objectFit: "contain" }} />',
                '<img src={pusheenCat} alt="AI" style={{ width: "100%", height: "100%", objectFit: "contain", transform: "scale(1.7)" }} />')

# 3. Sidebar.jsx
sb = 'frontend/src/components/Sidebar.jsx'
replace_in_file(sb,
                '<img src={pusheenCat} alt="Vetlog" style={{ width: 24, height: 24, objectFit: "contain" }} />',
                '<img src={pusheenCat} alt="Vetlog" style={{ width: 32, height: 32, objectFit: "contain", transform: "scale(1.7)" }} />')

print("Logos resized!")
