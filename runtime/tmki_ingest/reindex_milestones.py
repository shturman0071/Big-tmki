"""Пороги milestone re-index (25/50/75/100%) и чтение маркеров."""

from __future__ import annotations

from pathlib import Path

MILESTONE_THRESHOLDS: tuple[int, ...] = (25, 50, 75, 100)


def list_done_milestones(markers_dir: Path) -> list[int]:
    done: list[int] = []
    if not markers_dir.is_dir():
        return done
    for m in MILESTONE_THRESHOLDS:
        if (markers_dir / f"milestone-{m}.json").is_file():
            done.append(m)
    return done


def milestone_summary(percent: float, markers_dir: Path) -> dict[str, int | list[int] | None]:
    done = list_done_milestones(markers_dir)
    ready: int | None = None
    for m in MILESTONE_THRESHOLDS:
        if percent >= m and m not in done:
            ready = m
            break
    next_up: int | None = None
    for m in MILESTONE_THRESHOLDS:
        if percent < m:
            next_up = m
            break
    return {
        "milestones_done": done,
        "milestone_ready": ready,
        "next_milestone": next_up,
    }
