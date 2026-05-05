# IQGeo myw_db Tools Reference

## Overview

The `myw_db` command-line utility is the primary interface for managing IQGeo Network Management Toolkit (NMT) databases. This document provides a reference for all available operations and their usage in the migration context.

**Base command**: `myw_db <database_name> <operation> [options]`

**Example**: `myw_db iqgeo list --verbosity 2`

---

## Database Lifecycle Operations

### create
Create a new NMT database.

```bash
myw_db iqgeo create --host localhost --port 5432 --username postgres
```

**Use case**: Initialize a new target database for migration.  
**Output**: New PostgreSQL database with PostGIS extensions.

---

### install
Install myWorld/NMT schema tables into an existing database.

```bash
myw_db iqgeo install
```

**Use case**: After creating a blank database, install the NMT schema (structures, routes, cables, etc.).  
**Effect**: Creates all NMT tables, indexes, constraints.

---

### upgrade
Upgrade database from an earlier NMT release to current version.

```bash
myw_db iqgeo upgrade
```

**Use case**: When deploying a new NMT version to an existing database.  
**Effect**: Applies schema migrations, adds new columns/tables, updates constraints.

---

### drop
Delete database or specific data/metadata.

```bash
myw_db iqgeo drop --confirm
```

**Caution**: Destructive operation. Requires confirmation.

---

## Data Operations

### list
Show summary of database contents (object counts, status).

```bash
myw_db iqgeo list --verbosity 2
```

**Output**:
```
Opening database postgresql://***:***@postgis:5432/iqgeo ...
Structures:     2,451
Routes:         1,203
Cables:            456
Segments:        3,120
Equipment:       1,089
Connections:     2,340
Circuits:          567
```

**Use case**: Quick sanity check of data volume.  
**Note**: Requires fully installed schema (encounters errors on blank database).

---

### load
Load enumerators, feature definitions, and data from source files.

```bash
myw_db iqgeo load --file definitions.xml
```

**Input**: XML feature definitions and value lists.  
**Use case**: Load NMT specifications (cable types, equipment specs, etc.).

---

### import
Import data from an external datasource (shapefile, database, API).

```bash
myw_db iqgeo import --source postgis --connection postgresql://...
```

**Use case**: Bulk load migrated source data into NMT tables.

---

### dump
Output data or metadata to file (XML, JSON, CSV).

```bash
myw_db iqgeo dump --table structures --format json --output structures.json
```

**Use case**: Extract NMT data for analysis or external reporting.  
**Output**: Serialized data in requested format.

---

### run
Execute a Python script or SQL command against the database.

```bash
myw_db iqgeo run script.py [args...]
myw_db iqgeo run --sql "SELECT COUNT(*) FROM structure;"
myw_db iqgeo run --command "print(db.structures.count())"
```

**Options**:
- `--sql` — Execute raw SQL query
- `--command` — Execute Python command (has access to `db` object)
- `--commit` — Perform commit after script completes

**Use case**: Post-load validation, data transformation, analytics.

**Example: Count objects by type**:
```bash
myw_db iqgeo run --sql "
  SELECT 'Structures' as type, COUNT(*) as count FROM structure
  UNION ALL
  SELECT 'Equipment', COUNT(*) FROM equipment
  UNION ALL
  SELECT 'Cables', COUNT(*) FROM cable
  UNION ALL
  SELECT 'Segments', COUNT(*) FROM segment
  UNION ALL
  SELECT 'Routes', COUNT(*) FROM route;"
```

---

## Configuration & Maintenance

### configure
Configure feature properties (data validation rules, specifications, custom fields).

```bash
myw_db iqgeo configure --property max_cable_length --value 50000
```

**Use case**: Set NMT-wide constraints or custom parameters.

---

### add
Add a named search or query definition.

```bash
myw_db iqgeo add --type query --name fiber_cables \
  --definition "SELECT * FROM cable WHERE technology='fiber'"
```

**Use case**: Store reusable queries for later use.

