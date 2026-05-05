# IQGeo NMT Data Model Reference

## Overview

The IQGeo Network Management Toolkit (NMT) is a modern telecommunications network data model built on a hierarchical containment structure. The model separates **physical infrastructure** (structures, routes, conduits) from **transmission media** (cables, segments) and **connections** (circuits, patches).

**Key principle**: Explicit containment hierarchy via Foreign Key relationships, not spatial proximity.

## Core Object Types

### Feature (Base)

All NMT objects inherit from `Feature`, which provides:
- `id` — Unique identifier (URN format)
- `name` — Human-readable name
- Metadata (timestamps, audit trail, source system reference)
- Geometry (Point, LineString, or none)

### Structures (Point Features)

**Structures** are point-based physical locations where cables terminate or split.

**CRITICAL**: NMT does NOT use a single generic `structure` table. Each structure type is its own **separate feature type** with its own database table, `.def` file, and CSV for loading. The `myw_db load` command infers the target feature type from the CSV filename.

#### Concrete Structure Types

| NMT Feature Type | External Name | Key Fields | Typical Source |
|---|---|---|---|
| `pole` | Pole | id, name, location, type, height, owner, specification, installation_date | Wooden/steel poles |
| `cabinet` | Cabinet | id, name, location, specification, owner, installation_date | Street cabinets, FDHs |
| `manhole` | Manhole | id, name, location, specification, size_x/y/z, installation_date | Underground chambers |
| `wall_box` | Wall Box | id, name, location, specification, installation_date | Wall-mounted boxes |
| `building` | Building | id, name, location, owner | Head-ends, COs, data centers |
| `drop_point` | Drop Point | id, name, location, type, installation_date | Customer-facing DPs |

Each structure type has:
- `equipment` — reference_set of contained equipment (auto-populated)
- `routes` — reference_set of routes starting/ending here (auto-populated via `select(oh_route.in_structure,oh_route.out_structure,ug_route.in_structure,ug_route.out_structure)`)
- `in_fiber_segments` / `out_fiber_segments` — calculated segment sets
- `cables` — calculated cable set via method

**Generation rule**: When migrating, map each source structure record to the correct NMT feature type and produce a **separate CSV per type**. Do NOT consolidate into one file.

#### Structure
- **Base**: Point geometry
- **Attributes**:
  - `name` — Structure identifier
  - `specification` — Type reference (FK to `*_spec` table, e.g., `pole_spec`, `cabinet_spec`)
  - `location` — Point geometry (EWKT: `SRID=4326;POINT(lon lat)`)
  - `owner` — Owner string
  - `installation_date` — Date installed
  - `labor_costs` — Installation cost estimate
  - `in_fiber_segments` — Calculated reference set of incoming fiber segments
  - `out_fiber_segments` — Calculated reference set of outgoing fiber segments
- **Containment role**: Top-level container for equipment and conduits

**Directional semantics for calculated structure segment sets**:
- `in_fiber_segments`: segments where `out_structure = this_structure` and `in_structure != this_structure`
- `out_fiber_segments`: segments where `in_structure = this_structure` and `out_structure != this_structure`

**Key**: Structures are the anchor points for hierarchical containment.

#### Equipment
- **Base**: Point feature inside a Structure (or nested in another Equipment)

**CRITICAL**: Like structures, NMT uses **separate feature types per equipment category**. Each has its own `.def`, table, and CSV.

#### Concrete Equipment Types

| NMT Feature Type | External Name | Key Fields | Housing Model |
|---|---|---|---|
| `splice_closure` | Splice Closure | id, name, specification, root_housing, housing, location, loss | Contained in structure |
| `fiber_splitter` | Fiber Splitter | id, name, specification, root_housing, housing, location, directed, n_fiber_in_ports, n_fiber_out_ports | Contained in structure |
| `fiber_patch_panel` | Fiber Patch Panel | id, name, specification, root_housing, housing, location | Contained in structure/rack |
| `fiber_ont` | Fiber ONT | id, name, specification, root_housing, housing, location | Customer premises |
| `fiber_card` | Fiber Card | id, name, specification, root_housing, housing, location | In shelf/rack |
| `fiber_shelf` | Fiber Shelf | id, name, specification, root_housing, housing, location | In rack |
| `rack` | Rack | id, name, root_housing, housing, location | In room/structure |
| `coax_amplifier` | Coax Amplifier | id, name, specification, root_housing, housing, location | In structure |
| `coax_tap` | Coax Tap | id, name, specification, root_housing, housing, location | On pole/strand |

**Common equipment attributes**:
- `housing` — Direct parent reference (Structure, Rack, Room, or other Equipment)
- `root_housing` — Top-level Structure reference (always a structure type)
- `location` — Point geometry (EWKT)
- `specification` — FK to the corresponding `*_spec` table
- `fiber_connections` — reference_set via `select(mywcom_fiber_connection.housing)` (read-only)

**Generation rule**: Map each source equipment record to the correct NMT feature type. Produce a **separate CSV per equipment type**. The `housing` and `root_housing` fields must reference the **integer ID** of the parent structure (myw_db resolves cross-type references by ID).

- **Attributes**:
  - `name` — Equipment identifier
  - `specification` — Equipment type FK (e.g., `foreign_key(splice_closure_spec)`)
  - `housing` — Direct parent (Structure or Equipment reference)
  - `root_housing` — Top-level Structure reference
  - `location` — Point geometry (EWKT)
- **Containment role**: Can be nested; organizes connection points
- **Examples**: splice closures, fiber splitters, patch panels, ONTs

---

### Routes (Linear Physical Infrastructure)

**Routes** represent the physical paths cables and conduits follow between structures.

