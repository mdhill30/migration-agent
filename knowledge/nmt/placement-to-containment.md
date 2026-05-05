# Placement-Based to Containment Model Migration

## The Problem

Many source systems use a **placement-based** model where spatial proximity implies relationships:
- Equipment is drawn "near" a structure on the map
- Cables are drawn as single continuous lines
- Relationships are visual, not stored as foreign keys
- There are no internal cable segments, no housing references, no explicit topology

NMT requires an **explicit containment** model where:
- Every contained object has an explicit `root_housing` FK reference
- Cables are segmented into chains of cable_segments with explicit ordering
- Routes explicitly connect structures with FK references
- Geometry is inherited from housing (not independently stored)

## Common Source Patterns

### Pattern 1: Equipment Near Structure (No FK)

**Source**: Equipment features placed within a visual radius of a structure, no foreign key linking them.

**Detection signals**:
- Equipment layer has geometry (its own coordinates)
- No field referencing a structure ID
- Equipment visually clusters around structure points

**Inference method**: `spatial_proximity`
- Buffer each structure by configured radius (e.g., 5m)
- Assign equipment to nearest structure within buffer
- Flag equipment outside all buffers as DQR issues

**Confidence factors**:
- Single structure within radius → high confidence
- Multiple structures within radius → medium confidence (needs disambiguation)
- No structure within radius → low confidence (DQR issue, may need dummy structure)

### Pattern 2: Equipment With Structure FK

**Source**: Equipment has a field referencing its parent structure (e.g., `STRUCT_ID`, `LOCATION_ID`, `PARENT_MSLINK`).

**Detection signals**:
- FK field exists and has values matching structure IDs
- Equipment may or may not have independent geometry

**Inference method**: `foreign_key`
- Direct mapping: source FK → NMT `root_housing`
- Validate that FK values resolve to actual structures
- Flag broken references as DQR issues

### Pattern 3: Unsegmented Cables (Single Line)

**Source**: A cable is one continuous polyline from start to end, passing through multiple structures.

**Detection signals**:
- Cable layer has linear geometry
- Cable geometries pass through/near multiple structure points
- No separate "cable segment" layer exists
- Cable may have start/end structure references but no intermediate structure info

