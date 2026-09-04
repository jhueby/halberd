from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from halberd.library.loader import load_all_atomics


def generate_coverage_report(
    results: list[dict],
    output_path: str | None = None,
) -> str:
    techniques = load_all_atomics()
    tested_map = {}
    for r in results:
        tid = r.get("technique_id", "")
        if tid not in tested_map or r.get("status") == "success":
            tested_map[tid] = r

    total = len(techniques)
    tested = sum(1 for t in techniques if t.id in tested_map)
    passed = sum(
        1 for t in techniques
        if t.id in tested_map and tested_map[t.id].get("status") == "success"
    )
    failed = tested - passed
    untested = total - tested

    coverage_pct = (tested / total * 100) if total else 0

    tactics: dict[str, list] = {}
    for t in techniques:
        tactics.setdefault(t.tactic, []).append(t)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Halberd BAS - Coverage Report",
        f"Generated: {now}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total techniques | {total} |",
        f"| Tested | {tested} ({coverage_pct:.0f}%) |",
        f"| Passed | {passed} |",
        f"| Failed/Error | {failed} |",
        f"| Not tested | {untested} |",
        "",
        "## Coverage by Tactic",
        "",
        "| Tactic | Total | Tested | Passed | Gap |",
        "|--------|-------|--------|--------|-----|",
    ]

    for tactic, techs in sorted(tactics.items()):
        t_total = len(techs)
        t_tested = sum(1 for t in techs if t.id in tested_map)
        t_passed = sum(
            1 for t in techs
            if t.id in tested_map and tested_map[t.id].get("status") == "success"
        )
        gap = t_total - t_tested
        lines.append(f"| {tactic} | {t_total} | {t_tested} | {t_passed} | {gap} |")

    lines.extend([
        "",
        "## Detail",
        "",
        "| Technique | Name | Status | Duration |",
        "|-----------|------|--------|----------|",
    ])

    for t in techniques:
        r = tested_map.get(t.id)
        if r:
            status = r.get("status", "unknown")
            duration = f"{r.get('duration', 0):.2f}s"
        else:
            status = "NOT TESTED"
            duration = "-"
        lines.append(f"| {t.id} | {t.name} | {status} | {duration} |")

    report = "\n".join(lines) + "\n"

    if output_path:
        Path(output_path).write_text(report)

    return report
