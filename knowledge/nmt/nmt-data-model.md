# IQGeo NMT Data Model Reference

## Overview

The IQGeo Network Management Toolkit (NMT) is a modern telecommunications network data model built on a hierarchical containment structure. The model separates **physical infrastructure** (structures, routes, conduits) from **transmission media** (cables, segments) and **connections** (circuits, patches).

**Key principle**: Explicit containment hierarchy via Foreign Key relationships, not spatial proximity.

## Reference Field Format (URN)

**CRITICAL**: All `reference` fields in NMT use **URN format**: `feature_type/id`

Examples:
- `manhole/12345` — references manhole with id 12345
- `fiber_cable/206` — references fiber_cable with id 206
- `ug_route/185` — references ug_route with id 185
- `mywcom_fiber_segment/717082` — references a fiber segment
- `cabinet/5` — references cabinet with id 5

This applies to ALL reference fields in CSVs:
- `housing`, `root_housing` — e.g., `manhole/140407`, `ug_route/160909`
- `in_structure`, `out_structure` — e.g., `pole/100`, `wall_box/500`
- `cable` — e.g., `fiber_cable/71708`
- `in_segment`, `out_segment` — e.g., `mywcom_fiber_segment/717081`
- `in_object`, `out_object` — e.g., `mywcom_fiber_segment/847901`

**DO NOT** use bare integer IDs (e.g., `12345`) — they will create broken references that cannot be resolved by the platform. The feature type prefix is required so NMT knows which table to look up the referenced record in.

**CSV Quoting**: URN reference fields **MUST be double-quoted** in CSV files for `myw_db load`. Without quotes, `myw_db` strips the type prefix (e.g., `wall_box/195453` becomes `195453`). Use Python's `csv` module with quoting logic that quotes any field containing `/`.

`reference_set` fields (e.g., `equipment`, `routes`) are **read-only computed fields** — never include them in CSVs.

## Core Object Types

### Feature (Base)

All NMT objects inherit from `Feature`, which provides:
- `id` — Unique identifier (URN format)
- `name` — Human-readable name
- Metadata (timestamps, audit trail, source system reference)
- Geometry (Point, LineString, or none)

### Structures (Point Features)

**Structures** are point-based physical locations where cables terminate or split.

#### Structure
- **Base**: Point geometry
- **Attributes**:
  - `name` — Structure identifier
  - `specification` — Type reference (pole, pedestal, cabinet, etc.)
  - `location` — GeoJSON Point geometry
  - `laborCosts` — Installation cost estimate
  - `in_fiber_segments` — Calculated reference set of incoming fiber segments
  - `out_fiber_segments` — Calculated reference set of outgoing fiber segments
- **Containment role**: Top-level container for equipment and conduits
- **Examples**: poles, pedestals, cabinets, buildings, cross-boxes

**Directional semantics for calculated structure segment sets**:
- `in_fiber_segments`: segments where `out_structure = this_structure` and `in_structure != this_structure`
- `out_fiber_segments`: segments where `in_structure = this_structure` and `out_structure != this_structure`

**Key**: Structures are the anchor points for hierarchical containment.

#### Equipment
- **Base**: Point feature inside a Structure (or nested in another Equipment)
- **Attributes**:
  - `name` — Equipment identifier
  - `specification` — Equipment type (splitter, amplifier, patch panel)
  - `housing` — Direct parent (Structure or Equipment URN)
  - `rootHousing` — Top-level Structure URN
  - `circuits` — QURN list of circuits passing through
  - `location` — GeoJSON Point
- **Containment role**: Can be nested; organizes connection points
- **Examples**: patch panels, amplifiers, cross-connects, terminals

---

### Routes (Linear Physical Infrastructure)

**Routes** represent the physical paths cables and conduits follow between structures.

#### Route
- **Base**: LineString geometry from start Structure to end Structure
- **Attributes**:
  - `inStructure` — Starting Structure URN
  - `outStructure` — Ending Structure URN
  - `length` — Calculated or measured distance (meters)
  - `path` — GeoJSON LineString geometry
  - `laborCosts` — Installation/maintenance cost
- **Containment role**: Parent for Conduits (direct children), Cables (via Routes)
- **Examples**: underground conduit network between two poles, aerial cable run

