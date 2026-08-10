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
replace_in_file(cw, 'import pusheenCat from "../assets/pusheen.png";', 'import appLogo from "../assets/logo.png";')
replace_in_file(cw, 'src={pusheenCat}', 'src={appLogo}')

# 2. MessageBubble.jsx
mb = 'frontend/src/components/MessageBubble.jsx'
replace_in_file(mb, 'import pusheenCat from "../assets/pusheen.png";', 'import appLogo from "../assets/logo.png";')
replace_in_file(mb, 'src={pusheenCat}', 'src={appLogo}')

# 3. Sidebar.jsx
sb = 'frontend/src/components/Sidebar.jsx'
replace_in_file(sb, 'import pusheenCat from "../assets/pusheen.png";', 'import appLogo from "../assets/logo.png";')
replace_in_file(sb, 'src={pusheenCat}', 'src={appLogo}')

# 4. LandingPage.jsx
lp = 'frontend/src/components/LandingPage.jsx'
with open(lp, 'r') as f:
    lp_content = f.read()

# Add import for logo if not present
if 'import appLogo from' not in lp_content:
    lp_content = lp_content.replace("import pusheenCat from '../assets/pusheen.png';", "import pusheenCat from '../assets/pusheen.png';\nimport appLogo from '../assets/logo.png';")

# Replace <Cat> tags with the new logo
lp_content = lp_content.replace('<Cat size={20} className="text-primary" strokeWidth={2.25} />', '<img src={appLogo} alt="Vetlog" style={{ width: 28, height: 28, objectFit: "contain", transform: "scale(1.5)" }} />')
lp_content = lp_content.replace('<Cat size={14} strokeWidth={2.25} />', '<img src={appLogo} alt="Vetlog" style={{ width: 20, height: 20, objectFit: "contain", transform: "scale(1.5)" }} />')
lp_content = lp_content.replace('<Cat className="text-primary w-6 h-6" strokeWidth={2.25} />', '<img src={appLogo} alt="Vetlog" style={{ width: 24, height: 24, objectFit: "contain", transform: "scale(1.5)" }} />')

with open(lp, 'w') as f:
    f.write(lp_content)

print("Logos and LandingPage fixed!")
