# Ericsson Network Engineer (ENE) — Source System Knowledge

## Overview

Ericsson Network Engineer (ENE) is a GIS-based outside and inside plant network inventory management application built on ESRI ArcGIS/ArcSDE geodatabases. It manages telecommunications infrastructure including structures, cables, equipment, conduits, splices, and connectivity. Released as version 7.1.2 (2015) by Ericsson AB.

**Key characteristics:**

-   ArcSDE geodatabase backend (Oracle or MS SQL Server)
-   Versioned editing via Work Orders
-   Two geometric networks: `TelcoNet` and `StructSpanNet`
-   ESRI feature dataset called "Telco" containing all inventory classes. All ENE feature classes are registered as ESRI custom feature classes.
-   Class → Category → Type hierarchy for all inventory objects
-   Symbology/Rendering based on Class → Category → Type → Inventory Status
-   Spatial proximity-based placement model (not explicit FK containment)
-   Detail Views for inside plant (rack(Front)/floor/manhole cross-sections/Span cross-sections)
-   Schema owner is typically `NE`
-   Map projection is always non-geographic such as UTM, LCC etc. So data from NE would almost always need to be projected to geographic 
    i.e. lat/long for NMT.

## Data Model Architecture

### Fundamental Concepts

ENE uses an **ESRI geodatabase** with feature classes, object classes, and relationship classes. All telecom inventory lives in a "Telco" feature dataset.

**Key distinction from NMT**: ENE uses spatial snapping and geometric network junctions for connectivity, rather than explicit FK-based containment. Structures and spans participate in geometric networks, and cables "ride" spans based on spatial coincidence.

### Geometric Networks

ENE defines two geometric networks:

1. **TelcoNet** — Handles splice and equipment connectivity. Participants (Transmedia, Equipment, Splice Closure, Drop_line, Network_Interface and Attachment)
Equipment, splice and attachments are **simple junction features** and Transmedia are **complex edge features** in TelcoNet. 
NOTE: Transmedia is a complex edge because its not supposed to be split when a junction is added on a vertex (example: Slack loop or an equipment such as mid span terminal). Also note that even though network_interface and drop_line are part of the network, they were seldom used by customers so there might be no data in those tables.

2. **StructSpanNet** — Handles physical route/span connectivity Participants(structures and spans)

Structures are **simple junction features** and Spans are **simple edge features** in StructSpanNet.

### Feature Class Hierarchy (Class/Category/Type)

All inventory objects are organized into a rigid three-level hierarchy:

| Class               | Description                                                                      | Geometry               | Domain  |
| ------------------- | -------------------------------------------------------------------------------- | ---------------------- | ------- |
| **Structure**       | Physical locations: buildings, poles, manholes, CEVs, huts, antenna towers, SDUs | Point                  | OSP/ISP    |
| **Equipment**       | Active/passive devices placed in structures: MUX, SAI, DLC, routers, DSX         | Point (in detail view) | ISP/OSP |
| **Chassis**         | Sub-component of equipment: shelves, bays, frames                                | None (component)       | ISP     |
| **Slot**            | Place-holders for plugin cards within chassis                                    | None (component)       | ISP     |
| **Plugin**          | Cards (I/O, video) placed in slots                                               | None (component)       | ISP     |
| **Port**            | Connectivity endpoints on plugins, slots, or chassis                             | None (component)       | ISP     |
| **Span**            | Physical routes/pathways: conduit, trench, aerial strand, duct structure         | Polyline               | OSP/ISP     |
| **Span Unit**       | Sub-divisions within spans: risers, cable trays, inner ducts                     | Polyline               | OSP/ISP    |
| **Transmedia**      | Cables: copper, fiber, coaxial, wireless links                                   | Polyline               | OSP-ISP |
| **Transmedia Unit** | Individual strands/pairs/fibers within a cable                                   | None (component)       | OSP     |
| **Splice Closure**  | Physical containers protecting spliced cables                                    | Point                  | OSP     |
| **Attachment**      | Auxiliary items: anchors, guys, maintenance loops                                | Point                  | OSP     |
| **Structure Unit**  | Sub-structures: floors, rooms, racks, manhole walls                              | None (component)       | ISP     |
| **Inside Span**     | Internal spans within detail views                                               | Polyline               | ISP     |

**Domain values:**

-   `OSP` = Outside Plant (map/geographic view)
-   `ISP` = Inside Plant (detail views)
-   `OSP-ISP` = Both environments

### Model Suffixes

Model names often have environment suffixes:

-   No suffix = Aerial
-   `UG` = Underground (in conduit/structure)
-   `B` = Buried
-   `I` = Inside
-   `JP` = Joint pole (shared ownership)

## Key Feature Classes (Geodatabase Tables)

### Outside Plant Features

| Feature Class    | Type     | Network Participation  | Description                                                    |
| ---------------- | -------- | ---------------------- | -------------------------------------------------------------- |
| `STRUCTURE`      | Point    | StructSpanNet junction | Physical locations (poles, manholes, buildings, cabinets)      |
| `SPAN`           | Polyline | StructSpanNet edge     | Physical pathways between structures (conduit, trench, aerial) |
| `TRANSMEDIA`     | Polyline | TelcoNet Complex edge          | Cables (copper, fiber, coax) riding on spans                   |
| `SPLICE_CLOSURE` | Point    | TelcoNet junction      | Splice points between cables                                   |
| `EQUIPMENT`      | Point    | TelcoNet junction      | Active/passive devices                                         |
| `ATTACHMENT`     | Point    | None                   | Maintenance loops, anchors, guys                               |
| `ROUTE_LINE`     | Polyline | None                   | Design Assistant route lines (if installed)                    |
| `TASKSYMBOL`     | Point    | None                   | Work task display symbols                                      |

### Inside Plant Features (Detail Views)

| Feature Class     | Type                 | Description                      |
| ----------------- | -------------------- | -------------------------------- |
| `CHASSIS`         | Object (non-spatial) | Equipment shelves/bays           |
| `SLOT`            | Object (non-spatial) | Card slots within chassis        |
| `PLUGIN`          | Object (non-spatial) | Cards within slots               |
| `PORT`            | Object (non-spatial) | Connectivity endpoints           |
| `SPAN_UNIT`       | Polyline/Object      | Inner ducts, cable trays, risers |
| `STRUCTURE_UNIT`  | Object               | Floors, rooms, racks, walls      |
Not in ENE detail views| `TRANSMEDIA_UNIT` | Object (non-spatial) | Individual fibers/pairs/strands  | 

### Supporting Tables

| Table             | Purpose                                           |
| ----------------- | ------------------------------------------------- |
| `*_REF_ITEM`      | Reference/model data (e.g., `STRUCTURE_REF_ITEM`) |
| `*_REF_CONFIG`    | Configuration data for compound models            |
| `CONNECTION`   | Connection records (port-to-port, fiber-to-fiber, copper) |
| `CIRCUIT`      | Circuit definitions                               |
| `CIRCUIT_LINK` | Circuit route links                               |
| `WORK_ORDER`   | Work order metadata                               |
| `WORK_ORDER_ITEM`      | Work order line items  (For BOM)                   |
| `WORK_ORDER_OBJECTS`      | Data created or modified in workorders. Used for Validation                   |
| `NE_AUDIT_*`      | Audit trail tables                                |

## Connectivity Model

### How Connections Work

Is NODE-EDGE graph based and stores connectivity as ranges. The connections may be represented as a single row or as multiple contiguous rows that can be coalesced into a single row. Disjointed ranges would be multiple rows.

There are 4 tables that play a role in the connectivity model
1) connection - Primary Table with the from and to information with the units
2) connectivity_edge- A bi-directional replica of connection(used by ENE for tracing. Not needed for migration)
3) connectivity_vertex- Contains records for all transmedia and equipment with total unit count (Not required for migration but could be useful to look at total capacity of objects quickly).
4) connection_attributes - Stores attributes for the connection row like DB Loss, Splice type etc.


