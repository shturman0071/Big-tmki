from pathlib import Path

from tmki_tools import check_policy, load_gating_rules

RULES = Path(__file__).resolve().parents[2] / "schemas/tools/tool-gating.rules.json"


def test_chefmarkscheider_rag_allowed():
    rules = load_gating_rules(RULES)
    ctx = {
        "company_id": "company_tmki_ru",
        "project_id": "project_satimol",
        "department_id": "dept_markscheider",
        "project_role": "Chefmarkscheider",
        "employee_id": "emp_litovsky_d",
        "clearance": "restricted",
        "env": "production",
    }
    d = check_policy("rag_search", ctx, rules)
    assert d.allowed is True


def test_contractor_ocr_denied():
    rules = load_gating_rules(RULES)
    ctx = {
        "company_id": "company_tmki_ru",
        "project_id": "project_satimol",
        "project_role": "Подрядчик (external)",
        "employee_id": "emp_contractor",
        "clearance": "internal",
        "env": "production",
        "contractor_id": "contractor_x",
    }
    d = check_policy("ocr_mineru", ctx, rules)
    assert d.allowed is False
    assert d.deny_reason == "insufficient_role"
