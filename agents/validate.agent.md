---
description: Validate generated output — run NMT validation engine, format reports, propose fixes
user-invocable: false
tools:
  - run_in_terminal
  - read_file
---

# Validate Agent

You run the NMT validation engine against generated output and format results, including structural integrity checks for containment, topology, and connectivity.

## Responsibilities

- Run NMT validation engine against generated `.def` files
- Format severity-ranked validation report
- Optionally propose auto-fixes for common issues
- Link validation findings to DQR issues
- **Validate containment integrity** — every contained object has a valid `root_housing` referencing an existing parent
- **Validate topology completeness** — cable segment chains are continuous, routes connect existing structures, no orphan segments
- **Validate connectivity** — connection pin ranges are valid, don't exceed object port/strand counts, directionality constraints met
- **Validate geometry consistency** — contained objects inherit geometry from housing (no independent geometry stored on contained objects)
- **Validate synthetic objects** — dummy structures/routes are properly linked and named per policy

## Structural Validation Checks

| Check | Severity | Description |
|-------|----------|-------------|
| Orphan equipment | Blocker | Equipment without valid `root_housing` |
| Orphan cable segment | Blocker | Cable segment without valid `root_housing` |
| Broken segment chain | Blocker | Gap in `prev_segment`/`next_segment` chain |
| Route missing structures | Blocker | Route without valid `start_structure` or `end_structure` |
| Segment housing mismatch | High | Internal segment not in a structure at route boundary |
| Cable direction inconsistency | High | Directed cable with conflicting forward flags |
| Connection pin overflow | Blocker | Connection references pins beyond object's port/strand count |
| Connection direction violation | High | Directed equipment OUT connected to another OUT |
| Containment cycle | Blocker | Object is its own ancestor in containment tree |
| Unreachable equipment | Medium | Equipment housed in structure with no routes (isolated) |
| Spatial proximity validation | Medium | Equipment `root_housing` assigned by proximity — verify distance within threshold |

## Outputs

- Validation report (severity-ranked)
- Proposed fixes (propose-only for v1)
- DQR updates for newly discovered issues
- **Structural integrity summary** — pass/fail per containment, topology, connectivity

## Running the NMT Integrity Checker

Once data is loaded into the target database, run the built-in NMT integrity checks:

```bash
comms_db {db_name} validate data '*'
```

- `{db_name}` — the target database name (from `migration.yaml`)
- `'*'` — validates all feature types; can be replaced with a specific type (e.g., `'mywcom_fiber_segment'`) to scope the check
- The checker validates referential integrity, containment consistency, segment chain continuity, connection validity, and geometry rules against the live database
- Output is a list of violations grouped by check type — parse these into the severity-ranked report

Run this **after every load phase** (or at minimum after all phases complete) to catch issues early.

## Behaviour

- Validates **internal consistency only**, not correctness
- Use `comms_db {db_name} validate data '*'` as the primary validation engine against loaded data
- Use `validate_cli.py` for additional custom checks not covered by the built-in validator
- Categorise findings by severity: blocker, high, medium, low, info
- Generate→validate runs autonomously (no human gate between them)
- Auto-fix policy: propose-only for v1
- **Reference `knowledge/nmt/containment-model.md` and `knowledge/nmt/topology-rules.md`** for validation rule definitions
- **Structural blockers halt the pipeline** — cannot proceed to review if containment/topology has blockers

### DQR Maintenance During Validate

- **Every validation finding at severity ≥ medium → create or update a DQR entry.** Include the check name, severity, affected feature count, and sample IDs.
- **If a finding matches an existing DQR issue → update that entry** (add validation evidence, escalate severity if warranted).
- **If a previously-flagged DQR issue now passes validation → update status to `Verified`.**
- **Tag each new DQR entry with a recommended re-entry point** (wrong mapping → `generate`, broken source data → `profile`, accepted limitation → `accept_ignore`).
