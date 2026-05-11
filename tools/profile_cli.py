#!/usr/bin/env python3
"""
profile_cli.py — Schema inference, value profiling, null analysis, DMDD inventory generation.

Requires: GDAL (ogrinfo on PATH), PyYAML

Usage:
    python3 profile_cli.py schema --source <dir_or_file> [--format shapefile|gdb|csv|gpkg]
    python3 profile_cli.py values --source <shp_file> --field <FIELD> [--top 25]
    python3 profile_cli.py nulls --source <dir> --fields <comma_separated>
    python3 profile_cli.py inventory --source <dir> --output <dmdd.yaml>
    python3 profile_cli.py crs --source <dir>
"""

import argparse
import collections
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

# Fields that are system/OGC overhead — excluded from attribute inventory
SYSTEM_FIELDS = {
    "X_OGC_GEOM", "Y_OGC_GEOM", "Z_OGC_GEOM",
    "XScale_OGC", "YScale_OGC", "ZScale_OGC",
    "Rotation_O", "XFM_ID",
}

# Fields included but flagged as "No" (redundant coordinates / audit)
REDUNDANT_FIELDS = {
    "COORD_X", "COORD_Y", "LATCOORD", "LONCOORD",
    "CREATEDBY", "UPDATEDBY", "UPDATEDVER",
}


def run_ogrinfo(args, capture=True):
    """Run ogrinfo with given arguments, return stdout."""
    cmd = ["ogrinfo"] + args
    result = subprocess.run(cmd, capture_output=capture, text=True)
    if result.returncode != 0:
        print(f"ERROR: ogrinfo failed: {result.stderr}", file=sys.stderr)
        return ""
    return result.stdout


def find_layers(source_dir, fmt="shapefile"):
    """Find all layers in a source directory."""
    if fmt == "shapefile":
        return sorted(glob.glob(os.path.join(source_dir, "*.shp")))
    elif fmt == "gdb":
        # For GDB, list layers via ogrinfo
        output = run_ogrinfo([source_dir])
        layers = re.findall(r"^\d+: (\S+)", output, re.MULTILINE)
        return layers
    elif fmt == "csv":
        return sorted(glob.glob(os.path.join(source_dir, "*.csv")))
    elif fmt == "gpkg":
        # For GeoPackage, find .gpkg files and list their layers via ogrinfo
        gpkg_files = sorted(glob.glob(os.path.join(source_dir, "*.gpkg")))
        layers = []
        for gpkg in gpkg_files:
            output = run_ogrinfo([gpkg])
            for match in re.finditer(r"^\d+: (\S+)", output, re.MULTILINE):
                layers.append((gpkg, match.group(1)))
        return layers
    return []


def get_layer_name(shp_path):
    """Extract layer name from shapefile path."""
    return Path(shp_path).stem


def profile_schema(source_path, layer_name=None):
    """Profile a single layer: geometry, count, fields.
    
    For shapefiles: source_path is the .shp file, layer_name is derived from filename.
    For gpkg/gdb: source_path is the container file, layer_name must be provided.
    """
    if layer_name is None:
        layer_name = get_layer_name(source_path)
    output = run_ogrinfo(["-so", source_path, layer_name])

    info = {
        "name": layer_name,
        "path": source_path,
        "geometry": None,
        "count": 0,
        "fields": [],
    }

    for line in output.split("\n"):
        if line.startswith("Geometry:"):
            info["geometry"] = line.split(":", 1)[1].strip()
        elif line.startswith("Feature Count:"):
            info["count"] = int(line.split(":", 1)[1].strip())
        elif ": " in line and not line.startswith(" ") and not line.startswith("INFO"):
            # Field definition line: "FIELDNAME: Type (width.precision)"
            match = re.match(r"^([A-Za-z_][A-Za-z_0-9]*): (.+)$", line)
            if match:
                field_name = match.group(1)
                field_type = match.group(2).strip()
                info["fields"].append({
                    "name": field_name,
                    "type": field_type,
                })

    return info


def profile_values(shp_path, field_name, top=25):
    """Get value distribution for a specific field in a layer."""
    layer_name = get_layer_name(shp_path)
    output = run_ogrinfo(["-q", shp_path, "-sql",
                          f"SELECT {field_name} FROM {layer_name}"])

    values = []
    for line in output.split("\n"):
        if field_name in line and "=" in line:
            val = line.split("=", 1)[1].strip()
            values.append(val)

    counter = collections.Counter(values)
    results = {
        "layer": layer_name,
        "field": field_name,
        "total_records": len(values),
        "distinct_values": len(counter),
        "distribution": [
            {"value": val, "count": cnt}
            for val, cnt in counter.most_common(top)
        ],
    }
    return results