**Segment definition**: A Route contains ordered **Segments**, each representing:
- A continuous span from pole-to-pole or junction-to-junction
- A cable's path through that Route
- Potential splice points with other cables

---

### Conduits (Containment Paths)

**Conduits** represent logical containers for cables within physical infrastructure. They model both discrete (underground pipes) and continuous (multi-pole aerial) containment.

#### Conduit
- **Base**: LineString; direct child of Route or Structure
- **Attributes**:
  - `name` — Conduit identifier
  - `specification` — Type (PVC pipe, ductbank, riser, etc.)
  - `housing` — Direct parent (Route or Structure URN)
  - `rootHousing` — Top-level Structure URN
  - `inStructure` — Entry Structure URN
  - `outStructure` — Exit Structure URN
  - **Chain attributes** (continuous conduits only):
    - `inConduit` — Previous Conduit in chain (URN)
    - `outConduit` — Next Conduit in chain (URN)
    - `conduitRun` — Parent ConduitRun URN
  - `path` — GeoJSON LineString
- **Topology**: Forms ordered chains through `inConduit`/`outConduit`; chains grouped by `conduitRun`
- **Examples**: underground duct, riser, aerial conduit between poles

**Key containment rule**: Cables are housed in Conduits; Conduits are housed in Routes or at Structures.

---

### Cables (Transmission Media)

**Cables** represent the actual transmission medium (fiber, copper, coax) carrying signals.

#### Cable
- **Base**: LineString path (may differ from physical route)
- **Attributes**:
  - `name` — Cable identifier (e.g., "MAIN-F001")
  - `specification` — Cable type reference (fiber type, strand count, impedance)
  - `technology` — Physical media: `fiber` | `copper` | `coax`
  - `count` — Number of strands/pairs in cable
  - `directed` — Boolean; true if distribution (directional flow)
  - `path` — GeoJSON LineString
  - `laborCosts` — Splicing/termination labor cost
- **Geometry note**: Cable path is derived from traversing Segments; may not match Route exactly
- **Examples**: "FIBER-MAIN-001" (single-mode fiber), "COPPER-LOOP-A" (twisted pair)

#### Segment

**Table**: `mywcom_fiber_segment` (also `mywcom_copper_segment`, `mywcom_coax_segment` for other media)

- **Base**: LineString geometry — Cable's footprint in a single Route (or Conduit span)
- **Properties**: `versioned: true`, `track_changes: true`
- **Attributes**:
  - `id` — `integer`, primary key (sequence-generated)
  - `cable` — `reference`, mandatory, indexed — Parent Cable URN
  - `housing` — `reference`, indexed — Immediate parent (Conduit or Route URN)
  - `root_housing` — `reference`, indexed — Top-level Route URN
  - `directed` — `boolean`, mandatory — Inherits from Cable
  - `forward` — `boolean`, mandatory — Direction relative to cable orientation
  - `in_structure` — `reference`, mandatory, indexed — Start Structure URN
  - `out_structure` — `reference`, mandatory, indexed — End Structure URN
  - `in_segment` — `foreign_key(mywcom_fiber_segment)` — Previous segment in chain
  - `out_segment` — `foreign_key(mywcom_fiber_segment)` — Next segment in chain
  - `length` — `double` (unit: meters) — Segment length
  - `path` — `linestring` — GeoJSON LineString geometry
  - `strand_info` — `string()`, read_only, hidden — Internal strand metadata
- **Calculated fields** (platform-computed, never loaded during migration):
  - `fiber_connections` — `reference_set` → `select(mywcom_fiber_connection.in_object, mywcom_fiber_connection.out_object)`
  - `circuit_segments` — `reference_set` → `select(mywcom_circuit_segment.cable_segment)`
- **Referenced by calculated fields on**:
  - Cable: `cable_segments` → `select(mywcom_fiber_segment.cable)`
  - Route: `cable_segments` → `select(mywcom_fiber_segment.housing, ...)`
  - Conduit: `cable_segments` → `select(mywcom_fiber_segment.housing, ...)`
  - Structure: `in_fiber_segments` → `method(in_fiber_segments)` (uses `out_structure` index)
  - Structure: `out_fiber_segments` → `method(out_fiber_segments)` (uses `in_structure` index)
- **Topology**: Ordered chain of Segments across Routes forms the complete Cable via `in_segment`/`out_segment`
- **Splice points**: Connections between Segments represent cable junctions

