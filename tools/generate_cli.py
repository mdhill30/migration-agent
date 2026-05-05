#!/usr/bin/env python3
"""
generate_cli.py — Generate stage CLI: transform, load, reconcile, and validate output.

Requires: PyYAML, GDAL (for transform subcommands)

Usage:
    python3 generate_cli.py transform --job <job_dir> [--phase N]
    python3 generate_cli.py load --job <job_dir> --db <database> [--phase N]
    python3 generate_cli.py reconcile --job <job_dir> --db <database>
    python3 generate_cli.py env --job <job_dir>
    python3 generate_cli.py schema-check --job <job_dir> --db <database>
"""

import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def resolve_job_dir(job_arg):
    """Resolve job directory path (relative to jobs/ or absolute)."""
    job_path = Path(job_arg)
    if job_path.is_absolute() and job_path.is_dir():
        return job_path

    # Try relative to current dir
    if job_path.is_dir():
        return job_path.resolve()

    # Try under jobs/
    agents_root = Path(__file__).parent.parent
    jobs_path = agents_root / "jobs" / job_arg
    if jobs_path.is_dir():
        return jobs_path

    print(f"ERROR: Job directory not found: {job_arg}", file=sys.stderr)
    sys.exit(1)


def load_migration_yaml(job_dir):
    """Load migration.yaml from job directory."""
    path = job_dir / "migration.yaml"
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return yaml.safe_load(f)


def get_source_dir(job_dir, migration):
    """Determine source data directory."""
    source_location = migration.get("source_location", "source/IQGEO")
    source_dir = job_dir / source_location
    if not source_dir.is_dir():
        print(f"ERROR: Source directory not found: {source_dir}", file=sys.stderr)
        sys.exit(1)
    return source_dir


def get_output_dir(job_dir):
    """Get output data directory."""
    return job_dir / "output" / "data"


def get_scripts_dir(job_dir):
    """Get output scripts directory."""
    return job_dir / "output" / "scripts"


def count_csv_rows(csv_path):
    """Count data rows in a CSV file (excluding header)."""
    if not csv_path.exists():
        return 0
    with open(csv_path) as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        return sum(1 for _ in reader)


def get_csv_fields(csv_path):
    """Get field names from CSV header."""
    if not csv_path.exists():
        return []
    with open(csv_path) as f:
        reader = csv.reader(f)
        header = next(reader, None)
        return header or []


# ─── Commands ─────────────────────────────────────────────────────────────────


def cmd_env(args):
    """Print environment variables needed to run transform scripts."""
    job_dir = resolve_job_dir(args.job)
    migration = load_migration_yaml(job_dir)
    source_dir = get_source_dir(job_dir, migration)
    output_dir = get_output_dir(job_dir)

    prefix = migration.get("prefix", "migration")
    source_var = f"{prefix.upper()}_SOURCE_DIR"
    output_var = f"{prefix.upper()}_OUTPUT_DIR"
    target_var = f"{prefix.upper()}_TARGET_DB"

    print("# Export these before running transform/load scripts:")
    print(f"export {source_var}=\"{source_dir}\"")
    print(f"export {output_var}=\"{output_dir}\"")
    if args.db:
        print(f"export {target_var}=\"{args.db}\"")
    else:
        print(f"export {target_var}=\"<SET_TARGET_DB>\"")
    print()
    print("# Or run with inline env:")
    print(f"# {source_var}=\"{source_dir}\" {output_var}=\"{output_dir}\" bash load.sh --transform-only")


def cmd_transform(args):
    """Run transform scripts to generate CSVs."""
    job_dir = resolve_job_dir(args.job)
    migration = load_migration_yaml(job_dir)
    source_dir = get_source_dir(job_dir, migration)
    output_dir = get_output_dir(job_dir)
    scripts_dir = get_scripts_dir(job_dir)

    load_sh = scripts_dir / "load.sh"
    if not load_sh.exists():
        print(f"ERROR: {load_sh} not found", file=sys.stderr)
        sys.exit(1)

    prefix = migration.get("prefix", "migration")

    env = os.environ.copy()
    env[f"{prefix.upper()}_SOURCE_DIR"] = str(source_dir)
    env[f"{prefix.upper()}_OUTPUT_DIR"] = str(output_dir)

    cmd = ["bash", str(load_sh), "--transform-only"]
    if args.phase:
        cmd.extend(["--phase", str(args.phase)])

    print(f"Running transform (source={source_dir}, output={output_dir})...")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, env=env, cwd=str(scripts_dir))
    sys.exit(result.returncode)


