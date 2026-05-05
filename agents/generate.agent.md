---
description: Generate migration artefacts and load them into the target database
user-invocable: false
tools:
  - run_in_terminal
  - read_file
  - replace_string_in_file
  - create_file
  - vscode_askQuestions
---

# Generate Agent

You produce migration artefacts from the approved DMDD and load them into the target database. This stage covers both artefact generation (structural transformation logic, `.def` files, load scripts) and the supervised database load.

## Responsibilities

- Generate `.def` files from templates using approved mappings
- Apply value mappings from `AttrVal-*` sheets
- Apply agreed `fix_in_flight` DQR treatments
- Generate synthetic data (dummy structures, routes, fiber segments) where needed
- Emit `myw_db` load scripts
- **Execute containment rules** — assign `root_housing` and `housing` references per approved `containment_rules`
- **Execute cable segmentation** — split source cables into NMT cable_segment chains per `topology_construction` rules
- **Derive routes** — create route objects between structures per `topology_construction.route_derivation`
- **Generate internal cable segments** — create segments at structure crossings to maintain cable continuity
- **Build connection records** — produce NMT connection records per `connectivity_mapping` rules
- **Set geometry inheritance** — ensure contained objects inherit geometry from their housing (do not write independent geometry)
- **Generate synthetic objects** — create dummy structures, routes, and internal segments per `containment_rules.synthetic_generation`

## Execution Phases

Topology construction requires ordered execution:

1. **Phase 1 — Structures**: Load/create all structure objects (including synthetics)
2. **Phase 2 — Routes**: Load/derive routes between structures, set start/end_structure FKs
3. **Phase 3 — Conduits**: Load conduits into routes (if applicable)
4. **Phase 4 — Cable Segmentation**: Segment cables, assign root_housing, link prev/next, set forward flag
5. **Phase 5 — Equipment**: Load equipment, assign root_housing via containment rules
6. **Phase 6 — Connections**: Build connection records from connectivity mapping

Each phase depends on the previous — structures must exist before routes reference them, routes before cable segments are housed in them, etc.

## Outputs

- `.def` files in `output/`
- Value mapping configuration
- Synthetic data generation scripts (dummy structures, internal segments, derived routes)
- `myw_db` load scripts
- Topology construction log (decisions made, synthetic objects created, confidence scores)
- Load execution log with per-step status
- Feature-level row count summary (attempted/loaded/failed)
- Build report with blockers and retry guidance
- Updated handoff notes for downstream `validate`

## Behaviour

- Only generate from **approved** DMDD mappings (status = Approved)
- Use templates from `templates/` directory
- Apply transformations defined in DMDD transformation columns
- Reference `migration.yaml` for prefix, CRS, and policy settings
- Execute structural rules per `relationship_mapping`, `containment_rules`, `topology_construction`, `connectivity_mapping`
- Generate is mechanical — if DMDD is correct, output should be correct
- **Log all synthetic object creation** with reasons and confidence scores
- **Fail loudly** if a containment rule cannot be satisfied (e.g., no structure within proximity radius) — create DQR issue rather than silently skipping
- **Human gate before database writes** — confirm with the engineer before executing any `myw_db load` commands
- Execute load scripts in phase order; stop on blocker load errors and report the exact failing step
- Capture per-feature row counts; surface mismatches between generated rows and loaded rows
- Do not re-apply transformations during load — consume generated artefacts as-is

## myw_db Load CLI Reference

**CRITICAL**: The correct `myw_db` load syntax is:

```bash
myw_db <database_name> load <file_path>
```

- Feature type is **inferred from the CSV filename** (e.g., `pole.csv` → loads into `pole` feature type)
- Do NOT pass `data` or the feature type as positional arguments
- Fields in the CSV that don't exist in the target schema are **silently dropped** with a warning like: `***Warning*** <feature> does not contain the following fields: field1, field2`
- This means the .def schema must already include any custom fields (e.g., `external_ref`, `myw_source_id`) before loading — otherwise data is lost

**Example — correct**:
```bash
myw_db zayo_db load /path/to/output/data/pole.csv
```

**Example — WRONG** (produces "No such feature type: data" errors):
```bash
myw_db zayo_db load data pole /path/to/output/data/pole.csv
```

## Environment Variables for Transform Scripts

Transform scripts accept these environment variables:

| Variable | Purpose | Example |
|----------|---------|---------|
| `SUMMIT_SOURCE_DIR` | Path to source shapefiles | `jobs/summit_fiber/source/IQGEO` |
| `SUMMIT_OUTPUT_DIR` | Path to write output CSVs | `jobs/summit_fiber/output/data` |
| `SUMMIT_TARGET_DB` | Target database name | `zayo_db` |

**Always set these explicitly** — default paths in scripts may be stale.

## Key Learnings

### Schema Field Warnings

When `myw_db load` reports fields not in the schema, this means:
1. Records are still inserted (geometry + recognized fields)
2. Unrecognized field data is **permanently lost** from the load
3. To fix: add missing fields to `.def` files and reinstall schema before reloading

Fields commonly missing from base NMT schema:
- `external_ref` — source system ID (e.g., MSLINK)
- `myw_source_id` — source system UUID (e.g., DEV_ID)
- `manufacturer`, `model`, `owner` — equipment metadata
- `description` — free-text description
- `root_housing_ref` — equipment→structure FK reference
- `in_structure_ref`, `out_structure_ref` — route endpoint FKs

### Containment / Housing Assignment

- Spatial proximity search uses source CRS units (e.g., US Survey Feet for EPSG:2236)
- 10m ≈ 32.8 US Survey Feet — use `PROXIMITY_RADIUS_FT = 32.8`
- Typical unhoused rates: 29–35% for equipment in sparse networks
- Structure spatial index should include POLEPED, CABINET, HEADEND, FIBERNODE but **exclude** equipment layers (splice enclosures are not valid housing parents)
- Unhoused equipment → DQR issue with `needs_decision` treatment; options include expanding radius, creating synthetic structures, or accepting unhoused

### Route Endpoint Resolution

- STRAND.LINK1/LINK2 reference structure MSLINKs
- Build a combined MSLINK index across all structure layers (including splice enclosures for reference, but they are not route endpoints)
- Orphan rate of 50%+ indicates missing source layers or references to deleted records outside the extract
- Orphaned route endpoints → leave `in_structure`/`out_structure` null; flag in DQR

### CRS Handling

- Source data in projected CRS (e.g., EPSG:2236 FL State Plane East) must be reprojected to EPSG:4326 for NMT
- Use `osr.OAMS_TRADITIONAL_GIS_ORDER` on **both** source and target SRS to avoid axis-order issues
- Output geometry as EWKT: `SRID=4326;POINT(lon lat)` or `SRID=4326;LINESTRING(...)`
- US Survey Feet conversion factor: `0.3048006096012192` (NOT international feet `0.3048`)

### Load Script Orchestration

The `load.sh` script supports three modes:
- `--transform-only` — run Python transforms, produce CSVs, no database writes
- `--load-only` — skip transforms, load existing CSVs into database
- `--phase N` — run only phase N (1–6)
- No flags — full pipeline (transform + load)

Always run `--transform-only` first to verify CSV output before loading.
