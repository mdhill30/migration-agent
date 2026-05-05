# NMT Connectivity Model

## Overview

The NMT connectivity model represents signal-level connections between equipment ports and cable strands. It operates at the **strand level** — each individual fiber, copper pair, or coax conductor is trackable through the network.

Connectivity captures:
- **Splice connections**: Cable segment A strand 5 → Cable segment B strand 5 (fiber continuity)
- **Cross-connect**: Equipment port 1-4 → Equipment port 1-4 (patch cord)
- **Termination**: Cable segment strand 3 → Equipment port 3 (service delivery)

---

## Core Concepts

### Pin
A connection point on the signal network — a port on equipment or a strand on a cable. Pins are **not modeled explicitly** (no database record per pin). Their existence is inferred from the port/strand count attributes on the parent object.

**Pin numbering**:
- Equipment ports: 1 to `count` (e.g., 1-24 for 24-port patch panel)
- Cable strands: 1 to `count` (e.g., 1-12 for 12-fiber cable)
- Coax: single pin (count=1)

### Side
A connection interface on an object — a set of pins. Objects typically have two sides:

| Object Type | Sides | Semantics |
|---|---|---|
| **Directed Cable** | IN, OUT | Upstream (source) / Downstream (destination) |
| **Undirected Cable** | A, Z | Either end |
| **Directed Equipment** | IN, OUT | Upstream / Downstream |
| **Undirected Equipment** | Front, Back | Either face |

### Pin Range
A contiguous set of pins on the same side of an object. Notation: `side:low:high`

Examples:
- `out:1:5` — pins 1 through 5 on the OUT side
- `in:10:15` — pins 10 through 15 on the IN side
- `a:1:1` — single strand on side A

**Key constraint**: Range high ≥ low; range must not exceed object count.

### Connection
An explicit relationship between two pin ranges. Stored as a `Connection` record in the database.

**Semantics**:
- **Splice**: Connects two Segments (cable continuity)
- **Patch**: Connects two Equipment (service routing)
- **Termination**: Connects Segment to Equipment (service end-point)
- **Cross-connect**: Equipment to Equipment (internal patch)

---

## Connection Record Structure

```
connection:
  id                  → unique identifier
  in_object           → URN (Equipment or Segment)
  in_side             → "in" | "out" | "a" | "z" | "front" | "back"
  in_low              → integer (first pin)
  in_high             → integer (last pin)
  out_object          → URN (Equipment or Segment)
  out_side            → "in" | "out" | "a" | "z" | "front" | "back"
  out_low             → integer (first pin)
  out_high            → integer (last pin)
  splice              → boolean (true if segment-to-segment splice)
  housing             → URN of Structure or Equipment (where connection is located)
  root_housing        → URN of top-level Structure
```

---

## Connection Patterns

### Pattern 1: Cable Splice at Structure

**Scenario**: Two cable segments meet at a pole. Fiber from Segment A is spliced to Segment B.

**Source data**:
```
Splice at Pole X
  from_cable: FIBER-MAIN-001 (segment 1)
  from_strand: 1-12 (all fibers)
  to_cable: FIBER-BRANCH-001 (segment 1)
  to_strand: 1-12
```

**Target NMT structure**:
```
Connection:
  in_object: segment_fib_main_001_pole_x
  in_side: out
  in_low: 1
  in_high: 12
  out_object: segment_fib_branch_001_pole_x
  out_side: in
  out_low: 1
  out_high: 12
  splice: true
  housing: pole_x
  root_housing: pole_x
```

**Validation**:
- Both segments exist ✓
- Both have same technology (fiber) ✓
- Strand counts match ✓
- Housing is common junction (Structure) ✓

---

### Pattern 2: Equipment Port Cross-Connect

**Scenario**: Patch cord between two equipment in the same cabinet. Ports 1-4 on Panel A cross-connected to ports 1-4 on Panel B.

