# NMT Post-Load Configuration

## Layer Group Visibility

Loaded features won't appear in the NMT web UI until added to a layer group. Add them via direct SQL:

```sql
INSERT INTO myw_layer_group_item (layer_group, layer_name, min_scale, max_scale, visible)
VALUES ('mywcom_fiber_group', '{layer_name}', 0, 0, true)
ON CONFLICT DO NOTHING;
```

Common layer names: `structures`, `cable_segments`, `connections`, `internal_route`, `addresses`

---

## Sequence Update

After bulk-loading data with explicit IDs, update PostgreSQL sequences to avoid ID collisions on subsequent inserts:

```bash
docker exec {container} myw_db {db_name} load --update_sequence
```

This must be run after all data loads are complete.

---

## Environment Variables for Transform Scripts

Transform scripts accept these environment variables:

| Variable | Purpose | Example |
|----------|---------|---------|
| `SOURCE_DIR` | Path to source data files | `jobs/obe/source/` |
| `OUTPUT_DIR` | Path to write output CSVs | `jobs/obe/output/data` |
| `TARGET_DB` | Target database name | `myproj` |

**Always set these explicitly** — default paths in scripts may be stale.

---

## Load Script Entry Point Modes

The `run_migration.sh` script supports three modes:

| Flag | Behaviour |
|------|-----------|
| `--transform-only` | Run Python transforms, produce CSVs, no database writes |
| `--load-only` | Skip transforms, load existing CSVs into database |
| `--phase N` | Run only phase N (1, 2, 3, 4, 4b, 5, 6, 7) |
| *(no flags)* | Full pipeline (transform + load) |

Always run `--transform-only` first to verify CSV output before loading.
