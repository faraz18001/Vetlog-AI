import re

def to_jsx(html_str):
    # Change class to className
    s = html_str.replace('class="', 'className="')
    # Change style string to object
    s = s.replace('style="font-variation-settings: \'FILL\' 1;"', "style={{ fontVariationSettings: \"'FILL' 1\" }}")
    s = s.replace('style="font-variation-settings: \'FILL\' 0, \'wght\' 300, \'GRAD\' 0, \'opsz\' 24;"', "style={{ fontVariationSettings: \"'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24\" }}")
    # Close img tags
    s = re.sub(r'(<img[^>]*?[^/])>', r'\1/>', s)
    return s

def extract_body(file_path):
    with open(file_path, "r") as f:
        content = f.read()
    
    # Extract everything between <body> and </body>
    start = content.find("<body")
    end = content.find("</body>")
    body = content[start:end]
    body = body[body.find(">")+1:]
    
    # We want everything inside the body except the script tags at the end
    script_start = body.rfind("<script")
    if script_start != -1:
        body = body[:script_start]
        
    return body

hero_body = extract_body("/home/syedfaraz/.gemini/antigravity/brain/08135fdf-7e6b-49af-ab84-76c30615a626/.system_generated/steps/137/content.md")
features_body = extract_body("/home/syedfaraz/.gemini/antigravity/brain/08135fdf-7e6b-49af-ab84-76c30615a626/.system_generated/steps/145/content.md")

# For features, we don't need the header and footer again if hero has it, or we can just merge them.
# The Hero body has:
# - Ambient Background
# - TopNavBar
# - Hero Section
#
# The Features body has:
# - TopNavBar
# - Hero Spacer
# - Feature Showcase Section
# - Footer

# We will extract just the Feature Showcase Section and Footer from features_body
feat_start = features_body.find('<!-- Feature Showcase Section')
feat_html = features_body[feat_start:]

combined_html = hero_body + "\n" + feat_html

jsx = to_jsx(combined_html)

jsx_template = f"""import React, {{ useEffect }} from 'react';
import {{ Link }} from 'react-router-dom';
import './LandingPage.css';

export default function LandingPage() {{
    useEffect(() => {{
        const handleScroll = () => {{
            const nav = document.getElementById('main-nav');
            if (nav) {{
                if (window.scrollY > 20) {{
                    nav.classList.add('shadow-md');
                    nav.classList.replace('bg-surface-container/80', 'bg-surface-container');
                }} else {{
                    nav.classList.remove('shadow-md');
                    nav.classList.replace('bg-surface-container', 'bg-surface-container/80');
                }}
            }}
        }};
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }}, []);

    return (
        <div className="bg-surface text-on-surface font-body-md antialiased overflow-x-hidden relative selection:bg-primary/30 selection:text-primary-100 paper-grain min-h-screen flex flex-col">
            {{/* Replaced static 'Get Started' with react-router Link */}}
            {{/* We inject the parsed JSX below */}}
            <div dangerouslySetInnerHTML={{{{ __html: `
            {jsx.replace('`', '\\`').replace('$', '\\$')}
            ` }}}} />
        </div>
    );
}}
"""

# Wait, dangerouslySetInnerHTML doesn't support the `style={{}}` react syntax, it expects normal HTML style attributes.
# If we use dangerouslySetInnerHTML, we shouldn't change `class` to `className` or `style`!
# Let's just output pure JSX and not use dangerouslySetInnerHTML to ensure reactivity works better.

jsx_str = f"""import React, {{ useEffect }} from 'react';
import {{ Link }} from 'react-router-dom';
import './LandingPage.css';

export default function LandingPage() {{
    useEffect(() => {{
        const handleScroll = () => {{
            const nav = document.getElementById('main-nav');
            if (nav) {{
                if (window.scrollY > 20) {{
                    nav.classList.add('shadow-md');
                    nav.classList.replace('bg-surface-container/80', 'bg-surface-container');
                }} else {{
                    nav.classList.remove('shadow-md');
                    nav.classList.replace('bg-surface-container', 'bg-surface-container/80');
                }}
            }}
        }};
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }}, []);

    return (
        <div className="bg-surface text-on-surface font-body-md antialiased overflow-x-hidden relative selection:bg-primary/30 selection:text-primary-100 paper-grain min-h-screen flex flex-col">
            {jsx}
        </div>
    );
}}
"""

with open("src/components/LandingPage.jsx", "w") as f:
    f.write(jsx_str)

