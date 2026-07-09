import { useState, useCallback, useRef } from "react";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const threadId = useRef(uid());
  const abortRef = useRef(null);

  const sendMessage = useCallback(
    async (text) => {
      if (!text.trim() || isLoading) return;

      // Cancel any in-progress request
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const userMsg = {
        id: uid(),
        role: "user",
        content: text.trim(),
        timestamp: new Date(),
      };

      const aiMsgId = uid();
      const aiMsg = {
        id: aiMsgId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isStreaming: true,
        isError: false,
        usage: null,
        reportPath: null,
        tablePath: null,
        steps: [],
      };

      setMessages((prev) => [...prev, userMsg, aiMsg]);
      setIsLoading(true);

      var userId = null;
      try {
        var authRaw = localStorage.getItem("vetlog_auth");
        if (authRaw) {
          var auth = JSON.parse(authRaw);
          userId = auth.user_id;
        }
      } catch (e) {
        // ignore — fall back to null
      }

      var body = {
        message: text.trim(),
        thread_id: threadId.current,
      };
      if (userId) {
        body.user_id = userId;
      }

      try {
        const res = await fetch("/api/chat/stream/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          signal: controller.signal,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail ?? `HTTP ${res.status}`);
        }

        // Read the SSE stream line-by-line
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          // Keep the last (potentially incomplete) line in the buffer
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const raw = line.slice(6).trim();
            if (!raw) continue;

            let evt;
            try {
              evt = JSON.parse(raw);
            } catch {
              continue;
            }

            if (evt.type === "step") {
              // Append a new step to the step chain in real-time,
              // but skip it if it's identical to the last step (prevents duplicates).
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiMsgId
                    ? {
                        ...m,
                        steps:
                          m.steps.length > 0 &&
                          m.steps[m.steps.length - 1].label === evt.label &&
                          m.steps[m.steps.length - 1].detail === evt.detail
                            ? m.steps
                            : [...m.steps, { label: evt.label, detail: evt.detail }],
                      }
                    : m,
                ),
              );
            } else if (evt.type === "chunk") {
              // Append streamed text token directly — no fake typeout needed
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiMsgId
                    ? { ...m, content: m.content + evt.text }
                    : m,
                ),
              );
            } else if (evt.type === "done") {
              // Finalise the message with usage/report and stop streaming indicator
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiMsgId
                    ? {
                        ...m,
                        isStreaming: false,
                        usage: evt.usage ?? null,
                        reportPath: evt.report_path ?? null,
                        tablePath: evt.table_path ?? null,
                      }
                    : m,
                ),
              );
            } else if (evt.type === "error") {
              throw new Error(evt.message ?? "Agent error");
            } else if (evt.type === "eval_warning") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiMsgId
                    ? {
                        ...m,
                        evalWarnings: (m.evalWarnings || []).concat([
                          evt.message,
                        ]),
                      }
                    : m,
                ),
              );
            }
          }
        }
      } catch (err) {
        if (err.name === "AbortError") return;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === aiMsgId
              ? {
                  ...m,
                  content: err.message ?? "Something went wrong.",
                  isStreaming: false,
                  isError: true,
                }
              : m,
          ),
        );
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading],
  );

  const clearChat = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setIsLoading(false);
    threadId.current = uid();
  }, []);

  const loadThread = useCallback(async (targetThreadId) => {
    abortRef.current?.abort();
    setIsLoading(false);

    var userId = null;
    try {
      var authRaw = localStorage.getItem("vetlog_auth");
      if (authRaw) {
        var auth = JSON.parse(authRaw);
        userId = auth.user_id;
      }
    } catch (e) {
      // ignore
    }

    if (!userId) return;

    var url = "/api/conversations/" + targetThreadId + "?user_id=" + userId;
    var res = await fetch(url);
    if (!res.ok) return;

    var data = await res.json();
    var msgs = [];
    for (var i = 0; i < data.length; i++) {
      msgs.push({
        id: uid(),
        role: data[i].role,
        content: data[i].content,
        timestamp: new Date(data[i].created_at),
      });
    }

    threadId.current = targetThreadId;
    setMessages(msgs);
  }, []);

  // Derived session totals from all messages in state
  const sessionUsage = messages.reduce(
    (acc, m) => {
      if (m.usage) {
        acc.input_tokens += m.usage.input_tokens;
        acc.output_tokens += m.usage.output_tokens;
        acc.total_tokens += m.usage.total_tokens;
        acc.cost_usd += m.usage.cost_usd;
      }
      return acc;
    },
    { input_tokens: 0, output_tokens: 0, total_tokens: 0, cost_usd: 0 },
  );

  return { messages, isLoading, sendMessage, clearChat, loadThread, sessionUsage, threadId: threadId.current };
}
