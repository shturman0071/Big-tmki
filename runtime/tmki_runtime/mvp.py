from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

from tmki_loop import LoopEngine
from tmki_rag.folders import FolderAclContext, load_folder_catalog, load_folder_grants
from tmki_rag.search import rag_search
from tmki_llm import get_llm_provider
from tmki_tools import ToolRegistry, load_gating_rules

ROOT = Path(__file__).resolve().parents[2]
GATING_RULES = ROOT / "schemas/tools/tool-gating.rules.json"
FOLDERS_FILE = ROOT / "schemas/document/examples/satimol-folders.example.json"
GRANTS_FILE = ROOT / "schemas/org/examples/satimol-folder-grants.example.json"


def load_satimol_folder_acl(as_of: date | None = None) -> FolderAclContext:
    from datetime import date as date_cls

    return FolderAclContext.from_catalog(
        load_folder_catalog(FOLDERS_FILE),
        load_folder_grants(GRANTS_FILE),
        as_of=as_of or date_cls(2025, 9, 10),
    )


def _audit(event_type: str, trace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"event_type": event_type, "trace_id": trace_id, "payload": payload}


def _llm_handler(provider_name: str | None = None):
    def handler(request: dict[str, Any], _decision: Any) -> dict[str, Any]:
        inp = request["input"]
        if provider_name:
            os.environ["TMKI_LLM_PROVIDER"] = provider_name
        provider = get_llm_provider()
        result = provider.generate(
            query=inp.get("query", ""),
            citations=inp.get("citations", []),
            read_only_mode=bool(inp.get("read_only_mode")),
        )
        return {
            "answer": result.answer,
            "confidence": result.confidence,
            "citations": result.citations,
            "provider": result.provider,
            "model": result.model,
            "token_usage": result.token_usage,
            "summary": f"llm provider={result.provider} confidence={result.confidence}",
        }

    return handler


def _stub_llm_generate(request: dict[str, Any], _decision: Any) -> dict[str, Any]:
    return _llm_handler("stub")(request, _decision)


def _rag_handler(chunks: list[dict[str, Any]], folder_acl: Any | None = None):
    def handler(request: dict[str, Any], _decision: Any) -> dict[str, Any]:
        inp = request["input"]
        search_req = {
            "schema_version": "0.1",
            "trace_id": request["trace_id"],
            "query": inp["query"],
            "top_k": inp.get("top_k", 8),
            "policy_context": request["policy_context"],
        }
        resp = rag_search(search_req, chunks, folder_acl=folder_acl)
        return {
            **resp,
            "summary": f"rag results={len(resp.get('results', []))}",
        }

    return handler


def build_registry(
    chunks: list[dict[str, Any]],
    rules_path: Path | None = None,
    *,
    folder_acl: Any | None = None,
) -> ToolRegistry:
    rules = load_gating_rules(rules_path or GATING_RULES)
    registry = ToolRegistry(rules)
    registry.register("rag_search", _rag_handler(chunks, folder_acl))
    registry.register("llm_openai", _stub_llm_generate)
    return registry


def _judge_pass(answer: str, citations: list[dict[str, Any]], rag_ok: bool) -> bool:
    if not answer.strip():
        return False
    if rag_ok and not citations:
        return False
    return True