**Source data**:
```
Patch at Cabinet Y
  from_equipment: PATCH_PANEL_A (port 1-4)
  to_equipment: PATCH_PANEL_B (port 1-4)
  patch_cord_type: fiber
```

**Target NMT structure**:
```
Connection:
  in_object: equipment_patch_panel_a_cabinet_y
  in_side: out
  in_low: 1
  in_high: 4
  out_object: equipment_patch_panel_b_cabinet_y
  out_side: in
  out_low: 1
  out_high: 4
  splice: false
  housing: cabinet_y
  root_housing: cabinet_y
```

**Validation**:
- Port counts exist on both equipment ✓
- Both at same housing ✓
- pin_range_size matches (1-4 = 4 pins on each side) ✓

---

### Pattern 3: Segment Termination at Equipment

**Scenario**: Cable segment terminates at equipment. Strand 1-8 on segment connects to ports 1-8 on terminating equipment.

**Source data**:
```
Termination at Structure Z
  from_cable_segment: FIBER-MAIN-001-SEG3 (out side)
  from_strand: 1-8
  to_equipment: TERMINATION_FRAME_01 (in side)
  to_port: 1-8
```

**Target NMT structure**:
```
Connection:
  in_object: segment_fib_main_seg3
  in_side: out
  in_low: 1
  in_high: 8
  out_object: equipment_termination_frame_01
  out_side: in
  out_low: 1
  out_high: 8
  splice: false
  housing: structure_z
  root_housing: structure_z
```

**Validation**:
- Segment out side not already connected ✓
- Equipment in side not already connected ✓
- Strand count (8) ≤ segment count ✓
- Port count (8) ≤ equipment count ✓

---

### Pattern 4: Asymmetric Mapping (Fan-Out / Fan-In)

**Scenario**: One cable strand distributed to multiple equipment ports via splitter.

**Source data**:
```
Splitter at Pole X
  from_cable_segment: FIBER-MAIN-001-SEG1 (strand 1)
  to_equipment:
    - SPLITTER_OUT_1 (ports 1-4)
    - SPLITTER_OUT_2 (ports 1-4)
    - SPLITTER_OUT_3 (ports 1-4)
  (1:3 fan-out split)
```

**Target NMT structure**:
```
Connection 1:
  in_object: segment_fib_main_seg1
  in_side: out
  in_low: 1
  in_high: 1
  out_object: equipment_splitter_out_1
  out_side: in
  out_low: 1
  out_high: 1
  housing: pole_x
  root_housing: pole_x

Connection 2:
  in_object: segment_fib_main_seg1
  in_side: out
  in_low: 1
  in_high: 1
  out_object: equipment_splitter_out_2
  out_side: in
  out_low: 1
  out_high: 1
  housing: pole_x
  root_housing: pole_x

Connection 3:
  in_object: segment_fib_main_seg1
  in_side: out
  in_low: 1
  in_high: 1
  out_object: equipment_splitter_out_3
  out_side: in
  out_low: 1
  out_high: 1
  housing: pole_x
  root_housing: pole_x
```

**Validation**:
- Same segment strand can appear in multiple connections ✓
- Splitter function encoded in equipment specification (handled separately in implicit connections) ✓

---

### Pattern 5: Cable Continuity Splice (Derived from Segments)

**Scenario**: Source data has no explicit splice records, but cable segmentation has been performed. Wherever the same cable has a segment arriving at a structure (out_structure=X) AND a segment departing (in_structure=X), a splice connection must exist to maintain cable continuity.

**Algorithm** (validated on Summit Fiber: 6,026 segments → 11,072 connections at 2,346 structures):

1. Group all segments by cable URN
2. For each cable, identify structures where the cable has:
   - An arriving segment (segment.out_structure = structure)
   - A departing segment (segment.in_structure = structure)
3. At each such structure, create splice connection(s) between all arriving/departing segment pairs
4. Housing preference: splice_closure at structure > structure itself

