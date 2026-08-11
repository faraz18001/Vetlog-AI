import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { FileText, Download, Table, ChevronDown, ChevronUp, ArrowLeft } from "lucide-react";

function titleFromFilename(filename) {
  if (filename.startsWith("query_")) {
    const withoutExt = filename.replace(".md", "");
    const parts = withoutExt.split("_");
    // query_YYYY-MM-DD_HHMMSS_title_words
    if (parts.length >= 4) {
      const date = parts[1];
      const titleWords = parts.slice(3).join(" ");
      const formatted = titleWords.replace(/\b\w/g, (c) => c.toUpperCase());
      return formatted ? `${formatted} — ${date}` : formatted;
    }
  }

  const withoutExt = filename.replace(".md", "");
  const parts = withoutExt.split("_");
  const reportType = parts.slice(0, 2).join(" ");
  const date = parts[2] || "";
  const formatted = reportType.replace(/\b\w/g, (c) => c.toUpperCase());
  return date ? `${formatted} — ${date}` : formatted;
}

function groupByDate(items) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const yesterday = new Date(today.getTime() - 86400000);

  const groups = {};
  for (const item of items) {
    const d = new Date(item.created_at);
    d.setHours(0, 0, 0, 0);

    let key;
    if (d.getTime() === today.getTime()) {
      key = "Today";
    } else if (d.getTime() === yesterday.getTime()) {
      key = "Yesterday";
    } else if (d.getTime() >= today.getTime() - 7 * 86400000) {
      key = "Previous 7 Days";
    } else {
      key = "Older";
    }

    if (!groups[key]) groups[key] = [];
    groups[key].push(item);
  }

  const order = ["Today", "Yesterday", "Previous 7 Days", "Older"];
  return order.filter((k) => groups[k]).map((k) => ({ group: k, items: groups[k] }));
}

function ReportItem({ report }) {
  const [markdownContent, setMarkdownContent] = useState("");
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const title = titleFromFilename(report.filename);

  useEffect(() => {
    if (!isExpanded) return;

    let cancelled = false;
    async function fetchReport() {
      try {
        const response = await fetch(`/api/reports/${report.filename}`);
        if (!response.ok) throw new Error(`Could not load report (HTTP ${response.status})`);
        const data = await response.json();
        if (!cancelled) setMarkdownContent(data.content);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    fetchReport();
    return () => { cancelled = true; };
  }, [isExpanded, report.filename]);

  async function handleDownloadPdf() {
    try {
      const response = await fetch(`/api/reports/${report.filename}/pdf`);
      if (!response.ok) throw new Error(`PDF download failed (HTTP ${response.status})`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const pdfFilename = report.filename.replace(".md", ".pdf");
      const link = document.createElement("a");
      link.href = url;
      link.download = pdfFilename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF download error:", err);
    }
  }

  return (
    <div className="reports-page-item">
      <div className="reports-page-item-header">
        <div className="reports-page-item-title-row">
          {report.type === "table" ? (
            <Table size={15} strokeWidth={2} className="reports-page-item-icon reports-page-item-icon--table" />
          ) : (
            <FileText size={15} strokeWidth={2} className="reports-page-item-icon" />
          )}
          <span className="reports-page-item-title">{title}</span>
          <span className={"reports-page-item-badge reports-page-item-badge--" + report.type}>
            {report.type === "table" ? "Table" : "Report"}
          </span>
        </div>
        <div className="reports-page-item-actions">
          <button
            className="reports-page-item-toggle"
            onClick={() => setIsExpanded((prev) => !prev)}
            aria-expanded={isExpanded}
          >
            {isExpanded ? (
              <><ChevronUp size={14} strokeWidth={2} /> Collapse</>
            ) : (
              <><ChevronDown size={14} strokeWidth={2} /> Preview</>
            )}
          </button>
          <button
            className="reports-page-item-btn"
            onClick={handleDownloadPdf}
            title="Download as PDF"
          >
            <Download size={13} strokeWidth={2.5} />
            PDF
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="reports-page-item-preview">
          {isLoading && <p className="reports-page-item-status">Loading report…</p>}
          {error && <p className="reports-page-item-status reports-page-item-status--error">{error}</p>}
          {!isLoading && !error && (
            <div className="reports-page-item-markdown msg-content--ai">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdownContent}</ReactMarkdown>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ReportsPage({ userId, onBackToChat }) {
  const [reports, setReports] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchReports() {
      try {
        const response = await fetch(`/api/reports/user/?user_id=${userId}`);
        if (!response.ok) throw new Error(`Failed to load reports (HTTP ${response.status})`);
        const data = await response.json();
        setReports(data.reports);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }
    fetchReports();
  }, [userId]);

  const groupedReports = groupByDate(reports);

  return (
    <div className="reports-page">
      <div className="reports-page-header">
        <button className="reports-page-back" onClick={onBackToChat} aria-label="Back to chat">
          <ArrowLeft size={16} strokeWidth={2} />
          <span>Back to Chat</span>
        </button>
        <h1 className="reports-page-heading">Reports</h1>
        <p className="reports-page-subheading">All reports and data tables you have generated</p>
      </div>

      <div className="reports-page-content">
        {isLoading && (
          <div className="reports-page-empty">
            <p>Loading reports…</p>
          </div>
        )}

        {error && (
          <div className="reports-page-empty">
            <p className="reports-page-empty--error">{error}</p>
          </div>
        )}

        {!isLoading && !error && reports.length === 0 && (
          <div className="reports-page-empty">
            <FileText size={40} strokeWidth={1.5} className="reports-page-empty-icon" />
            <h2>No reports yet</h2>
            <p>Reports you generate in chat will appear here. Try asking the assistant to create a report or export data.</p>
          </div>
        )}

        {!isLoading && !error && groupedReports.map((section) => (
          <div key={section.group} className="reports-page-group">
            <h2 className="reports-page-group-title">{section.group}</h2>
            <div className="reports-page-list">
              {section.items.map((report) => (
                <ReportItem key={report.filename} report={report} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
