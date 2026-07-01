import pytest

from tmki_loop import LoopEngine


def test_happy_path_transitions():
    engine = LoopEngine(run_id="r1", trace_id="t1", env="development")
    engine.transition("context_ready")
    engine.transition("plan_ready")
    engine.begin_step()
    engine.complete_step()
    engine.transition("judge_pending")
    engine.transition("loop_complete", stop_reason="judge_pass")
    assert engine.snapshot.loop_state == "loop_complete"


def test_budget_exceeded():
    engine = LoopEngine(run_id="r1", trace_id="t1", env="production")
    engine.snapshot.budget = {"max_steps": 1}
    engine.transition("context_ready")
    engine.transition("plan_ready")
    engine.begin_step()
    engine.complete_step()
    engine.transition("plan_ready")
    with pytest.raises(RuntimeError, match="budget_exceeded"):
        engine.begin_step()
    assert engine.snapshot.loop_state == "budget_exceeded"


def test_step_failure_allows_retry():
    engine = LoopEngine(run_id="r1", trace_id="t1", env="development")
    engine.transition("context_ready")
    engine.transition("plan_ready")
    engine.begin_step()
    engine.fail_step(error_code="E1", tool_name="rag_search")
    assert engine.snapshot.loop_state == "plan_ready"
    assert engine.snapshot.consecutive_failures == 1


def test_circuit_breaker_same_tool():
    engine = LoopEngine(run_id="r2", trace_id="t2", env="development")
    engine.transition("context_ready")
    engine.transition("plan_ready")
    engine.begin_step()
    engine.fail_step(error_code="E1", tool_name="rag_search")
    engine.begin_step()
    engine.fail_step(error_code="E1", tool_name="rag_search")
    assert engine.snapshot.circuit_breaker_tripped is True
    assert engine.snapshot.loop_state == "degraded_readonly"