**Source data** (derived — no explicit source):
```
Cable FIBER-001 has:
  Segment A: in_structure=Pole1, out_structure=Pole2  (arrives at Pole2)
  Segment B: in_structure=Pole2, out_structure=Pole3  (departs from Pole2)
  → Splice at Pole2
```

**Target NMT structure**:
```
Connection:
  in_object: mywcom_fiber_segment/{seg_A_id}
  in_side: out
  in_low: 1
  in_high: 1    (per-strand; use cable.count for full-width)
  out_object: mywcom_fiber_segment/{seg_B_id}
  out_side: in
  out_low: 1
  out_high: 1
  splice: true
  housing: splice_closure/{closure_id}  OR  {structure_id}
  root_housing: {structure_id}
  location: SRID=4326;POINT(lon lat)  (structure location)
```

**Key decisions — Side Assignment Rule for Directed Segments**:

The `in_side`/`out_side` on a connection record identifies **which end of the segment** is at the housing (splice location):
- If `segment.out_structure = housing` → the segment's **out** end is here → use side `"out"`
- If `segment.in_structure = housing` → the segment's **in** end is here → use side `"in"`

In Pattern 5 (cable continuity):
- Segment A *arrives* at Pole2 (its `out_structure = Pole2`) → `in_side = "out"`
- Segment B *departs* from Pole2 (its `in_structure = Pole2`) → `out_side = "in"`

**CRITICAL**: Do NOT confuse "arriving/departing cable direction" with side values. The side refers to the segment's own endpoint label, not the cable's travel direction.

Additional decisions:
- `in_low/in_high = 1/1` — per-strand connections (one record per strand pair); OR use `cable.count` for full-width splice (one record per cable crossing)
- `housing` prefers splice_closure over bare structure — if a `splice_closure` equipment record exists with `root_housing = structure`, use its URN as housing
- Creates N×M connections at each structure where N arriving segments meet M departing segments for the same cable (typically 1×1)

**Statistics** (typical fiber OSP migration without explicit splice data):
- Average connections per structure: 4.7 (multiple cables crossing same structure)
- ~95% of connections are 1:1 (single arrive → single depart for a cable)
- ~5% are many-to-many (cable branches at structure)

**Validation**:
- Both in_object and out_object are segments of the same cable ✓
- Both segments share a common structure (arrive/depart) ✓
- housing references a valid structure or equipment at that structure ✓
- splice = true for all cable-continuity connections ✓

---

## Circuit Tracing

**Circuits** represent end-to-end services. They are derived by tracing through segments and connections.

### Circuit Definition

```
circuit:
  id                  → unique identifier
  name                → human-readable name
  in_feature          → serving equipment (URN)
  in_pins             → port range on in_feature
  out_feature         → terminating equipment (URN)
  out_pins            → port range on out_feature
  path                → LineString (rendered for visualization)
  segments_used       → list of segment URNs traversed
  connections_used    → list of connection URNs traversed
```

### Tracing Algorithm

1. **Start at in_feature port**
2. **Find Connection** where `in_object=in_feature`, `in_side=out`, `in_low ≤ in_pins ≤ in_high`
3. **Follow Connection** to `out_object` (destination)
4. **If destination is Equipment**: Done (termination). Record as `out_feature` / `out_pins`.
5. **If destination is Segment**: 
   - Trace segment through housing (Route)
   - At end structure, find next Connection
   - Repeat from step 2
6. **Return ordered list**: [Segment1, Connection1, Segment2, Connection2, ..., EquipmentN]

### Example Circuit Trace

**Network topology**:
```
Equipment_A (port 1) 
  ↓ Connection(ports 1→1, segment_1_in:1)
Segment_1 (strand 1)
  ↓ Route traversal
  ↓ Connection splice (segment_1_out:1 → segment_2_in:1)
Segment_2 (strand 1)
  ↓ Connection termination (segment_2_out:1 → equipment_b_port:1)
Equipment_B (port 1)
```

