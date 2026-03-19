#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = "BoilerHAUS/avantis-paper-bot"
ROOT = Path(__file__).resolve().parent.parent
ROADMAP_JSON = ROOT / "docs/roadmap/EXPERIMENTATION_ROADMAP_V1.json"
OUT_MD = ROOT / "docs/roadmap/EXPERIMENTATION_ROADMAP_STATUS.md"

STATUS_ORDER = {
    "complete": 0,
    "in_progress": 1,
    "blocked": 2,
    "planned": 3,
    "superseded": 4,
    "manual_review_required": 5,
}


def gh_json(args: list[str]) -> Any:
    cmd = ["gh", *args]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(proc.stdout)


def fetch_issues(issue_numbers: list[int]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for n in issue_numbers:
        issue = gh_json(["issue", "view", str(n), "--repo", REPO, "--json", "number,title,state,labels,url,closedAt"])
        out[n] = issue
    return out


def item_status(issue: dict[str, Any]) -> str:
    if issue["state"].upper() == "CLOSED":
        return "complete"
    labels = {label["name"] for label in issue.get("labels", [])}
    if "blocked" in labels:
        return "blocked"
    if "superseded" in labels:
        return "superseded"
    if any(label.startswith("priority:") for label in labels):
        return "in_progress"
    return "planned"


def gate_status(required_issue_ids: list[int], issue_map: dict[int, dict[str, Any]]) -> tuple[str, list[int]]:
    incomplete = [n for n in required_issue_ids if item_status(issue_map[n]) != "complete"]
    if not incomplete:
        return "complete", []
    return "blocked", incomplete


def render() -> str:
    roadmap = json.loads(ROADMAP_JSON.read_text(encoding="utf-8"))
    all_issue_ids = [item["issue"] for phase in roadmap["phases"] for item in phase["items"]]
    gate_issue_ids = [n for gate in roadmap["gates"].values() for n in gate["required_issue_ids"]]
    issue_ids = sorted(set(all_issue_ids + gate_issue_ids))
    issues = fetch_issues(issue_ids)

    lines: list[str] = []
    lines.append("# experimentation roadmap status")
    lines.append("")
    lines.append("## metadata")
    lines.append("- source roadmap: `docs/roadmap/EXPERIMENTATION_ROADMAP_V1.json`")
    lines.append("- status type: generated")
    lines.append("- generation rule: issue-linked roadmap items derive state from GitHub issue metadata where possible")
    lines.append("- ambiguity policy: prefer manual follow-up over silent inference")
    lines.append("")

    # gate summary
    lines.append("## gate summary")
    for gate_id, gate in roadmap["gates"].items():
        status, blockers = gate_status(gate["required_issue_ids"], issues)
        blocker_text = "none" if not blockers else ", ".join(f"#{n}" for n in blockers)
        lines.append(f"- **{gate_id}**: `{status}` — {gate['description']} (blockers: {blocker_text})")
    lines.append("")

    # current phase
    current_phase = None
    for phase in roadmap["phases"]:
        if any(item_status(issues[item["issue"]]) != "complete" for item in phase["items"]):
            current_phase = phase
            break
    if current_phase is None:
        current_phase = roadmap["phases"][-1]
    lines.append("## current phase")
    lines.append(f"- current phase: **{current_phase['name']}** (`{current_phase['id']}`)")
    lines.append("")

    lines.append("## experimentation-ready definition")
    for bullet in roadmap["gates"]["experimentation_ready"].get("operational_definition", []):
        lines.append(f"- {bullet}")
    lines.append("")

    for phase in roadmap["phases"]:
        lines.append(f"## {phase['name']}")
        if "gate" in phase:
            gate = roadmap["gates"][phase["gate"]]
            gate_state, blockers = gate_status(gate["required_issue_ids"], issues)
            lines.append(f"- gate: `{phase['gate']}` → `{gate_state}`")
            if blockers:
                lines.append(f"- blockers: {', '.join(f'#{n}' for n in blockers)}")
        complete_count = sum(1 for item in phase["items"] if item_status(issues[item["issue"]]) == "complete")
        total_count = len(phase["items"])
        lines.append(f"- progress: {complete_count}/{total_count} items complete")
        lines.append("")
        lines.append("| item | issue | status | priority |")
        lines.append("|---|---:|---|---|")
        phase_items = sorted(
            phase["items"],
            key=lambda item: (STATUS_ORDER.get(item_status(issues[item["issue"]]), 99), item["issue"]),
        )
        for item in phase_items:
            issue = issues[item["issue"]]
            status = item_status(issue)
            labels = {label["name"] for label in issue.get("labels", [])}
            priority = next((label for label in sorted(labels) if label.startswith("priority:")), "-")
            lines.append(f"| {item['title']} | #{item['issue']} | `{status}` | `{priority}` |")
        lines.append("")

    lines.append("## authored-vs-generated split")
    for note in roadmap["authored_truth"]["notes"]:
        lines.append(f"- {note}")
    lines.append("")
    lines.append("## manual override rule")
    lines.append("- If a PR only partially advances a roadmap item, reviewers must record that explicitly in the PR and/or issue thread; the generated roadmap should prefer `planned`/`in_progress` over incorrect completion.")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        content = render()
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr)
        return exc.returncode
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(content, encoding="utf-8")
    print(f"wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