---

### maintain
Perform database maintenance: statistics, vacuum, index optimization.

```bash
myw_db iqgeo maintain --analyze --vacuum
```

**Use case**: Optimize database after large data loads.

---

### checkpoint
Create a named version/snapshot of the database state.

```bash
myw_db iqgeo checkpoint --name pre_validation_run
```

**Use case**: Save state before risky operations (allow rollback).

---

### backup
Copy database to disk archive (full backup).

```bash
myw_db iqgeo backup --output /backups/iqgeo_20260505.tar.gz
```

**Output**: Compressed database dump.

---

### restore
Restore database from backup archive.

```bash
myw_db iqgeo restore --input /backups/iqgeo_20260505.tar.gz
```

---

## Validation & Quality

### validate
Check database integrity (referential constraints, geometry validity, etc.).

```bash
myw_db iqgeo validate
```

**Output**:
```
Checking referential integrity...
  ✗ 12 orphaned segments (housing reference missing)
  ✓ All cable references valid
  ✗ 3 invalid geometries detected
  ✓ All containment chains valid

Issues found: 15
```

**Use case**: Post-load validation before sign-off.

---

## Distribution & Replication

### initialise
Initialize master database for replication to satellites.

```bash
myw_db iqgeo initialise --replication-id master_01
```

---

### extract
Create a SQLite extract (read-only snapshot for mobile/offline use).

```bash
myw_db iqgeo extract --output field_extract.db --area bbox.geojson
```

**Use case**: Create offline/mobile copy of network data for field crews.

---

### export
Export master changes to sync directory (for incremental synchronization).

```bash
myw_db iqgeo export --since "2026-05-01" --output /sync
```

**Output**: Change set files (deltas) for replication.

---

### update
Apply master updates to a SQLite extract (merge changes from central).

```bash
myw_db iqgeo update --extract field_extract.db --changeset /sync/changes.xml
```

---

### convert
Convert database to SQLite format (for deployment/distribution).

```bash
myw_db iqgeo convert --output iqgeo_readonly.db --read-only
```

---

### package
Package a SQLite database for deployment.

```bash
myw_db iqgeo package --sqlite iqgeo_readonly.db --output iqgeo_v1.0.pkg
```

---

### configure_extract
Configure download of extracts (size limits, sync policies).

```bash
myw_db iqgeo configure_extract --max-size 500mb --sync-interval daily
```

---

## Connection Options

All operations accept these connection parameters:

```bash
--host localhost              # PostgreSQL server (default: localhost)
--port 5432                   # PostgreSQL port (default: 5432)
--username postgres           # Database user (default: from pg_env)
--password mypassword         # Password (default: from pg_env)
--password_stdin              # Read password from stdin (secure)
```

**Security**: Use `--password_stdin` or environment variables for production.

---

## Verbosity & Output

### Common options

```bash
--verbosity LEVEL             # 0=quiet, 1=errors, 2=info, 3=debug (default: 2)
--summary LEVEL               # Summary output level (default: 0)
--json                        # Output in JSON format
--csv                         # Output in CSV format
```

---

## Migration Workflow: Using myw_db

### Phase 1: Database Setup

```bash
# Create target database
docker exec iqgeo_myproj myw_db iqgeo create

# Install NMT schema
docker exec iqgeo_myproj myw_db iqgeo install

# Verify installation
docker exec iqgeo_myproj myw_db iqgeo run --sql "
  SELECT COUNT(*) as table_count 
  FROM information_schema.tables 
  WHERE table_schema = 'public';"
```

### Phase 2: Load Migrated Data

```bash
# Import from external source (e.g., CSV, shapefile)
docker exec iqgeo_myproj myw_db iqgeo import \
  --source csv \
  --file structures.csv \
  --table structure

# Bulk load multiple object types
docker exec iqgeo_myproj myw_db iqgeo load \
  --file migrated_definitions.xml
```

### Phase 3: Validation