**Inference method**: `segment_at_structures`
1. Identify all structures within snap tolerance of the cable line
2. Order structures along the cable geometry (by linear referencing / distance along line)
3. Split cable geometry at each structure point
4. Create one route-spanning cable_segment per inter-structure span
5. Create one internal cable_segment per structure crossing
6. Link segments with `prev_segment` / `next_segment`
7. Create routes between consecutive structures (if routes don't exist)

**Parameters**:
- `snap_tolerance_m`: How close a structure must be to the cable to count as "on" it (default: 2m)
- `create_internal_segments`: Whether to create internal segments at each structure (default: true)
- `create_routes`: Whether to synthesize routes if they don't exist (default: true)

### Pattern 4: Cables With Segment Table (Pre-Segmented)

**Source**: Separate cable and cable_segment tables already exist.

**Detection signals**:
- Two related layers: cables (attributes) and segments (geometry + FK to cable)
- Segments may or may not have route/housing references

**Inference method**: `foreign_key` + `segment_ordering`
- Map segment.cable_fk → NMT `cable_ref`
- Determine segment order from geometry (path distance) or sequence field
- Assign housing from explicit FK or spatial intersection with routes

### Pattern 5: No Routes in Source

**Source**: Only structures and cables exist — no linear route/conduit features.

**Detection signals**:
- No linear layer that connects structures
- Cables exist as lines between structures
- May have a "conduit" or "duct" layer that could serve as routes

**Inference method**: `derive_from_cables` or `derive_from_conduits`
1. For each pair of adjacent structures along a cable path, create a route
2. Set route geometry = cable geometry between those structures
3. Deduplicate routes where multiple cables share the same inter-structure span
4. Set `start_structure` and `end_structure` on each route

### Pattern 6: Equipment Hierarchy (Nested Equipment)

**Source**: Equipment has parent-child relationships (rack contains shelf contains card).

**Detection signals**:
- Self-referencing FK in equipment table (e.g., `PARENT_EQUIP_ID`)
- Or separate tables per level (RACK, SHELF, CARD) with inter-table FKs

**Inference method**: `foreign_key` (hierarchical)
- Map parent FK → NMT `housing` (direct parent equipment)
- Set `root_housing` to the top-level structure (walk up hierarchy)
- Preserve nesting depth

### Pattern 7: Connection Records

**Source**: Explicit connection/splice/patch records exist.

**Detection signals**:
- Table with fields like `FROM_EQUIP`, `FROM_PORT`, `TO_EQUIP`, `TO_PORT`
- Or splice tables with `CABLE_A`, `STRAND_A`, `CABLE_B`, `STRAND_B`

**Inference method**: `connection_table`
- Map source connection fields to NMT pin-range notation
- Determine side (IN/OUT) from source port naming or equipment type
- Determine pin numbers from source strand/port numbering

### Pattern 8: Naming Convention Implies Relationship

**Source**: Object names encode their parent (e.g., equipment named "MH-001-SPLICE-01" belongs to manhole "MH-001").

**Detection signals**:
- Naming patterns with common prefixes
- Parseable structure in object names/IDs

**Inference method**: `naming_convention`
- Define regex/pattern to extract parent reference from child name
- Validate extracted references against actual parent objects
- Fall back to spatial proximity if naming parse fails

## Decision Matrix

| Source Has | Routes Exist | Cables Segmented | Equipment FK | Strategy |
|-----------|-------------|-----------------|-------------|----------|
| FK to structure | Yes | Yes | Yes | Direct mapping (simplest) |
| FK to structure | Yes | No | Yes | Segment cables at route boundaries |
| FK to structure | No | No | Yes | Derive routes from cables, then segment |
| No FK | Yes | Yes | No | Spatial proximity for equipment housing |
| No FK | Yes | No | No | Spatial proximity + cable segmentation |
| No FK | No | No | No | Full inference: proximity + route derivation + segmentation |

## Synthetic Object Generation

When source data is insufficient, synthetic objects must be created:

### Dummy Structures
- **When**: Cable passes through an area with no mapped structure (e.g., slack point, splice point not in source)
- **Policy**: `migration.yaml` → `dummy_structure_policy` controls whether to auto-create or flag for review
- **Naming**: Prefix with configured prefix (e.g., `ai_structure_001`)

### Internal Cable Segments
- **When**: Cable segmentation creates structure crossings
- **Always**: Every structure crossing needs an internal segment for cable continuity
- **Geometry**: Inherits from structure (point)

### Synthetic Routes
- **When**: Source has no route layer, routes derived from cable geometry
- **Geometry**: Extracted from cable lines between structures
- **Deduplication**: Multiple cables on same path → single route

## Confidence Scoring

Each inference should carry a confidence score:
- **High** (>90%): Direct FK match, unambiguous spatial match (single candidate within tolerance)
- **Medium** (60-90%): Multiple candidates but clear best match, naming convention match with validation
- **Low** (<60%): Multiple equidistant candidates, naming parse ambiguous, no candidates within tolerance

Low-confidence inferences should be flagged as DQR issues for human review.

## Common Pitfalls

1. **Coordinate system mismatch**: Source equipment in different CRS than structures → proximity calculation wrong
2. **Z-coordinate confusion**: 3D coordinates where Z is elevation vs. Z is meaningless → affects proximity
3. **Multi-point structures**: Buildings with large footprints — centroid distance is misleading
4. **Aerial vs. underground**: Equipment on a pole vs. in a manhole below — same XY, different context
5. **Boundary structures**: Equipment at the exact boundary between two structures — need disambiguation rule
6. **Cable direction ambiguity**: Source cable has no intrinsic direction — segment ordering may be arbitrary
7. **Missing intermediate structures**: Cable goes A→B but passes through unmapped C — creates oversized segments
