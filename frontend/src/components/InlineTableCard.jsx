import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Table2, Download, ChevronDown, ChevronUp } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

function extractFilename(path) {
  return path.replace("reports/", "");
}

export default function InlineTableCard({ path }) {
  const [content, setContent] = useState("");
  const [title, setTitle] = useState("Query Results");
  const [rowCount, setRowCount] = useState(null);
  const [isExpanded, setIsExpanded] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const filename = extractFilename(path);

  useEffect(() => {
    async function fetchTable() {
      try {
        const res = await fetch(`/api/reports/${filename}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const md = data.content;

        setContent(md);

        const titleMatch = md.match(/^##\s+(.+)$/m);
        if (titleMatch) setTitle(titleMatch[1].trim());

        const rowsMatch = md.match(/\*(\d+)\s*rows/);
        if (rowsMatch) setRowCount(parseInt(rowsMatch[1], 10));
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }
    fetchTable();
  }, [filename]);

  return (
    <div className="inline-table-card">
      <div className="inline-table-header">
        <div className="inline-table-title-row">
          <span className="inline-table-icon" aria-hidden="true">
            <Table2 size={16} strokeWidth={2.25} />
          </span>
          <span className="inline-table-title">{title}</span>
          {rowCount !== null && (
            <span className="inline-table-badge">{rowCount} rows</span>
          )}
        </div>

        <div className="inline-table-actions">
          <button
            className="inline-table-toggle"
            onClick={() => setIsExpanded((p) => !p)}
            aria-expanded={isExpanded}
            aria-label={isExpanded ? "Collapse table" : "Expand table"}
          >
            {isExpanded ? <ChevronUp size={15} strokeWidth={2.25} /> : <ChevronDown size={15} strokeWidth={2.25} />}
          </button>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            className="inline-table-body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          >
            {isLoading ? (
              <p className="inline-table-status">Loading table…</p>
            ) : error ? (
              <p className="inline-table-status inline-table-status--error">{error}</p>
            ) : (
              <div className="inline-table-scroll">
                <div className="inline-table-markdown msg-content--ai">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {content}
                  </ReactMarkdown>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
