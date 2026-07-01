#!/usr/bin/env python3
"""Provisioning папки сотрудника на рабочем столе (#44)."""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision employee desktop folder")
    parser.add_argument("--employee-id", default="emp_litovsky_d")
    parser.add_argument("--display-name", default="Литовский Д.")
    parser.add_argument("--folder-id", default=None)
    args = parser.parse_args()

    from tmki_desktop_sync.provision import provision_employee_desktop

    result = provision_employee_desktop(
        employee_id=args.employee_id,
        display_name=args.display_name,
        folder_id=args.folder_id,
    )
    print(f"desktop: {result.desktop_path} (created={result.created_desktop})")
    print(f"server:  {result.server_path}")
    print(f"manifest: {result.manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
