# NMT Topology Rules

## Overview

NMT topology describes how network objects connect spatially: structures connected by routes, cables threading through routes as ordered segment chains, and conduits providing physical pathways within routes.

## Structure-Route Topology

```
Structure A ←——— Route ———→ Structure B
   │                              │
   │  start_structure       end_structure
   │                              │
   └── (equipment, internal segments)
```

- Every route has exactly one `start_structure` and one `end_structure`
- Route direction (start→end) is not semantically significant — it's a geometric convention
- A structure can be the start/end of multiple routes
- Routes model physical pathways: trenches, aerial spans, conduit paths

## Cable Segmentation

A cable in NMT is an ordered chain of cable segments. Each segment spans exactly one route (or is internal to one structure).

```
Cable: [seg1] → [seg2] → [seg3] → [seg4] → [seg5]

Structure A   Route 1   Structure B   Route 2   Structure C
  [seg1]  →   [seg2]  →   [seg3]   →  [seg4]  →   [seg5]
 (internal)  (in route)  (internal)  (in route)  (internal)

seg1.root_housing = Structure A (internal)
seg2.root_housing = Route 1
seg3.root_housing = Structure B (internal)
seg4.root_housing = Route 2
seg5.root_housing = Structure C (internal)
```

### Segment Chain Rules

- `prev_segment` / `next_segment` form a doubly-linked list
- First segment: `prev_segment = NULL`
- Last segment: `next_segment = NULL`
- Two valid chain patterns:
  - **Transit-only** (preferred for migration): `transit(route1) → transit(route2) → ...`
  - **Alternating** (full model): `internal(struct) → transit(route) → internal(struct) → ...`
- Internal segments are **optional** — they are only needed when:
  - Equipment is mounted at a structure and connections terminate there
  - Explicit cable slack or storage loops exist at a structure
- For migration, **transit-only chains are preferred** unless the source data has splice/termination detail that requires internal segments

### Cable Direction (Forward Flag)

Each cable segment has a `forward` flag:
- `True`: segment direction matches the route direction (start_structure → end_structure)
- `False`: segment direction is opposite to the route direction

For directed cables, this determines which end is IN and which is OUT.

## Conduit Topology

Conduits model physical tubes within routes:

```
Route
├── Conduit (duct)
│   ├── Sub-conduit
│   │   └── Cable Segment
│   └── Cable Segment
└── Cable Segment (directly in route, no conduit)
```

### Continuous Conduits

Conduit types marked as "continuous" chain through multiple routes:
```
Conduit span 1 (Route 1) → Conduit span 2 (Route 2) → Conduit span 3 (Route 3)
  prev_conduit = NULL         prev = span1                  prev = span2
  next_conduit = span2        next = span3                  next = NULL
```

Each conduit span references:
- `root_housing` → the route it traverses
- `start_structure` / `end_structure` → structures at each end

## Directionality

### Directed (Unidirectional) Cables
- Sides labeled IN and OUT
- IN = upstream end, OUT = downstream end
- Application enforces: OUT port → IN side of cable → OUT side of cable → IN port
- Distribution cables are typically directed

### Undirected (Bidirectional) Cables
- Sides labeled A and Z
- No intrinsic direction — either side can connect to IN or OUT ports
- No directionality constraints on connections

### Directed Equipment
- Ports labeled IN and OUT
- Signal flows IN → (internal function) → OUT
- Application enforces connection direction

### Undirected Equipment
- Ports labeled Front and Back
- No intrinsic signal direction
- Any port can connect to any other port (patch panels)

## Route Derivation Strategies

When source data lacks explicit routes:

1. **From cable geometry**: Split cable lines at structure locations to create route segments between consecutive structures
2. **From conduit/duct geometry**: Use existing linear duct features as routes
3. **From connectivity records**: If source records "A connects to B", create routes between A and B
4. **Synthetic**: Create minimal routes to satisfy containment requirements

## Cable Segmentation Strategies

When source has unsegmented cables (single line from A to Z):

1. **Segment at structures**: Find all structures along the cable path, split cable geometry at each structure, create one route-segment + one internal-segment per structure crossing
2. **Segment at route boundaries**: If routes exist, split cable at route start/end points
3. **Minimal segmentation**: Create minimum segments needed (one per route the cable traverses)

### Proven Implementation: Spatial Snap Segmentation

When source data provides cable geometry and structure point locations but no explicit segment records, use this algorithm (validated on Summit Fiber: 8,270 cables → 6,026 segments):

**Algorithm**:
1. Build spatial index of all structures (by `external_ref`) with their WGS84 point locations
2. Build route index keyed by `(in_structure_ref, out_structure_ref)` pairs (both orderings)
3. For each cable:
   a. Walk cable vertices; find structures within `SNAP_TOLERANCE` of each vertex
   b. Split cable geometry at each matched structure point
   c. Create one segment per consecutive structure pair (sub-linestring between them)
   d. Look up the route matching the segment's `(in_structure, out_structure)` pair
   e. Assign `housing = route` if found; leave empty if no matching route
   f. Set `forward = True` if segment direction matches route direction (in→out)

**Key parameters**:
- `SNAP_TOLERANCE`: 0.0003° (~30m at mid-latitudes) — balances matching accuracy vs. false positives
- Cables with no structure matches are skipped (typically short drops or isolated segments)
- Cables with only one structure match produce no segments (need at least 2 for a span)

**Output fields**: `cable`, `housing`, `root_housing`, `directed`, `forward`, `in_structure`, `out_structure`, `in_segment`, `out_segment`, `length`, `path`

**Segment path geometry**: Each transit segment's `path` MUST be populated with the EWKT linestring of its housing route. The trace engine reads `segment.path.coords[0]` to determine start/end coordinates — a NULL path causes `AttributeError: 'NoneType' object has no attribute 'coords'` at runtime. When generating segments, read the route geometry from the route CSV/table and copy it to the segment's `path` field.

**Statistics** (typical fiber OSP migration):
- ~73% of cables produce segments (multi-structure match)
- ~27% of cables have no structure match (short drops, spur connections)
- Average segments per cable: 1.2 (most cables span 1-2 routes)

**Important**: This approach produces transit-only segment chains (one segment per route span). Internal segments are NOT generated. This is the preferred approach for migration — internal segments should only be added in a later pass if the source data contains splice/termination records that require them.

## Validation Rules (Topology)

| Rule | Severity |
|------|----------|
| Every route must reference existing start_structure and end_structure | Blocker |
| Cable segment chain must be continuous (no NULL gaps in middle of chain) | Blocker |
| Transit segments must be housed in a route whose in/out structures match segment in/out structures | Blocker |
| Adjacent transit segments must share a common structure (seg1.out_structure == seg2.in_structure) | High |
| Internal segments (if present) must be housed in a structure that is start/end of adjacent route | High |
| Conduit start/end structures must match its route's start/end structures | Medium |
| Continuous conduit chains must traverse connected routes | Medium |
| No isolated structures (structures with no routes, unless explicitly allowed) | Low |
