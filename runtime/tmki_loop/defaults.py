from __future__ import annotations

from typing import Any

_DEFAULT_BUDGET: dict[str, dict[str, Any]] = {
    "production": {
        "max_steps": 10,
        "max_tokens": 32000,
        "max_cost_usd": 2.5,
        "timeout_ms": 120000,
        "max_step_duration_ms": 60000,
        "max_retries_per_step": 2,
    },
    "development": {
        "max_steps": 15,
        "max_tokens": 64000,
        "max_cost_usd": 10.0,
        "timeout_ms": 180000,
        "max_step_duration_ms": 90000,
        "max_retries_per_step": 3,
    },
}

_DEFAULT_CIRCUIT_BREAKER = {
    "failure_threshold": 3,
    "same_error_threshold": 2,
    "same_tool_threshold": 2,
    "recovery_mode": "degraded_readonly",
}


def budget_for_env(env: str) -> dict[str, Any]:
    if env == "staging":
        return dict(_DEFAULT_BUDGET["production"])
    return dict(_DEFAULT_BUDGET.get(env, _DEFAULT_BUDGET["production"]))


def default_circuit_breaker() -> dict[str, Any]:
    return dict(_DEFAULT_CIRCUIT_BREAKER)
