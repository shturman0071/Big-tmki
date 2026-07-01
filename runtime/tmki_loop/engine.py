from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from tmki_loop.defaults import budget_for_env, default_circuit_breaker


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class LoopSnapshot:
    schema_version: str
    run_id: str
    trace_id: str
    loop_state: str
    step_index: int
    updated_at: str
    previous_state: str | None = None
    budget: dict[str, Any] | None = None
    budget_consumed: dict[str, Any] = field(default_factory=lambda: {"steps": 0, "tokens": 0, "cost_usd": 0.0, "elapsed_ms": 0})
    circuit_breaker: dict[str, Any] | None = None
    circuit_breaker_tripped: bool = False
    consecutive_failures: int = 0
    last_error_code: str | None = None
    stop_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "loop_state": self.loop_state,
            "step_index": self.step_index,
            "updated_at": self.updated_at,
            "budget_consumed": self.budget_consumed,
            "circuit_breaker_tripped": self.circuit_breaker_tripped,
            "consecutive_failures": self.consecutive_failures,
        }
        if self.previous_state:
            data["previous_state"] = self.previous_state
        if self.budget:
            data["budget"] = self.budget
        if self.circuit_breaker:
            data["circuit_breaker"] = self.circuit_breaker
        if self.last_error_code:
            data["last_error_code"] = self.last_error_code
        if self.stop_reason:
            data["stop_reason"] = self.stop_reason
        return data


_TERMINAL = frozenset({"loop_complete", "budget_exceeded", "cancelled", "failed"})

_ALLOWED: dict[str, frozenset[str]] = {
    "init": frozenset({"context_ready", "cancelled", "failed"}),
    "context_ready": frozenset({"plan_ready", "cancelled", "failed"}),
    "plan_ready": frozenset({"step_running", "budget_exceeded", "cancelled", "failed"}),
    "step_running": frozenset({"step_done", "plan_ready", "circuit_open", "budget_exceeded", "failed", "cancelled"}),
    "step_done": frozenset({"plan_ready", "judge_pending", "loop_complete", "failed"}),
    "judge_pending": frozenset({"loop_complete", "plan_ready", "failed"}),
    "circuit_open": frozenset({"degraded_readonly", "failed"}),
    "degraded_readonly": frozenset({"loop_complete", "failed"}),
}


class LoopEngine:
    def __init__(
        self,
        *,
        run_id: str,
        trace_id: str,
        env: str = "production",
    ) -> None:
        self.snapshot = LoopSnapshot(
            schema_version="0.1",
            run_id=run_id,
            trace_id=trace_id,
            loop_state="init",
            step_index=0,
            updated_at=_now_iso(),
            budget=budget_for_env(env),
            circuit_breaker=default_circuit_breaker(),
        )
        self._last_error_code: str | None = None
        self._last_tool_name: str | None = None
        self._same_error_streak = 0
        self._same_tool_streak = 0

    def transition(self, new_state: str, *, stop_reason: str | None = None) -> LoopSnapshot:
        current = self.snapshot.loop_state
        allowed = _ALLOWED.get(current, frozenset())
        if new_state not in allowed and new_state not in _TERMINAL:
            raise ValueError(f"Недопустимый переход {current} → {new_state}")
        self.snapshot.previous_state = current
        self.snapshot.loop_state = new_state
        self.snapshot.updated_at = _now_iso()
        if stop_reason:
            self.snapshot.stop_reason = stop_reason
        return self.snapshot

    def begin_step(self) -> None:
        self.snapshot.step_index += 1
        budget = self.snapshot.budget or {}
        if self.snapshot.budget_consumed["steps"] >= budget.get("max_steps", 10):
            self.transition("budget_exceeded", stop_reason="max_steps")
            raise RuntimeError("budget_exceeded")
        self.transition("step_running")

    def complete_step(self, *, tokens: int = 0, cost_usd: float = 0.0) -> None:
        self.snapshot.budget_consumed["steps"] += 1
        self.snapshot.budget_consumed["tokens"] += tokens
        self.snapshot.budget_consumed["cost_usd"] += cost_usd
        self.snapshot.consecutive_failures = 0
        self._same_error_streak = 0
        self._same_tool_streak = 0
        self.transition("step_done")

    def fail_step(self, *, error_code: str, tool_name: str | None = None) -> None:
        self.snapshot.consecutive_failures += 1
        self.snapshot.last_error_code = error_code

        if error_code == self._last_error_code:
            self._same_error_streak += 1
        else:
            self._same_error_streak = 1
        self._last_error_code = error_code

        if tool_name:
            if tool_name == self._last_tool_name:
                self._same_tool_streak += 1
            else:
                self._same_tool_streak = 1
            self._last_tool_name = tool_name

        cb = self.snapshot.circuit_breaker or {}
        if (
            self.snapshot.consecutive_failures >= cb.get("failure_threshold", 3)
            or self._same_error_streak >= cb.get("same_error_threshold", 2)
            or (tool_name and self._same_tool_streak >= cb.get("same_tool_threshold", 2))
        ):
            self.snapshot.circuit_breaker_tripped = True
            self.transition("circuit_open", stop_reason="circuit_breaker")
            recovery = cb.get("recovery_mode", "fail_run")
            if recovery == "degraded_readonly":
                self.transition("degraded_readonly")
            else:
                self.transition("failed", stop_reason="circuit_breaker")
            return

        self.transition("plan_ready")
