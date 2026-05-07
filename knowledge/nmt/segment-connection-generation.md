# NMT Segment & Connection Generation

## Phase 4b — Fiber Segment Generation

### Overview

Segment transform scripts derive `mywcom_fiber_segment` records from cables + structures. Each segment represents one route span — a cable's path between two adjacent structures.

### Algorithm

1. Load all structures into a spatial index (keyed by `external_ref`)
2. Load routes into a lookup keyed by `(in_structure_ref, out_structure_ref)` (both orderings)
3. Walk each cable's vertices; match structures within `SNAP_TOLERANCE` (~0.0003° ≈ 30m)
4. Split cable linestring at each matched structure point → one segment per span
5. Assign `housing = route` by looking up the route matching segment endpoints
6. Set `forward = True` if segment direction matches route (in→out)
7. **Set `path` = the EWKT geometry of the housing route** (segment inherits its route's linestring). A segment with NULL path will crash the trace engine

### Chain Construction

- Generate **transit-only** segments: one per route span
- Chain segments directly (transit→transit) without internal segments unless source data has explicit splice/termination records requiring them
- Use route_index from phase 2 to determine which spans each cable traverses
- Set `in_structure`/`out_structure` per span endpoints
- Set `in_segment`/`out_segment` as **plain integer IDs** (not URNs) referencing adjacent segments in the chain

### Output Schema

CSV columns: `id, cable, housing, root_housing, directed, forward, in_structure, out_structure, in_segment, out_segment, length, path`

### Expected Results

- ~73% of cables produce segments; ~27% have no structure match (short drops)
- Typical ratio: 0.7–0.8 segments per cable

---

## Phase 7 — Fiber Connection Generation

### Overview

Connection transform scripts derive `mywcom_fiber_connection` splice records from segments. Connections represent fiber continuity at structures where a cable arrives and departs.

### Algorithm

1. Group segments by cable, then by structure (where cable arrives/departs)
2. At each structure where same cable has arriving segment (`out_structure=X`) AND departing segment (`in_structure=X`), create splice connection
3. Housing preference: splice_closure at structure > structure itself
4. Set `in_low=1, in_high=1, out_low=1, out_high=1` for per-strand or cable count for full-width

### Side Assignment Rule (CRITICAL — Common Source of Inversion Bugs)

The `in_side`/`out_side` on a connection identifies **which end of the referenced segment** is at the housing:

| Condition | Side Value | Meaning |
|---|---|---|
| `segment.out_structure = housing` | `"out"` | The segment's OUT end is here |
| `segment.in_structure = housing` | `"in"` | The segment's IN end is here |

**Do NOT confuse cable travel direction with side values** — side refers to the segment's own endpoint label.

### Output Schema

CSV columns: `id, in_object, out_object, in_side, in_low, in_high, out_side, out_low, out_high, splice, housing, root_housing, location`

### Expected Results

- ~1.8 connections per segment (cables typically cross multiple structures)
- 0 splice_closures indexed in first pass is normal if equipment hasn't been loaded with proper `root_housing` referencing structures

---

## Through-Splitter Connections (Pattern 6 in connectivity-model.md)

When a source fibre relationship occurs at a **true optical power splitter** (confirmed 1:N split ratio, asymmetric fiber counts), do NOT create a segment↔segment splice. Instead create TWO connections:

1. **Segment → Splitter IN port**:
   - `in_object` = segment URN
   - `in_side` = segment_side_at_structure
   - `out_object` = `fiber_splitter/{id}`
   - `out_side` = `"in"`
   - `pin` = 1 (always 1 for single-input splitter)

2. **Splitter OUT port → Segment**:
   - `in_object` = `fiber_splitter/{id}`
   - `in_side` = `"out"`
   - `in_low` = output_port_number (1-N)
   - `out_object` = segment URN
   - `out_side` = segment_side_at_structure

### Splitter Connection Rules

- `splice = false` (equipment connection, not a direct fiber splice)
- `housing = fiber_splitter/{id}` (the equipment itself is the housing)
- `root_housing = structure URN` (the structure containing the splitter)
- IN pin = always 1 for 1:N splitters; OUT pin = sequential 1 to N (must be ≤ `n_fiber_out_ports`)
- Identify splitters by checking if the source equipment is a TRUE optical power splitter (1:N ratio)

---

## Pass-Through vs True Splitter (CRITICAL)

Source systems often label fiber distribution/pass-through points as "splitters" when they are actually splice closures.

### Signs of a Pass-Through Point (NOT a true splitter)

- Same fiber count on IN as OUT (1:1 strand mapping)
- Multiple cables passing through with strand-for-strand continuity
- No asymmetric fiber count (e.g., 24 strands in → 24 strands out)

### Correct Modelling

| Source Label | Actual Behaviour | NMT Model | Connection Type |
|---|---|---|---|
| "Splitter" with 1:1 ratio | Pass-through | `splice_closure` | segment↔segment splice (`splice=true`) |
| Splitter with 1:N ratio | True optical split | `fiber_splitter` | Through-splitter pattern (see above) |

---

## Deduplication

Source data may contain multiple fibre records per segment (one per tube/ribbon). When resolving source splice/connection records to NMT connections, deduplicate on `(in_object, in_side, in_low, out_object, out_side, out_low)` before writing. Multiple source records mapping to the same physical connection must produce only one output record.