ENE connectivity is established through the **Connection Editor** and stored in connection tables. Connections are between:

-   **Equipment port ↔ Transmedia unit** (cable terminated at equipment)
-   **Transmedia unit ↔ Transmedia unit** (cable-to-cable splice at splice closure)
-   **Equipment port ↔ Equipment port** (jumper/patch connection)

### Connection Concepts

| Concept                 | Description                                                     |
| ----------------------- | --------------------------------------------------------------- |
| **Admin Label**         | Administrative naming for ports/pairs/fibers (e.g., "UND,1-96") |
| **Admin Label Name**    | Alpha-numeric prefix identifying the source (max 20 chars)      |
| **Admin Number**        | Numeric range representing unit count                           |
| **Default Admin Label** | Auto-assigned label before connections: `UND` + port range      |
| **Physical Unit Names** | Buffer/Fiber naming (e.g., "Buffer 1;Fiber 1")                  |
| **Port Groups**         | Logical grouping of ports on equipment                          |

### Connection Types

1. **Cable-to-Cable (Splice)**: At splice closures; connects fibers/pairs from one cable to another
NOTE: ENE allows an equipment to be used as a splice as well so there may be cable to cable records where the connector is equipment.
2. **Cable-to-Equipment (Termination)**: Connects cable fibers/pairs to equipment ports
3. **Equipment-to-Equipment (Jumper)**: Cross-connects between equipment ports
4. **Mid-span Terminal**: Equipment placed along a cable (cable does NOT split physically)

### Auto-Connection Rules

Defined in Toolbox, these rules govern automatic connection behavior:

-   Whether new transmedia auto-connects to source transmedia
-   Which splice closure model to place between transmedia
-   Splice definitions for specific transmedia-to-transmedia combinations

## Containment and Association Model

### Spatial Association (Not FK-based)

**Critical migration concern**: ENE uses **spatial proximity** for containment, not explicit FK relationships. A cable is "in" a conduit because it is spatially coincident with the span, not because it has a foreign key pointing to the span. Associations can be made by the user and when made is stored in the Transmedia_Span_Association table.

### Association Types

ENE defines associations between features through an **Inventory Association** system:

| Association                | Description                    | Cardinality  |
| -------------------------- | ------------------------------ | ------------ |
| Structure → Equipment      | Equipment placed in structure  | One-to-Many  |
| Structure → Splice Closure | Splice in/on structure         | One-to-Many  |
| Span → Transmedia          | Cables riding on span          | Many-to-Many |
| Span → Span Unit           | Inner ducts within span        | One-to-Many  |
| Equipment → Chassis        | Chassis within equipment       | One-to-Many  |
| Chassis → Slot             | Slots within chassis           | One-to-Many  |
| Slot → Plugin              | Cards in slots                 | One-to-One   |
| Plugin/Chassis/Slot → Port | Ports on equipment             | One-to-Many  |
| Structure → Structure Unit | Sub-structures (floors, rooms) | One-to-Many  |

### Parent-Child Containment

Structures and Equipment support parent-child nesting:

-   Building (parent) → Floor Plan (child) → Room/Aisle/Bay (child) → Rack (child)
-   Equipment contains one or more Chassis
-   Chassis contains Slots, Plugins, and Ports
-   Ports can be located directly on the chassis or on plugins for the most part but in some cases could also be on slots.
-   Slots can be a parent or child of plugin depending on whether the slot is on the chassis or in a plugin.

### Wiring Limits Associations

A special association type linking serving equipment to customer premises:

-   Equipment (SAI, terminal, etc.) → one or more customer Structures
-   Stores `SERVING_STRUCTURE` and `SERVING_EQUIPMENT` attributes
-   Tracks Service Capacity vs. demand

## Work Order System

All modifications in ENE occur within a **Work Order** context. Work orders provide:

-   Versioned editing (ESRI geodatabase versioning)
-   Status lifecycle: Created → Engineering → Approved → Released → Construction → As-Built → Closed
-   Validation before posting
-   Bill of Materials (BOM) generation
-   Audit trail

### Inventory Status

Objects have inventory statuses reflecting their lifecycle:

-   Proposed, Planned, Engineered, In Service, Removed, Abandoned

Status transitions are controlled by work order type and defined in Toolbox.

## Circuits

ENE has two circuit systems (mutually exclusive):

### Circuit Manager (Built-in)

-   Creates circuit links between equipment
-   Routes circuits through the network
-   Stores in `CIRCUIT` and `CIRCUIT_LINK` tables

### Circuit Assistant (Separate License)

-   Capacity planning and logical network management
-   Operates outside work order context
-   More advanced topology tracing

## Detail View Data Model (Inside Plant)

Types of Detail Views:

-   **Cross Section Views** — Span cross-sections showing ducts/cables
-   **Manhole Layout Views** — "Butterfly" views showing walls, ducts, cables
-   **Floor Plans** — Building interior with rooms and racks
-   **Front/Rack Views** — Equipment front panel (chassis/slot/Plugin layout)

### What Detail Views Are

Detail Views are ENE's mechanism for representing **inside-plant** environments that cannot be shown on the geographic map. Each detail view is a self-contained graphical document stored as a binary object (a gzipped VectorDraw/Flipper XML with optional embedded raster images). A detail view belongs to a single **structure unit** (its "owner"), which is always a sub-structure such as a rack, floor, room, or manhole wall.

Detail views are not spatial features — they live outside the geodatabase's coordinate system. Their internal coordinate space uses arbitrary units (typically inches, sometimes millimeters) with an origin local to the drawing.

### View Types

ENE assigns a numeric `view_type` to each detail view:

| view_type | Meaning | What it shows |
|-----------|---------|---------------|
| `-2` | Front View | Equipment front panel: chassis, slots, plugins in a rack/frame |
| `-1` | Floor Plan | Building interior: rooms, aisles, racks on a floor |
| Other | Cross-section / Manhole | Span cross-sections (duct layouts), manhole "butterfly" views (walls, ducts, cables) |

Front views are the primary focus for NMT equipment capacity attribution because they show the physical layout of chassis positions within a rack/frame.

### Detail View Storage

Each detail view is stored as a row in the **detail view items** table. The key column is `detail_item` — a BLOB containing gzipped VectorDraw XML. This XML encodes:

- **Vector shapes**: polygons defining the outlines of structure units, chassis, slots, plugins, and other objects drawn in the view.
- **Text annotations**: labels, names, identifiers placed on or near shapes.
- **Embedded rasters**: JPEG (or PNG/BMP) images — typically the pre-rendered ENE front-view screenshot used as a visual reference.

Each view row also carries a **detail_item_name** (a stable GUID) that serves as the cross-reference key between the imported item table and the ENE source identifier tables.

### Shapes, Points, and Text

The graphical content of a detail view is decomposed into three related tables:

**Shapes** — Each shape represents one drawn object in the view. Every shape carries:
- An `object_class` identifying what kind of inventory object it represents (STRUCTURE_UNIT, CHASSIS, SLOT, PLUGIN, EQUIPMENT).
- An `object_oid` linking it to the actual inventory record in the corresponding feature table.
- A `detail_oid` scoping it to its parent detail view.

A single inventory object can have **multiple shapes** in a view — for example, a chassis may have one shape for its outline and separate shapes for its position bands.

