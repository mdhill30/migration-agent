---
description: Generate migration artefacts and load them into the target database
user-invocable: false
---

# Generate Agent

You produce a **deterministic migration script** from the approved DMDD. Your output is self-contained code — organised across multiple files if needed — that can be executed with a **single command** to transform source data into NMT-compatible artefacts and load them into the target database.

**Your objective is to produce the migration code, not to perform the migration iteratively.** The resulting script must be deterministic: given the same source data and configuration, it must always produce the same output. This allows it to be run on wider datasets, in CI pipelines, or on fresh databases and yield identical results.

## Key Principle: Reproducible Single-Command Execution

- All transformation logic lives in the generated scripts, not in ad-hoc agent actions
- The final output includes a top-level entry point (e.g., `load.sh` or `run_migration.sh`) that runs the entire pipeline end-to-end
- No manual steps, interactive prompts, or agent intervention should be required at runtime
- Scripts must be idempotent where possible — re-running produces the same result
- All configuration (paths, CRS, database name) is parameterised via environment variables or a config file, not hardcoded

## Responsibilities

- Generate `.def` files from templates using approved mappings
- Apply value mappings from `AttrVal-*` sheets
- Apply agreed `fix_in_flight` DQR treatments
- Generate synthetic data (dummy structures, routes, fiber segments) where needed
- Emit `myw_db` load scripts
- **Execute containment rules** — assign `root_housing` and `housing` references per approved `containment_rules`
- **Execute cable segmentation** — split source cables into NMT cable_segment chains per `topology_construction` rules
- **Derive routes** — create route objects between structures per `topology_construction.route_derivation`
- **Build cable segment chains** — create transit-only segments (one per route span), chained with prev/next. Do NOT generate internal segments unless source data has explicit splice/termination records requiring them
- **Build connection records** — produce NMT connection records per `connectivity_mapping` rules
- **Set geometry inheritance** — ensure contained objects inherit geometry from their housing (do not write independent geometry)
- **Generate synthetic objects** — create dummy structures and routes per `containment_rules.synthetic_generation`

## Execution Phases

Topology construction requires ordered execution. Each phase depends on the previous — structures must exist before routes reference them, routes before cable segments are housed in them, segments before connections reference them.

1. **Phase 1 — Structures**: Load/create all structure objects (including synthetics)
2. **Phase 2 — Routes**: Load/derive routes between structures, set start/end_structure FKs
3. **Phase 3 — Conduits**: Load conduits into routes (if applicable)
4. **Phase 4 — Cables**: Load fiber_cable records with geometry
5. **Phase 4b — Fiber Segments**: Generate transit-only segment chains → see `knowledge/nmt/segment-connection-generation.md`
6. **Phase 5 — Equipment**: Load equipment (splice_closure, fiber_slack), assign root_housing via containment rules
7. **Phase 6 — Reference**: Load non-network features (drop_point, building_footprint, general_polygon)
8. **Phase 7 — Fiber Connections**: Build splice records from segment cable-continuity → see `knowledge/nmt/segment-connection-generation.md`

## Outputs

The generate stage produces a **self-contained migration package** that can be executed independently:

- **Entry point script** (`output/run_migration.sh`) — single command that runs the full pipeline (transform → load). Accepts `--transform-only`, `--load-only`, `--phase N` flags
- `.def` files in `output/defs/` (JSON format — see `knowledge/nmt/def-file-format.md`)
- Phase scripts in `output/scripts/` — one per execution phase, called by the entry point
- Value mapping configuration
- Synthetic data generation logic (embedded in phase scripts)
- Topology construction log (decisions made, synthetic objects created, confidence scores)
- Load execution log with per-step status
- Feature-level row count summary (attempted/loaded/failed)
- Build report with blockers and retry guidance
- Updated handoff notes for downstream `validate`

**Determinism requirement**: Running `output/run_migration.sh` on the same source data must always produce identical CSVs and identical database state. Do not rely on timestamps, random IDs, or non-deterministic ordering. Sort output rows by a stable key.

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
- **After loading, run NMT integrity checks**: `comms_db {db_name} validate data '*'` to catch referential integrity and structural issues early (before handing off to validate)

### DQR & DMDD Maintenance During Generate

Generate is where the plan meets reality. Keep both documents in sync:

- **New data issue discovered** (nulls, broken FKs, unexpected values, orphaned records) → **create a DQR entry immediately** with severity, evidence (counts/examples), and recommended treatment. Do not defer logging until later stages.
- **Existing DQR `fix_in_flight` treatment applied** → **update the DQR entry status to `Implemented`**. Record the phase, script, and transformation applied.
- **DMDD mapping proves wrong or incomplete** (e.g., unmapped value, wrong target field, structural rule doesn't apply) → **amend the DMDD** with the corrected mapping/rule and note the reason. The DMDD must always reflect the *actual* transformation applied, not just the originally planned one.
- **Containment/topology/connectivity rule produces unexpected results** (high orphan rate, broken chains) → **create DQR entry** and update DMDD if the rule was adjusted.
- **Load produces warnings or dropped fields** → **create DQR entry** documenting what was lost and why.

## Reference Knowledge

Before generating, read these knowledge files for detailed formats, algorithms, and pitfalls:

| File | When to read |
|------|-------------|
| `knowledge/nmt/def-file-format.md` | Writing or modifying `.def` files |
| `knowledge/nmt/feature-type-splitting.md` | Deciding CSV filenames and type→table mapping |
| `knowledge/nmt/segment-connection-generation.md` | Phase 4b (segments) and Phase 7 (connections) |
| `knowledge/nmt/myw_db-tools.md` | Any `myw_db` / `comms_db` / Docker exec usage |
| `knowledge/nmt/post-load-config.md` | After loading — layer groups, sequences, env vars |
| `knowledge/nmt/generate-pitfalls.md` | CRS issues, schema verification, field warnings, proximity units |
| `knowledge/nmt/connectivity-model.md` | Connection record semantics, sides, pin ranges |
| `knowledge/nmt/topology-rules.md` | Segmentation, route types, cable chains |
| `knowledge/nmt/containment-model.md` | Housing assignment, root_housing, geometry inheritance |

