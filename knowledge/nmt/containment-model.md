# NMT Containment Model

## Overview

The NMT containment model enforces **explicit hierarchical relationships** between network objects. Unlike spatial systems where proximity implies containment, NMT requires direct Foreign Key (FK) assignments via `housing` attributes.

This document provides detailed guidance on inferring, validating, and generating containment relationships during migration.

## Containment Hierarchy

```
Structure (root)
│
├─ Equipment (optional nesting)
│  └─ Equipment* (recursive nesting allowed)
│
├─ Route (logical connection path)
│  ├─ Conduit (within route)
│  │  └─ Cable → Segment (within conduit)
│  │
│  └─ Cable → Segment (directly in route)
│
└─ Conduit (at structure start/end)
   └─ Cable → Segment (if conduit is discrete)
```

## Containment Attributes

Every object (except Structures) must declare:

| Attribute | Cardinality | Meaning | Example |
|---|---|---|---|
| `housing` | 1:1 | Direct parent object | `route_main_01` |
| `rootHousing` | 1:1 | Top-level Structure URN | `pole_123` |

**Rules**:
- `rootHousing` must always point to a Structure
- `housing` can point to any container (Route, Structure, Equipment, Conduit)
- Nested objects: `housing` is direct parent, `rootHousing` traces to Structure

### Example: Nested Equipment

```
Structure: pole_main
├─ Equipment: patch_panel_01 (housing=pole_main, rootHousing=pole_main)
   ├─ Equipment: sub_panel_a (housing=patch_panel_01, rootHousing=pole_main)
   └─ Equipment: sub_panel_b (housing=patch_panel_01, rootHousing=pole_main)
```

## Top-Level Objects

| Object | Geometry | Description |
|--------|----------|-------------|
| **Structure** | Point | Buildings, cabinets, poles, manholes, chambers, wall boxes. Anchor for containment hierarchy. |
| **Route** | Linear | Path between two structures. Houses cable segments and conduits. References `inStructure` and `outStructure`. |

## Contained Objects

| Object | Housed In | Key References | Geometry |
|--------|-----------|----------------|----------|
| **Equipment** | Structure or Equipment | `rootHousing` → structure | Inherited from `rootHousing` |
| **Cable** | (virtual — composed of segments) | Ordered list of cable segments | Inherited from segments |
| **Segment** | Route or Conduit | `rootHousing` → route/structure, `cable` → cable, `sequenceOrder` | Inherited from `rootHousing` |
| **Conduit** | Route or Structure | `rootHousing` → route, `inStructure`, `outStructure`, `inConduit`, `outConduit` | Inherited from `rootHousing` |
├── Cable Segment (internal segment — within a single structure)
└── (connects to Routes)