**Circuit record**:
```
circuit_service_001:
  in_feature: equipment_a
  in_pins: "1"
  out_feature: equipment_b
  out_pins: "1"
  segments_used: [segment_1, segment_2]
  connections_used: [conn_a_seg1, conn_splice, conn_seg2_b]
  path: LineString derived from segment geometries
```

---

## Connectivity Inference

### Inference 1: Connection from Explicit FK

**When**: Source has direct splice/patch records  
**How**: Map source fields directly to Connection attributes

```python
connection = Connection(
    in_object=map_object(source.from_cable),
    in_side="out",
    in_low=source.from_strand_start,
    in_high=source.from_strand_end,
    out_object=map_object(source.to_cable),
    out_side="in",
    out_low=source.to_strand_start,
    out_high=source.to_strand_end,
    splice=True,
    housing=find_common_structure(source.location)
)
```

### Inference 2: Connection from Equipment Port Mapping

**When**: Source has equipment ports assigned to cable terminals  
**How**: Infer Connection from segment → equipment mapping

```sql
INSERT INTO connection (in_object, in_side, in_low, in_high, 
                        out_object, out_side, out_low, out_high,
                        housing, root_housing)
SELECT
  s.id,
  'out',
  sp.strand_number,
  sp.strand_number,
  e.id,
  'in',
  sp.port_number,
  sp.port_number,
  s.root_housing,
  s.root_housing
FROM segment s
JOIN source_segment_port_map sp ON s.source_id = sp.segment_id
JOIN equipment e ON sp.equipment_id = e.source_id;
```

### Inference 3: Fan-Out/Fan-In from Splitter Specs

**When**: Source specifies splitter equipment but not explicit connections  
**How**: Generate connections based on splitter function

```yaml
fix_in_flight:
  splitter_connections:
    check: "equipment.specification LIKE '%splitter%'"
    strategy: "generate_from_spec"
    config:
      1:2_splitter: "duplicate in_strand to 2 out_strands"
      1:4_splitter: "duplicate in_strand to 4 out_strands"
      8:1_splitter: "merge 8 in_strands to 1 out_strand"
      crossbar: "cartesian product in_pins × out_pins"
```

---

## Connectivity Validation

### Check 1: No Pin Range Conflicts

```sql
-- Verify no overlapping connections from same source
SELECT 
  a.in_object, a.in_side, a.in_low, a.in_high,
  b.in_object, b.in_side, b.in_low, b.in_high
FROM connection a
JOIN connection b ON a.id < b.id
  AND a.in_object = b.in_object
  AND a.in_side = b.in_side
WHERE NOT (a.in_high < b.in_low OR b.in_high < a.in_low);
```

**Fix**: Resolve overlapping pin assignments. Flag as DQR issue if ambiguous.

### Check 2: Pin Range Validity

```sql
-- Verify pins exist on referenced object
SELECT c.id, c.in_object, c.in_low, c.in_high, o.count
FROM connection c
JOIN object o ON c.in_object = o.id
WHERE c.in_high > o.count;
```

**Fix**: Adjust pin ranges to fit object capacity, or flag data quality issue.

### Check 3: Connected Objects Exist

```sql
-- Verify both ends of connection exist
SELECT 'in_object missing' as error, id FROM connection 
WHERE in_object NOT IN (SELECT id FROM object)
UNION ALL
SELECT 'out_object missing', id FROM connection 
WHERE out_object NOT IN (SELECT id FROM object);
```

**Fix**: Create missing objects, or delete orphaned connections.

### Check 4: Splices at Valid Junctions

```sql
-- Verify splice connections occur at common Structure
SELECT c.id, c.in_object, c.out_object
FROM connection c
WHERE c.splice = true
  AND NOT EXISTS (
    SELECT 1 FROM structure s
    WHERE s.id = c.housing
      AND EXISTS (
        SELECT 1 FROM segment seg1 WHERE seg1.id = c.in_object AND seg1.root_housing = s.id
      )
      AND EXISTS (
        SELECT 1 FROM segment seg2 WHERE seg2.id = c.out_object AND seg2.root_housing = s.id
      )
  );
```