**CRITICAL**: NMT uses **separate feature types for route subtypes**:

| NMT Feature Type | External Name | Key Fields |
|---|---|---|
| `ug_route` | Route (Underground) | id, path, in_structure, out_structure, length, cover_type |
| `oh_route` | Route (Overhead) | id, path, in_structure, out_structure, length |

**Generation rule**: Split source routes by construction method / laying type. Produce `ug_route.csv` and `oh_route.csv` separately. Underground routes have a `cover_type` enum field (values: `direct_buried`, `duct`, etc.).

#### Route
- **Base**: LineString geometry from start Structure to end Structure
- **Attributes**:
  - `in_structure` — Starting Structure reference (integer ID)
  - `out_structure` — Ending Structure reference (integer ID)
  - `length` — Calculated or measured distance (meters)
  - `path` — LineString geometry (EWKT: `SRID=4326;LINESTRING(...)`)
  - `cover_type` — (ug_route only) Construction cover type enum
  - `cable_segments` — reference_set via `select(mywcom_fiber_segment.housing,...)` (read-only)
  - `cables` — Calculated cable set via method (read-only)
- **Containment role**: Parent for Conduits (direct children), Cable Segments
- **Examples**: underground conduit network between two poles, aerial cable run

**Note on structure references**: `in_structure` and `out_structure` are cross-type references. In the CSV, provide the integer ID of the target structure. NMT resolves the reference across all structure types (pole, cabinet, manhole, etc.) at load time.

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

**CRITICAL**: NMT uses technology-specific feature types:

| NMT Feature Type | External Name | Technology |
|---|---|---|
| `fiber_cable` | Fiber Cable | Fiber optic |
| `copper_cable` | Copper Cable | Copper twisted pair |
| `coax_cable` | Coax Cable | Coaxial |

#### Fiber Cable (`fiber_cable`)
- **Base**: LineString path
- **Attributes**:
  - `name` — Cable identifier (e.g., "MAIN-F001")
  - `specification` — FK to `fiber_cable_spec`
  - `type` — Cable type enum (`cable_type`)
  - `fiber_count` — Number of fibers (integer)
  - `directed` — Boolean; true if distribution (mandatory, default true)
  - `path` — LineString geometry (EWKT, mandatory)
  - `owner` — Owner string
  - `installation_date` — Date installed
  - `loss` — Fiber loss (dB/km)
  - `cable_segments` — reference_set via `select(mywcom_fiber_segment.cable)` (read-only)
- **Geometry note**: Cable path is derived from traversing Segments; typically matches route geometry
- **Examples**: "FIBER-MAIN-001" (single-mode fiber, 48-count)

#### Fiber Segment (`mywcom_fiber_segment`)
- **Base**: Cable's footprint in a single Route or Structure
- **Attributes**:
  - `cable` — Parent Cable reference (integer FK, mandatory)
  - `housing` — Immediate parent (Route or Structure reference)
  - `root_housing` — Top-level Route or Structure reference
  - `directed` — Boolean (mandatory); inherits from Cable
  - `forward` — Boolean (mandatory); segment direction relative to cable
  - `in_structure` — Entry Structure reference (mandatory)
  - `out_structure` — Exit Structure reference (mandatory)
  - `in_segment` — Previous segment in chain (FK to `mywcom_fiber_segment`)
  - `out_segment` — Next segment in chain (FK to `mywcom_fiber_segment`)
  - `in_equipment` — Equipment at entry point (reference)
  - `out_equipment` — Equipment at exit point (reference)
  - `path` — LineString geometry (EWKT, mandatory)
  - `fiber_connections` — reference_set via `select(mywcom_fiber_connection.in_object,mywcom_fiber_connection.out_object)` (read-only)
- **Topology**: Ordered chain of Segments via `in_segment`/`out_segment` FKs forms the complete Cable path
- **Internal segments**: Segments housed in structures (not routes) represent cable within structures; `in_structure == out_structure` for these

**Key principle**: Cables are segmented across Routes for granular failure and capacity management. The segment chain is: `internal_start → route_segment → internal_end` (minimum 3 segments per cable).

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

**CRITICAL**: NMT uses technology-specific connection types:

| NMT Feature Type | External Name | Technology |
|---|---|---|
| `mywcom_fiber_connection` | Fiber Connection | Fiber |
| `mywcom_copper_connection` | Copper Connection | Copper |
| `mywcom_coax_connection` | Coax Connection | Coaxial |

#### Fiber Connection (`mywcom_fiber_connection`)
- **Base**: Point geometry at the connection location
- **Attributes**:
  - `in_object` — Source segment reference (FK to `mywcom_fiber_segment`)
  - `out_object` — Destination segment reference (FK to `mywcom_fiber_segment`)
  - `in_side` — Source side string (e.g., "in", "out", "a", "z")
  - `in_low` / `in_high` — Source strand/port range (integer, mandatory)
  - `out_side` — Destination side string
  - `out_low` / `out_high` — Destination strand/port range (integer, mandatory)
  - `splice` — Boolean; true if connecting two segments (cable splice), false if equipment connection
  - `housing` — Immediate location (Structure or Equipment reference)
  - `root_housing` — Top-level Structure reference
  - `location` — Point geometry (EWKT, mandatory)
- **Semantics**:
  - **Splice** (`splice=true`): Cable continuity across junction (segment-to-segment at structure)
  - **Equipment connection** (`splice=false`): Connection through equipment (segment-to-segment with equipment as housing)
- **Examples**:
  - Splice: Segment A fibers 1-12 → Segment B fibers 1-12 at manhole (housing=manhole)
  - Splitter: Segment A fiber 1 → Segment B fiber 1 at splitter (housing=fiber_splitter)

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

