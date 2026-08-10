import sys
import os

# 1. ChatWindow.jsx
cw_file = 'frontend/src/components/ChatWindow.jsx'
with open(cw_file, 'r') as f:
    cw_content = f.read()
cw_content = cw_content.replace('import { ArrowRight, Cat } from "lucide-react";', 'import { ArrowRight, Cat } from "lucide-react";\nimport pusheenCat from "../assets/pusheen.png";')
cw_content = cw_content.replace('<Cat size={32} strokeWidth={1.75} />', '<img src={pusheenCat} alt="Vetlog AI" style={{ width: 32, height: 32, objectFit: "contain" }} />')
with open(cw_file, 'w') as f:
    f.write(cw_content)

# 2. MessageBubble.jsx
mb_file = 'frontend/src/components/MessageBubble.jsx'
with open(mb_file, 'r') as f:
    mb_content = f.read()
mb_content = mb_content.replace('import { Cat, Check, Copy, UserRound, Loader2 } from "lucide-react";', 'import { Cat, Check, Copy, UserRound, Loader2 } from "lucide-react";\nimport pusheenCat from "../assets/pusheen.png";')
mb_content = mb_content.replace('<Cat size={17} strokeWidth={2.25} />', '<img src={pusheenCat} alt="AI" style={{ width: 20, height: 20, objectFit: "contain" }} />')
with open(mb_file, 'w') as f:
    f.write(mb_content)

# 3. Sidebar.jsx
sb_file = 'frontend/src/components/Sidebar.jsx'
with open(sb_file, 'r') as f:
    sb_content = f.read()
sb_content = sb_content.replace('import { MessageCirclePlus, MessageSquare, Settings, CircleUserRound, LogOut, PanelLeftClose, PanelLeftOpen, Cat } from "lucide-react";', 'import { MessageCirclePlus, MessageSquare, Settings, CircleUserRound, LogOut, PanelLeftClose, PanelLeftOpen, Cat } from "lucide-react";\nimport pusheenCat from "../assets/pusheen.png";')
sb_content = sb_content.replace('<Cat size={22} strokeWidth={2.25} />', '<img src={pusheenCat} alt="Vetlog" style={{ width: 24, height: 24, objectFit: "contain" }} />')
with open(sb_file, 'w') as f:
    f.write(sb_content)

print("Logos patched!")
