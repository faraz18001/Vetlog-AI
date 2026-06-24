import { useState, useCallback, useRef } from "react";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

/** Typeout animation — "writes" text into a message incrementally */
async function typeout(text, msgId, setMessages, signal) {
  const len = text.length;
  const chunkSize = len > 600 ? 8 : len > 200 ? 4 : 2;
  const delay = len > 600 ? 6 : len > 200 ? 10 : 15;

  for (let i = chunkSize; i < len; i += chunkSize) {
    if (signal?.aborted) return;
    await new Promise((r) => setTimeout(r, delay));
    const slice = text.slice(0, i);
    setMessages((prev) =>
      prev.map((m) => (m.id === msgId ? { ...m, content: slice } : m)),
    );
  }

  // Settle on the complete text and stop streaming
  setMessages((prev) =>
    prev.map((m) =>
      m.id === msgId ? { ...m, content: text, isStreaming: false } : m,
    ),
  );
}

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const threadId = useRef(uid());
  const abortRef = useRef(null);

  const sendMessage = useCallback(
    async (text) => {
      if (!text.trim() || isLoading) return;

      // Cancel any in-progress typeout
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
      };

      setMessages((prev) => [...prev, userMsg, aiMsg]);
      setIsLoading(true);

      try {
        const res = await fetch("/api/chat/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: text.trim(),
            thread_id: threadId.current,
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail ?? `HTTP ${res.status}`);
        }

        const data = await res.json();
        const reply =
          typeof data.response === "string"
            ? data.response
            : JSON.stringify(data.response);

        // Attach usage metadata before typeout so it's visible once done
        if (data.usage) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === aiMsgId ? { ...m, usage: data.usage } : m,
            ),
          );
        }

        await typeout(reply, aiMsgId, setMessages, controller.signal);
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

  return { messages, isLoading, sendMessage, clearChat, sessionUsage };
}