**Fix**: Verify splice location matches segment end points.

---

## Migration Workflow: Connectivity Phase

### Step 1: Profile Connectivity Data

1. Identify source connectivity records (splice tables, port mappings, terminals)
2. Categorize by type (splice, patch, termination, cross-connect)
3. Sample and validate source FK references
4. Document confidence level per category

### Step 2: Plan Connectivity Mappings

1. Design connection inference rules (FK-first → naming → spatial)
2. Handle gaps: synthetic generation for missing connections
3. Configure valid side pairs per object type
4. Define pin range transformation rules

**DMDD sections**:
```yaml
connectivity_mapping:
  splice_patterns:
    - source: "splice_table"
      condition: "type = 'fiber'"
      map_to: Connection(splice=true)
      rule: "direct FK mapping"
      
  equipment_ports:
    - source: "equipment_terminal"
      map_to: Connection(splice=false)
      rule: "segment→equipment connection"
      confidence: "high"
```

### Step 3: Generate Connections

1. Execute FK-based mapping
2. Apply naming pattern inference
3. Generate missing connections from implicit rules (splitters)
4. Create circuit records by tracing paths

### Step 4: Validate Connectivity

- No overlapping pin ranges ✓
- All pins within object capacity ✓
- Both connection endpoints exist ✓
- Splices at valid junctions ✓
- All circuits traceable ✓

### Step 5: Review & Correct

- Spot-check sample circuits end-to-end
- Verify splitter fan-out logic
- Confirm termination points
- Validate capacity (strand count = connection count)

---

## FAQ

**Q: Can a single pin be involved in multiple connections?**  
A: Yes, for fan-out (1 input → multiple outputs). Not for parallel connections on same port.

**Q: What if strand/port counts don't match?**  
A: Document in DQR. Options: truncate to smaller range, flag as capacity issue, reject connection.

**Q: How are implicit connections (internal to equipment) represented?**  
A: Not as explicit Connection records. Encoded in equipment `specification` (splitter function, cross-connect matrix). Derived during circuit tracing.

**Q: Can a circuit use multiple routes?**  
A: Yes. Circuit traces through segments on different routes, connected by splices at intermediate structures.

## Equipment Functions

Equipment types have a configured **function** that determines implicit internal connections:
- **Pass-through** (e.g., patch panel): 1:1 mapping, in port N connects to out port N
- **Splitter** (e.g., 1:8 splitter): 1 input connects to N outputs
- **Combiner/Mux**: N inputs combine to fewer outputs
- **Amplifier**: Pass-through with signal boost (1:1)

The function determines how signals traverse the equipment without explicit connection records.

## Circuit Model (Fiber)

Circuits (customer services) are modeled as qualified reference sets:
- On `fiber_segment`: field `circuits` stores URNs like `ftth_circuit/1324?fibers=1:1`
- On `equipment`: field `circuits` stores URNs like `ftth_circuit/1324?ports=in=1:1&out=1:1`

A circuit inherits its geometry from participating fiber_segment records.

## Validation Rules (Connectivity)

| Rule | Severity |
|------|----------|
| Connection pin ranges must not exceed the object's port/strand count | Blocker |
| Connection endpoints must reference existing objects | Blocker |
| Directed equipment: connections from OUT can only go to IN of next object | High |
| Pin ranges in a connection must be equal in size (from_high - from_low == to_high - to_low) | Blocker |
| No duplicate connections on the same pin range | High |
| Equipment function must be valid for the equipment type | Medium |

## Migration Implications

When migrating connectivity:
- Source systems may store connections as simple "A connects to B" without pin-level detail → need to infer pin ranges
- Source systems may not distinguish IN/OUT sides → need to determine directionality
- Strand numbering in source may differ from NMT conventions → need strand renumbering rules
- Equipment functions must be assigned based on source equipment type → map source type to NMT function
- If source has no connection data, connections may need to be derived from circuit/service records or left empty