Route
├── Conduit
│   ├── Conduit (nested: sub-duct within duct)
│   └── Cable Segment
└── Cable Segment (directly housed in route)
```

## Geometry Inheritance Rules

1. **Equipment** inherits geometry from `root_housing` (the top-level structure). Equipment has no independent geometry.
2. **Cable Segment** inherits geometry from `root_housing` (the route or structure it traverses). The `forward` flag indicates whether the segment direction matches the route direction.
3. **Conduit** inherits geometry from `root_housing` (the route).
4. **Cable** inherits geometry from the ordered union of its cable segments.
5. **Internal cable segments** (within a structure) inherit the point geometry of that structure.

## Internal Cable Segments

A cable segment housed within a single structure (not spanning a route) is called an **internal segment**. These model:
- Cable slack (excess cable coiled inside a structure)
- Risers (cable running between floors in a building)
- Cable passing through a structure without termination

Internal segments are **optional** in NMT. For migration projects, the preferred approach is to generate **transit-only segment chains** (one segment per route span, chained directly). Internal segments should only be added when the source data explicitly contains:
- Splice/termination records at a structure requiring a segment endpoint
- Measured cable slack or storage loops

A transit-only chain still correctly models cable topology — the `in_structure`/`out_structure` fields on adjacent transit segments identify the shared structure between them.

## Validation Rules (Containment)

| Rule | Severity |
|------|----------|
| Every equipment must have a valid `root_housing` referencing an existing structure | Blocker |
| Every cable segment must have a valid `root_housing` referencing an existing route or structure | Blocker |
| Every route must have valid `start_structure` and `end_structure` | Blocker |
| Cable segment chains must be continuous (no gaps in `prev_segment`/`next_segment`) | High |
| Equipment `root_housing` must be an ancestor in the containment tree | High |
| Conduit `start_structure` and `end_structure` must match the route's structures | Medium |
| No orphan contained objects (contained objects without valid housing) | Blocker |

## Migration Implications

When migrating from a placement-based system:
- Source equipment placed "near" a structure must be explicitly assigned to that structure via `root_housing`
- Source cables as single lines must be segmented at structure boundaries to create proper cable segment chains
- Routes may need to be synthesized from cable geometry between structures
- Internal cable segments must be created at each structure a cable passes through
- The containment hierarchy must be built bottom-up: structures first, then routes, then cables/equipment

---

## Containment Inference Rules

### Rule 1: Distance-Based Proximity

**When**: Source data lacks explicit parent FKs  
**How**: Assign object to nearest container of correct type within threshold

```sql
-- Assign Conduit to nearest Route (distance < 50m buffer)
UPDATE conduit c
SET housing = r.id
FROM route r
WHERE ST_DWithin(c.path::geography, r.path::geography, 50)
ORDER BY ST_Distance(c.path::geography, r.path::geography)
LIMIT 1;
```

**Thresholds** (configurable per project):
- Equipment to Structure: 500m (typical pole spacing)
- Conduit to Route: 5m (conduit should be within route corridor)
- Segment to Conduit: 1m (segment must be inside conduit)

### Rule 2: Naming Conventions (Hierarchical Codes)

**When**: Source naming encodes hierarchy  
**How**: Parse naming patterns to infer parent-child relationships

**Example patterns**:
```
Route naming:   "ROUTE_MAIN_01"
├─ Conduit:     "CONDUIT_MAIN_01A", "01B", "01C"
│                (prefix matches parent)
├─ Cable:       "CABLE_MAIN_01_FIB", "01_COP"
│                (prefix encodes route)
└─ Segment:     "SEG_MAIN_01_001", "001", "002"
                 (numbers indicate sequence in cable)
```

**Implementation**:
```yaml
containment_rules:
  - pattern: "^CONDUIT_(?P<route_code>\\w+)_"
    infers: housing from route with code $route_code
    
  - pattern: "^SEG_(?P<cable_name>\\w+)_(?P<sequence>\\d+)"
    infers: |
      housing from segment's cable parent (forward reference)
      sequence order from $sequence
```

### Rule 3: Topology-Based (Network Flow)

**When**: Source has cable endpoints (from/to structure) but no intermediate containment  
**How**: Derive Routes from cable topology, then assign Segments

**Algorithm**:

1. **Build initial Routes from cable endpoints**:
   ```sql
   INSERT INTO route (in_structure, out_structure, path)
   SELECT DISTINCT
     c.in_structure,
     c.out_structure,
     ST_ShortestLine(s1.location, s2.location)  -- geodesic
   FROM cable c
   JOIN structure s1 ON c.in_structure = s1.id
   JOIN structure s2 ON c.out_structure = s2.id;
   ```

2. **Segment cables across routes**:
   ```sql
   INSERT INTO segment (cable, housing, root_housing, sequence_order)
   SELECT
     c.id,
     r.id,  -- assign to route
     s.id,  -- root structure
     ROW_NUMBER() OVER (PARTITION BY c.id ORDER BY ...)
   FROM cable c
   JOIN route r ON (c.in_structure = r.in_structure AND c.out_structure = r.out_structure)
   JOIN structure s ON r.in_structure = s.id;
   ```

3. **Create intermediate Structures if cable spans multiple poles**:
   ```sql
   -- If cable path crosses polygon (buffer) around intermediate structure,
   -- split cable at that structure
   WITH intersects AS (
     SELECT c.id, s.id as structure_id
     FROM cable c, structure s
     WHERE ST_Intersects(c.path, ST_Buffer(s.location, 5))
       AND c.in_structure != s.id
       AND c.out_structure != s.id
   )
   -- Insert intermediate route segments...
   ```

---

## Synthetic Containment Generation

**When**: Source lacks structure entirely for intermediate containment  
**How**: Create synthetic parent objects based on cable topology

### Scenario 1: Cable with No Routing Structure

**Source data**:
```
Cable: FIBER-MAIN-001
  from: pole_100
  to: pole_200
  path: [lon,lat] → [lon,lat]