**Key principle**: Cables are segmented across Routes for granular failure and capacity management.

---

### Inside Plant (Building Internals)

**Inside Plant** features model the internal structure of buildings, data centers, and large structures — providing containment hierarchy below the Structure level.

#### Floor
- **Base**: Point feature inside a Structure
- **Attributes**:
  - `name` — Floor identifier (e.g., "Ground", "Level 1")
  - `housing` — Direct parent (Structure or Equipment URN) — `read_only`
  - `root_housing` — Top-level Structure URN — `read_only`
  - `equipment` — Child equipment housed on this floor — `read_only` reference_set
  - `circuits` — Circuits passing through — `read_only` reference_set
  - `labor_costs` — Installation cost
  - `location` — GeoJSON Point
- **Containment role**: Intermediate container within Structure → Floor → Room → Rack

#### Room
- **Base**: Point feature inside a Floor
- **Attributes**:
  - `name` — Room identifier (e.g., "Comms Room A")
  - `housing` — Direct parent (Floor URN) — `read_only`
  - `root_housing` — Top-level Structure URN — `read_only`
  - `equipment` — Child equipment in this room — `read_only` reference_set
  - `circuits` — Circuits passing through — `read_only` reference_set
  - `labor_costs` — Installation cost
  - `location` — GeoJSON Point
- **Containment role**: Contains Racks, Slots, and Equipment

#### Rack
- **Base**: Point feature inside a Room (or directly in a Structure)
- **Attributes**:
  - `name` — Rack identifier (e.g., "Rack-01")
  - `housing` — Direct parent (Room or Structure URN) — `read_only`
  - `root_housing` — Top-level Structure URN — `read_only`
  - `equipment` — Equipment mounted in this rack — `read_only` reference_set
  - `circuits` — Circuits passing through — `read_only` reference_set
  - `labor_costs` — Installation cost
  - `location` — GeoJSON Point
- **Containment role**: Contains Slots and Equipment

#### Slot
- **Base**: Point feature inside a Rack
- **Attributes**:
  - `name` — Slot identifier (e.g., "U1", "U12")
  - `housing` — Direct parent (Rack URN) — `read_only`
  - `root_housing` — Top-level Structure URN — `read_only`
  - `equipment` — Equipment in this slot — `read_only` reference_set
  - `circuits` — Circuits passing through — `read_only` reference_set
  - `labor_costs` — Installation cost
  - `location` — GeoJSON Point
- **Containment role**: Leaf container for Equipment

#### Splice Closure
- **Base**: Point feature inside a Structure or Equipment
- **Attributes**:
  - `name` — Closure identifier
  - `specification` — Type reference (`foreign_key(splice_closure_spec)`)
  - `housing` — Direct parent (Structure or Equipment URN) — `read_only`
  - `root_housing` — Top-level Structure URN — `read_only`
  - `equipment` — Child equipment — `read_only` reference_set
  - `fiber_splices` — `select(mywcom_fiber_connection.housing)` — connections housed here
  - `circuits` — Circuits passing through — `read_only` reference_set
  - `loss` — Splice loss (dB)
  - `location` — GeoJSON Point
- **Containment role**: Organizes fiber splices at a junction

#### Rack Suite (Inside Plant module)
- **Base**: Point feature with layout definition
- **Attributes**:
  - `name` — Suite identifier
  - `housing` — Direct parent — `read_only`
  - `root_housing` — Top-level Structure URN — `read_only`
  - `equipment` — Equipment in this suite — `read_only` reference_set
  - `circuits` — Circuits passing through — `read_only` reference_set
  - `layout` — JSONB rack layout definition
  - `vertical_spacing` / `horizontal_spacing` — Rack spacing (meters)
  - `populate_with` — JSONB auto-population template
  - `labor_costs` — Installation cost
  - `location` — GeoJSON Point
- **Containment role**: Groups multiple racks in a defined physical layout

**Inside Plant containment hierarchy**:
```
Structure
└── Floor
    └── Room
        ├── Rack
        │   └── Slot
        │       └── Equipment
        ├── Rack Suite
        │   └── Rack → Slot → Equipment
        └── Splice Closure
            └── Equipment
```

---

### Circuits (Services/Logical Paths)