def run_mvp(
    *,
    message: str,
    policy_context: dict[str, Any],
    chunks: list[dict[str, Any]],
    trace_id: str | None = None,
    run_id: str | None = None,
    folder_acl: Any | None = None,
    use_satimol_folder_acl: bool = True,
) -> dict[str, Any]:
    """
    MVP flow: schemas/runtime/mvp-flow.json (стадии 1–8, без реального LLM).
    """
    trace_id = trace_id or str(uuid4())
    run_id = run_id or str(uuid4())
    env = policy_context.get("env", "production")

    if folder_acl is None and use_satimol_folder_acl:
        folder_acl = load_satimol_folder_acl()

    engine = LoopEngine(run_id=run_id, trace_id=trace_id, env=env)
    registry = build_registry(chunks, folder_acl=folder_acl)
    audit_events: list[dict[str, Any]] = [
        _audit("run_started", trace_id, {"run_id": run_id}),
    ]

    engine.transition("context_ready")
    audit_events.append(_audit("loop_state_changed", trace_id, {"loop_state": "context_ready"}))

    context_bundle = {
        "message": message,
        "policy_context": policy_context,
    }

    engine.transition("plan_ready")

    # Step: rag_search
    engine.begin_step()
    rag_req = {
        "schema_version": "0.1",
        "trace_id": trace_id,
        "run_id": run_id,
        "step_id": str(uuid4()),
        "tool_id": "rag_search",
        "policy_context": policy_context,
        "input": {"query": message, "top_k": 8},
    }
    rag_resp = registry.execute(rag_req)
    if rag_resp["status"] == "denied":
        audit_events.append(_audit("tool_call_denied", trace_id, {"tool_name": "rag_search", "deny_reason": rag_resp.get("deny_reason")}))
        engine.fail_step(error_code="TOOL_DENIED", tool_name="rag_search")
        return _finalize(engine, audit_events, run_id, trace_id, failed=True)

    if rag_resp["status"] == "failed":
        engine.fail_step(error_code=rag_resp.get("error", {}).get("code", "RAG_FAILED"), tool_name="rag_search")
        return _finalize(engine, audit_events, run_id, trace_id, failed=True)

    rag_output = rag_resp["output"]
    citations = [r["citation"] for r in rag_output.get("results", [])]
    rag_ok = bool(citations) and not rag_output.get("denied_by_policy")
    audit_events.append(_audit("tool_call_completed", trace_id, {"tool_name": "rag_search", "result_count": len(citations)}))
    if citations:
        audit_events.append(_audit("document_accessed", trace_id, {"doc_id": citations[0]["doc_id"], "access_mode": "rag", "chunk_count": len(citations)}))

    engine.complete_step(tokens=0)

    read_only = engine.snapshot.loop_state == "degraded_readonly"
    if rag_output.get("denied_by_policy") or not citations:
        read_only = True

    # Step: llm_openai (stub)
    engine.transition("plan_ready")
    engine.begin_step()
    llm_req = {
        "schema_version": "0.1",
        "trace_id": trace_id,
        "run_id": run_id,
        "step_id": str(uuid4()),
        "tool_id": "llm_openai",
        "policy_context": policy_context,
        "input": {"query": message, "citations": citations, "read_only_mode": read_only},
    }
    llm_resp = registry.execute(llm_req)
    if llm_resp["status"] != "completed":
        engine.fail_step(error_code="LLM_FAILED", tool_name="llm_openai")
        return _finalize(engine, audit_events, run_id, trace_id, failed=True)

    answer = llm_resp["output"]["answer"]
    confidence = llm_resp["output"]["confidence"]
    engine.complete_step(tokens=500, cost_usd=0.01)

    engine.transition("judge_pending")
    if _judge_pass(answer, citations, rag_ok):
        audit_events.append(_audit("judge_pass", trace_id, {"checklist_version": "mvp-v0.1"}))
        engine.transition("loop_complete", stop_reason="judge_pass")
    else:
        audit_events.append(_audit("judge_fail", trace_id, {"checklist_version": "mvp-v0.1", "failed_checks": ["citations"]}))
        engine.transition("failed", stop_reason="unrecoverable_error")

    audit_events.append(_audit("run_completed", trace_id, {"run_id": run_id, "status": engine.snapshot.loop_state}))

    return {
        "run_id": run_id,
        "trace_id": trace_id,
        "loop_state": engine.snapshot.to_dict(),
        "context_bundle": context_bundle,
        "output": {
            "answer": answer,
            "confidence": confidence,
            "citations": citations,
        },
        "audit_events": audit_events,
    }


def _finalize(
    engine: LoopEngine,
    audit_events: list[dict[str, Any]],
    run_id: str,
    trace_id: str,
    *,
    failed: bool,
) -> dict[str, Any]:
    if failed and engine.snapshot.loop_state not in ("failed", "circuit_open", "budget_exceeded"):
        pass
    audit_events.append(_audit("run_completed", trace_id, {"run_id": run_id, "status": engine.snapshot.loop_state}))
    return {
        "run_id": run_id,
        "trace_id": trace_id,
        "loop_state": engine.snapshot.to_dict(),
        "output": None,
        "audit_events": audit_events,
    }


def load_chunks(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["chunks"]