def profile_nulls(source_dir, fields, fmt="shapefile"):
    """Check null rates for specified fields across all layers."""
    layers = find_layers(source_dir, fmt)
    results = []

    for shp_path in layers:
        layer_name = get_layer_name(shp_path)
        schema = profile_schema(shp_path)
        layer_fields = {f["name"] for f in schema["fields"]}

        for field in fields:
            if field not in layer_fields:
                continue

            output = run_ogrinfo(["-q", shp_path, "-sql",
                                  f'SELECT {field} FROM "{layer_name}" WHERE {field} IS NULL'])
            null_count = output.count("OGRFeature")
            total = schema["count"]

            results.append({
                "layer": layer_name,
                "field": field,
                "null_count": null_count,
                "total": total,
                "null_percent": round(100 * null_count / total, 1) if total > 0 else 0,
            })

    return results


def detect_crs(source_dir):
    """Read CRS from .prj files in the source directory."""
    prj_files = glob.glob(os.path.join(source_dir, "*.prj"))
    if not prj_files:
        return {"error": "No .prj files found"}

    # Read first .prj file
    prj_path = prj_files[0]
    with open(prj_path, "r") as f:
        wkt = f.read().strip()

    # Extract key parameters
    info = {
        "prj_file": os.path.basename(prj_path),
        "wkt_snippet": wkt[:200],
        "all_prj_files": [os.path.basename(p) for p in prj_files],
    }

    # Try to identify EPSG
    if "FL83-EF" in wkt or ("Central_Meridian\",-81" in wkt and "Latitude_Of_Origin\",24.33" in wkt):
        info["likely_epsg"] = "EPSG:2236"
        info["description"] = "Florida State Plane East (NAD83), US Survey Feet"
    elif "FL83-WF" in wkt or ("Central_Meridian\",-82" in wkt and "Latitude_Of_Origin\",24.33" in wkt):
        info["likely_epsg"] = "EPSG:2237"
        info["description"] = "Florida State Plane West (NAD83), US Survey Feet"

    # Detect units
    if "Foot" in wkt:
        info["units"] = "US Survey Feet"
    elif "Meter" in wkt or "metre" in wkt:
        info["units"] = "Meters"

    return info


def generate_inventory(source_dir, fmt="shapefile"):
    """Generate DMDD object and attribute inventories."""
    layers = find_layers(source_dir, fmt)
    object_inventory = []
    attribute_inventory = []

    for layer in layers:
        if isinstance(layer, tuple):
            schema = profile_schema(layer[0], layer[1])
        else:
            schema = profile_schema(layer)

        # Determine include flag
        include = "Yes"
        if schema["count"] < 10 and schema["geometry"] == "Point":
            include = "Pending Review"
        # Heuristic: annotation/text/reference layers
        name_lower = schema["name"].lower()
        if any(kw in name_lower for kw in ["text", "streetname", "waterline"]):
            include = "No"

        object_inventory.append({
            "feature": schema["name"],
            "geometry": schema["geometry"],
            "count": schema["count"],
            "include_in_mapping": include,
        })

        # Attribute inventory (exclude system fields)
        for field in schema["fields"]:
            if field["name"] in SYSTEM_FIELDS:
                continue

            attr_include = "Yes"
            if field["name"] in REDUNDANT_FIELDS:
                attr_include = "No"
            elif include == "No":
                continue  # Skip attributes for excluded layers

            attribute_inventory.append({
                "feature": schema["name"],
                "attribute": field["name"],
                "data_type": field["type"],
                "include_in_mapping": attr_include,
            })

    return {
        "object_inventory": object_inventory,
        "attribute_inventory": attribute_inventory,
    }