**Circuits** represent services (data flows, voice calls, wavelengths) traveling through the network. NMT has three circuit types.

#### Logical Circuit
- **Base**: LineString geometry representing the logical path
- **Attributes**:
  - `name` — Circuit identifier
  - `in_feature` — Source equipment/structure URN — `read_only`
  - `out_feature` — Destination equipment/structure URN — `read_only`
  - `circuit_paths` — `select(circuit_path.logical_circuit)` — ordered path segments (calculated)
  - `path` — GeoJSON LineString
- **Relationship**: Composed of ordered CircuitPath segments
- **Examples**: "BACKBONE-CIRCUIT-001", "METRO-RING-CH3"

#### Circuit Path
- **Base**: LineString segment of a Logical Circuit
- **Attributes**:
  - `name` — Path segment identifier
  - `status` — Circuit status (enum: `circuit_status`)
  - `in_feature` — Entry point URN — `read_only`
  - `in_pins` — Entry port/strand range
  - `out_feature` — Exit point URN — `read_only`
  - `out_pins` — Exit port/strand range
  - `logical_circuit` — Parent Logical Circuit reference (FK)
- **Role**: Individual hop in an end-to-end circuit; platform resolves physical path

#### FTTH Circuit
- **Base**: LineString geometry (fiber-to-the-home specific)
- **Attributes**:
  - `name` — Circuit identifier
  - `in_feature` — OLT/splitter equipment URN — `read_only`
  - `in_pins` — Source port range
  - `out_feature` — ONT/customer equipment URN — `read_only`
  - `out_pins` — Destination port range
  - `connected` — Boolean (platform-set, `read_only`) — whether circuit is physically complete
  - `path` — GeoJSON LineString
  - `address` — Customer address reference (FK used by address.circuits select)
- **Role**: Specialized circuit for FTTH deployments; links to Address for service tracking
- **Examples**: "FTTH-001-SMITH", "GPON-PORT3-ONT42"

---

### Connections (Explicit Relationships)

**Connections** model explicit point-to-point relationships: splices, patch cords, port-to-port links.

#### Connection

**Table**: `mywcom_fiber_connection` (also `mywcom_copper_connection`, `mywcom_coax_connection` for other media)

- **Base**: Point geometry; usually at a Structure or Equipment
- **Properties**: `versioned: true`, `track_changes: true`
- **Attributes**:
  - `id` — integer, primary key (sequence-generated)
  - `in_object` — `reference`, indexed — Source object URN (Segment, Equipment, Circuit, Structure)
  - `out_object` — `reference`, indexed — Destination object URN
  - `in_side` — `string(16)`, mandatory — Source side/port name (e.g., "east", "north", "port_1")
  - `in_low` — `integer`, mandatory — Source strand/port range low (e.g., 1)
  - `in_high` — `integer`, mandatory — Source strand/port range high (e.g., 12)
  - `out_side` — `string(16)`, mandatory — Destination side/port name
  - `out_low` — `integer`, mandatory — Destination strand/port range low
  - `out_high` — `integer`, mandatory — Destination strand/port range high
  - `splice` — `boolean`, indexed — true if connecting two Segments (cable splice)
  - `housing` — `reference`, indexed — Immediate location Structure/Equipment URN
  - `root_housing` — `reference`, indexed — Top-level Structure URN
  - `location` — `point` — GeoJSON Point geometry
- **Semantics**:
  - **Splice** (segment-to-segment): Cable continuity across junction
  - **Patch** (equipment-to-equipment): Service connection via cord/fiber
  - **Cross-connect**: Equipment port-to-port connectivity
- **Referenced by calculated fields on**:
  - Structure: `fiber_connections` → `select(mywcom_fiber_connection.housing)`
  - Segment: `fiber_connections` → `select(mywcom_fiber_connection.in_object, mywcom_fiber_connection.out_object)`
  - Equipment: `fiber_connections` → `select(mywcom_fiber_connection.in_object, mywcom_fiber_connection.out_object)`
  - Splice Closure: `fiber_splices` → `select(mywcom_fiber_connection.housing)`
- **Examples**:
  - Splice: Segment A → Segment B at Structure X
  - Patch: Equipment A (port 1-4) → Equipment B (port 1-4) via fiber patch cord

---

### Non-Network Features

