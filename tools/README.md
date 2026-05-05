# Tools

Python CLI tools for compute-heavy migration operations. All tools use `argparse` with subcommands.

## Prerequisites

- **GDAL** (`ogrinfo` on PATH) — for shapefile/GDB/spatial format access
- **PyYAML** — for DMDD/DQR YAML operations

## Implemented Tools

### `profile_cli.py` — Schema inference, value profiling, null analysis

Crawls source data directories to extract schemas, field types, value distributions, and null rates. Produces machine-readable output for DMDD population.

```bash
# Overview of all layers in a directory
python3 tools/profile_cli.py schema --source source/IQGEO --format shapefile

# Value distribution for a specific coded field
python3 tools/profile_cli.py values --source source/IQGEO/SUMMIT_FIBERSPAN.shp --field MODEL --top 25

# Null rate analysis across layers
python3 tools/profile_cli.py nulls --source source/IQGEO --fields DEV_ID,NAME,DESCR

# Detect CRS from .prj files
python3 tools/profile_cli.py crs --source source/IQGEO

# Generate DMDD object/attribute inventory and update YAML
python3 tools/profile_cli.py inventory --source source/IQGEO --output dmdd.yaml
```

### `dmdd_cli.py` — DMDD YAML operations

Validates, summarizes, and manipulates the DMDD YAML file.

```bash
# Summary of DMDD contents
python3 tools/dmdd_cli.py summary --file dmdd.yaml

# Validate DMDD structure (errors + warnings)
python3 tools/dmdd_cli.py validate --file dmdd.yaml

# Detailed statistics table
python3 tools/dmdd_cli.py stats --file dmdd.yaml

# Add a new object to inventory
python3 tools/dmdd_cli.py add-object --file dmdd.yaml --feature LAYER_NAME --geometry Point --count 500
```

### `dqr_cli.py` — Data Quality Review issue lifecycle

Manages DQR issues: add, close, summarize, list open.

```bash
# Summary with severity/treatment breakdown
python3 tools/dqr_cli.py summary --file dqr.yaml

# List open issues
python3 tools/dqr_cli.py open --file dqr.yaml

# Add a new issue
python3 tools/dqr_cli.py add --file dqr.yaml \
    --category coded_values --object SUMMIT_POLEPED --attribute LOCATION \
    --check "Numeric codes have unknown meaning" \
    --severity medium --treatment needs_decision

# Close an issue with final treatment
python3 tools/dqr_cli.py close --file dqr.yaml --id DQR-001 --treatment accept_ignore
```

## Planned Tools

- `generate_cli.py` — .def file generation, value mappings, load scripts
- `validate_cli.py` — NMT validation engine wrapper
- `reconcile_cli.py` — source-vs-target count reconciliation
