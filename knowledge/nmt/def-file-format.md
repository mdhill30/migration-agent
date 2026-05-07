# NMT .def File Format

## Overview

`.def` files are **JSON** (not INI, YAML, or any other format). They define the schema for a feature type in the database. `myw_db load` uses these to create/update tables.

**Correct approach**: Copy the base `.def` from the target NMT database (`myw_db <db> dump <dir> features`) and add any custom fields needed for migration. Do NOT write `.def` files from scratch unless the feature type doesn't exist yet.

---

## Structure of a .def File

```json
{
   "datasource": "myworld",
   "name": "pole",
   "external_name": "Pole",
   "title": "{display_name}: [name]",
   "track_changes": true,
   "versioned": true,
   "geom_indexed": true,
   "editable": {
      "insert_from_gui": true,
      "update_from_gui": true,
      "delete_from_gui": true
   },
   "fields": [
      {"name": "id", "type": "integer", "key": true, "generator": "sequence"},
      {"name": "name", "type": "string(64)"},
      {"name": "location", "type": "point", "mandatory": "true"},
      {"name": "specification", "type": "foreign_key(pole_spec)"},
      {"name": "owner", "type": "string(32)"},
      {"name": "installation_date", "type": "date"},
      {"name": "equipment", "type": "reference_set", "read_only": "true"},
      {"name": "routes", "type": "reference_set", "value": "select(oh_route.in_structure,...)", "read_only": "true"}
   ],
   "groups": [...],
   "searches": [...],
   "queries": [...],
   "filters": []
}
```

---

## Key Field Types

| Type | Description | Example |
|------|-------------|---------|
| `integer` | Integer (use with `"key": true, "generator": "sequence"` for PK) | id |
| `string(N)` | Varchar of length N; `string()` = unlimited | name, owner |
| `double` | Float | height, loss |
| `boolean` | true/false | directed, forward |
| `date` | Date (YYYY-MM-DD) | installation_date |
| `timestamp` | Datetime | created_at |
| `point` | Point geometry (EWKT in CSV) | location |
| `linestring` | LineString geometry (EWKT in CSV) | path |
| `reference` | Cross-type FK (**URN format: `feature_type/id`**) | housing → `manhole/123`, cable → `fiber_cable/456` |
| `reference_set` | Computed reverse-lookup (read-only, never loaded) | equipment, routes |
| `foreign_key(type)` | FK to specific feature type | specification → `pole_spec` |

---

## Rules for .def Generation

1. **Always use JSON format** — `.def` files are loaded by `myw_db load <file>.def`
2. **`id` field must be first**, with `"key": true` and `"generator": "sequence"`
3. **Geometry field** (`point` or `linestring`) must have `"mandatory": "true"`
4. **`reference_set` fields are read-only** — never include them in CSVs; they're computed by the platform
5. **`reference` fields** use **URN format** (`feature_type/id`) in CSVs — e.g., `manhole/12345`, `fiber_cable/206`, `mywcom_fiber_segment/717081`. NEVER use bare integer IDs.
6. **URN fields MUST be double-quoted in CSVs** — Without quotes, `myw_db load` strips the type prefix (e.g., `wall_box/195453` becomes `195453`). When writing CSVs, quote any field value containing `/`. Use Python's `csv` module and ensure URN fields are quoted.
7. **`foreign_key(type)` fields** reference a specific table — value in CSV must be a valid ID in that table
8. **Custom migration fields** (e.g., `external_ref`) must be added to the `.def` before loading data, or the data will be silently dropped
9. **Do NOT invent field names** — check the base `.def` from the database; use exact NMT field names

---

## Workflow

1. Dump base definitions: `myw_db <db> dump <dir> features`
2. Copy relevant `.def` files to `output/defs/`
3. Add any custom fields needed (e.g., `external_ref`)
4. Load definitions: `myw_db <db> load output/defs/<feature>.def`
5. Then load data: `myw_db <db> load output/data/<feature>.csv`

---

## Common Custom Fields for Migration

Fields commonly missing from base NMT schema that need to be added:
- `external_ref` — source system ID (e.g., MSLINK)
- `myw_source_id` — source system UUID (e.g., DEV_ID)
- `manufacturer`, `model`, `owner` — equipment metadata
- `description` — free-text description
- `root_housing_ref` — equipment→structure FK reference
- `in_structure_ref`, `out_structure_ref` — route endpoint FKs
