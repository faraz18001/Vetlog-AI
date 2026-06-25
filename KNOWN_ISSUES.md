# Known Issues

## Report tool can't handle bulk data
`execute_sql_query` limits output to 10 rows (token efficiency). When the user asks the agent to generate a report with all rows (e.g. "show all 311 donations with dates"), the LLM only sees 10 rows and passes incomplete data to `generate_report`.

**Fix:** Make `generate_report` run its own SQL internally with a 1000-row limit per report type, so it can produce complete reports regardless of what the LLM sees. Update SYSTEM_PROMPT to tell the LLM not to pass raw data to the report tool.