These features support planning, field operations, and demand management. They are not part of the network topology but are commonly present in NMT deployments and may be included in migrations.

#### Design
- **Base**: No geometry (has polygon `boundary` for spatial extent)
- **Attributes**:
  - `name` — Design identifier (primary key)
  - `details` — Description
  - `status` — Enum (`design_state`): New, In Progress, Complete, etc.
  - `user_group` — Owning team
  - `boundary` — Polygon defining design area
  - `created_at` / `create_user` — Auto-generated audit
  - `updated_at` / `update_user` — Auto-generated audit
- **Role**: Versioning container. All versioned network features reference a Design via `design_id`. Designs enable concurrent editing and change tracking across multiple users.
- **Migration note**: `design_id` is set by the platform when objects are created in a design context. During bulk migration, objects are typically loaded without a design (live data).

#### Address
- **Base**: Point geometry
- **Attributes**:
  - `name` — Address label
  - `street_number` / `street_name` — Street address components
  - `city` — City
  - `postcode` — Postal/zip code
  - `building` — Reference to associated Building structure — `read_only`
  - `service_status` — Enum (`service_status`): active, pending, etc.
  - `serving_equipment` — Reference to serving ONT/splitter/tap (`reference(fiber_splitter,fiber_tap,fiber_ont)`)
  - `serving_structure` — Reference to nearest network structure
  - `circuits` — `select(ftth_circuit.address)` — FTTH circuits serving this address (calculated)
  - `location` — GeoJSON Point
- **Role**: Demand-side feature linking customers to the network. Connects to FTTH circuits and serving equipment.
- **Migration note**: Often loaded from external address databases (national post office, customer records). The `building` FK is platform-managed based on spatial containment.

#### Service Area
- **Base**: Polygon geometry
- **Attributes**:
  - `name` — Area identifier (primary key)
  - `boundary` — Polygon geometry
- **Role**: Simple named boundary defining a service territory (e.g., exchange area, cabinet serving area)
- **Migration note**: Typically imported from planning systems or GIS boundary datasets.

#### Cabinet Area (Comsof module)
- **Base**: Polygon geometry
- **Attributes**:
  - `boundary` — Polygon geometry
  - `comsof_auto` — Boolean; true if imported from Comsof planning tool
- **Role**: Defines the serving area for a cabinet. Used in FTTH planning to assign addresses to cabinets.
- **Migration note**: Only present when Comsof integration is enabled.

#### Hazard
- **Base**: Point geometry
- **Attributes**:
  - `hazard_type` — Enum (`hazard_type`): e.g., overhead wires, traffic, confined space
  - `description` — Free-text hazard details
  - `photo_upload` — File attachment (field photo)
  - `location` — GeoJSON Point
  - `design_id` — Associated design
- **Role**: Field-captured safety hazard near network infrastructure. Used during survey and construction.
- **Migration note**: Rarely migrated from source systems; typically captured live in the field.

#### Permit Area
- **Base**: Polygon geometry
- **Attributes**:
  - `permit_type` — Enum (`permit_type`): road opening, wayleave, etc.
  - `permit_id` — External permit reference number
  - `valid_from` / `valid_to` — Date range for permit validity
  - `issuing_authority` — Authority name
  - `boundary` — Polygon geometry
  - `design_id` — Associated design
- **Role**: Regulatory permit zone with validity tracking. Links construction work to required permissions.
- **Migration note**: May be migrated from project management or permitting systems.

#### Under Construction
- **Base**: Point geometry
- **Attributes**:
  - `type_of_work` — Enum (`construction_type`): e.g., trenching, aerial, splicing
  - `start_date` / `end_date` — Construction period
  - `notes` — Free-text description
  - `location` — GeoJSON Point
  - `design_id` — Associated design
- **Role**: Marks active construction sites on the map for awareness and coordination.
- **Migration note**: Operational feature; rarely migrated.

---

## Containment Hierarchy

The NMT model enforces a **strict containment hierarchy**:

```
Structure
├── Floor
│   └── Room
│       ├── Rack
│       │   └── Slot
│       │       └── Equipment
│       ├── Rack Suite
│       │   └── Rack → Slot → Equipment
│       └── Splice Closure
│           └── Equipment
├── Equipment
│   ├── Equipment (nested)
│   └── Conduit (starts/ends here)
├── Conduit
│   └── Cable → Segment
└── Route
    ├── Segment (Cable spans)
    ├── Conduit (traverse)
    └── Route (nested segments)
```