**Points** — Define the geometry of each shape. Points are polygon vertices (x, y coordinates in the view's local coordinate system). A shape's bounding box is computed from its points — there are no pre-computed bounding boxes stored in the database.

**Text** — Text annotations associated with shapes. Each text record carries the string content and a position (x, y) within the view. Texts are linked to shapes, not directly to inventory objects.

The relationship chain is:

```
detail_view_items  (the view BLOB + metadata)
    ↓ detail_oid
detail_view_shapes  (drawn objects, each with object_class + object_oid)
    ↓ shape_oid
detail_view_points  (polygon vertices defining shape geometry)
detail_view_text    (labels/annotations on shapes)
```

### How Shapes Link to Inventory

Each shape's `object_class` and `object_oid` point to the corresponding inventory table:

| object_class | Inventory Table | What it represents in the view |
|-------------|----------------|-------------------------------|
| STRUCTURE_UNIT | `structure_unit` | Rack frame, floor outline, room boundary, manhole wall |
| CHASSIS | `chassis` | Equipment shelf, bay, or card cage drawn inside a rack |
| SLOT | `slot` | Card position within a chassis |
| PLUGIN | `plugin` | Card or module inserted into a slot |
| EQUIPMENT | `equipment` | Standalone equipment drawn in the view |

This linkage is how a graphical rectangle in a front view can be traced back to a physical rack, chassis, or slot record with its attributes (name, type, dimensions, parent relationships).

### View Ownership

Every front view belongs to a **structure unit** — typically a rack or frame. The ownership relationship is stored in the **structure_unit_detail** table, which maps `detail_oid` → `structure_unit_oid`. From the structure unit record, you can retrieve the rack name (e.g., `FRAME:FRAME:D7266383`), its parent structure (the building or room), and its physical attributes.

### Front View Anatomy

A front view of a rack/frame typically contains these elements:

```
┌─────────────────────────────┐
│  STRUCTURE_UNIT shape       │  ← The housing (rack frame outline)
│  ┌───────────────────────┐  │
│  │  CHASSIS shape         │  │  ← Equipment shelf/bay
│  │  ┌──┬──┬──┬──┬──┬──┐  │  │
│  │  │S1│S2│S3│S4│S5│S6│  │  │  ← SLOT shapes (card positions)
│  │  │  │PL│  │PL│  │  │  │  │  ← PLUGIN shapes (inserted cards)
│  │  └──┴──┴──┴──┴──┴──┘  │  │
│  └───────────────────────┘  │
│  ┌───────────────────────┐  │
│  │  CHASSIS bands         │  │  ← Position bands dividing the rack
│  │  (rack view only)      │  │     into equal-height rows
│  └───────────────────────┘  │
│                             │
│  STRUCTURE_UNIT shape       │  ← Label area or secondary SU (not the housing)
│  (text: rack name, etc.)    │
└─────────────────────────────┘
```

**Two structural patterns exist:**

1. **Rack views** — The chassis's physical dimensions (from the chassis base table: `length` × `height`) closely match one of the STRUCTURE_UNIT shapes in the view. That matching SU shape is the **housing**. The rack's vertical space is divided into **chassis band shapes** — horizontal stripes that partition the housing height. Each band represents one mountable position. Band count = position total; bands should tile the housing height contiguously.

2. **Shelf views** — The chassis dimensions do NOT match any SU shape (the chassis is a shelf unit, not a full rack bay). Instead, the housing is identified by finding the SU shape that **geometrically contains** the chassis's drawn outline. Positions are determined by **slot shapes** linked to the chassis via `parent_uuid`, not by bands. Slot count = position total.

### Equipment Hierarchy in Context

In a front view, the equipment hierarchy maps to NMT attributes as follows:

```
Structure Unit (rack/frame)          → NMT "housing" (the rack)
  └── Equipment (e.g., FDF, FIP)     → NMT equipment record
       └── Chassis (shelf/bay)       → Determines equipment dimensions + position count
            ├── Slot 1               ┐
            ├── Slot 2               │ → NMT position total (occupancy)
            ├── ...                  │
            └── Slot N               ┘
                 └── Plugin          → Card in slot (internal component, not separate NMT record)
```

The key relationship chain for resolving equipment from a view:
- **Chassis** `parent_uuid` → **Equipment** `uuid` (determines which equipment the chassis belongs to)
- **Slot** `parent_uuid` → **Chassis** `uuid` (determines which slots belong to which chassis)
- **Structure_unit_detail** `detail_oid` → `structure_unit_oid` (determines which rack owns the view)

### Dimensions and Units

ENE detail views use a local coordinate system with units that vary by deployment. SaskTel views use **inches**. All shape geometry (point coordinates, computed bounding boxes) is in these source units. For NMT output, dimensions must be converted to **meters**.

Two separate dimension sets are relevant:

| Attribute | Source | Meaning |
|-----------|--------|---------|
| Rack (housing) X/Y dimensions | Computed from the housing SU **shape** bounding box in the view | Physical rack frame width and height |
| Equipment (chassis) X/Y dimensions | From the chassis **base table** (`length`, `height` columns) | Physical chassis width and height |

Note: the chassis base-table dimensions and the chassis shape dimensions in the view are NOT necessarily the same. The base-table dimensions are the authoritative physical size. The shape dimensions reflect how the chassis is drawn, which may include visual padding or rendering transforms.

### Detail View Table Relationships (Diagram)

```
                    ┌──────────────────────┐
                    │  detail_view_items   │
                    │  (BLOB + metadata)   │
                    │  PK: objectid        │
                    │  detail_item_name    │◄──── stable GUID cross-reference
                    │  detail_item (BLOB)  │
                    │  view_type           │
                    └─────────┬────────────┘
                              │ detail_oid (ENE source OID)
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
┌──────────────────┐ ┌────────────────┐ ┌────────────────────┐
│detail_view_shapes│ │detail_view_text│ │structure_unit_detail│
│ PK: objectid     │ │ shape_oid (FK) │ │ detail_oid          │
│ object_class     │ │ text_string    │ │ structure_unit_oid  │──► structure_unit
│ object_oid   ────┼─┼────────────────┼─┼──► chassis, slot,   │    (rack owner)
│ detail_oid       │ │ x, y position  │ │    plugin, equipment│
└────────┬─────────┘ └────────────────┘ └────────────────────┘
         │ shape_oid
         ▼
┌──────────────────┐
│detail_view_points│
│ shape_oid (FK)   │
│ x, y coordinates │
│ (polygon vertices)│
└──────────────────┘
```

### What a Front View Means for NMT

From a single front view, the pipeline derives two NMT records:

**1. Rack NMT record** — One per view, describing the housing:
- Rack identity (structure unit name, UUID, type)
- Physical dimensions (width × height of the housing SU shape, converted to meters)
- Position total (number of chassis bands or slots)
- Position order (top-to-bottom or bottom-to-top, derived from band ordering; null for shelf views)
- Position side (FRONT for front views)

**2. Equipment NMT record** — One per equipment found through the chassis:
- Equipment identity (name, UUID, type)
- Physical dimensions (chassis base-table length × height, converted to meters)
- Position in housing (always 1 — one equipment per view in current scope)
- Position occupancy (= position total from the rack record)
- Position side (FRONT)

## Data Export Formats

ENE exports data in several formats:

| Format                | Use Case                                                       |
| --------------------- | -------------------------------------------------------------- |
| **ESRI Geodatabase**  | Direct SDE connection or file geodatabase export               |
| **Shapefiles**        | Feature class geometry + attributes                            |
| **XML**               | Reference data and work order data export/import               |
| **XML Schema (.xsd)** | Validates import/export XML files                              |
| **Model XML**         | Individual or bulk model export (all database tables/rows for a model) |

### XML Import/Export Schema

ENE uses an XML schema (`ImportProject.xml`) for data exchange:

-   Source data files validated against ENE XML schema
-   Schema based on the ENE data model
-   Contains either work order data or reference data

## Exported Data Format (File Geodatabase / GeoPackage)

### Layer Names

ENE data is typically exported as an ESRI File Geodatabase (`.gdb`) or converted to GeoPackage (`.gpkg`). Layers may use a `SIMPLE_` prefix in simplified exports.

| Full GDB Layer           | Simplified Export Layer     | Geometry        |
| ------------------------ | --------------------------- | --------------- |
| `STRUCTURE`              | `SIMPLE_LOCATION` (partial) | Point           |
| `EQUIPMENT`              | `SIMPLE_EQUIPMENT`          | MultiPoint      |
| `SPAN`                   | `SIMPLE_SPAN`               | MultiLineString |
| `SPLICE_CLOSURE`         | `SIMPLE_SPLICE_CLOSURE`     | MultiPoint      |
| `TRANSMEDIA`             | `SIMPLE_TRANSMEDIA`         | MultiLineString |
| `PORT`                   | (non-spatial table)         | None            |
| `CHASSIS`                | (non-spatial table)         | None            |
| `SLOT`                   | (non-spatial table)         | None            |
| `PLUGIN`                 | (non-spatial table)         | None            |
| `TRANSMEDIA_UNIT`        | (non-spatial table)         | None            |
| `STRUCTURE_UNIT`         | (non-spatial table)         | None            |
| `SPAN_UNIT`              | (non-spatial table)         | None            |
| `TRANS_SPAN_ASSOCIATION` | (non-spatial table)         | None            |
| `SPAN_SPAN_UNIT`         | (non-spatial table)         | None            |
| `SLOT_PLUGIN`            | (non-spatial table)         | None            |
| `ATTACHMENT`             | (Point)                     | Point           |

### Structure Naming Convention

ENE encodes structure class/category in the **STRUCTURE_NAME** field itself using the pattern:

```
CLASS_ABBREV:CATEGORY_ABBREV:ID
```

Examples:

-   `POL:PPOLE:C328900` → Pole, Power Pole, ID C328900
-   `PED:CPM::99372` → Pedestal, Company Pole Mounted, ID 99372
-   `BUILD:SDU::96106` → Building, SDU (Single Dwelling Unit), ID 96106
-   `VAULT:MH-S:C12345` → Vault (Manhole), MH-Straight, ID C12345
-   `CAB:EC:C507172` → Cabinet, EC (Equipment Cabinet), ID C507172
-   `SPJCT:SPJCT:C322783` → Span Junction, ID C322783
-   `CLOSR:BSCLS:C123` → Closure, BS Closure, ID C123
-   `TOWER:TOWER:C456` → Tower, ID C456

**Structure abbreviation decode table:**

| Abbreviation    | Full Category                  | Typical NMT Target       |
| --------------- | ------------------------------ | ------------------------ |
| `POL:PPOLE`     | Pole, Power                    | `pole`                   |
| `POL:CPOLE`     | Pole, Company                  | `pole`                   |
| `POL:FPOLE`     | Pole, Foreign                  | `pole`                   |
| `POL:SVMST`     | Pole, Service Mast             | `pole`                   |
| `PED:CPM`       | Pedestal, Company Pole Mounted | `pole` or `cabinet`      |
| `PED:SST`       | Pedestal, Company Steel Stake  | `cabinet` (pedestal)     |
| `PED:JSPED`     | Pedestal, Joint Standard Ped   | `cabinet` (pedestal)     |
| `PED:JLAPD`     | Pedestal, Joint Large Ped      | `cabinet` (pedestal)     |
| `PED:JLPED`     | Pedestal, Joint Light Ped      | `cabinet` (pedestal)     |
| `PED:JTPED`     | Pedestal, Joint TRF Ped        | `cabinet` (pedestal)     |
| `PED:JUPED`     | Pedestal, Joint U Ped          | `cabinet` (pedestal)     |
| `BUILD:SDU`     | Building, Single Dwelling Unit | `building` or `wall_box` |
| `BUILD:MDU`     | Building, Multi Dwelling Unit  | `building`               |
| `BUILD:BUS`     | Building, Business             | `building`               |
| `BUILD:CDO`     | Building, CDO                  | `building`               |
| `BUILD:SEB`     | Building, SEB                  | `building`               |
| `BUILD:PS`      | Building, Power Station        | `building`               |
| `BUILD:FLOOR`   | Building, Floor                | (sub-structure)          |
| `VAULT:MH-S`    | Vault, Manhole Straight        | `manhole`                |
| `VAULT:MH-T`    | Vault, Manhole Turning         | `manhole`                |
| `VAULT:HHOLE`   | Vault, Handhole                | `manhole` (handhole)     |
| `VAULT:FTTX`    | Vault, FTTX                    | `manhole`                |
| `CAB:EC`        | Cabinet, Equipment Cabinet     | `cabinet`                |
| `CAB:JWI`       | Cabinet, JWI                   | `cabinet`                |
| `CAB:JWIEX`     | Cabinet, JWI Extension         | `cabinet`                |
| `CAB:FC`        | Cabinet, Fiber Cabinet         | `cabinet`                |
| `CAB:VAULT`     | Cabinet, Vault                 | `cabinet`                |
| `CAB:PAD`       | Cabinet, Pad                   | `cabinet`                |
| `SPJCT:SPJCT`   | Span Junction                  | (synthetic/route vertex) |
| `CLOSR:BSCLS`   | Closure, BS Closure            | `splice_closure`         |
| `CLOSR:PULLBOX` | Closure, Pullbox               | (access point)           |
| `TOWER:TOWER`   | Tower                          | `pole` (tower)           |
| `TOWER:FIXED`   | Tower, Fixed                   | `pole` (tower)           |
| `FTTX:*`        | FTTX structures                | varies                   |

### Key Attribute Columns by Layer

#### STRUCTURE Layer

| Attribute               | Type       | Description                                     | Migration Relevance          |
| ----------------------- | ---------- | ----------------------------------------------- | ---------------------------- |
| `STRUCTURE_NAME`        | String(25) | Unique identifier (CLASS:CAT:ID format)         | Primary key; parse for type  |
| `CATEGORY_NAME`         | String(20) | Category (e.g., "POLE", "PEDESTAL", "BUILDING") | Determines NMT target type   |
| `TYPE_NAME`             | String(20) | Subtype (e.g., "POWER", "COMPANY POLE MOUNTED") | Refines target type          |
| `LOCATION_CODE`         | String(20) | Location reference code                         | Cross-ref to SIMPLE_LOCATION |
| `PARENT_STRUCTURE_NAME` | String(25) | Parent structure (containment)                  | **Explicit containment FK**  |
| `INVENTORY_STATUS_CODE` | String(4)  | Status code (IPL, ABD, PDA, etc.)               | Filter/map to NMT status     |
| `CLLI_CODE`             | String(11) | CLLI identifier                                 | Map to NMT name/reference    |
| `ST_CLLI_CD`            | String(20) | SaskTel CLLI code                               | Customer-specific CLLI       |
| `ST_RTE_ID`             | String(20) | Route identifier                                | Route grouping key           |
| `ST_TRMNL_ID`           | String(20) | Terminal identifier                             | Equipment cross-ref          |
| `ST_PL_CL_CD`           | Int16      | Pole class code                                 | Specification detail         |
| `ST_DSA_ID`             | String(5)  | Distribution Serving Area ID                    | Service area mapping         |
| `ST_ENVMT_CD`           | String(6)  | Environment code                                | Aerial/buried/indoor         |
| `UUID`                  | String(40) | Global unique identifier                        | Stable cross-reference key   |
| `SHAPE`                 | Point      | WGS84 geometry                                  | Direct geometry mapping      |

#### SPAN Layer

| Attribute               | Type            | Description                       | Migration Relevance           |
| ----------------------- | --------------- | --------------------------------- | ----------------------------- |
| `SPAN_NAME`             | String(25)      | Unique identifier                 | Primary key                   |
| `CATEGORY_NAME`         | String(20)      | "OUTSIDE PLANT" or "INSIDE PLANT" | Domain filter                 |
| `TYPE_NAME`             | String(20)      | Subtype (see below)               | **Determines NMT route type** |
| `FROM_STRUCTURE_NAME`   | String(25)      | Start structure (CLASS:CAT:ID)    | → `in_structure` FK           |
| `TO_STRUCTURE_NAME`     | String(25)      | End structure (CLASS:CAT:ID)      | → `out_structure` FK          |
| `INVENTORY_STATUS_CODE` | String(4)       | Status code                       | Filter                        |
| `CALCULATED_LENGTH`     | Real            | Calculated length                 | → `length`                    |
| `MEASURED_LENGTH`       | Real            | Field-measured length             | Preferred over calculated     |
| `DUCTS_AVAILABLE`       | Int             | Number of ducts in span           | Conduit generation            |
| `INNER_DUCTS_AVAILABLE` | Int             | Inner duct count                  | Sub-conduit generation        |
| `UUID`                  | String(40)      | Global unique identifier          | Cross-reference key           |
| `SHAPE`                 | MultiLineString | WGS84 geometry                    | → `path`                      |
| `SHAPE_Length`          | Real            | Geometry length                   | Verification                  |

**Span TYPE_NAME → NMT Route mapping:**

| ENE TYPE_NAME    | NMT Target              | Notes                    |
| ---------------- | ----------------------- | ------------------------ |
| `BURIED`         | `ug_route`              | Direct-buried cable path |
| `CONDUIT`        | `ug_route`              | Duct system underground  |
| `UNDERGROUND`    | `ug_route`              | Generic underground      |
| `TUNNEL`         | `ug_route`              | Tunnel route             |
| `UNDERWATER`     | `ug_route`              | Submarine route          |
| `FORMATION`      | `ug_route`              | Multi-duct formation     |
| `CORE HOLE`      | `ug_route`              | Building entry           |
| `FOREIGN BURIED` | `ug_route`              | Third-party buried       |
| `MESSENGER`      | `oh_route`              | Aerial (messenger wire)  |
| `FLOOR SPAN`     | `mywcom_internal_route` | Inside plant             |
| `RISER`          | `mywcom_internal_route` | Building riser           |
| `TROUGH`         | `mywcom_internal_route` | Inside cable trough      |

#### EQUIPMENT Layer

| Attribute               | Type         | Description                     | Migration Relevance        |
| ----------------------- | ------------ | ------------------------------- | -------------------------- |
| `EQUIPMENT_NAME`        | String(25)   | Unique identifier               | Primary key                |
| `CATEGORY_NAME`         | String(20)   | Equipment category              | Determines NMT type        |
| `TYPE_NAME`             | String(20)   | Equipment subtype               | Refines NMT type           |
| `STRUCTURE_NAME`        | String(25)   | Parent structure (CLASS:CAT:ID) | → `housing` FK             |
| `INVENTORY_STATUS_CODE` | String(4)    | Status                          | Filter                     |
| `CLLI_CODE`             | String(15)   | CLLI code                       | Identification             |
| `ST_CO_ID`              | String(30)   | Managed Region ID               | Grouping                   |
| `ST_TRMNL_ID`           | String(20)   | Terminal identifier             | Cross-reference            |
| `ST_PC_QTY`             | String(50)   | Preferred count quantity        | Port/pair count            |
| `SERVICE_CAPACITY`      | Int          | Service pair/port capacity      | Equipment spec             |
| `MID_SPAN_DISTANCE`     | Real         | Distance along cable (mid-span) | Mid-span terminal location |
| `MID_SPAN_TRANSMEDIA`   | String(40)   | Cable UUID for mid-span         | Mid-span cable ref         |
| `UUID`                  | String(40)   | Global unique identifier        | Cross-reference            |
| `ADMINLABEL`            | String(2000) | Admin label assignments         | Connection mapping         |

#### TRANSMEDIA Layer

| Attribute                  | Type            | Description               | Migration Relevance       |
| -------------------------- | --------------- | ------------------------- | ------------------------- |
| `TRANSMEDIA_NAME`          | String(25)      | Unique identifier         | Primary key               |
| `CATEGORY_NAME`            | String(20)      | Media category            | Determines cable type     |
| `TYPE_NAME`                | String(20)      | Media subtype             | Refines cable type        |
| `FROM_STRUCTURE_NAME`      | String(25)      | Start structure           | → segment `in_structure`  |
| `TO_STRUCTURE_NAME`        | String(25)      | End structure             | → segment `out_structure` |
| `FROM_EQUIPMENT_NAME`      | String(25)      | Start equipment           | Termination ref           |
| `TO_EQUIPMENT_NAME`        | String(25)      | End equipment             | Termination ref           |
| `FROM_SPLICE_CLOSURE_NAME` | String(25)      | Start splice              | Connection ref            |
| `TO_SPLICE_CLOSURE_NAME`   | String(25)      | End splice                | Connection ref            |
| `INVENTORY_STATUS_CODE`    | String(4)       | Status                    | Filter                    |
| `CALCULATED_LENGTH`        | Real            | Calculated length         | → segment `length`        |
| `MEASURED_LENGTH`          | Real            | Measured length           | Preferred                 |
| `JUMPER_FLAG`              | String(1)       | Is jumper cable           | Filter/special handling   |
| `BFT_SOURCE_EQUIPMENT`     | String(20)      | Back-feed terminal source | FTTX mapping              |
| `UUID`                     | String(40)      | Global unique identifier  | Cross-reference           |
| `ADMINLABEL`               | String(2000)    | Admin label data          | Unit/fiber numbering      |
| `SHAPE`                    | MultiLineString | WGS84 geometry            | → `path`                  |

**Transmedia CATEGORY → NMT Cable mapping:**

| ENE CATEGORY     | ENE TYPE       | NMT Target                   |
| ---------------- | -------------- | ---------------------------- |
| `FIBER`          | `FIBER`        | `fiber_cable`                |
| `COPPER`         | `COPPER`       | `copper_cable`               |
| `COPPER`         | `STUB`         | `copper_cable` (stub)        |
| `COAX`           | `COAX`         | `coax_cable`                 |
| `FTTX`           | `DISTRIBUTION` | `fiber_cable` (distribution) |
| `FTTX`           | `FTTX DROP`    | `fiber_cable` (drop)         |
| `FTTX`           | `FTTX STUB`    | `fiber_cable` (stub)         |
| `FTTX`           | `TETHER`       | `fiber_cable` (tether)       |
| `PRESSURIZATION` | `AIR PIPE`     | (exclude or custom)          |

#### SPLICE_CLOSURE Layer

| Attribute             | Type       | Description                      | Migration Relevance |
| --------------------- | ---------- | -------------------------------- | ------------------- |
| `SPLICE_CLOSURE_NAME` | String(25) | Unique identifier                | Primary key         |
| `CATEGORY_NAME`       | String(20) | Media type (FIBER, COPPER, COAX) | Type classification |
| `TYPE_NAME`           | String(20) | Subtype                          | Refines type        |
| `STRUCTURE_NAME`      | String(25) | Parent structure                 | → `housing` FK      |
| `CONNECTOR_TYPE_NAME` | String(20) | Connector type                   | Specification       |
| `UUID`                | String(40) | Global unique identifier         | Cross-reference     |

#### PORT Table (Non-spatial)

| Attribute         | Type       | Description           | Migration Relevance |
| ----------------- | ---------- | --------------------- | ------------------- |
| `PORT_NAME`       | String(25) | Port identifier       | Connection endpoint |
| `EQUIPMENT_NAME`  | String(25) | Parent equipment      | Equipment FK        |
| `CHASSIS_NAME`    | String(25) | Parent chassis        | Hierarchy           |
| `SLOT_NAME`       | String(25) | Parent slot           | Hierarchy           |
| `PLUGIN_NAME`     | String(25) | Parent plugin         | Hierarchy           |
| `CATEGORY_NAME`   | String(20) | Port category         | Type                |
| `TYPE_NAME`       | String(20) | Port type             | Type                |
| `PORT_GROUP_NAME` | String(20) | Logical grouping      | Grouping            |
| `SEQUENCE_NUMBER` | Int        | Order within parent   | → fiber/pair number |
| `UUID`            | String(40) | Unique ID             | Cross-reference     |
| `PARENT_UUID`     | String(40) | Parent component UUID | Hierarchy FK        |

#### TRANSMEDIA_UNIT Table (Non-spatial)

| Attribute                  | Type         | Description          | Migration Relevance   |
| -------------------------- | ------------ | -------------------- | --------------------- |
| `TRANSMEDIA_NAME`          | String(25)   | Parent cable         | Cable FK              |
| `TRANSMEDIA_UNIT_NAME`     | String(25)   | Unit identifier      | Unit naming           |
| `TRANSMISSION_MEDIA_TYPE`  | String(10)   | Media type           | fiber/copper/coax     |
| `NUMBER_OF_UNITS`          | Int          | Unit count in bundle | Fiber/pair count      |
| `BUNDLING_LEVELS`          | Int          | Nesting depth        | Buffer tube structure |
| `BUNDLING_LABEL`           | String(40)   | Bundle name          | Tube/binder labeling  |
| `BUNDLING_SCHEME`          | String(60)   | Bundle scheme        | Color code scheme     |
| `COLOR_SCHEME`             | String(2500) | Color assignments    | Fiber color mapping   |
| `LOW_RANGE` / `HIGH_RANGE` | Int          | Unit range           | Fiber/pair numbering  |
| `OPTICAL_MODE`             | String(10)   | SM/MM                | Fiber specification   |
| `UUID`                     | String(40)   | Unique ID            | Cross-reference       |

#### TRANSMEDIA_SPAN_ASSOCIATION Table (Non-spatial)

| Attribute         | Type       | Description           | Migration Relevance            |
| ----------------- | ---------- | --------------------- | ------------------------------ |
| `SPAN_UUID`       | String(40) | Span UUID             | **Cable-to-route association** |
| `TRANSMEDIA_UUID` | String(40) | Cable UUID            | Cable FK                       |
| `SPAN_UNIT_UUID`  | String(40) | Span unit (duct) UUID | Conduit assignment             |

**This table is critical** — it provides the explicit cable-to-span (cable-to-route) relationship that ENE normally stores spatially. Use it to derive the NMT `housing` field on segments.

### Inventory Status Codes

| Code   | Meaning                 | Migration Action                                |
| ------ | ----------------------- | ----------------------------------------------- |
| `IPL`  | In Place (Active)       | Include — primary migration target              |
| `ABD`  | Abandoned               | Usually exclude; or map to NMT abandoned status |
| `PDA`  | Proposed/Design Active  | Usually exclude (not yet built)                 |
| `PDR`  | Proposed/Design Removed | Exclude                                         |
| `PEAB` | Pending Abandon         | Include with flag                               |
| `PLA`  | Planned Active          | Usually exclude                                 |
| `PLR`  | Planned Removed         | Exclude                                         |
| `PABD` | Pending Abandoned       | Include with flag                               |

### UUID Cross-Referencing

ENE uses **UUID** (String 40) as the primary cross-reference key between tables. This is more reliable than NAME fields for joins:

-   `STRUCTURE.UUID` ↔ referenced in `SPAN.FROM_STRUCTURE_UUID` (if available)
-   `TRANSMEDIA.UUID` ↔ `TRANS_SPAN_ASSOCIATION.TRANSMEDIA_UUID`
-   `SPAN.UUID` ↔ `TRANS_SPAN_ASSOCIATION.SPAN_UUID`
-   `EQUIPMENT.UUID` ↔ `PORT.PARENT_UUID` (indirect via chassis)
-   `TRANSMEDIA.UUID` ↔ `TRANSMEDIA_UNIT.TRANSMEDIA_UUID` (or via name)

When UUID-based joins are not available, fall back to NAME-based joins (e.g., `EQUIPMENT.STRUCTURE_NAME` → `STRUCTURE.STRUCTURE_NAME`).

## Common Export Quirks

1. **OBJECTID**: ESRI-managed unique identifier per feature class (NOT globally unique)
2. **GLOBALID**: GUID-based globally unique identifier (if enabled)
3. **SHAPE**: Geometry column in geodatabase (ESRI proprietary binary)
4. **MODEL_NUMBER**: FK to reference/model data tables
5. **CATEGORY_CODE / TYPE_CODE**: Numeric codes for category/type (decoded via lookup tables)
6. **STATUS_CODE**: Inventory status numeric code
7. **WORK_ORDER_ID**: FK to work order table
8. **NULL handling**: ESRI geodatabases use database-native NULLs
9. **Coordinate System**: Varies per deployment — SaskTel data is WGS84 (EPSG:4326)
10. **Date fields**: Stored as database timestamps
11. **ST\_ prefix columns**: SaskTel-specific custom attributes (alternative names document full meaning)
12. **SIMPLE\_ prefix layers**: Simplified/denormalized export views (structure info embedded in name fields)

## Migration Considerations (ENE → NMT)

### Structural Model Transformation

| ENE Concept              | NMT Equivalent                                           | Transformation Required                                              |
| ------------------------ | -------------------------------------------------------- | -------------------------------------------------------------------- |
| Structure (point)        | `manhole`, `pole`, `cabinet`, `building`, `wall_box`     | Map by category/type to specific NMT structure types                 |
| Span (polyline)          | `ug_route`, `oh_route`                                   | Map by category (Underground→ug_route, Aerial→oh_route)              |
| Span Unit                | `mywcom_conduit`                                         | Inner ducts become conduits; cable trays may need synthetic conduits |
| Transmedia (polyline)    | `fiber_cable`, `copper_cable`, `coax_cable`              | One-to-one; map by technology                                        |
| Transmedia Unit          | `mywcom_fiber_segment`, `mywcom_copper_segment`          | Segments need explicit in/out structure references                   |
| Splice Closure           | `splice_closure`                                         | Direct mapping; add housing FK                                       |
| Equipment                | Equipment types (patch panel, splitter, etc.)            | Map by category/type to NMT equipment types                          |
| Chassis/Slot/Plugin/Port | NMT equipment hierarchy                                  | Flatten or map per deployment needs                                  |
| Connection records       | `mywcom_fiber_connection`, `mywcom_copper_connection`    | Restructure from port-pair to segment-based                          |
| Circuit                  | Logical circuit records                                  | Map to NMT circuit model                                             |
| Association (spatial)    | FK references (`housing`, `cable`, `in_structure`, etc.) | Must derive explicit FKs from spatial relationships                  |

### Key Challenges

1. **Spatial → Explicit Containment**: ENE stores containment implicitly via spatial coincidence. NMT requires explicit FK relationships. Must derive:

    - Cable-to-route assignment (`housing` field on segments) — **use `TRANS_SPAN_ASSOCIATION` table**
    - Equipment-to-structure assignment (`housing` field) — **use `EQUIPMENT.STRUCTURE_NAME`** (already explicit!)
    - Splice-to-structure assignment — **use `SPLICE_CLOSURE.STRUCTURE_NAME`** (already explicit!)
    - Segment in/out structure — **use `SPAN.FROM/TO_STRUCTURE_NAME`** (already explicit!)

2. **Span → Segment Generation**: ENE has one span per structure-to-structure hop (already segmented at structures). Each span + cable combination produces one NMT segment. The span IS the segment geometry.

3. **Multi-Span Cables**: A single ENE cable (TRANSMEDIA) may traverse multiple spans. The `TRANS_SPAN_ASSOCIATION` table tells you which spans a cable traverses. Each association becomes one NMT segment, and segments must be chained with `in_segment`/`out_segment`.

4. **Structure Type Resolution**: Parse `STRUCTURE_NAME` prefix OR use `CATEGORY_NAME`+`TYPE_NAME` to determine the correct NMT structure type (pole, manhole, cabinet, building, wall_box).

5. **Span Junction Handling**: `SPJCT:SPJCT` structures are synthetic junction points where spans meet. They may need to become NMT structures or be absorbed into route geometry depending on whether equipment/splices are at that location.

6. **FTTX Equipment Mapping**: FTTX categories (FDH, FDT, FSB, FST, TO) require careful mapping to NMT splitter/drop_point types. These often have back-feed terminal (BFT) references.

7. **Admin Label Parsing**: The `ADMINLABEL` field (String 2000) on equipment and transmedia encodes port/pair assignments in a proprietary format. Must be parsed to derive connection unit numbering.

8. **Coordinate System**: SaskTel data is already in WGS84 (EPSG:4326), so no CRS transformation needed.

9. **Status Filtering**: Filter on `INVENTORY_STATUS_CODE = 'IPL'` (In Place) for active network. Decide policy for ABD (Abandoned) — typically exclude.

10. **Conduit Generation from Spans**: Spans with `DUCTS_AVAILABLE > 0` need synthetic `mywcom_conduit` records created. The `SPAN_UNIT` and `SPAN_SPAN_UNIT` tables provide existing duct definitions; the `TRANS_SPAN_ASSOCIATION.SPAN_UNIT_UUID` indicates which duct a cable occupies.

### Typical Source Data Extraction

ENE data is typically provided as:

-   **ESRI File Geodatabase (`.gdb`)** — full extract with all layers, including non-spatial tables (PORT, CHASSIS, TRANSMEDIA_UNIT, TRANSMEDIA_SPAN_ASSOCIATION)
-   **GeoPackage (`.gpkg`)** — converted from GDB; simplified exports may use `SIMPLE_` prefix and embed structure references as name strings rather than UUIDs
-   **Shapefiles** per feature class (geometry + attributes, but no relationship tables)
-   **CSV/DBF** attribute tables for non-spatial classes

- There may be situations that would need extraction of data from an ENE database especially on tables driven by ESRI objectid relationships. If the table required is unversioned, the table contents can be extracted as is. However, if the table is versioned, then the output of the multiversion view needs to be extracted. The naming convention is MV_<Table_name>. Example, MV_DETAIL_VIEW_ITEMS. 

**Full GDB is strongly preferred** because it includes:

-   `TRANSMEDIA_SPAN_ASSOCIATION` (cable-to-route mapping)
-   `PORT` table (equipment hierarchy and connectivity endpoints)
-   `TRANSMEDIA_UNIT` (fiber/pair bundling and count details)
-   `SPAN_UNIT` and `SPAN_SPAN_UNIT` (conduit structure)
-   `STRUCTURE_UNIT` (sub-structure hierarchy)

**Simplified exports** (SIMPLE\_\* layers) lose the relationship tables but embed key references in NAME fields (e.g., `FROM_STRUCTURE_NAME`, `TO_STRUCTURE_NAME`, `STRUCTURE_NAME`).

### Mapping Strategy Template

```
ENE Class: STRUCTURE
  Categories: POLE, PEDESTAL, BUILDING, VAULT, CABINET, CLOSURE, TOWER, SPAN JUNCTION
  → NMT Mapping:
    POLE (POWER, COMPANY, FOREIGN, SERVICE MAST) → pole
    PEDESTAL (CPM, SST, JS*, JL*, JT*, JU*) → cabinet (type=pedestal)
    BUILDING (SDU) → wall_box or building (depending on scale)
    BUILDING (MDU, BUS, CDO, SEB, PS) → building
    VAULT (MH-STRAIGHT, MH-TURNING) → manhole
    VAULT (HANDHOLE) → manhole (type=handhole)
    CABINET (EC, JWI, FC, PAD, VAULT) → cabinet
    CLOSURE (BS CLOSURE, PULLBOX) → (merge with splice_closure or create access point)
    TOWER (TOWER, FIXED) → pole (type=tower)
    SPAN JUNCTION → (synthetic vertex, may not need separate NMT object)
  Key: CATEGORY_NAME + TYPE_NAME determines target; parse STRUCTURE_NAME prefix for quick decode

ENE Class: SPAN
  Categories: OUTSIDE PLANT, INSIDE PLANT
  → NMT Mapping:
    OUTSIDE PLANT | BURIED → ug_route
    OUTSIDE PLANT | CONDUIT → ug_route (generate conduits from DUCTS_AVAILABLE)
    OUTSIDE PLANT | UNDERGROUND → ug_route
    OUTSIDE PLANT | TUNNEL → ug_route
    OUTSIDE PLANT | UNDERWATER → ug_route
    OUTSIDE PLANT | FORMATION → ug_route (multi-duct formation)
    OUTSIDE PLANT | CORE HOLE → ug_route (building entry)
    OUTSIDE PLANT | FOREIGN BURIED → ug_route (ownership=foreign)
    OUTSIDE PLANT | MESSENGER → oh_route
    INSIDE PLANT | FLOOR SPAN → mywcom_internal_route
    INSIDE PLANT | RISER → mywcom_internal_route
    INSIDE PLANT | TROUGH → mywcom_internal_route
  Key: TYPE_NAME is the discriminator; FROM/TO_STRUCTURE_NAME give endpoints

ENE Class: TRANSMEDIA
  Categories: FIBER, COPPER, COAX, FTTX, PRESSURIZATION
  → NMT Mapping:
    FIBER | FIBER → fiber_cable
    COPPER | COPPER → copper_cable
    COPPER | STUB → copper_cable (short stub cable)
    COAX | COAX → coax_cable
    FTTX | DISTRIBUTION → fiber_cable (distribution)
    FTTX | FTTX DROP → fiber_cable (drop)
    FTTX | FTTX STUB → fiber_cable (stub)
    FTTX | TETHER → fiber_cable (tether)
    PRESSURIZATION | AIR PIPE → exclude (non-telecom)
  Key: CATEGORY determines cable technology; FROM/TO fields give segment endpoints

ENE Class: SPLICE_CLOSURE
  Categories: FIBER, COPPER, COAX, ENVIRONMENT JUNCTION, PRESSURIZATION
  → NMT Mapping:
    FIBER | * → splice_closure (fiber)
    COPPER | * → splice_closure (copper)
    COAX | * → splice_closure (coax)
    ENVIRONMENT JUNCTION → (may map to structure or exclude)
    PRESSURIZATION → exclude
  Key: STRUCTURE_NAME gives housing FK

ENE Class: EQUIPMENT
  Categories: COPPER, FIBER, FTTX, WIRELESS, MONITORING, PRESSURIZATION, FOREIGN, SASKTEL
  → NMT Mapping (selection):
    COPPER | TERMINAL → drop_point
    COPPER | NID → drop_point (NID)
    COPPER | CDF → fiber_patch_panel (copper distribution frame)
    COPPER | CROSS CONNECT → cross_connect
    FIBER | FDF → fiber_patch_panel
    FIBER | FIP → fiber_patch_panel (fiber interconnect)
    FIBER | FRAME → fiber_patch_panel
    FIBER | ONT → ont
    FTTX | FDH → fiber_splitter (fiber distribution hub)
    FTTX | FDT → fiber_splitter (fiber distribution terminal)
    FTTX | FSB → fiber_splitter
    FTTX | FST → fiber_splitter
    FTTX | TO → drop_point (FTTX tap-off)
    WIRELESS | ANTENNA → (custom/exclude)
    MONITORING | MONITORING → (custom/exclude)
    PRESSURIZATION | * → exclude
  Key: STRUCTURE_NAME gives housing FK; CATEGORY+TYPE determines NMT equipment type
```

### Connectivity Mapping

```
ENE Data Available:
  - PORT table: PORT_NAME, EQUIPMENT_NAME, CHASSIS_NAME, SLOT_NAME, PLUGIN_NAME,
    SEQUENCE_NUMBER, UUID, PARENT_UUID
  - TRANSMEDIA_UNIT table: TRANSMEDIA_NAME, NUMBER_OF_UNITS, LOW_RANGE, HIGH_RANGE,
    BUNDLING_LABEL, COLOR_SCHEME, OPTICAL_MODE
  - Connection data (if exported): FROM_PORT_UUID, TO_PORT_UUID, connection type
  - ADMINLABEL field on EQUIPMENT and TRANSMEDIA: encodes connection assignments
  - TRANS_SPAN_ASSOCIATION: links cables to spans (cable routing)

NMT Connection Record:
  in_object (segment or equipment URN)
  out_object (segment or equipment URN)
  in_unit (fiber/pair number)
  out_unit (fiber/pair number)
  type (splice, patch, terminate)

Transformation Steps:
  1. Build cable→segment mapping using TRANS_SPAN_ASSOCIATION (cable UUID → span UUID)
  2. For each connection, resolve PORT to equipment + port sequence
  3. Resolve TRANSMEDIA_UNIT range to specific fiber/pair numbers
  4. Map connection endpoints:
     - Port↔TransmediaUnit → terminate (equipment↔segment connection)
     - TransmediaUnit↔TransmediaUnit → splice (segment↔segment connection)
     - Port↔Port → patch (equipment↔equipment jumper)
  5. Create NMT connection with appropriate URNs and unit numbers

Key join paths:
  STRUCTURE_UNIT.PARENT_STRUCTURE_UUID->STRUCTURE.UUID
  PORT.EQUIPMENT_NAME → EQUIPMENT.EQUIPMENT_NAME → EQUIPMENT.STRUCTURE_NAME → housing
  PORT.PARENT_UUID->CHASSIS.UUID
  TRANSMEDIA.UUID → TRANS_SPAN_ASSOCIATION.TRANSMEDIA_UUID → SPAN.UUID → route
  PORT.SEQUENCE_NUMBER → NMT fiber/pair unit number
  TRANSMEDIA_UNIT.LOW_RANGE/HIGH_RANGE → fiber/pair numbering range



### Cable-to-Route Derivation

The `TRANSMEDIA_SPAN_ASSOCIATION` table is the **primary mechanism** for determining which route a cable traverses:

For each cable (TRANSMEDIA):
  1. Look up TRANSMEDIA_SPAN_ASSOCIATION where TRANSMEDIA_UUID = cable.UUID
  2. Get the SPAN_UUID(s) — one cable may traverse multiple spans
  3. Each SPAN maps to an NMT route (ug_route or oh_route)
  4. For each span the cable traverses, create one NMT segment:
     - cable = fiber_cable/cable_id (URN)
     - housing = ug_route/route_id or oh_route/route_id (URN)
     - in_structure = SPAN.FROM_STRUCTURE_NAME → structure URN
     - out_structure = SPAN.TO_STRUCTURE_NAME → structure URN
     - path = SPAN.SHAPE geometry (or cable's clipped geometry)
  5. Chain segments with in_segment/out_segment references
```

If `TRANSMEDIA_SPAN_ASSOCIATION` is missing or incomplete, fall back to **spatial intersection** between cable geometry and span geometry to derive the association.

## Validation Error Codes (Reference)

ENE validates work orders before posting. Common validation concerns that may indicate data quality issues in source data:

-   Missing required associations (e.g., cable not associated to span)
-   Invalid status transitions
-   Unconnected ports/fibers at boundaries
-   Duplicate admin labels
-   Model reference integrity failures
-   Spatial integrity (features not snapped to network)

## Terminology Cross-Reference

| ENE Term             | NMT Equivalent                        | Notes                       |
| -------------------- | ------------------------------------- | --------------------------- |
| Structure            | Structure types (manhole, pole, etc.) | Map by category/type        |
| Span                 | Route (ug_route, oh_route)            | Spans are physical pathways |
| Span Unit            | Conduit (mywcom_conduit)              | Inner ducts/cable trays     |
| Transmedia           | Cable (fiber_cable, etc.)             | Transport medium            |
| Transmedia Unit      | Segment (mywcom_fiber_segment)        | Per-hop cable segments      |
| Splice Closure       | splice_closure                        | Splice enclosure            |
| Equipment            | Various equipment types               | Map by function             |
| Port                 | Connection endpoint                   | Part of equipment hierarchy |
| Connection           | Connection (mywcom_fiber_connection)  | Splice/patch/terminate      |
| Circuit              | Circuit                               | Logical path                |
| Work Order           | N/A (migration artifact)              | Version control unit        |
| Geodatabase          | PostgreSQL/PostGIS                    | Database platform           |
| Feature Class        | NMT table                             | Database table              |
| Association          | FK reference (housing, cable, etc.)   | Explicit relationship       |
| Admin Label          | Fiber/pair number                     | Unit identifier             |
| Model/Reference Item | Specification                         | Template/type definition    |
| Detail View          | Inside Plant view                     | Interior visualization      |
| OSP                  | Outside Plant                         | Geographic network view     |
| ISP                  | Inside Plant                          | Equipment-level view        |

## NMT Load & Containment Practices (verified — SaskTel ENE XML, copper OSP)

Lessons confirmed against a live NMT `comms` deployment (V-recent) while migrating an
ENE Model XML export. Always verify the target schema first — deployments differ.

### Target schema verification (do this before generating)
- **Route feature**: some deployments have a single **`route`** feature (with `type` /
  `sub_type`), NOT `ug_route`/`oh_route`. Query `myw.dd_feature` and `myw.dd_field`
  (columns: `table_name`, `internal_name`, `type`, `mandatory`, `read_only`, `generator`).
- **Copper equipment types** present in the copper NMT model:
  `copper_load_coil`, `copper_terminal`, `copper_splice_closure`, `copper_bridge_tap`,
  `copper_build_out`, `copper_capacitor`, `copper_dslam`, `copper_pair_gain`,
  `copper_repeater`, `copper_shelf`, plus `mywcom_copper_segment/connection/slack`.
  ENE `NID` → **`copper_terminal`** (there is often **no** `drop_point`); ENE `LOAD COIL`
  → **`copper_load_coil`**; ENE copper splice → **`copper_splice_closure`**.
- **`copper_cable`** pair-count field is **`copper_count`** (not `count`); `path` and
  `directed` are mandatory.

### Read-only computed containment (CRITICAL)
`route.in_structure/out_structure` and equipment `housing`/`root_housing` are typically
**read_only** — computed by the comms NetworkView triggers, which bulk `myw_db load`
**bypasses**. After loading, drive the managers directly via `myw_db <db> run script.py --commit`:

```python
from myworldapp.core.server.base.core.myw_progress import MywProgressHandler
from myworldapp.modules.comms.server.api.network_view import NetworkView
nw = NetworkView(db.view(), MywProgressHandler())      # `db` injected by `myw_db run`
for r in db.view().table("route").recs():
    nw.struct_mgr.ensureStructuresFor(r)               # sets route in/out_structure
for st in db.view().table("access_structure").recs():  # repeat per structure type
    nw.struct_mgr.house(st)                            # houses coincident equipment/segments
# `--commit` commits; omit it for a safe dry run (rolled back)
```
- **Place equipment on its housing structure's point** during transform (NMT geometry
  inheritance) so `house()` matches it (`struct_tolerance = 1.0`).
