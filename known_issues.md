# Vetlog AI - Known Issues & Architecture Backlog

This document tracks known architectural limitations and planned improvements for the backend AI agent.

### 1. Database Settings & Multi-User Support
- **GitHub Issue:** [#1](https://github.com/faraz18001/Vetlog-AI/issues/1)
- **Current State:** API keys and LLM provider settings are saved directly to the `.env` file via `config_manager.py`.
- **Issue:** Programmatically rewriting `.env` is brittle and only works for a single-user local deployment. It prevents the app from being used by multiple clinics or users.
- **Planned Fix:** Create an `app_settings` and/or `users` table in the SQLite database to store configurations. Migrate the API keys out of the `.env` file and fetch them from the database dynamically on each request.

### 2. Large Data Requests (The 10-Row SQL Limit)
- **Current State:** `execute_sql_query` has a hardcoded limit of 10 rows to protect the LLM's context window and token budget.
- **Status:** RESOLVED via `query_to_inline_table` tool (2026-06-30).
- **Issue:** If a user asks for detailed information on 100+ rows (e.g., "Show me all 150 donations from June"), the agent cannot see past the 10th row. Aggregate queries (SUM/COUNT) don't solve this if the user wants actual row-by-row details.
- **Planned Fix:** Create a `query_to_inline_table` tool. The Python backend will execute unbounded queries, format the results as a Markdown table, save it to a temporary report file, and pass just the file path back to the LLM. The frontend will then render the 100+ row table inline inside the chat window, completely bypassing the LLM's context limit.

### 3. Hardcoded Report Templates
- **GitHub Issue:** [#2](https://github.com/faraz18001/Vetlog-AI/issues/2)
- **Current State:** The `generate_report` tool uses a strict dictionary mapping for templates (`daily_summary` and `donation_ledger`).
- **Issue:** The agent cannot generate custom, free-form reports or detailed breakdowns if they don't exactly match the hardcoded templates.
- **Planned Fix:** Refactor `generate_report` into `generate_dynamic_report`, allowing the LLM to pass raw Markdown directly into the tool, giving it total freedom over the report's structure and contents.

### 4. Context Window Management (Memory Compaction)
- **GitHub Issue:** [#3](https://github.com/faraz18001/Vetlog-AI/issues/3)
- **Current State:** LangGraph passes the entire conversation history (`messages` array) to the LLM on every turn.
- **Issue:** For long, continuous chats (e.g., 50+ turns), the token count will eventually exceed the model's context window limit, causing the agent to crash or become extremely expensive to run.
- **Planned Fix:** Implement a "Summarization Node" or sliding window using LangGraph's `RemoveMessage` utility. When the message count exceeds a threshold (e.g., 20 messages), summarize the oldest messages into a single context paragraph and prune them from the active state, keeping token usage low while preserving the agent's memory.

### 5. LLM Model Picker — Auto-Populate Model Dropdown
- **GitHub Issue:** [#4](https://github.com/faraz18001/Vetlog-AI/issues/4)

### 6. Chrome Extension — Aggressive DOM Observer Scrapes Wrong Chat
- **GitHub Issue:** [#5](https://github.com/faraz18001/Vetlog-AI/issues/5)
- **Assignee:** M-AmmarBaig
- **Current State:** Settings modal shows a free-text input for the model name. User must go online, research which model their provider offers, and type it in manually.
- **Issue:** Poor UX — user shouldn't need to know model names by heart. Most providers expose a `/v1/models` endpoint that lists available models, but most require the API key to access.
- **Planned Fix:** Add `GET /api/config/llm/models?provider=X` endpoint. For OpenRouter (public, no key needed), fetch and filter to tool-calling models live. For OpenAI/Groq/Mistral/Cerebras/Gemini, read the stored API key from `.env` and fetch live. For Ollama, keep text input (user-installed models vary). Frontend: on provider select, fetch models and render `<select>` dropdown with results + "Custom model…" fallback option.