```bash
# Validate database integrity
docker exec iqgeo_myproj myw_db iqgeo validate

# Query validation results
docker exec iqgeo_myproj myw_db iqgeo run --sql "
  SELECT issue_type, COUNT(*) as count
  FROM validation_log
  WHERE severity >= 'warning'
  GROUP BY issue_type;"
```

### Phase 4: Backup & Distribution

```bash
# Create checkpoint before release
docker exec iqgeo_myproj myw_db iqgeo checkpoint \
  --name release_candidate_v1

# Create read-only extract for field teams
docker exec iqgeo_myproj myw_db iqgeo extract \
  --output field_teams_may2026.db \
  --read-only
```

---

## Common SQL Queries with myw_db run

### Count objects by type

```bash
docker exec iqgeo_myproj myw_db iqgeo run --sql "
  SELECT 'Structure' as type, COUNT(*) as count FROM structure
  UNION ALL
  SELECT 'Route', COUNT(*) FROM route
  UNION ALL
  SELECT 'Cable', COUNT(*) FROM cable
  UNION ALL
  SELECT 'Segment', COUNT(*) FROM segment
  UNION ALL
  SELECT 'Equipment', COUNT(*) FROM equipment
  UNION ALL
  SELECT 'Connection', COUNT(*) FROM connection
  ORDER BY type;"
```

### Find orphaned segments

```bash
docker exec iqgeo_myproj myw_db iqgeo run --sql "
  SELECT s.id, s.name, s.housing
  FROM segment s
  LEFT JOIN route r ON s.housing = r.id
  LEFT JOIN conduit c ON s.housing = c.id
  WHERE s.housing IS NULL
    OR (r.id IS NULL AND c.id IS NULL);"
```

### Verify containment integrity

```bash
docker exec iqgeo_myproj myw_db iqgeo run --sql "
  SELECT 'Segments with invalid root_housing' as check_name, COUNT(*) as issues
  FROM segment s
  LEFT JOIN structure st ON s.root_housing = st.id
  WHERE s.root_housing IS NOT NULL AND st.id IS NULL

  UNION ALL

  SELECT 'Equipment with invalid root_housing', COUNT(*)
  FROM equipment e
  LEFT JOIN structure st ON e.root_housing = st.id
  WHERE e.root_housing IS NOT NULL AND st.id IS NULL;"
```

### Check cable segmentation

```bash
docker exec iqgeo_myproj myw_db iqgeo run --sql "
  SELECT 
    c.id,
    c.name,
    COUNT(s.id) as segment_count,
    COUNT(DISTINCT s.housing) as distinct_parents
  FROM cable c
  LEFT JOIN segment s ON c.id = s.cable
  GROUP BY c.id, c.name
  ORDER BY segment_count DESC;"
```

### List connections by type

```bash
docker exec iqgeo_myproj myw_db iqgeo run --sql "
  SELECT 
    CASE 
      WHEN splice THEN 'Splice'
      ELSE 'Patch/Termination'
    END as connection_type,
    COUNT(*) as count,
    COUNT(DISTINCT housing) as locations
  FROM connection
  GROUP BY splice;"
```

---

## Error Handling & Troubleshooting

### "Table not found" errors

**Cause**: Schema not installed or incomplete.  
**Fix**: Run `myw_db iqgeo install` to create missing tables.

### "No such file or directory" with --sql

**Cause**: myw_db expects a file path, not inline SQL without `--sql` flag.  
**Fix**: Ensure you use `--sql` before SQL string, or create script file.

### Connection refused

**Cause**: PostgreSQL server not reachable or credentials wrong.  
**Fix**: Verify `--host`, `--port`, `--username`, `--password`.

### Validation errors for orphaned objects

**Cause**: Data migration incomplete or containment rules not applied.  
**Fix**: Re-run migration pipeline to infer missing housing relationships.

---

## Reference

For authoritative documentation, see IQGeo Platform Tools documentation or run:

```bash
myw_db --version
myw_db --help
myw_db iqgeo <operation> --help
```

