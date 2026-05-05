#!/usr/bin/env python3
"""
dmdd_cli.py — DMDD YAML operations: validate, diff, merge, summary.

Requires: PyYAML

Usage:
    python3 dmdd_cli.py summary --file <dmdd.yaml>
    python3 dmdd_cli.py validate --file <dmdd.yaml>
    python3 dmdd_cli.py add-object --file <dmdd.yaml> --feature <name> --geometry <type> --count <n>
    python3 dmdd_cli.py stats --file <dmdd.yaml>
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def load_dmdd(filepath):
    """Load DMDD YAML file."""
    with open(filepath, "r") as f:
        return yaml.safe_load(f) or {}


def save_dmdd(filepath, dmdd):
    """Save DMDD YAML file."""
    with open(filepath, "w") as f:
        yaml.dump(dmdd, f, default_flow_style=False, sort_keys=False, width=120)


def cmd_summary(args):
    """Print DMDD summary."""
    dmdd = load_dmdd(args.file)
    summary = dmdd.get("summary", {})
    obj_inv = dmdd.get("object_inventory", [])
    attr_inv = dmdd.get("attribute_inventory", [])
    obj_map = dmdd.get("object_mapping", [])
    attr_map = dmdd.get("attribute_mapping", [])

    print(f"DMDD: {summary.get('customer', 'Unknown')} ({summary.get('date', 'Unknown')})")
    print(f"Vendor: {summary.get('vendor', 'Unknown')}")
    print()
    print(f"Object Inventory:    {len(obj_inv)} layers")
    print(f"Attribute Inventory: {len(attr_inv)} attributes")
    print(f"Object Mappings:     {len(obj_map)} mappings")
    print(f"Attribute Mappings:  {len(attr_map)} mappings")

    if obj_inv:
        total_features = sum(o.get("count", 0) for o in obj_inv)
        included = sum(1 for o in obj_inv if o.get("include_in_mapping") == "Yes")
        excluded = sum(1 for o in obj_inv if o.get("include_in_mapping") == "No")
        pending = sum(1 for o in obj_inv if o.get("include_in_mapping") == "Pending Review")
        print(f"\nTotal source features: {total_features:,}")
        print(f"Layers: {included} included, {excluded} excluded, {pending} pending review")


def cmd_validate(args):
    """Validate DMDD structure and completeness."""
    dmdd = load_dmdd(args.file)
    errors = []
    warnings = []

    # Check required sections
    if not dmdd.get("summary"):
        errors.append("Missing 'summary' section")
    if not dmdd.get("object_inventory"):
        errors.append("Missing 'object_inventory' section")

    # Validate object inventory entries
    for i, obj in enumerate(dmdd.get("object_inventory", [])):
        if not obj.get("feature"):
            errors.append(f"object_inventory[{i}]: missing 'feature' name")
        if not obj.get("geometry"):
            warnings.append(f"object_inventory[{i}] ({obj.get('feature', '?')}): missing 'geometry'")
        if obj.get("include_in_mapping") not in ("Yes", "No", "Pending Review"):
            warnings.append(f"object_inventory[{i}] ({obj.get('feature', '?')}): "
                          f"invalid include_in_mapping: {obj.get('include_in_mapping')}")

    # Validate attribute inventory entries
    for i, attr in enumerate(dmdd.get("attribute_inventory", [])):
        if not attr.get("feature"):
            errors.append(f"attribute_inventory[{i}]: missing 'feature' name")
        if not attr.get("attribute"):
            errors.append(f"attribute_inventory[{i}]: missing 'attribute' name")

    # Check referential integrity: attributes reference valid objects
    obj_names = {o.get("feature") for o in dmdd.get("object_inventory", [])}
    for i, attr in enumerate(dmdd.get("attribute_inventory", [])):
        if attr.get("feature") and attr["feature"] not in obj_names:
            warnings.append(f"attribute_inventory[{i}]: feature '{attr['feature']}' "
                          f"not found in object_inventory")

    # Report
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  ✗ {e}")
    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  ⚠ {w}")
    if not errors and not warnings:
        print("✓ DMDD is valid")

    return len(errors)


def cmd_stats(args):
    """Print detailed statistics from DMDD."""
    dmdd = load_dmdd(args.file)
    obj_inv = dmdd.get("object_inventory", [])
    attr_inv = dmdd.get("attribute_inventory", [])

    print("Object Inventory:")
    print(f"  {'Layer':<40} {'Geometry':<15} {'Count':>8} {'Include':<15}")
    print(f"  {'-'*40} {'-'*15} {'-'*8} {'-'*15}")
    for obj in obj_inv:
        print(f"  {obj.get('feature', '?'):<40} {obj.get('geometry', '?'):<15} "
              f"{obj.get('count', 0):>8} {obj.get('include_in_mapping', '?'):<15}")

    print(f"\nAttribute Inventory ({len(attr_inv)} attributes):")
    # Group by feature
    by_feature = {}
    for attr in attr_inv:
        feat = attr.get("feature", "?")
        by_feature.setdefault(feat, []).append(attr)

    for feat, attrs in by_feature.items():
        included = sum(1 for a in attrs if a.get("include_in_mapping") == "Yes")
        print(f"  {feat}: {len(attrs)} attributes ({included} included)")


def cmd_add_object(args):
    """Add an object to the inventory."""
    dmdd = load_dmdd(args.file)
    if "object_inventory" not in dmdd:
        dmdd["object_inventory"] = []

    entry = {
        "feature": args.feature,
        "geometry": args.geometry,
        "count": args.count,
        "include_in_mapping": args.include or "Pending Review",
    }
    dmdd["object_inventory"].append(entry)
    save_dmdd(args.file, dmdd)
    print(f"Added {args.feature} to object_inventory")


def main():
    parser = argparse.ArgumentParser(description="DMDD YAML operations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # summary
    p_sum = subparsers.add_parser("summary", help="Print DMDD summary")
    p_sum.add_argument("--file", required=True, help="DMDD YAML file")

    # validate
    p_val = subparsers.add_parser("validate", help="Validate DMDD structure")
    p_val.add_argument("--file", required=True, help="DMDD YAML file")

    # stats
    p_stats = subparsers.add_parser("stats", help="Detailed statistics")
    p_stats.add_argument("--file", required=True, help="DMDD YAML file")

    # add-object
    p_add = subparsers.add_parser("add-object", help="Add object to inventory")
    p_add.add_argument("--file", required=True, help="DMDD YAML file")
    p_add.add_argument("--feature", required=True, help="Feature/layer name")
    p_add.add_argument("--geometry", required=True, help="Geometry type")
    p_add.add_argument("--count", type=int, required=True, help="Feature count")
    p_add.add_argument("--include", help="Include flag (Yes/No/Pending Review)")

    args = parser.parse_args()

    commands = {
        "summary": cmd_summary,
        "validate": cmd_validate,
        "stats": cmd_stats,
        "add-object": cmd_add_object,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
