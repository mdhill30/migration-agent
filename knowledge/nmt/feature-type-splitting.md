# NMT Feature Type Splitting Rules

## Core Principle

NMT does NOT use generic consolidated feature types. Each concrete type (e.g., `pole`, `cabinet`, `manhole`) is its own database table, `.def` file, and CSV. `myw_db load` infers the target feature type from the CSV filename.

**NEVER** produce a single generic `structure.csv`, `equipment.csv`, or `route.csv` — these will fail at load time because no such feature types exist in the NMT schema.

---

## Structures

Each structure subtype is a separate NMT feature:

| NMT Feature Type | Typical Source TYPE Codes |
|---|---|
| `pole` | POLE, POLEPED, WOODEN_POLE, STEEL_POLE |
| `cabinet` | CABINET, FDH, CROSS_CONNECT, PED |
| `manhole` | MANHOLE, HANDHOLE, VAULT, PULL_BOX |
| `wall_box` | WALL_BOX, BUILDING_ENTRY, NID, BEP |
| `building` | BUILDING, HEADEND, CENTRAL_OFFICE, HUB |
| `drop_point` | DROP_POINT, SERVICE_POINT, TAP |

- Map source TYPE codes to the correct NMT feature type
- Produce one CSV per type (e.g., `pole.csv`, `cabinet.csv`)

---

## Equipment

Each equipment category is a separate NMT feature:

| NMT Feature Type | Typical Source TYPE Codes |
|---|---|
| `splice_closure` | SPLICE_ENCLOSURE, SPLICE_CASE, CLOSURE |
| `fiber_splitter` | SPLITTER, PLC_SPLITTER (true 1:N optical power splitters ONLY) |
| `fiber_patch_panel` | PATCH_PANEL, ODF, FDP |
| `fiber_ont` | ONT, ONU, CPE |
| `fiber_card` | CARD, LINE_CARD, MODULE |
| `fiber_shelf` | SHELF, SUBRACK, CHASSIS |
| `rack` | RACK, FRAME, BAY |

- Map source equipment TYPE codes to the correct NMT feature type
- Produce one CSV per type (e.g., `splice_closure.csv`, `fiber_splitter.csv`)

---

## Routes

Split by construction method:

| NMT Feature Type | Source Indicators |
|---|---|
| `ug_route` | Underground, buried, trench, conduit, duct |
| `oh_route` | Overhead, aerial, pole-to-pole, strand |

- Map based on laying type or construction method field
- If unknown, default to `ug_route` (more common in most networks)

---

## Cables / Segments / Connections

Technology-specific:

| Technology | Cable | Segment | Connection |
|---|---|---|---|
| Fiber | `fiber_cable` | `mywcom_fiber_segment` | `mywcom_fiber_connection` |
| Copper | `copper_cable` | `mywcom_copper_segment` | `mywcom_copper_connection` |
| Coax | `coax_cable` | `mywcom_coax_segment` | `mywcom_coax_connection` |

---

## Reference / Non-Network Features

| NMT Feature Type | Purpose |
|---|---|
| `address` | Address points |
| `building_footprint` | Building outlines |
| `general_polygon` | Coverage areas, zones |
