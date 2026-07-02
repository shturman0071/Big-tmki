#!/usr/bin/env python3
"""Демо: создание документа по внутреннему шаблону TMKI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_OUT = (
    Path(__file__).resolve().parents[1] / "artifacts" / "leadership-demo" / "documents"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create document from TMKI template")
    parser.add_argument(
        "--template",
        default="instruction_internal",
        help="template_id из catalog.json",
    )
    parser.add_argument("--title", default="Инструкция по маркшейдерскому контролю")
    parser.add_argument("--author", default="Инженер маркшейдерского отдела")
    parser.add_argument("--department", default="Маркшейдерское обеспечение / Сатимол")
    parser.add_argument("--body", default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    body = args.body or (
        "1. Ежесменно фиксировать контрольные точки на плане участка.\n"
        "2. Сверять отметки с проектной документацией.\n"
        "3. Несоответствия оформлять актом и передавать начальнику участка."
    )

    from tmki_document.author import create_document_from_template

    result = create_document_from_template(
        template_id=args.template,
        fields={
            "title": args.title,
            "author": args.author,
            "department": args.department,
            "body": body,
        },
        output_dir=args.output_dir,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("TMKI — документ по шаблону\n")
        print(f"  template: {result['template_title']} ({result['template_id']})")
        print(f"  policy external_law_check: {result['policy']['external_law_check']}")
        for kind, path in result["outputs"].items():
            print(f"  {kind}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
