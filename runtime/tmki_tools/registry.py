from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from tmki_tools.gating import GatingDecision, check_policy

ToolHandler = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


class ToolRegistry:
    def __init__(self, rules: dict[str, Any]) -> None:
        self._rules = rules
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, tool_id: str, handler: ToolHandler) -> None:
        self._handlers[tool_id] = handler

    def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        tool_id = request["tool_id"]
        trace_id = request["trace_id"]
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        decision = check_policy(tool_id, request["policy_context"], self._rules)
        if not decision.allowed:
            return {
                "schema_version": "0.1",
                "trace_id": trace_id,
                "tool_id": tool_id,
                "status": "denied",
                "deny_reason": decision.deny_reason,
                "occurred_at": now,
            }

        handler = self._handlers.get(tool_id)
        if not handler:
            return {
                "schema_version": "0.1",
                "trace_id": trace_id,
                "tool_id": tool_id,
                "status": "failed",
                "error": {"code": "TOOL_NOT_REGISTERED", "message": f"Нет handler для {tool_id}"},
                "occurred_at": now,
            }

        try:
            output = handler(request, decision)
            return {
                "schema_version": "0.1",
                "trace_id": trace_id,
                "tool_id": tool_id,
                "status": "completed",
                "output": output,
                "output_summary": output.get("summary", ""),
                "occurred_at": now,
            }
        except Exception as exc:  # noqa: BLE001 — MVP boundary
            return {
                "schema_version": "0.1",
                "trace_id": trace_id,
                "tool_id": tool_id,
                "status": "failed",
                "error": {"code": "TOOL_EXECUTION_ERROR", "message": str(exc)},
                "occurred_at": now,
            }
