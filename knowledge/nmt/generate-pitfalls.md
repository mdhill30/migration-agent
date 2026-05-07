# NMT Generate — Common Pitfalls & Lessons Learned

## Schema Field Warnings

When `myw_db load` reports fields not in the schema:
1. Records are still inserted (geometry + recognized fields)
2. Unrecognized field data is **permanently lost** from the load
3. To fix: add missing fields to `.def` files and reinstall schema before reloading

---

## Containment / Housing Assignment

- Spatial proximity search uses source CRS units (e.g., US Survey Feet for EPSG:2236)
- 10m ≈ 32.8 US Survey Feet — use `PROXIMITY_RADIUS_FT = 32.8`
- Typical unhoused rates: 29–35% for equipment in sparse networks
- Structure spatial index should include POLEPED, CABINET, HEADEND, FIBERNODE but **exclude** equipment layers (splice enclosures are not valid housing parents)
- Unhoused equipment → DQR issue with `needs_decision` treatment; options include expanding radius, creating synthetic structures, or accepting unhoused

---

## Route Endpoint Resolution

- STRAND.LINK1/LINK2 reference structure MSLINKs
- Build a combined MSLINK index across all structure layers (including splice enclosures for reference, but they are not route endpoints)
- Orphan rate of 50%+ indicates missing source layers or references to deleted records outside the extract
- Orphaned route endpoints → leave `in_structure`/`out_structure` null; flag in DQR

---

## CRS Handling

- Source data in projected CRS (e.g., EPSG:2236 FL State Plane East) must be reprojected to EPSG:4326 for NMT
- Use `osr.OAMS_TRADITIONAL_GIS_ORDER` on **both** source and target SRS to avoid axis-order issues
- Output geometry as EWKT: `SRID=4326;POINT(lon lat)` or `SRID=4326;LINESTRING(...)`
- US Survey Feet conversion factor: `0.3048006096012192` (NOT international feet `0.3048`)

---

## Pre-Generate Schema Verification

**Before generating CSVs, verify feature type schemas against the actual database.** Wrong column names in CSVs cause data to be silently dropped.

Steps:
1. Query the database for the actual column names of each target feature type:
   ```bash
   docker exec {container} myw_db {db_name} run --sql "SELECT column_name FROM information_schema.columns WHERE table_name = '{feature_type}' ORDER BY ordinal_position;"
   ```
2. Use these exact column names as CSV headers
3. Common mistakes to avoid:
   - `fiber_cable`: uses `type` and `fiber_count` (NOT `technology` or `count`)
   - `address`: `id` field is integer (source string IDs require conversion to sequential integers)
   - Feature types that don't exist produce no error — data just disappears

---

## Docker Pitfalls

- `myw_db run --sql "INSERT ..."` does NOT auto-commit — use `--commit` flag or use `psql` directly
- File paths in commands must reference the container filesystem, not the host
- Check container paths: `myw_db` is typically at `/opt/iqgeo/platform/Tools/myw_db`, `comms_db` at `/opt/iqgeo/platform/WebApps/myworldapp/modules/comms/tools/comms_db`

---

## Load Syntax

The correct `myw_db` load syntax is:

```bash
myw_db <database_name> load <file_path>
```

- Feature type is **inferred from the CSV filename** (e.g., `pole.csv` → loads into `pole` feature type)
- Do NOT pass `data` or the feature type as positional arguments

**Correct**: `myw_db myproj load /tmp/migration/pole.csv`  
**WRONG**: `myw_db myproj load data pole /tmp/migration/pole.csv` (produces "No such feature type: data" errors)