def cmd_schema(args):
    """Handle 'schema' subcommand."""
    source = args.source
    fmt = args.format

    if os.path.isfile(source):
        # Single file
        info = profile_schema(source)
        print(json.dumps(info, indent=2))
    else:
        # Directory
        layers = find_layers(source, fmt)
        print(f"Found {len(layers)} layers in {source}\n")
        print(f"{'Layer':<40} {'Geometry':<15} {'Count':>8}  Fields")
        print("-" * 90)
        for layer in layers:
            if isinstance(layer, tuple):
                info = profile_schema(layer[0], layer[1])
            else:
                info = profile_schema(layer)
            field_names = [f["name"] for f in info["fields"] if f["name"] not in SYSTEM_FIELDS]
            print(f"{info['name']:<40} {info['geometry'] or 'None':<15} {info['count']:>8}  {', '.join(field_names[:6])}")
            if len(field_names) > 6:
                print(f"{'':>65}  ...+{len(field_names)-6} more")


def cmd_values(args):
    """Handle 'values' subcommand."""
    results = profile_values(args.source, args.field, args.top)
    print(f"Layer: {results['layer']}")
    print(f"Field: {results['field']}")
    print(f"Total records: {results['total_records']}")
    print(f"Distinct values: {results['distinct_values']}")
    print(f"\nTop {args.top} values:")
    print(f"  {'Value':<40} {'Count':>8}")
    print(f"  {'-'*40} {'-'*8}")
    for item in results["distribution"]:
        print(f"  {item['value']:<40} {item['count']:>8}")


def cmd_nulls(args):
    """Handle 'nulls' subcommand."""
    fields = [f.strip() for f in args.fields.split(",")]
    results = profile_nulls(args.source, fields, args.format)
    print(f"{'Layer':<35} {'Field':<15} {'Nulls':>8} {'Total':>8} {'%':>6}")
    print("-" * 75)
    for r in results:
        print(f"{r['layer']:<35} {r['field']:<15} {r['null_count']:>8} {r['total']:>8} {r['null_percent']:>5.1f}%")


def cmd_crs(args):
    """Handle 'crs' subcommand."""
    info = detect_crs(args.source)
    print(json.dumps(info, indent=2))


def cmd_inventory(args):
    """Handle 'inventory' subcommand."""
    inventory = generate_inventory(args.source, args.format)

    if args.output and yaml:
        # Write to YAML
        with open(args.output, "r") as f:
            dmdd = yaml.safe_load(f) or {}
        dmdd["object_inventory"] = inventory["object_inventory"]
        dmdd["attribute_inventory"] = inventory["attribute_inventory"]
        with open(args.output, "w") as f:
            yaml.dump(dmdd, f, default_flow_style=False, sort_keys=False, width=120)
        print(f"Updated {args.output} with {len(inventory['object_inventory'])} objects, "
              f"{len(inventory['attribute_inventory'])} attributes")
    else:
        # Print JSON
        print(json.dumps(inventory, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Profile source data for NMT migration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # schema
    p_schema = subparsers.add_parser("schema", help="Infer schemas from source layers")
    p_schema.add_argument("--source", required=True, help="Source directory or file")
    p_schema.add_argument("--format", default="shapefile", choices=["shapefile", "gdb", "csv", "gpkg"])

    # values
    p_values = subparsers.add_parser("values", help="Profile value distributions")
    p_values.add_argument("--source", required=True, help="Source shapefile")
    p_values.add_argument("--field", required=True, help="Field name to profile")
    p_values.add_argument("--top", type=int, default=25, help="Number of top values")

    # nulls
    p_nulls = subparsers.add_parser("nulls", help="Check null rates across layers")
    p_nulls.add_argument("--source", required=True, help="Source directory")
    p_nulls.add_argument("--fields", required=True, help="Comma-separated field names")
    p_nulls.add_argument("--format", default="shapefile", choices=["shapefile", "gdb", "csv", "gpkg"])

    # crs
    p_crs = subparsers.add_parser("crs", help="Detect CRS from .prj files")
    p_crs.add_argument("--source", required=True, help="Source directory")

    # inventory
    p_inv = subparsers.add_parser("inventory", help="Generate DMDD inventory")
    p_inv.add_argument("--source", required=True, help="Source directory")
    p_inv.add_argument("--output", help="Output DMDD YAML file (updates in place)")
    p_inv.add_argument("--format", default="shapefile", choices=["shapefile", "gdb", "csv", "gpkg"])

    args = parser.parse_args()

    commands = {
        "schema": cmd_schema,
        "values": cmd_values,
        "nulls": cmd_nulls,
        "crs": cmd_crs,
        "inventory": cmd_inventory,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