**Rules**:
1. **Every Segment must have a `housing`** (direct parent Route or Conduit)
2. **Every Conduit must have a `housing`** (parent Route or Structure)
3. **Root housing** attributes trace back to top-level Structure
4. **Cables never contain objects**; they traverse Segments
5. **Inside Plant objects** (Floor, Room, Rack, Slot) chain via `housing` back to Structure

---

## Containment Inference Rules

When source data lacks explicit parent-child FKs, use these heuristics:

### Distance-Based (Spatial Proximity)
- Assign Cable Segments to nearest Route or Conduit
- Assign Equipment to nearest Structure (within threshold)
- Use Route geometry to snap unattached Conduits

### Naming-Based (Hierarchical Codes)
- Conduit name includes parent Route code → infer housing
- Equipment name includes parent Structure code → infer housing
- Example: "ROUTE-01" contains "CONDUIT-01A", "01B", etc.

### Topology-Based (Network Flow)
- Segment must run through a Route or Conduit
- Derive Route from Cable endpoints (inStructure → outStructure)
- Order Segments by position along Route (0.0 → 1.0 normalized distance)

### Synthetic Generation
- If no Route exists between two Structures with a Cable, create one
- If Cable crosses multiple Structures without Segments, segment it
- Default to creating continuous Conduits for underground cables

---

## Connectivity Patterns

### Pattern 1: Fiber to Two Splice Points

**Source**: Two splice records (from/to cable IDs) at a location

```
Cable A, Segment 1 ─────┐
                        ├─ Connection (splice: true)
Cable A, Segment 2 ─────┘
```

**Target**: Single Connection object with:
- `splice=true`
- `inObject=Segment1`, `outObject=Segment2`
- `housing=Structure` (location of splice)

---

### Pattern 2: Equipment Port Cross-Connect

**Source**: Two patch records (in/out equipment, port ranges) at a location

```
Equipment A (port 1-4) ─────┐
                           ├─ Connection (patch)
Equipment B (port 1-4) ─────┘
```

**Target**: Connection with:
- `inObject=Equipment A URN`, `inLow=1`, `inHigh=4`
- `outObject=Equipment B URN`, `outLow=1`, `outHigh=4`
- `splice=false` (not a cable splice)
- `housing=Structure` (cabinet location)

---

### Pattern 3: Circuit Service End-to-End

**Source**: Circuit records (in/out terminals, port info)

```
Structure A (Equipment X, port 7) ─────────►
                                    Circuit
◄───────── Structure B (Equipment Y, port 3)
```

**Target**: Circuit object with:
- `inFeature=Equipment X URN`, `inPins="7"`
- `outFeature=Equipment Y URN`, `outPins="3"`
- `path=derived` from Segments and Connections en route

---

## Topology Construction Algorithm

### Phase 1: Build Base Objects
1. Create Structures (poles, buildings)
2. Create top-level Cables
3. Assign specifications from source system mappings

### Phase 2: Derive Routes
For each pair of Structures with Cables between them:
1. Shortest-path between Structure A and Structure B (using existing Route geometry or derived)
2. Create Route if none exists
3. Assign geometry from source system (conduit network, cable routing)

### Phase 3: Segment Cables
For each Cable traversing multiple Structures:
1. Project Cable onto Route geometry (or derive path)
2. Split into ordered Segments at each Structure/junction
3. Assign each Segment to a Route or Conduit parent
4. Set `inStructure`, `outStructure`, `rootHousing`

### Phase 4: Assign Conduits
For each Route segment:
1. If source has duct/conduit data → create Conduit objects
2. Chain continuous Conduits via `inConduit`/`outConduit`
3. Assign `housing=Route` for discrete conduits
4. Chain via `conduitRun` for continuous multi-span conduits

### Phase 5: Build Connections
For each splice/patch/cross-connect in source:
1. Locate both end objects (Segments, Equipment)
2. Create Connection with proper `inObject`/`outObject`
3. Link to `housing` (Structure or Equipment)
4. Set strand/port ranges

---

## Calculated Fields

Calculated fields are defined by IQGeo platform metadata with either `value: "method(...)"` or `value: "select(...)"`. They are never loaded during migration — the platform computes them at runtime.