def cmd_load(args):
    """Load generated CSVs into target database."""
    job_dir = resolve_job_dir(args.job)
    migration = load_migration_yaml(job_dir)
    source_dir = get_source_dir(job_dir, migration)
    output_dir = get_output_dir(job_dir)
    scripts_dir = get_scripts_dir(job_dir)

    if not args.db:
        print("ERROR: --db is required for load", file=sys.stderr)
        sys.exit(1)

    load_sh = scripts_dir / "load.sh"
    if not load_sh.exists():
        print(f"ERROR: {load_sh} not found", file=sys.stderr)
        sys.exit(1)

    prefix = migration.get("prefix", "migration")

    env = os.environ.copy()
    env[f"{prefix.upper()}_SOURCE_DIR"] = str(source_dir)
    env[f"{prefix.upper()}_OUTPUT_DIR"] = str(output_dir)
    env[f"{prefix.upper()}_TARGET_DB"] = args.db

    cmd = ["bash", str(load_sh), "--load-only"]
    if args.phase:
        cmd.extend(["--phase", str(args.phase)])

    print(f"Loading into {args.db} (output={output_dir})...")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, env=env, cwd=str(scripts_dir))
    sys.exit(result.returncode)


def cmd_reconcile(args):
    """Reconcile generated CSV row counts against source and loaded counts."""
    job_dir = resolve_job_dir(args.job)
    migration = load_migration_yaml(job_dir)
    output_dir = get_output_dir(job_dir)

    dmdd_path = job_dir / "dmdd.yaml"
    if not dmdd_path.exists():
        print(f"ERROR: {dmdd_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(dmdd_path) as f:
        dmdd = yaml.safe_load(f)

    # Build source count index from object inventory
    source_counts = {}
    for obj in dmdd.get("object_inventory", []):
        source_counts[obj["feature"]] = obj.get("count", 0)

    # Check generated CSV counts
    print("=" * 72)
    print("  RECONCILIATION REPORT")
    print("=" * 72)
    print()
    print(f"{'Feature':<30} {'Source':>8} {'Generated':>10} {'Status':<12}")
    print("-" * 72)

    csv_files = sorted(output_dir.glob("*.csv")) if output_dir.exists() else []
    total_generated = 0

    for csv_path in csv_files:
        feature_name = csv_path.stem
        row_count = count_csv_rows(csv_path)
        total_generated += row_count

        # Try to match to a source layer
        status = "OK"
        source_count = ""

        print(f"{feature_name:<30} {source_count:>8} {row_count:>10} {status:<12}")

    print("-" * 72)
    print(f"{'TOTAL':<30} {'':>8} {total_generated:>10}")
    print()

    # Show expected vs actual for known mappings from DMDD object_mapping
    obj_mappings = dmdd.get("object_mapping", [])
    if obj_mappings:
        print("Object Mapping Coverage:")
        print(f"{'Target Feature':<30} {'Source Layer':<35} {'Source Count':>12}")
        print("-" * 72)
        for m in obj_mappings:
            iqgeo = m.get("iqgeo_features", {})
            source = m.get("source_mapping", {})
            target = iqgeo.get("internal_name", "?")
            src_layer = source.get("table_layer", "?")
            src_count = source_counts.get(src_layer, "?")
            print(f"{target:<30} {src_layer:<35} {str(src_count):>12}")
        print()

    # If db provided, also query loaded counts
    if args.db:
        print(f"Database counts (from {args.db}):")
        print(f"{'Feature':<30} {'DB Count':>10}")
        print("-" * 72)
        for csv_path in csv_files:
            feature_name = csv_path.stem
            try:
                result = subprocess.run(
                    ["myw_db", args.db, "info", "feature", feature_name],
                    capture_output=True, text=True, timeout=30,
                )
                # Parse count from output if available
                print(f"{feature_name:<30} {'(run myw_db info)':>10}")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                print(f"{feature_name:<30} {'ERROR':>10}")
        print()


def cmd_schema_check(args):
    """Check which CSV fields exist in the target database schema."""
    job_dir = resolve_job_dir(args.job)
    output_dir = get_output_dir(job_dir)

    if not args.db:
        print("ERROR: --db is required for schema-check", file=sys.stderr)
        sys.exit(1)

    if not output_dir.exists():
        print(f"ERROR: Output directory not found: {output_dir}", file=sys.stderr)
        sys.exit(1)

    csv_files = sorted(output_dir.glob("*.csv"))
    if not csv_files:
        print("No CSV files found in output directory.")
        return

    print("=" * 72)
    print("  SCHEMA COMPATIBILITY CHECK")
    print("=" * 72)
    print()
    print(f"Target DB: {args.db}")
    print(f"Output dir: {output_dir}")
    print()

    all_warnings = []

    for csv_path in csv_files:
        feature_name = csv_path.stem
        csv_fields = get_csv_fields(csv_path)

        if not csv_fields:
            continue

        # Query schema from myw_db
        try:
            result = subprocess.run(
                ["myw_db", args.db, "info", "feature", feature_name],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                print(f"  {feature_name}: FEATURE NOT IN SCHEMA")
                all_warnings.append((feature_name, csv_fields, "feature_missing"))
                continue

            # Parse fields from info output
            schema_fields = set()
            for line in result.stdout.splitlines():
                line = line.strip()
                if line and not line.startswith(("Feature", "=", "-", "Geometry")):
                    # Field lines typically start with the field name
                    parts = line.split()
                    if parts:
                        schema_fields.add(parts[0])

            missing = [f for f in csv_fields if f not in schema_fields and f not in ("location", "path", "boundary")]
            if missing:
                print(f"  {feature_name}: MISSING fields → {', '.join(missing)}")
                all_warnings.append((feature_name, missing, "fields_missing"))
            else:
                print(f"  {feature_name}: OK ({len(csv_fields)} fields)")

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"  {feature_name}: ERROR ({e})")

    if all_warnings:
        print()
        print("─" * 72)
        print("ACTIONS REQUIRED:")
        print()
        for feature, fields, issue_type in all_warnings:
            if issue_type == "feature_missing":
                print(f"  • {feature}: Create .def file with all fields")
            else:
                print(f"  • {feature}: Add fields to .def: {', '.join(fields)}")
        print()
        print("Fields will be SILENTLY DROPPED during myw_db load if not in schema.")


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Generate stage CLI — transform, load, and reconcile migration data."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # env
    p_env = subparsers.add_parser("env", help="Print environment variables for scripts")
    p_env.add_argument("--job", required=True, help="Job directory name or path")
    p_env.add_argument("--db", help="Target database name")

    # transform
    p_transform = subparsers.add_parser("transform", help="Run transform scripts")
    p_transform.add_argument("--job", required=True, help="Job directory name or path")
    p_transform.add_argument("--phase", type=int, help="Run only specific phase (1-6)")

    # load
    p_load = subparsers.add_parser("load", help="Load CSVs into target database")
    p_load.add_argument("--job", required=True, help="Job directory name or path")
    p_load.add_argument("--db", required=True, help="Target database name")
    p_load.add_argument("--phase", type=int, help="Run only specific phase (1-6)")

    # reconcile
    p_reconcile = subparsers.add_parser("reconcile", help="Reconcile row counts")
    p_reconcile.add_argument("--job", required=True, help="Job directory name or path")
    p_reconcile.add_argument("--db", help="Target database name (optional, adds DB counts)")

    # schema-check
    p_schema = subparsers.add_parser("schema-check", help="Check CSV fields vs DB schema")
    p_schema.add_argument("--job", required=True, help="Job directory name or path")
    p_schema.add_argument("--db", required=True, help="Target database name")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "env": cmd_env,
        "transform": cmd_transform,
        "load": cmd_load,
        "reconcile": cmd_reconcile,
        "schema-check": cmd_schema_check,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