```

**Problem**: No Segments or Routes defined  
**Solution**: Generate synthetic Route

```yaml
synthetic_generation:
  missing_route:
    rule: "if cable.in_structure and cable.out_structure and no route exists"
    action: "create_route"
    template:
      name: "ROUTE_{in_structure}_{out_structure}"
      in_structure: "$cable.in_structure"
      out_structure: "$cable.out_structure"
      path: "$cable.path"
      specification: "auto_generated"
```

### Scenario 2: Cable with No Conduit Parent

**Source data**:
```
Cable: COPPER-LOOP-A
  segment_1: housed_in=route_main_01
  segment_2: housed_in=??? (missing)
```

**Problem**: Segment 2 has no parent  
**Solution**: Assign to same Route as Segment 1, or create Conduit

```yaml
fix_in_flight:
  orphan_segment_housing:
    check: "segment.housing IS NULL"
    strategy: "inherit_from_cable_route"
    action: |
      SELECT housing FROM segment
      WHERE cable = orphan.cable
      AND housing IS NOT NULL
      ORDER BY sequence_order DESC
      LIMIT 1
```

---

## Containment Validation

### Check 1: No Orphaned Objects

```sql
-- Find objects without housing
SELECT 'Equipment' as type, id, name
FROM equipment
WHERE housing IS NULL
UNION ALL
SELECT 'Conduit', id, name
FROM conduit
WHERE housing IS NULL
UNION ALL
SELECT 'Segment', id, name
FROM segment
WHERE housing IS NULL;
```

**Fix**: Assign housing via inference rules, or flag as DQR issue.

### Check 2: Housing Chain Integrity

```sql
-- Verify rootHousing points to actual Structure
SELECT s.id, s.name
FROM segment s
LEFT JOIN structure st ON s.root_housing = st.id
WHERE s.root_housing IS NOT NULL
AND st.id IS NULL;
```

**Fix**: Recalculate `rootHousing` by tracing `housing` chain to Structure.

### Check 3: Circular References

```sql
-- Detect cycles: object housing chains must terminate at Structure
WITH RECURSIVE chain AS (
  SELECT id, housing, 1 as depth
  FROM conduit
  WHERE housing IS NOT NULL
  
  UNION ALL
  
  SELECT c.id, next.housing, chain.depth + 1
  FROM chain
  JOIN conduit next ON chain.housing = next.id
  WHERE chain.depth < 100
)
SELECT DISTINCT id FROM chain WHERE depth = 100;
```

**Fix**: Investigate and correct circular `housing` assignments.

### Check 4: Type Compatibility

```sql
-- Verify housing type is valid for child type
SELECT c.id, c.housing, c_housing_type.type as housing_type
FROM conduit c
JOIN (
  SELECT id, 'route' as type FROM route
  UNION ALL
  SELECT id, 'structure' as type FROM structure
) c_housing_type ON c.housing = c_housing_type.id
WHERE c_housing_type.type NOT IN ('route', 'structure');
```

**Valid parent-child pairs**:
| Parent | Children |
|--------|----------|
| Structure | Equipment, Conduit |
| Equipment | Equipment, Connection |
| Route | Conduit, Segment |
| Conduit | Segment |

---

## Validation Rules (Containment)

| Rule | Severity |
|------|----------|
| Every equipment must have a valid `root_housing` referencing an existing structure | Blocker |
| Every cable segment must have a valid `root_housing` referencing an existing route or structure | Blocker |
| Every route must have valid `in_structure` and `out_structure` | Blocker |
| Cable segment chains must be continuous (no gaps in `sequence_order`) | High |
| Equipment `root_housing` must be reachable from containing structure | High |
| Conduit `in_structure` and `out_structure` must match the route's structures | Medium |
| No orphan contained objects (contained objects without valid housing) | Blocker |

---

## FAQ

**Q: Can a Segment be housed in Equipment instead of Route/Conduit?**  
A: Yes, if the segment terminates at equipment. Use sparingly; typically segments are in Routes/Conduits.

**Q: What if a cable spans 3 structures but we only have endpoints?**  
A: Create intermediate Segments at each structure intersection. Use topology-based segmentation.

**Q: How do we handle "virtual" structures with no physical location?**  
A: Assign synthetic location (e.g., centroid of child equipment). Document in DQR.

**Q: Can Equipment contain Routes or Conduits?**  
A: Not directly; Equipment is a leaf node (can only contain other Equipment or Connections).
