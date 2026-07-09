"""Real-time hallucination checker — hooks into LangGraph callbacks.

Runs automatically on every agent tool call. Logs warnings to stderr
and attaches evaluation metadata to LangSmith traces.
"""

import json
import re
import sys
from typing import Any

from langgraph.callbacks import BaseCallbackHandler


def _check_donation_query(sql: str) -> str | None:
    sql_upper = sql.upper()
    has_pkr = "PKR" in sql_upper or "donation" in sql.lower()
    if not has_pkr:
        return None

    has_bill_exclusion = "NOT LIKE" in sql_upper and "CHECK-OUT" in sql_upper
    has_alloc_exclusion = "NOT LIKE" in sql_upper and "FUNDS ALLOCATED" in sql_upper

    if not has_bill_exclusion and not has_alloc_exclusion:
        return "DONATION QUERY: missing bill and allocation exclusions. Add: AND text NOT LIKE 'Check-out%' AND text NOT LIKE 'Funds allocated%'."
    if not has_bill_exclusion:
        return "DONATION QUERY: missing bill exclusion. Add: AND text NOT LIKE 'Check-out%'"
    if not has_alloc_exclusion:
        return "DONATION QUERY: missing allocation exclusion. Add: AND text NOT LIKE 'Funds allocated%'"
    return None


def _check_patient_query(sql: str) -> str | None:
    """Return a warning if the SQL tries to extract patient names with substr/instr."""
    sql_upper = sql.upper()
    has_patient_context = any(
        word in sql_upper for word in ["PATIENT", "COUNT(DISTINCT", "DISTINCT TRIM"]
    )
    if not has_patient_context:
        return None

    uses_substring = "SUBSTR(" in sql_upper or "INSTR(" in sql_upper
    if uses_substring:
        return "PATIENT QUERY: uses substr/instr to extract names from free text. This will count action prefixes as patients. Use query_to_inline_table instead."
    return None


def _check_sender_filter(sql: str) -> str | None:
    """Return a warning if the SQL uses exact sender match instead of LIKE."""
    sql_upper = sql.upper()
    if "SENDER" not in sql_upper:
        return None
    if "LIKE" in sql_upper:
        return None
    for pattern in ["SENDER =", "SENDER=", "sender =", "sender="]:
        idx = sql.find(pattern)
        if idx >= 0:
            rest = sql[idx + len(pattern):].strip()
            name = rest.split("'")[1] if "'" in rest else rest.split('"')[1] if '"' in rest else rest[:20]
            return f"SENDER FILTER: uses exact match for '{name}'. Use LIKE '%{name}%' to catch variants (e.g. 'Dr. Faraz' vs 'Faraz')."
    return None


def _check_response(response: str) -> list[str]:
    """Check assistant response for overconfident claims."""
    warnings = []
    text_lower = response.lower()

    has_patient_count = any(
        word in text_lower for word in ["patient", "treated by"]
    ) and re.search(r"\b\d+\b", text_lower)

    if has_patient_count:
        admits_uncertainty = any(
            word in text_lower
            for word in [
                "approximately", "roughly", "more than", "about",
                "manual", "scan", "uncertain", "imprecise", "can see",
                "shows", "found in", "appear", "listed",
            ]
        )
        if not admits_uncertainty:
            warnings.append(
                "RESPONSE: reports a precise patient count without uncertainty qualifier. "
                "Patient names are free text and cannot be reliably counted by SQL."
            )

    has_donation_context = any(
        word in text_lower for word in ["donation", "donated", "donor", "fund drive", "pkr"]
    )
    if has_donation_context and "check-out" in text_lower:
        warnings.append(
            "RESPONSE: donation summary mentions 'Check-out' which is a patient bill, not a donation."
        )

    return warnings


class HallucinationCallback(BaseCallbackHandler):
    """LangGraph callback that checks tool calls and responses for hallucination patterns."""

    def __init__(self):
        super().__init__()
        self._tool_sql: dict[str, str] = {}
        self._warnings: list[str] = []

    def on_tool_start(self, serialized: dict[str, Any], input_str: str, **kwargs: Any) -> None:
        tool_name = serialized.get("name", "")
        if not tool_name:
            return
        try:
            inputs = json.loads(input_str)
        except (json.JSONDecodeError, TypeError):
            inputs = {"raw": str(input_str)}

        query = inputs.get("query", "")
        if query and isinstance(query, str):
            self._tool_sql[tool_name] = query

            warning = _check_donation_query(query)
            if warning:
                self._warnings.append(warning)
                self._emit(tool_name, warning)

            warning = _check_patient_query(query)
            if warning:
                self._warnings.append(warning)
                self._emit(tool_name, warning)

            warning = _check_sender_filter(query)
            if warning:
                self._warnings.append(warning)
                self._emit(tool_name, warning)

    def on_llm_end(self, response, **kwargs: Any) -> None:
        content = ""
        try:
            generations = getattr(response, "generations", [[]])
            if generations and generations[0]:
                msg = generations[0][0]
                extracted = getattr(msg, "text", "")
                if extracted:
                    content = str(extracted)
                else:
                    msg_dict = getattr(msg, "message", None)
                    if msg_dict is not None:
                        content_obj = getattr(msg_dict, "content", "")
                        if isinstance(content_obj, str):
                            content = content_obj
                        elif isinstance(content_obj, list):
                            parts = []
                            for block in content_obj:
                                if isinstance(block, dict):
                                    parts.append(block.get("text", ""))
                                else:
                                    parts.append(str(block))
                            content = " ".join(parts)
        except Exception:
            pass

        if content:
            for warning in _check_response(content):
                self._warnings.append(warning)
                self._emit("response", warning)

    def _emit(self, source: str, message: str) -> None:
        print(f"[Vetlog Eval] {source}: {message}", file=sys.stderr, flush=True)

    def clear(self) -> None:
        self._tool_sql.clear()
        self._warnings.clear()

    def get_warnings(self) -> list[str]:
        return list(self._warnings)


_hallucination_callback: HallucinationCallback | None = None


def get_hallucination_callback() -> HallucinationCallback:
    global _hallucination_callback
    if _hallucination_callback is None:
        _hallucination_callback = HallucinationCallback()
    return _hallucination_callback
