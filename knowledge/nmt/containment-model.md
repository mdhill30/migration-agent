# NMT Containment Model

## Overview

Network Manager Telecom divides objects into **top-level objects** (positioned on the map) and **contained objects** (inherit location from their housing). This strict hierarchy is the backbone of NMT data integrity.

## Top-Level Objects

| Object | Geometry | Description |
|--------|----------|-------------|
| **Structure** | Point | Buildings, cabinets, poles, manholes, chambers, wall boxes. Houses equipment and cable segments. Connected to other structures via routes. |
| **Route** | Linear | Path between two structures. Houses cable segments and conduits. References `start_structure` and `end_structure`. Direction is not significant. |

## Contained Objects

| Object | Housed In | Key References | Geometry |
|--------|-----------|----------------|----------|
| **Equipment** | Structure or Equipment | `root_housing` → structure | Inherited from `root_housing` |
| **Cable** | (virtual — composed of segments) | Ordered list of cable segments | Inherited from segments |
| **Cable Segment** | Route or Conduit | `root_housing` → route/structure, `cable_ref` → cable, `prev_segment`, `next_segment` | Inherited from `root_housing` |
| **Conduit** | Route or Conduit | `root_housing` → route, `start_structure`, `end_structure`, `prev_conduit`, `next_conduit` | Inherited from `root_housing` |

## Key Foreign Key References

```
equipment.root_housing      → structure (the top-level structure housing this equipment)
equipment.housing           → structure or equipment (direct parent in hierarchy)

cable_segment.root_housing  → route or structure (top-level housing)
cable_segment.housing       → route or conduit (direct container)
cable_segment.cable_ref     → cable (the cable this segment belongs to)
cable_segment.prev_segment  → cable_segment (previous in chain, NULL if first)
cable_segment.next_segment  → cable_segment (next in chain, NULL if last)

conduit.root_housing        → route
conduit.start_structure     → structure
conduit.end_structure       → structure
conduit.prev_conduit        → conduit (for continuous conduit types)
conduit.next_conduit        → conduit (for continuous conduit types)

route.start_structure       → structure
route.end_structure         → structure
```

## Containment Hierarchy (Nesting)

```
Structure
├── Equipment
│   └── Equipment (nested: rack → shelf → card)
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

Internal segments connect two route-spanning segments and ensure cable continuity through structures.

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
