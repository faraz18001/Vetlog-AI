import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Derive a human-readable title from the report filename.
 * e.g. "daily_summary_2025-06-25_june_24.md" → "Daily Summary — 2025-06-25"
 */
function titleFromFilename(filename) {
  const withoutExtension = filename.replace(".md", "");
  const parts = withoutExtension.split("_");

  // The first two parts are the report type words, the third is the date.
  const reportType = parts.slice(0, 2).join(" ");
  const date = parts[2] || "";

  const formatted = reportType.replace(/\b\w/g, (c) => c.toUpperCase());
  return date ? `${formatted} — ${date}` : formatted;
}

/**
 * Pull just the base filename from a path like "reports/daily_summary_2025-06-25.md".
 */
function extractFilename(reportPath) {
  return reportPath.replace("reports/", "");
}

/**
 * ReportCard — rendered inside the chat when the agent generates a report.
 *
 * Shows a collapsible markdown preview of the report and two action buttons:
 *   - "Download PDF" — fetches the PDF from the server and downloads it directly
 *     (no new tab, no print dialog).
 *   - "Download .md" — downloads the raw markdown file to the user's machine.
 */
export default function ReportCard({ reportPath }) {
  const [markdownContent, setMarkdownContent] = useState("");
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const filename = extractFilename(reportPath);
  const title = titleFromFilename(filename);

  // Fetch the report's markdown content from the backend on mount.
  useEffect(() => {
    async function fetchReport() {
      try {
        const response = await fetch(`/api/reports/${filename}`);

        if (!response.ok) {
          throw new Error(`Could not load report (HTTP ${response.status})`);
        }

        const data = await response.json();
        setMarkdownContent(data.content);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }

    fetchReport();
  }, [filename]);

  async function handleDownloadPdf() {
    try {
      const response = await fetch(`/api/reports/${filename}/pdf`);
      if (!response.ok) throw new Error(`PDF download failed (HTTP ${response.status})`);

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);

      const pdfFilename = filename.replace(".md", ".pdf");
      const link = document.createElement("a");
      link.href = url;
      link.download = pdfFilename;
      link.click();

      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF download error:", err);
    }
  }

  function handleDownloadMarkdown() {
    if (!markdownContent) return;

    const blob = new Blob([markdownContent], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();

    URL.revokeObjectURL(url);
  }

  return (
    <div className="report-card">
      {/* Header row */}
      <div className="report-card-header">
        <div className="report-card-title-row">
          <span className="report-card-icon" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <rect
                x="2" y="1" width="10" height="14"
                rx="1.5" stroke="currentColor" strokeWidth="1.3"
              />
              <path
                d="M5 5h6M5 8h6M5 11h4"
                stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"
              />
            </svg>
          </span>
          <span className="report-card-title">{title}</span>
        </div>

        <button
          className="report-card-toggle"
          onClick={() => setIsExpanded((prev) => !prev)}
          aria-expanded={isExpanded}
          aria-label={isExpanded ? "Collapse report preview" : "Expand report preview"}
        >
          {isExpanded ? "Collapse" : "Preview"}
        </button>
      </div>

      {/* Collapsible markdown preview */}
      {isExpanded && (
        <div className="report-card-preview">
          {isLoading && (
            <p className="report-card-status">Loading report…</p>
          )}

          {error && (
            <p className="report-card-status report-card-status--error">{error}</p>
          )}

          {!isLoading && !error && (
            <div className="report-card-markdown msg-content--ai">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {markdownContent}
              </ReactMarkdown>
            </div>
          )}
        </div>
      )}

      {/* Action buttons */}
      <div className="report-card-actions">
        <button
          className="report-card-btn report-card-btn--primary"
          onClick={handleDownloadPdf}
          title="Download as a PDF file directly"
        >
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden>
            <path
              d="M2 9v2.5h9V9M6.5 1v7M4 6l2.5 2.5L9 6"
              stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"
            />
          </svg>
          Download PDF
        </button>

        <button
          className="report-card-btn report-card-btn--secondary"
          onClick={handleDownloadMarkdown}
          disabled={!markdownContent}
          title="Download the raw markdown file"
        >
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden>
            <path
              d="M2 9v2.5h9V9M6.5 1v7M4 6l2.5 2.5L9 6"
              stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"
            />
          </svg>
          Download .md
        </button>
      </div>
    </div>
  );
}
