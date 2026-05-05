#!/usr/bin/env python3
"""
dqr_cli.py — Data Quality Review issue lifecycle management.

Requires: PyYAML

Usage:
    python3 dqr_cli.py summary --file <dqr.yaml>
    python3 dqr_cli.py add --file <dqr.yaml> --category <cat> --object <obj> [--attribute <attr>]
                        --check <description> --severity <low|medium|high> --treatment <treatment>
    python3 dqr_cli.py close --file <dqr.yaml> --id <DQR-NNN> --treatment <treatment>
    python3 dqr_cli.py open --file <dqr.yaml>
"""

import argparse
import sys

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

VALID_SEVERITIES = ("low", "medium", "high", "info")
VALID_TREATMENTS = ("fix_in_source", "fix_in_flight", "fix_in_target", "accept_ignore", "needs_decision")
VALID_STATUSES = ("open", "closed", "deferred")
VALID_CATEGORIES = (
    "null_values", "coded_values", "data_type", "coordinate_precision",
    "connectivity", "referential_integrity", "duplicates", "missing_data",
    "format_mismatch", "business_rule",
)


def load_dqr(filepath):
    """Load DQR YAML file."""
    with open(filepath, "r") as f:
        return yaml.safe_load(f) or {}


def save_dqr(filepath, dqr):
    """Save DQR YAML file."""
    with open(filepath, "w") as f:
        yaml.dump(dqr, f, default_flow_style=False, sort_keys=False, width=120)


def next_id(dqr):
    """Get next DQR issue ID."""
    issues = dqr.get("issues", [])
    if not issues:
        return "DQR-001"
    max_num = max(int(i["id"].split("-")[1]) for i in issues if i.get("id"))
    return f"DQR-{max_num + 1:03d}"


def cmd_summary(args):
    """Print DQR summary."""
    dqr = load_dqr(args.file)
    issues = dqr.get("issues", [])

    if not issues:
        print("No DQR issues recorded.")
        return

    open_issues = [i for i in issues if i.get("status") == "open"]
    closed_issues = [i for i in issues if i.get("status") == "closed"]

    print(f"DQR Summary: {len(issues)} total issues ({len(open_issues)} open, {len(closed_issues)} closed)")
    print()

    # By severity
    by_severity = {}
    for i in issues:
        sev = i.get("severity", "unknown")
        by_severity.setdefault(sev, []).append(i)

    print("By severity:")
    for sev in ("high", "medium", "low", "info"):
        count = len(by_severity.get(sev, []))
        if count:
            open_count = sum(1 for i in by_severity[sev] if i.get("status") == "open")
            print(f"  {sev:<8}: {count} ({open_count} open)")

    # By treatment
    print("\nBy treatment:")
    by_treatment = {}
    for i in issues:
        t = i.get("treatment", "unknown")
        by_treatment.setdefault(t, []).append(i)
    for treatment, items in sorted(by_treatment.items()):
        print(f"  {treatment:<20}: {len(items)}")

    # List open issues
    if open_issues:
        print(f"\nOpen issues ({len(open_issues)}):")
        print(f"  {'ID':<10} {'Severity':<8} {'Object':<30} {'Check'}")
        print(f"  {'-'*10} {'-'*8} {'-'*30} {'-'*40}")
        for i in open_issues:
            print(f"  {i.get('id', '?'):<10} {i.get('severity', '?'):<8} "
                  f"{i.get('source_object', '?'):<30} {i.get('check', '?')[:40]}")


def cmd_add(args):
    """Add a new DQR issue."""
    dqr = load_dqr(args.file)
    if "issues" not in dqr:
        dqr["issues"] = []

    issue_id = next_id(dqr)
    issue = {
        "id": issue_id,
        "category": args.category,
        "source_object": args.object,
        "source_attribute": args.attribute or "",
        "check": args.check,
        "affected_count": args.affected_count or 0,
        "affected_percent": args.affected_percent or 0,
        "examples": args.examples or "",
        "severity": args.severity,
        "treatment": args.treatment,
        "target_area": args.target_area or "",
        "dmdd_refs": [],
        "status": "open",
        "owner": args.owner or "migration_engineer",
    }
    dqr["issues"].append(issue)
    save_dqr(args.file, dqr)
    print(f"Added {issue_id}: {args.check}")


def cmd_close(args):
    """Close a DQR issue."""
    dqr = load_dqr(args.file)
    issues = dqr.get("issues", [])

    for issue in issues:
        if issue.get("id") == args.id:
            issue["status"] = "closed"
            if args.treatment:
                issue["treatment"] = args.treatment
            save_dqr(args.file, dqr)
            print(f"Closed {args.id} (treatment: {issue['treatment']})")
            return

    print(f"ERROR: Issue {args.id} not found", file=sys.stderr)
    sys.exit(1)


def cmd_open(args):
    """List open issues."""
    dqr = load_dqr(args.file)
    issues = [i for i in dqr.get("issues", []) if i.get("status") == "open"]

    if not issues:
        print("No open DQR issues.")
        return

    for i in issues:
        print(f"[{i['id']}] {i.get('severity', '?').upper()}: "
              f"{i.get('source_object', '?')}.{i.get('source_attribute', '*')} — "
              f"{i.get('check', '?')} (treatment: {i.get('treatment', '?')})")


def main():
    parser = argparse.ArgumentParser(description="DQR issue lifecycle management")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # summary
    p_sum = subparsers.add_parser("summary", help="Print DQR summary")
    p_sum.add_argument("--file", required=True, help="DQR YAML file")

    # add
    p_add = subparsers.add_parser("add", help="Add a new DQR issue")
    p_add.add_argument("--file", required=True, help="DQR YAML file")
    p_add.add_argument("--category", required=True, choices=VALID_CATEGORIES)
    p_add.add_argument("--object", required=True, help="Source object/layer name")
    p_add.add_argument("--attribute", help="Source attribute name")
    p_add.add_argument("--check", required=True, help="Description of the issue")
    p_add.add_argument("--severity", required=True, choices=VALID_SEVERITIES)
    p_add.add_argument("--treatment", required=True, choices=VALID_TREATMENTS)
    p_add.add_argument("--affected-count", type=int, help="Number of affected records")
    p_add.add_argument("--affected-percent", type=float, help="Percentage affected")
    p_add.add_argument("--examples", help="Example values")
    p_add.add_argument("--target-area", help="Target area affected")
    p_add.add_argument("--owner", help="Issue owner")

    # close
    p_close = subparsers.add_parser("close", help="Close a DQR issue")
    p_close.add_argument("--file", required=True, help="DQR YAML file")
    p_close.add_argument("--id", required=True, help="Issue ID (e.g., DQR-001)")
    p_close.add_argument("--treatment", choices=VALID_TREATMENTS, help="Final treatment")

    # open
    p_open = subparsers.add_parser("open", help="List open issues")
    p_open.add_argument("--file", required=True, help="DQR YAML file")

    args = parser.parse_args()

    commands = {
        "summary": cmd_summary,
        "add": cmd_add,
        "close": cmd_close,
        "open": cmd_open,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