- **Snap route/segment endpoints to structure coordinates** before reprojection to avoid
  `geom_mismatch_at`. Snapped endpoints let `ensureStructuresFor`/`structureAt` match exactly.

### Network-structure registration (route endpoints)
Valid route-endpoint structure types come from the **`mywcom.structures`** setting. A
structure type must be listed there or `StructureManager.structureAt()` ignores it (routes
get no `out_structure`). Add one via a run script: read `db.setting("mywcom.structures")`,
add the key, `db.setSetting("mywcom.structures", value)` (commit). Example: `wall_box` for
SDU drops when the customer wants SDU→`wall_box`.

### Connection sides (avoid the `KeyError: 'a'` validator crash)
Connection `in_side`/`out_side` must be **`in`/`out`** (the keys of `equip_n_pins_fields`),
never `a`/`z` for endpoints the validator port-checks. Rules that pass `comms_db validate`:
- **Segment** side = the end at the connection's housing structure
  (`out` if `segment.out_structure == housing`, else `in`).
- **`copper_terminal`** has only `in` ports → side must be `in`.
- Load coils/segments accept either side (implicit/cable port counts).

### Validation
Run **per category with `--verbosity 2`** — the `'*'` wildcard and verbosity 1 under-report:
`comms_db <db> validate data <structures|routes|equipment|cables|segments|connections> --verbosity 2`.

