import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from app.tools import REPORTS_DIR

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/{filename}")
def get_report_content(filename: str):
    """
    Return the markdown content of a saved report as JSON.
    The frontend fetches this to render an inline preview inside the chat.
    """
    filepath = os.path.join(REPORTS_DIR, filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report not found.")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    return {"filename": filename, "content": content}

@router.get("/{filename}/export", response_class=HTMLResponse)
def export_report_html(filename: str):
    """
    Return the report as a styled, print-ready HTML page.
    """
    filepath = os.path.join(REPORTS_DIR, filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report not found.")

    with open(filepath, "r", encoding="utf-8") as f:
        md_content = f.read()

    try:
        import markdown as md_lib
        body_html = md_lib.markdown(md_content, extensions=["tables", "fenced_code"])
    except ImportError:
        body_html = f"<pre>{md_content}</pre>"

    report_title = filename.replace("_", " ").replace(".md", "").title()

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <title>{report_title}</title>
      <style>
        body {{
          font-family: 'Segoe UI', Arial, sans-serif;
          max-width: 820px;
          margin: 48px auto;
          padding: 0 24px;
          color: #1a1a1a;
          line-height: 1.7;
        }}
        h1, h2, h3 {{ font-weight: 600; margin-top: 1.5em; }}
        h2 {{ font-size: 1.5rem; border-bottom: 2px solid #e5e5e5; padding-bottom: 8px; }}
        h3 {{ font-size: 1.15rem; }}
        table {{
          width: 100%;
          border-collapse: collapse;
          margin: 1.25em 0;
          font-size: 0.9rem;
        }}
        th {{
          background: #f4f4f5;
          font-weight: 600;
          text-align: left;
          padding: 10px 14px;
          border: 1px solid #d4d4d8;
        }}
        td {{
          padding: 8px 14px;
          border: 1px solid #e4e4e7;
          vertical-align: top;
        }}
        tr:nth-child(even) td {{ background: #fafafa; }}
        hr {{ border: none; border-top: 1px solid #e5e5e5; margin: 2em 0; }}
        em {{ color: #71717a; font-size: 0.875rem; }}
        code {{ background: #f4f4f5; padding: 2px 6px; border-radius: 4px; }}
        @media print {{
          body {{ margin: 24px; }}
          @page {{ margin: 2cm; }}
        }}
      </style>
    </head>
    <body>
      {body_html}
      <script>
        window.onload = function() {{ window.print(); }};
      </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html)