Both `method()` and `select()` fields are platform-calculated:
- **`method(x)`** — calls a Python/JS method at runtime to resolve the value
- **`select(table.field, ...)`** — performs a reverse-lookup query on related tables
- **`select()`** — empty select; resolved by platform internal lookup (e.g. child equipment by housing FK)

### Structure

| Field | Type | Calculation |
|---|---|---|
| `equipment` | `reference_set` | `select()` — child equipment housed in this structure |
| `routes` | `reference_set` | `select()` — routes starting or ending at this structure |
| `in_fiber_segments` | `reference_set` | `method(in_fiber_segments)` — segments where `out_structure = this` and `in_structure != this` |
| `out_fiber_segments` | `reference_set` | `method(out_fiber_segments)` — segments where `in_structure = this` and `out_structure != this` |
| `cables` | `reference_set` | `method(cables)` — cables derived from in/out fiber segments |
| `fiber_connections` | `reference_set` | `select(mywcom_fiber_connection.housing)` — connections housed here (cabinet only) |

### Route

| Field | Type | Calculation |
|---|---|---|
| `in_structure` | `reference` | `read_only` — set by platform from geometry start point |
| `out_structure` | `reference` | `read_only` — set by platform from geometry end point |
| `cable_segments` | `reference_set` | `select(mywcom_fiber_segment.housing, mywcom_copper_segment.housing, mywcom_coax_segment.housing)` |
| `cables` | `reference_set` | `method(cables)` — cables with segments in this route |
| `conduits` | `reference_set` | `select()` — conduits housed in this route (ug_route) |

### Cable (fiber / copper / coax)

| Field | Type | Calculation |
|---|---|---|
| `cable_segments` | `reference_set` | `select(mywcom_fiber_segment.cable)` — segments belonging to this cable |
| `cable_slacks` | `reference_set` | `select(mywcom_fiber_slack.cable)` — slack records for this cable |
| `splices` | `reference_set` | `method(splices)` — splice connections on this cable |
| `connections` | `reference_set` | `method(connections)` — all connections on this cable |
| `length` | `double` | `method(length)` — computed cable length (copper_cable only) |

### Segment

| Field | Type | Calculation |
|---|---|---|
| `fiber_connections` | `reference_set` | `select(mywcom_fiber_connection.in_object, mywcom_fiber_connection.out_object)` |
| `circuit_segments` | `reference_set` | `select(mywcom_circuit_segment.cable_segment)` — circuit segments using this cable segment |

### Conduit

| Field | Type | Calculation |
|---|---|---|
| `conduits` | `reference_set` | `select()` — child conduits nested in this conduit |
| `cable_segments` | `reference_set` | `select(mywcom_fiber_segment.housing, mywcom_copper_segment.housing, mywcom_coax_segment.housing)` |
| `cables` | `reference_set` | `method(cables)` — cables with segments housed in this conduit |
| `continuousConduits` | `reference_set` | `method(continuousConduits)` — blown fiber bundle/tube only |

### Equipment

| Field | Type | Calculation |
|---|---|---|
| `fiber_connections` | `reference_set` | `select(mywcom_fiber_connection.in_object, mywcom_fiber_connection.out_object)` |
| `cables` | `reference_set` | `method(cables)` — cables connected to this equipment |
| `equipment` | `reference_set` | `select()` — child equipment nested in this equipment |

### Circuit

| Field | Type | Calculation |
|---|---|---|
| `circuit_paths` | `reference_set` | `select(circuit_path.logical_circuit)` — path segments for this circuit |

---

## Validation Checklist

- [ ] All Segments have `cable` reference to parent Cable
- [ ] All Segments have `housing` (Route or Conduit)
- [ ] All Conduits have `housing` (Route or Structure)
- [ ] All Equipment has `housing` (Structure or Equipment)
- [ ] All Connections have `inObject` and `outObject`
- [ ] Segment chains are continuous (no gaps in Routes)
- [ ] No orphaned Structures, Equipment, Conduits, or Cables
- [ ] Geometry valid and consistent (LineString/Point types)
- [ ] Root housing attributes point to top Structure
- [ ] Circuits reference existing Segments or Equipment

---

## Data Model JSON Schema

See `nmt-model-schema.json` for formal JSON Schema definitions of all objects.

