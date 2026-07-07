# Astound Source System — ESRI ArcFM / Schneider Fiber Manager

## Overview

The source system is **Schneider Electric Fiber Manager** (formerly Telvent Miner & Miner ArcFM Fiber Manager), built on the **ESRI ArcGIS** platform. It uses ESRI's geometric network model for connectivity and a hierarchical containment model (via `FIBERPARENT` / class model names) for the fiber and internal equipment domains.

The data was exported as an ESRI File Geodatabase and converted to CSV + JSON definition files.

---

## Table of Contents

1. [Physical Infrastructure](#1-physical-infrastructure)
2. [Fiber Network](#2-fiber-network)
3. [RF/Coax Network](#3-rfcoax-network)
4. [Coax Signal Model (cx\_\*)](#4-coax-signal-model)
5. [Circuits & Logical Paths](#5-circuits--logical-paths)
6. [Network Topology (ESRI Geometric Network)](#6-network-topology)
7. [MDU (Multi-Dwelling Unit)](#7-mdu-multi-dwelling-unit)
8. [Reference / Other](#8-reference--other)
9. [Key Relationship Patterns](#9-key-relationship-patterns)
10. [Enumeration Values](#10-enumeration-values)

---

## 1. Physical Infrastructure

These layers represent the physical plant — poles, conduit, aerial/underground routes, and structures that house or support equipment.

| Layer                   | Geometry                  | Description                                         |
| ----------------------- | ------------------------- | --------------------------------------------------- |
| `support_structure`     | Point                     | Poles, aerial structures                            |
| `underground_structure` | Point                     | Manholes, handholes, pedestals, vaults              |
| `overhead_span`         | Linestring                | Aerial cable route segments between poles           |
| `underground_span`      | Linestring                | Underground cable route segments between structures |
| `duct`                  | None (inherits from span) | Innerducts within underground spans                 |
| `down_guy`              | Point                     | Guy wire anchor points at poles                     |
| `transition_point`      | Point                     | Aerial-to-underground transition points             |
| `fiber_slack_loop`      | Point                     | Slack storage loops on fiber routes                 |

### `support_structure`

| Field                    | Type         | Description                  |
| ------------------------ | ------------ | ---------------------------- |
| `id`                     | integer (PK) | Primary key                  |
| `globalid`               | string       | ESRI GlobalID (UUID)         |
| `networkid`              | string       | Geometric network ID         |
| `poletype`               | enum         | Pole type code (see enums)   |
| `name`                   | string       | Pole identifier              |
| `owner`                  | string       | Pole owner                   |
| `residentialcount`       | integer      | Residential addresses served |
| `commercialcount`        | integer      | Commercial addresses served  |
| `riserflag`              | integer      | Has riser attachment         |
| `latitude` / `longitude` | double       | Coordinates                  |

### `underground_structure`

| Field           | Type         | Description                                               |
| --------------- | ------------ | --------------------------------------------------------- |
| `id`            | integer (PK) | Primary key                                               |
| `globalid`      | string       | ESRI GlobalID                                             |
| `networkid`     | string       | Geometric network ID                                      |
| `structuretype` | enum         | Structure type (Manhole, Handhole, Pedestal, Vault, etc.) |
| `name`          | string       | Structure identifier                                      |

### `overhead_span`

| Field       | Type         | Description          |
| ----------- | ------------ | -------------------- |
| `id`        | integer (PK) | Primary key          |
| `globalid`  | string       | ESRI GlobalID        |
| `networkid` | string       | Geometric network ID |
| `type`      | string       | Span type            |
| `length`    | double       | Span length          |
| `isinmdu`   | integer      | Within MDU area      |

### `underground_span`

| Field          | Type         | Description          |
| -------------- | ------------ | -------------------- |
| `id`           | integer (PK) | Primary key          |
| `globalid`     | string       | ESRI GlobalID        |
| `networkid`    | string       | Geometric network ID |
| `containsduct` | integer      | Contains innerducts  |

### `duct`

| Field               | Type         | Description                   |
| ------------------- | ------------ | ----------------------------- |
| `id`                | integer (PK) | Primary key                   |
| `globalid`          | string       | ESRI GlobalID                 |
| `networkid`         | string       | Geometric network ID          |
| `undergroundspanid` | string (FK)  | → `underground_span.globalid` |
| `diameter`          | double       | Duct diameter                 |
| `name`              | string       | Duct identifier               |

### `down_guy`

| Field                | Type         | Description                    |
| -------------------- | ------------ | ------------------------------ |
| `id`                 | integer (PK) | Primary key                    |
| `globalid`           | string       | ESRI GlobalID                  |
| `supportstructureid` | string (FK)  | → `support_structure.globalid` |
| `anchortype`         | string       | Type of anchor                 |

---

## 2. Fiber Network

The fiber model uses a **hierarchical containment** pattern. Every fiber-domain object has:

-   `FIBERPARENT` — GlobalID of the parent container
-   `THISFIBERCLASSMODELNAME` — This object's class type
-   `FIBERPARENTCLASSMODELNAME` — Parent's class type
-   `FIBERCHILDCLASSMODELNAME` — Expected child class type

### Containment Hierarchy

```
patch_location (FIBERPATCHLOCATION)
  └── f_rack (RACK)
       └── f_patch_panel (PATCHPANEL)
            └── f_patch_panel_card (PATCHPANELCARD)
                 ├── f_frontside_port (FRONTSIDEPORT)
                 └── f_backside_port (BACKSIDEPORT)
       └── f_device (FIBERDEVICE)
            └── f_device_port (DEVICEPORT)
       └── f_combiner (COMBINER)
            ├── f_combiner_input_port
            └── f_combiner_output_port

splice_point (SPLICEPOINT)
  └── f_splitter (SPLITTERDEVICE)
       ├── f_splitter_input_port (SPLITTERINPUTPORT)
       └── f_splitter_output_port (SPLITTEROUTPUTPORT)
  └── f_splitterpanel (SPLITTERPANEL)
       └── f_splitterpanelcard (SPLITTERPANELCARD)
  └── f_fiber_connection_object (splice records)

fiber_optic_cable (SHEATH)
  └── f_buffer_tube (BUFFERTUBE)
       └── f_fiber (FIBERSTRAND)

coaxial_cable (COAXIALCABLE)
  └── cx_rfsignal / cx_coaxpower (signal objects)
```

### Layer Details

#### `fiber_optic_cable` — Physical fiber cable sheath

| Field                      | Type         | Description                |
| -------------------------- | ------------ | -------------------------- |
| `id`                       | integer (PK) | Primary key                |
| `globalid`                 | string       | ESRI GlobalID              |
| `fiberparent`              | string       | Empty for top-level cables |
| `thisfiberclassmodelname`  | string       | `"SHEATH"`                 |
| `fiberchildclassmodelname` | string       | `"BUFFERTUBE"`             |
| `fibercount`               | integer      | Total fiber count          |
| `cablename`                | string       | Cable identifier           |
| `cabletype`                | string       | Cable type/model           |
| `cablelength`              | double       | Total length               |
| `aerialunderground`        | string       | Placement type             |
| `cableowner`               | string       | Owner                      |
| `market`                   | string       | Market/region              |

#### `f_buffer_tube` — Buffer tubes within a cable

| Field                       | Type         | Description                    |
| --------------------------- | ------------ | ------------------------------ |
| `id`                        | integer (PK) | Primary key                    |
| `globalid`                  | string       | ESRI GlobalID                  |
| `fiberparent`               | string (FK)  | → `fiber_optic_cable.globalid` |
| `thisfiberclassmodelname`   | string       | `"BUFFERTUBE"`                 |
| `fiberparentclassmodelname` | string       | `"SHEATH"`                     |
| `fiberchildclassmodelname`  | string       | `"FIBERSTRAND"`                |
| `buffertubeposition`        | integer      | Position in cable              |
| `buffertubenumber`          | integer      | Tube number                    |
| `buffertubecolor`           | string       | Color code                     |

#### `f_fiber` — Individual fiber strands

| Field                       | Type         | Description                     |
| --------------------------- | ------------ | ------------------------------- |
| `id`                        | integer (PK) | Primary key                     |
| `globalid`                  | string       | ESRI GlobalID                   |
| `fiberparent`               | string (FK)  | → `f_buffer_tube.globalid`      |
| `thisfiberclassmodelname`   | string       | `"FIBERSTRAND"`                 |
| `fiberparentclassmodelname` | string       | `"BUFFERTUBE"`                  |
| `fibernumber`               | integer      | Fiber number within tube        |
| `fibercolor`                | string       | Color of fiber                  |
| `modetype`                  | string       | Singlemode / Multimode          |
| `available`                 | integer      | Is fiber available (not in use) |
| `status`                    | string       | Current status                  |
| `fibercircuitglobalid`      | string (FK)  | → `f_circuit.globalid`          |

#### `f_fiber_connection_object` — Splice / connector records

| Field                       | Type         | Description                               |
| --------------------------- | ------------ | ----------------------------------------- |
| `id`                        | integer (PK) | Primary key                               |
| `globalid`                  | string       | ESRI GlobalID                             |
| `containerglobalid`         | string (FK)  | → splice_point or patch_location GlobalID |
| `containerclassmodelname`   | string       | `"SPLICEPOINT"` or `"FIBERPATCHLOCATION"` |
| `aconnectionobjectglobalid` | string (FK)  | → A-side fiber/port GlobalID              |
| `bconnectionobjectglobalid` | string (FK)  | → B-side fiber/port GlobalID              |
| `aclassmodelname`           | string       | A-side class (e.g., `"FIBERSTRAND"`)      |
| `bclassmodelname`           | string       | B-side class (e.g., `"FIBERSTRAND"`)      |
| `traynumber`                | integer      | Splice tray number                        |
| `splicetype`                | string       | Fusion / Mechanical                       |
| `attenuation1310`           | double       | Loss at 1310nm (dB)                       |
| `attenuation1550`           | double       | Loss at 1550nm (dB)                       |
| `connectiontype`            | integer      | Type code                                 |
| `fibercircuitglobalid`      | string (FK)  | → `f_circuit.globalid`                    |

#### `splice_point` — Physical splice enclosure locations

| Field                    | Type         | Description                        |
| ------------------------ | ------------ | ---------------------------------- |
| `id`                     | integer (PK) | Primary key                        |
| `globalid`               | string       | ESRI GlobalID                      |
| `fiberstructureglobalid` | string (FK)  | → `underground_structure.globalid` |
| `poleglobalid`           | string (FK)  | → `support_structure.globalid`     |
| `splicepointname`        | string       | Splice closure name                |
| `spliceenclosuretype`    | string       | Enclosure model                    |
| `locationtype`           | string       | Aerial / Underground               |

#### `patch_location` — Hub / headend buildings

| Field                     | Type         | Description                        |
| ------------------------- | ------------ | ---------------------------------- |
| `id`                      | integer (PK) | Primary key                        |
| `globalid`                | string       | ESRI GlobalID                      |
| `fiberstructureglobalid`  | string (FK)  | → `underground_structure.globalid` |
| `poleglobalid`            | string (FK)  | → `support_structure.globalid`     |
| `name`                    | string       | Building/site name                 |
| `type`                    | string       | Location type                      |
| `ospfeedtype`             | string       | Feed type                          |
| `nodenum`                 | string       | Associated node number             |
| `thisfiberclassmodelname` | string       | `"FIBERPATCHLOCATION"`             |

#### `device_point` — Generic equipment locations

| Field                    | Type         | Description                        |
| ------------------------ | ------------ | ---------------------------------- |
| `id`                     | integer (PK) | Primary key                        |
| `globalid`               | string       | ESRI GlobalID                      |
| `fiberstructureglobalid` | string (FK)  | → `underground_structure.globalid` |
| `poleglobalid`           | string (FK)  | → `support_structure.globalid`     |
| `devicepointname`        | string       | Device name                        |
| `devicetype`             | string       | Device type                        |

#### `f_rack` — Equipment racks

| Field                       | Type        | Description                 |
| --------------------------- | ----------- | --------------------------- |
| `fiberparent`               | string (FK) | → `patch_location.globalid` |
| `thisfiberclassmodelname`   | string      | `"RACK"`                    |
| `fiberparentclassmodelname` | string      | `"FIBERPATCHLOCATION"`      |
| `fiberchildclassmodelname`  | string      | `"PATCHPANEL"`              |
| `name`                      | string      | Rack identifier             |
| `slotrows` / `slotcolumns`  | integer     | Rack dimensions             |

#### `f_patch_panel` — Patch panels in racks

| Field                                      | Type        | Description         |
| ------------------------------------------ | ----------- | ------------------- |
| `fiberparent`                              | string (FK) | → `f_rack.globalid` |
| `thisfiberclassmodelname`                  | string      | `"PATCHPANEL"`      |
| `fiberparentclassmodelname`                | string      | `"RACK"`            |
| `fiberchildclassmodelname`                 | string      | `"PATCHPANELCARD"`  |
| `numberofcardrows` / `numberofcardcolumns` | integer     | Card layout         |

#### `f_patch_panel_card` — Cards/shelves in panels

| Field         | Type        | Description                |
| ------------- | ----------- | -------------------------- |
| `fiberparent` | string (FK) | → `f_patch_panel.globalid` |

#### `f_frontside_port` / `f_backside_port` — Patch panel ports

| Field                         | Type        | Description                           |
| ----------------------------- | ----------- | ------------------------------------- |
| `fiberparent`                 | string (FK) | → `f_patch_panel_card.globalid`       |
| `portnumber`                  | integer     | Port position                         |
| `portname`                    | string      | Port label                            |
| `porttype`                    | string      | Connector type (SC, LC, etc.)         |
| `fibercircuitglobalid`        | string (FK) | → `f_circuit.globalid`                |
| `pigtailcolor`                | string      | (backside only) Pigtail color         |
| `impliedconnectionsourceguid` | string      | (backside only) Implied cross-connect |

#### `f_splitter` — Optical splitters (1×N)

| Field                     | Type        | Description                           |
| ------------------------- | ----------- | ------------------------------------- |
| `fiberparent`             | string (FK) | → splice_point or rack GlobalID       |
| `thisfiberclassmodelname` | string      | `"SPLITTERDEVICE"`                    |
| `types`                   | string      | Split ratio (e.g., "1 x 32", "1 x 2") |

#### `f_splitter_input_port` / `f_splitter_output_port`

| Field                  | Type        | Description             |
| ---------------------- | ----------- | ----------------------- |
| `fiberparent`          | string (FK) | → `f_splitter.globalid` |
| `portnumber`           | integer     | Port number             |
| `portname`             | string      | Port label              |
| `portstatus`           | string      | Status                  |
| `fibercircuitglobalid` | string (FK) | → `f_circuit.globalid`  |

#### `f_device` — Active fiber devices (OLT, ONT, etc.)

| Field          | Type        | Description          |
| -------------- | ----------- | -------------------- |
| `fiberparent`  | string (FK) | → container GlobalID |
| `rackglobalid` | string (FK) | → `f_rack.globalid`  |
| `name`         | string      | Device name          |
| `devicetype`   | string      | Device type          |
| `manufacturer` | string      | Manufacturer         |
| `devicemodel`  | string      | Model number         |

#### `f_device_port` — Ports on active devices

| Field                  | Type        | Description            |
| ---------------------- | ----------- | ---------------------- |
| `fiberparent`          | string (FK) | → `f_device.globalid`  |
| `portnumber`           | integer     | Port number            |
| `portname`             | string      | Port label             |
| `porttype`             | string      | Connector type         |
| `portfunction`         | string      | TX/RX/TXRX             |
| `fibercircuitglobalid` | string (FK) | → `f_circuit.globalid` |

#### `f_fiberbacksideports` / `f_fiberfrontsideport` — Fiber ports on RF nodes

| Field                                   | Type        | Description            |
| --------------------------------------- | ----------- | ---------------------- |
| `fiberparent`                           | string (FK) | → RF node GlobalID     |
| `inputportglobalid`                     | string (FK) | → connected port       |
| `fibercircuitglobalid`                  | string (FK) | → `f_circuit.globalid` |
| `attenuationafreq` / `attenuationbfreq` | double      | Attenuation values     |

#### `f_plnode` — Patch location network node

| Field         | Type        | Description        |
| ------------- | ----------- | ------------------ |
| `fiberparent` | string (FK) | → parent container |
| `nodetype`    | string      | Node type          |

#### `f_combiner` / `f_passivedevice` — WDM combiners & passive devices

| Field                               | Type        | Description          |
| ----------------------------------- | ----------- | -------------------- |
| `fiberparent`                       | string (FK) | → container GlobalID |
| `fiberrackglobalid`                 | string (FK) | → `f_rack.globalid`  |
| (passive) `lambdamin` / `lambdamax` | double      | Wavelength filtering |

#### `f_splitterpanel` / `f_splitterpanelcard` — Splitter panel housing

#### `fiber_dataset_net_junctions` — ESRI geometric network junction points (auto-generated)

---

## 3. RF/Coax Network

### DHFC (Designer Hybrid Fiber Coax) — System Overview

The coax/RF portion of the Astound data model comes from **Schneider Electric's Designer Hybrid Fiber Coax (DHFC)** application, an industry-leading system for creating and maintaining HFC (Hybrid Fiber Coax) networks. DHFC provides a transparent workflow that analyzes the validity of a design in real time, giving engineers immediate feedback on how one component or node decision affects the entire network.

Per the [official documentation](<https://productinfo.se.com/arcfmsolution/dhfc-with-arcgis-pro/DHFC%20Config/English/Designer%20Hybrid%20Fiber%20Coax%20Config%20Guide%20(bookmap)_0000282840.xml>):

> The core architecture of DHFC comprises a connected series of applications: **Geodatabase** (geospatial data / system of record), **ArcGIS Server** (intermediary between geodatabase and DHFC client), **DHFC Catalog Service** (non-GIS configurations: specs, groupings, project files), **Solution Center DHFC Plugin** (configuration hub), and **DHFC Client Application** (desktop design tool).

#### DHFC Data Architecture Principles

The DHFC data model separates the coax network into:

1. **Physical Network** — Geographic features (points, lines, polygons) representing the physical plant

    - RF equipment (nodes, amplifiers, taps, couplers, splitters, terminators)
    - RF cables (distribution coax)
    - Physical structures (shared with fiber: poles, pedestals, manholes)
    - Boundary/service areas (node boundaries, power supply boundaries)

2. **Signal Network** — Non-spatial object classes tracking RF signal propagation and power distribution

    - RF signal objects (`cx_rfsignal`) — logical signals carried on coax
    - RF ports (input/output/frontside/backside) — signal entry/exit points on devices
    - Power signal objects (`cx_coaxpower`) — AC power on the coax plant
    - Power ports — power distribution through devices

3. **Dual-Network Model (Analog + Digital)** — The same physical plant supports two separate signal networks:
    - **Analog (`_a`)** — Forward-path RF signals (traditional video/CATV)
    - **Digital (`_d`)** — DOCSIS/digital overlay (data, voice, digital video)

#### DHFC Connectivity Model

Unlike the fiber model (which uses `FIBERPARENT` containment), the RF/coax model uses:

-   **`NETWORKID`** — A unique identifier for each device in the geometric network (distinct from `GLOBALID`)
-   **`FEDFROMCOMPONENTID`** — Points to the upstream device's `NETWORKID`, forming a directed signal tree from node to endpoints
-   **Port objects** — `rf_node_coax_port`, `rf_amplifier_port`, `rf_coupler_port` link devices to cables via `connecteditemid`
-   **ESRI Geometric Network** — The `n_2_*` tables store binary connectivity, but the explicit FK fields above are the practical source of topology

#### DHFC Signal Calculation

DHFC calculates RF signal levels at every device in the network:

-   Forward signal levels (from headend/node toward customer) — measured in dBmV
-   Return signal levels (from customer toward headend) — measured in dBmV
-   Power levels (AC voltage on the coax plant) — measured in volts/amps
-   Signal-to-noise ratios, carrier-to-noise, distortion metrics

These calculated values are stored in the `cx_*` port tables (`inputhigh`, `inputlow`, `rfsignalhighattenuation`, etc.) and on device attributes (`forwarddropsignalhigh`, `forwarddropsignallow`).

#### DHFC Equipment Hierarchy

```
Headend / Hub (patch_location)
  └── Fiber optic cable → rf_node (optical-to-electrical conversion)
       │
       ├── rf_cable_a (trunk/distribution cable)
       │    ├── rf_amplifier (line amplifier / trunk station)
       │    │    ├── Internal: rf_equalizer (frequency tilt compensation)
       │    │    └── Internal: rf_pad (signal attenuation)
       │    │
       │    ├── rf_coupler (directional coupler — asymmetric split)
       │    │    └── rf_cable_a (leg output at reduced signal level)
       │    │
       │    ├── rf_splitter (symmetric split — 2-way or 3-way)
       │    │    └── rf_cable_a (equal-level outputs)
       │    │
       │    ├── rf_tap (subscriber access — multi-port, high isolation)
       │    │    └── rf_drop (customer premise cable)
       │    │         └── address_point (service address)
       │    │
       │    ├── rf_splice (cable-to-cable connection)
       │    ├── rf_inline_eq (inline equalizer between devices)
       │    └── rf_power_block (prevents AC power from passing)
       │
       ├── rf_power_supply (AC power source for coax plant)
       │    └── rf_power_inserter (injects AC power onto coax)
       │
       └── rf_terminator (end-of-line — prevents signal reflections)
```

#### DHFC vs. Fiber Manager Integration

The RF node (`rf_node`) is the bridge between the fiber and coax domains:

-   **Fiber side**: The node has fiber ports (`f_fiberbacksideports`, `f_fiberfrontsideport`) connected to fiber strands via `f_fiber_connection_object`
-   **Coax side**: The node has coax ports (`rf_node_coax_port_a/d`) connected to RF cables via `connecteditemid`
-   Both domains share the same physical structures (`support_structure`, `underground_structure`) via `aerialstructureid`/`ugstructureid`

### Naming Convention: `_a` (Analog) vs `_d` (Digital)

The RF network is **dual-modeled**. Every device type exists in both variants:

-   **`_a`** — Analog/forward-path (750MHz/870MHz/1GHz traditional HFC plant)
-   **`_d`** — Digital overlay (DOCSIS/return-path/upgraded digital plant)

They share identical schemas but represent **separate signal networks** within the same physical infrastructure.

#### Why Two Networks?

In a traditional HFC system:

-   The **analog network** carries forward-path RF signals (broadcast video, CATV channels) from the headend toward customers. This is the "legacy" cable TV plant.
-   The **digital network** carries DOCSIS data signals (internet, VoIP, digital video) which may use different frequency plans, different amplifier configurations, or upgraded equipment.

Many operators upgraded their plant incrementally — adding digital capabilities alongside existing analog infrastructure. DHFC models this by maintaining parallel `_a` and `_d` records for each device, allowing engineers to analyze each signal path independently while sharing the same physical geometry.

#### Parent Feature Class vs. Detail Table Pattern

For each RF equipment type, DHFC maintains:

| Role                     | Example                                | Has Geometry                   | In Geometric Network | Purpose                                       |
| ------------------------ | -------------------------------------- | ------------------------------ | -------------------- | --------------------------------------------- |
| **Parent feature class** | `rf_tap`                               | Yes (Point)                    | Yes                  | Map display, geometric network participation  |
| **Analog detail table**  | `rf_tap_a`                             | Yes (Point, usually identical) | No                   | Full signal-level attributes, analog network  |
| **Digital detail table** | `rf_tap_d`                             | Yes (Point, usually identical) | No                   | Full signal-level attributes, digital network |
| **Port table**           | `rf_tap` ports via `rf_coupler_port_a` | No                             | No                   | Per-port connectivity and signal levels       |

The parent feature class participates in the ESRI geometric network and provides the canonical geometry. The `_a`/`_d` tables carry the detailed engineering attributes. In the Astound export, the geometry is duplicated between parent and detail tables.

### Signal Flow Pattern

All RF devices use `FEDFROMCOMPONENTID` → upstream device's `NETWORKID` to establish the signal chain. This is the DHFC "feed" model: each device knows which upstream component feeds it RF signal, creating a directed acyclic graph (DAG) from the optical node to every endpoint.

```
rf_node_a/d (fiber-to-coax conversion, source of RF signal)
  │
  ├── rf_cable_a/d (distribution cable, fedfromcomponentid → node.networkid)
  │     │
  │     ├── rf_amplifier_a/d (line amp, fedfromcomponentid → cable/upstream)
  │     │     └── rf_cable_a/d → next device...
  │     │
  │     ├── rf_coupler_a/d (directional coupler / tap-off)
  │     │     └── rf_cable_a/d → downstream...
  │     │
  │     ├── rf_tap_a/d (subscriber access point)
  │     │     └── rf_drop (customer drop)
  │     │
  │     └── rf_splice_a/d (cable splice)
  │
  └── rf_terminator_a/d (end of line)
```

#### Signal-Level Attributes (DHFC Calculated Fields)

Each `_a`/`_d` device table stores DHFC-calculated signal metrics:

| Attribute Pattern          | Description                                   | Units |
| -------------------------- | --------------------------------------------- | ----- |
| `forwarddropsignalhigh`    | Forward-path signal drop at highest frequency | dB    |
| `forwarddropsignallow`     | Forward-path signal drop at lowest frequency  | dB    |
| `reversegainsignalhigh`    | Return-path gain at highest frequency         | dB    |
| `reversegainsignallow`     | Return-path gain at lowest frequency          | dB    |
| `inputhigh` / `inputlow`   | RF input level at device (on ports)           | dBmV  |
| `outputhigh` / `outputlow` | RF output level at device (on ports)          | dBmV  |
| `rfsignalhighattenuation`  | Attenuation at high frequency                 | dB    |
| `rfsignallowattenuation`   | Attenuation at low frequency                  | dB    |

These values are calculated by DHFC's RF engine traversing the signal tree from node to endpoint, applying each device's insertion loss, cable attenuation per meter, and frequency-dependent characteristics.

### Power Network Pattern

DHFC also models the **AC power distribution** on the coax plant (line powering). This is separate from the RF signal network:

-   **`rf_power_supply_a/d`** — AC power sources that inject voltage onto the coax cable
-   **`rf_power_inserter_a/d`** — Devices that inject AC power at specific points
-   **`rf_power_block_a/d`** — Devices that prevent AC from passing (power boundary)
-   **`cx_coaxpower`** — Non-spatial power signal objects tracking voltage/current

Power flows through the same coax cables as RF signal but has different rules:

-   Power passes through amplifiers (which require it) and passive devices
-   Power blocks and power inserters create power segments
-   Power supply boundaries (`rf_power_supply_bndy`) define service areas

### Layer Details

#### `rf_node_a` / `rf_node_d` — Fiber-to-Coax optical nodes

| Field                | Type         | Description                        |
| -------------------- | ------------ | ---------------------------------- |
| `id`                 | integer (PK) | Primary key                        |
| `networkid`          | string       | Network ID (used as FK target)     |
| `globalid`           | string       | ESRI GlobalID                      |
| `aerialstructureid`  | string (FK)  | → `support_structure.globalid`     |
| `ugstructureid`      | string (FK)  | → `underground_structure.globalid` |
| `name`               | string       | Node name/number                   |
| `portconfiguration`  | string       | Port layout                        |
| `coaxportcount`      | integer      | Number of coax output ports        |
| `fiberportcount`     | integer      | Number of fiber input ports        |
| `designfrequency`    | double       | Design frequency (MHz)             |
| `powersupplyid`      | string (FK)  | → `rf_power_supply.networkid`      |
| `fedfromcomponentid` | string       | Upstream fiber feed                |

#### `rf_node_coax_port_a` / `rf_node_coax_port_d` — Node coax ports

| Field             | Type         | Description                |
| ----------------- | ------------ | -------------------------- |
| `id`              | integer (PK) | Primary key                |
| `globalid`        | string       | ESRI GlobalID              |
| `nodeid`          | string (FK)  | → `rf_node_a.networkid`    |
| `connecteditemid` | string (FK)  | → `rf_cable_a.networkid`   |
| `portnumber`      | integer      | Port number                |
| `portname`        | string       | Port label (A, B, C, D...) |
| `homespassed`     | integer      | Homes passed on this port  |
| `ispoweronly`     | integer      | Power-only port flag       |

#### `rf_amplifier_a` / `rf_amplifier_d` — Line amplifiers

| Field                          | Type         | Description                          |
| ------------------------------ | ------------ | ------------------------------------ |
| `id`                           | integer (PK) | Primary key                          |
| `networkid`                    | string       | Network ID                           |
| `globalid`                     | string       | ESRI GlobalID                        |
| `aerialstructureid`            | string (FK)  | → `support_structure.globalid`       |
| `ugstructureid`                | string (FK)  | → `underground_structure.globalid`   |
| `fedfromcomponentid`           | string (FK)  | → upstream device networkid          |
| `name`                         | string       | Amplifier name                       |
| `amptype`                      | string       | Type (Trunk, Bridger, Line Extender) |
| `ampnumber`                    | string       | Amp number in cascade                |
| `cascadenumber`                | integer      | Cascade depth from node              |
| `manufacturer`                 | string       | Manufacturer                         |
| `modelnumber`                  | string       | Model                                |
| `internalpowermapping`         | string       | Power routing                        |
| `forwardeqid` / `returneqid`   | string       | Equalizer references                 |
| `forwardpadid` / `returnpadid` | string       | Pad references                       |

#### `rf_amplifier_port_a` / `rf_amplifier_port_d` — Amplifier ports

| Field             | Type        | Description                  |
| ----------------- | ----------- | ---------------------------- |
| `amplifierid`     | string (FK) | → `rf_amplifier_a.networkid` |
| `connecteditemid` | string (FK) | → `rf_cable_a.networkid`     |
| `portnumber`      | integer     | Port number                  |

#### `rf_cable_a` / `rf_cable_d` — Coaxial distribution cable

| Field                | Type         | Description                 |
| -------------------- | ------------ | --------------------------- |
| `id`                 | integer (PK) | Primary key                 |
| `networkid`          | string       | Network ID                  |
| `globalid`           | string       | ESRI GlobalID               |
| `fedfromcomponentid` | string (FK)  | → upstream device networkid |
| `length`             | double       | Cable length                |
| `diameter`           | string       | Cable size                  |
| `manufacturer`       | string       | Manufacturer                |
| `nodename`           | string       | Parent node name            |
| `isdirectbury`       | integer      | Direct burial flag          |
| `name`               | string       | Cable identifier            |

#### `rf_tap_a` / `rf_tap_d` — Customer taps

| Field                                            | Type         | Description                        |
| ------------------------------------------------ | ------------ | ---------------------------------- |
| `id`                                             | integer (PK) | Primary key                        |
| `networkid`                                      | string       | Network ID                         |
| `globalid`                                       | string       | ESRI GlobalID                      |
| `aerialstructureid`                              | string (FK)  | → `support_structure.globalid`     |
| `ugstructureid`                                  | string (FK)  | → `underground_structure.globalid` |
| `fedfromcomponentid`                             | string (FK)  | → upstream device networkid        |
| `portcount`                                      | integer      | Number of subscriber ports         |
| `name`                                           | string       | Tap name                           |
| `manufacturer` / `modelnumber`                   | string       | Equipment details                  |
| `isendofline`                                    | integer      | End-of-line flag                   |
| `isselfterminating`                              | integer      | Self-terminating flag              |
| `forwarddropsignalhigh` / `forwarddropsignallow` | double       | Signal levels                      |

#### `rf_coupler_a` / `rf_coupler_d` — Directional couplers

| Field                                | Type        | Description                 |
| ------------------------------------ | ----------- | --------------------------- |
| `networkid`                          | string      | Network ID                  |
| `fedfromcomponentid`                 | string (FK) | → upstream device networkid |
| `couplertype`                        | string      | Type code                   |
| `forwardlosshigh` / `forwardlosslow` | double      | Loss values                 |
| `portconfiguration`                  | string      | Port layout                 |

#### `rf_coupler_port_a` / `rf_coupler_port_d` — Coupler ports

| Field             | Type        | Description                |
| ----------------- | ----------- | -------------------------- |
| `couplerid`       | string (FK) | → `rf_coupler_a.networkid` |
| `connecteditemid` | string (FK) | → `rf_cable_a.networkid`   |

#### `rf_splice_a` / `rf_splice_d` — Coax cable splices

| Field                | Type        | Description                   |
| -------------------- | ----------- | ----------------------------- |
| `networkid`          | string      | Network ID                    |
| `fedfromcomponentid` | string (FK) | → upstream device networkid   |
| `feedscomponentid`   | string (FK) | → downstream device networkid |
| `diameter`           | string      | Cable diameter at splice      |

#### `rf_power_supply_a` / `rf_power_supply_d` — Power supplies

| Field                                 | Type        | Description           |
| ------------------------------------- | ----------- | --------------------- |
| `networkid`                           | string      | Network ID            |
| `globalid`                            | string      | ESRI GlobalID         |
| `aerialstructureid` / `ugstructureid` | string (FK) | Structure attachment  |
| `name`                                | string      | PS name               |
| `amperage` / `maxamperage`            | double      | Current draw/capacity |
| `voltage`                             | double      | Voltage               |
| `manufacturer`                        | string      | Manufacturer          |

#### `rf_power_inserter_a` / `rf_power_inserter_d` — Power inserters

-   Contains `rf_power_inserter_port_a/d` (ports)

#### `rf_terminator_a` / `rf_terminator_d` — End-of-line terminators

#### `rf_equalizer_a` / `rf_equalizer_d` — Equalizers (internal to amps)

#### `rf_inline_eq_a` / `rf_inline_eq_d` — Inline equalizers

#### `rf_pad_a` / `rf_pad_d` — Signal attenuator pads

#### `rf_power_block_a` / `rf_power_block_d` — Power blocking devices

#### `rf_hot_dot_a` / `rf_hot_dot_d` — Signal test points

#### `rf_housing_to_housing_a` / `rf_housing_to_housing_d` — Internal housing connections

#### `rf_drop` — Customer drop cables (NOT split into \_a/\_d)

| Field             | Type         | Description           |
| ----------------- | ------------ | --------------------- |
| `id`              | integer (PK) | Primary key           |
| `globalid`        | string       | ESRI GlobalID         |
| `networkid`       | string       | Network ID            |
| `aerial_ug`       | string       | Aerial or underground |
| `recorded_length` | double       | Drop length           |

#### `rf_drop_arrow` — Drop arrow annotation points

### Boundary / Service Area Layers

| Layer                               | Geometry | Description                  |
| ----------------------------------- | -------- | ---------------------------- |
| `rf_node_boundary_a` / `_d`         | Polygon  | Node service area boundaries |
| `rf_power_supply_boundary_a` / `_d` | Polygon  | Power supply service areas   |
| `rf_do_not_build_boundary_a` / `_d` | Polygon  | Restricted build zones       |
| `rf_node_dhfc_a`                    | Point    | Digital HFC node variant     |

#### `rf_node_boundary_a` / `rf_node_boundary_d`

| Field           | Type        | Description             |
| --------------- | ----------- | ----------------------- |
| `networkid`     | string      | Network ID              |
| `nodenetworkid` | string (FK) | → `rf_node_a.networkid` |
| `name`          | string      | Node boundary name      |
| `homespassed`   | integer     | Total homes in boundary |
| `market`        | string      | Market/region           |
| `hubsite`       | string      | Hub site name           |

### Cable-to-Span Junction Tables

| Junction Table                | Left FK                                     | Right FK                                                  |
| ----------------------------- | ------------------------------------------- | --------------------------------------------------------- |
| `rf_cable_a_overhead_span`    | `rfcablenetworkid` → `rf_cable_a.networkid` | `overheadspannetworkid` → `overhead_span.networkid`       |
| `rf_cable_a_underground_span` | `rfcablenetworkid` → `rf_cable_a.networkid` | `undergroundspannetworkid` → `underground_span.networkid` |
| `rf_cable_a_duct`             | `rfcableid` → `rf_cable_a`                  | `ductid` → `duct`                                         |
| `rf_cable_d_overhead_span`    | (same pattern as \_a)                       |                                                           |
| `rf_cable_d_underground_span` | (same pattern as \_a)                       |                                                           |
| `rf_cable_d_duct`             | (same pattern as \_a)                       |                                                           |

### Power Supply Boundary Junction Tables

| Junction Table                                 | Description                                       |
| ---------------------------------------------- | ------------------------------------------------- |
| `rf_power_supply_boundary_a_rf_power_supply_a` | Links PS boundary polygons to PS points (analog)  |
| `rf_power_supply_boundary_rf_power_supply_d`   | Links PS boundary polygons to PS points (digital) |

### "Parent" RF Feature Classes (Geometry-Only)

These are legacy ESRI geometric network features that hold only geometry and basic attributes. The detailed attribute data lives in the `_a`/`_d` tables:

| Layer                    | Description                   |
| ------------------------ | ----------------------------- |
| `rf_amplifier`           | Amplifier geometry points     |
| `rf_node`                | Node geometry points          |
| `rf_power_inserter`      | Power inserter geometry       |
| `rf_power_supply`        | Power supply geometry         |
| `rf_power_stop`          | Power stop geometry           |
| `rf_splice`              | Coax splice geometry          |
| `rf_splitter`            | RF splitter geometry          |
| `rf_tap`                 | Tap geometry                  |
| `rf_terminator`          | Terminator geometry           |
| `rf_in_line_equalizer`   | Inline equalizer geometry     |
| `rf_signal_dot`          | Signal measurement annotation |
| `rf_status_monitor_unit` | Status monitoring device      |

---

## 4. Coax Signal Model (DHFC Non-Spatial Objects)

The `cx_*` tables model **logical RF and power signals** carried on the coaxial network. These are DHFC's **non-spatial object classes** — they have no geometry of their own but are contained within spatial features via the `FIBERPARENT` relationship (same containment pattern as fiber domain).

In DHFC's architecture, these objects represent the **signal-level view** of the network:

-   **RF Signal Objects** track individual radio frequencies propagating through the plant
-   **Port Objects** represent the physical input/output connections on each device, storing per-port signal levels
-   **Power Objects** track AC line power distribution through the coax plant

#### Port Architecture

DHFC uses a **four-port model** for coax devices:

| Port Type          | Table Pattern        | Direction            | Purpose                                     |
| ------------------ | -------------------- | -------------------- | ------------------------------------------- |
| **Input Port**     | `cx_rfinputport`     | Signal enters device | Upstream connection (from feeder cable)     |
| **Output Port**    | `cx_rfoutputport`    | Signal exits device  | Downstream connection (to distribution)     |
| **Frontside Port** | `cx_rffrontsideport` | Customer-facing      | Subscriber ports (e.g., tap ports to drops) |
| **Backside Port**  | `cx_rfbacksideports` | Equipment-internal   | Internal connections between modules        |

Each port records signal levels (`inputhigh`/`inputlow`/`outputhigh`/`outputlow`), attenuation, and connectivity (`connecteditemid`, `impliedconnectionsourceguid`). The port `fiberparent` links back to the parent device's `GLOBALID`.

#### Relationship to Spatial Features

```
rf_amplifier_a (spatial feature, has geometry, GLOBALID = "ABC123")
  ├── cx_rfinputport    (fiberparent = "ABC123", portnumber = 1)
  ├── cx_rfoutputport   (fiberparent = "ABC123", portnumber = 1)
  ├── cx_rfoutputport   (fiberparent = "ABC123", portnumber = 2)
  ├── cx_rfsignal       (fiberparent = "ABC123", radiofrequency = 750.0)
  ├── cx_coaxpower      (fiberparent = "ABC123", power = 60.0)
  └── cx_powerinputport (fiberparent = "ABC123", portnumber = 1)
```

| Layer                   | Description                                     |
| ----------------------- | ----------------------------------------------- |
| `cx_rfsignal`           | RF signal objects (frequencies carried on coax) |
| `cx_rfinputport`        | RF input ports on coax devices                  |
| `cx_rfoutputport`       | RF output ports on coax devices                 |
| `cx_rffrontsideport`    | RF front-side device ports (subscriber-facing)  |
| `cx_rfbacksideports`    | RF back-side device ports (internal/equipment)  |
| `cx_coaxpower`          | Coax power signal objects (AC line power)       |
| `cx_powerinputport`     | Power input ports                               |
| `cx_poweroutputport`    | Power output ports                              |
| `cx_powerfrontsideport` | Power front-side ports                          |
| `cx_powerbacksideports` | Power back-side ports                           |

### `cx_rfsignal`

| Field                  | Type        | Description              |
| ---------------------- | ----------- | ------------------------ |
| `globalid`             | string      | ESRI GlobalID            |
| `fiberparent`          | string (FK) | → parent device GlobalID |
| `fibercircuitglobalid` | string (FK) | → circuit                |
| `radiofrequency`       | double      | Signal frequency         |
| `status`               | string      | Signal status            |
| `available`            | integer     | Availability             |

### `cx_rfinputport` / `cx_rfoutputport`

| Field                                                | Type        | Description                      |
| ---------------------------------------------------- | ----------- | -------------------------------- |
| `fiberparent`                                        | string (FK) | → parent device GlobalID         |
| `portnumber`                                         | integer     | Port number                      |
| `portname`                                           | string      | Port label                       |
| `inputhigh` / `inputlow`                             | double      | Signal level range               |
| `rfsignalhighattenuation` / `rfsignallowattenuation` | double      | Attenuation values               |
| `porttype`                                           | string      | Port type                        |
| `impliedconnectionsourceguid`                        | string      | (output only) Auto-connection    |
| `returninputhigh` / `returninputlow`                 | double      | (output only) Return path levels |

### `cx_coaxpower`

| Field         | Type        | Description              |
| ------------- | ----------- | ------------------------ |
| `fiberparent` | string (FK) | → parent device GlobalID |
| `power`       | double      | Power level              |
| `status`      | string      | Power status             |

---

## 5. Circuits & Logical Paths

### `f_circuit` — End-to-end fiber circuits

| Field                        | Type         | Description               |
| ---------------------------- | ------------ | ------------------------- |
| `id`                         | integer (PK) | Primary key               |
| `globalid`                   | string       | ESRI GlobalID             |
| `circuitname`                | string       | Circuit identifier        |
| `circuitlength`              | double       | Total circuit length      |
| `circuittype`                | string       | Circuit type              |
| `circuitgroup`               | string       | Grouping                  |
| `circuitmanagementsystem`    | string       | External CMS reference    |
| `circuitotdratten1310`       | double       | OTDR attenuation @ 1310nm |
| `circuitotdratten1550`       | double       | OTDR attenuation @ 1550nm |
| `otdrdate`                   | timestamp    | OTDR test date            |
| `circuitpowermeteratten1310` | double       | Power meter @ 1310nm      |
| `circuitpowermeteratten1550` | double       | Power meter @ 1550nm      |
| `emergencycontactname`       | string       | Emergency contact         |

### `f_circuitcomponent` — Ordered circuit path components

| Field              | Type         | Description                                                                         |
| ------------------ | ------------ | ----------------------------------------------------------------------------------- |
| `id`               | integer (PK) | Primary key                                                                         |
| `globalid`         | string       | ESRI GlobalID                                                                       |
| `circuitguid`      | string (FK)  | → `f_circuit.globalid`                                                              |
| `elementguid`      | string (FK)  | → specific port/fiber/connection GlobalID                                           |
| `elementmodelname` | string       | Element class (e.g., `"FIBERSTRAND"`, `"CONNECTIONOBJECT"`, `"FIBERBACKSIDEPORTS"`) |
| `featureguid`      | string (FK)  | → physical feature hosting the element                                              |
| `featuremodelname` | string       | Feature class (e.g., `"RFNODE"`, `"SPLICEPOINT"`, `"SHEATH"`)                       |
| `graphid`          | integer      | Sequence position in circuit trace                                                  |

### Circuit Trace Example

```
Circuit: "HE-to-Node-42"
  graphid=1: elementmodelname=DEVICEPORT, featuremodelname=FIBERPATCHLOCATION
  graphid=2: elementmodelname=BACKSIDEPORT, featuremodelname=FIBERPATCHLOCATION
  graphid=3: elementmodelname=FIBERSTRAND, featuremodelname=SHEATH
  graphid=4: elementmodelname=CONNECTIONOBJECT, featuremodelname=SPLICEPOINT
  graphid=5: elementmodelname=FIBERSTRAND, featuremodelname=SHEATH
  graphid=6: elementmodelname=CONNECTIONOBJECT, featuremodelname=SPLICEPOINT
  graphid=7: elementmodelname=SPLITTERINPUTPORT, featuremodelname=SPLICEPOINT
  ...
  graphid=N: elementmodelname=FIBERBACKSIDEPORTS, featuremodelname=RFNODE
```

---

## 6. Network Topology

Two ESRI geometric networks exist, stored as binary blob pages:

| Network | Domain             | Tables  |
| ------- | ------------------ | ------- |
| **N_1** | Fiber / Structures | `n_1_*` |
| **N_2** | RF / Coax          | `n_2_*` |

### Tables per Network

| Table Suffix | Description                  | Fields                                                     |
| ------------ | ---------------------------- | ---------------------------------------------------------- |
| `_desc`      | Element-to-feature mapping   | `userclassid`, `userid`, `usersubid`, `elementtype`, `eid` |
| `_e_desc`    | Edge descriptor blobs        | `pagenumber`, `pageblob`                                   |
| `_e_topo`    | Edge topology blobs          | `pagenumber`, `pageblob`                                   |
| `_e_status`  | Edge enabled/disabled status | `pagenumber`, `pageblob`                                   |
| `_j_desc`    | Junction descriptor blobs    | `pagenumber`, `pageblob`                                   |
| `_j_topo`    | Junction topology blobs      | `pagenumber`, `pageblob`                                   |
| `_j_topo2`   | Extended junction topology   | `pagenumber`, `pageblob`                                   |
| `_j_status`  | Junction enabled/disabled    | `pagenumber`, `pageblob`                                   |
| `_flo_dir`   | Flow direction blobs         | `pagenumber`, `pageblob`                                   |
| `_props`     | Network properties           | `propertyname`, `propertyvalue`                            |

### `n_X_desc` — The Key Mapping Table

| Field         | Type    | Description                                       |
| ------------- | ------- | ------------------------------------------------- |
| `id`          | integer | Row ID                                            |
| `userclassid` | integer | ESRI ObjectClassID → identifies the feature class |
| `userid`      | integer | Feature OID within that class                     |
| `usersubid`   | integer | Sub-element (e.g., which edge segment)            |
| `elementtype` | integer | 1 = Junction, 2 = Edge                            |
| `eid`         | integer | Internal element ID used in topo blobs            |

> **Note:** The binary blob topology tables are ESRI's internal geometric network format. For practical migration, the **relationship fields on feature tables** (`fiberparent`, `fedfromcomponentid`, `connecteditemid`, etc.) provide equivalent connectivity information in a more accessible form.

---

## 7. MDU (Multi-Dwelling Unit)

Design layers for multi-dwelling unit premises wiring.

| Layer                 | Geometry   | Description                    |
| --------------------- | ---------- | ------------------------------ |
| `mdu_boundary`        | Polygon    | MDU property boundary          |
| `mdu_path_element`    | Linestring | Cable/conduit paths within MDU |
| `mdu_polygon_element` | Polygon    | Building footprints / areas    |
| `mdu_text_element`    | Point      | Text labels / annotations      |

### `mdu_boundary`

| Field       | Type         | Description   |
| ----------- | ------------ | ------------- |
| `id`        | integer (PK) | Primary key   |
| `globalid`  | string       | ESRI GlobalID |
| `networkid` | string       | Network ID    |
| `name`      | string       | MDU name      |
| `market`    | string       | Market/region |

### `mdu_path_element` / `mdu_polygon_element` / `mdu_text_element`

| Field           | Type        | Description               |
| --------------- | ----------- | ------------------------- |
| `mduboundaryid` | string (FK) | → `mdu_boundary.globalid` |
| `style`         | string      | Display style             |

---

## 8. Reference / Other

| Layer                           | Geometry | Description                                |
| ------------------------------- | -------- | ------------------------------------------ |
| `address_point`                 | Point    | Customer service addresses                 |
| `parcel`                        | Polygon  | Property parcels                           |
| `structures_net_junctions`      | Point    | Geometric network orphan junctions         |
| `splice_point__attach`          | None     | Attachments (photos/docs) to splice points |
| `patch_location__attach`        | None     | Attachments to patch locations             |
| `underground_structure__attach` | None     | Attachments to UG structures               |

### `address_point`

| Field                | Type         | Description                        |
| -------------------- | ------------ | ---------------------------------- |
| `id`                 | integer (PK) | Primary key                        |
| `globalid`           | string       | ESRI GlobalID                      |
| `networkid`          | string       | Network ID                         |
| `ugstructureid`      | string (FK)  | → `underground_structure.globalid` |
| `aerialstructureid`  | string (FK)  | → `support_structure.globalid`     |
| `tapid`              | string (FK)  | → `rf_tap.globalid` or networkid   |
| `commercialmducount` | integer      | Commercial/MDU unit count          |
| Address fields       | string       | Street, city, state, zip, etc.     |

### `parcel`

| Field                        | Type         | Description   |
| ---------------------------- | ------------ | ------------- |
| `id`                         | integer (PK) | Primary key   |
| `globalid`                   | string       | ESRI GlobalID |
| `name`                       | string       | Parcel name   |
| `parcel_num`                 | string       | Parcel number |
| `address` / `town` / `state` | string       | Location      |

### `coaxial_cable` — Physical coax cable (the sheath-level object)

| Field                     | Type         | Description                            |
| ------------------------- | ------------ | -------------------------------------- |
| `id`                      | integer (PK) | Primary key                            |
| `globalid`                | string       | ESRI GlobalID                          |
| `fiberparent`             | string       | Parent reference (fiber model pattern) |
| `thisfiberclassmodelname` | string       | Class model name                       |
| `cablename`               | string       | Cable name                             |
| `cabletype`               | string       | Cable type                             |
| `cablelength`             | double       | Length                                 |
| `aerialunderground`       | string       | Placement                              |
| `cableowner`              | string       | Owner                                  |
| `segmentid`               | string       | Segment reference                      |
| `cablediameter`           | string       | Diameter                               |
| `market`                  | string       | Market                                 |
| `fibercircuitglobalid`    | string (FK)  | → `f_circuit.globalid`                 |

---

## 9. Key Relationship Patterns

### Pattern 1: Fiber Containment (FIBERPARENT hierarchy)

```
┌─────────────────────┐     fiberparent      ┌──────────────────┐
│ f_fiber             │ ──────────────────── → │ f_buffer_tube    │
│ THISFIBERCLASSMODEL │                        │ THISFIBERCLASS   │
│ = "FIBERSTRAND"     │                        │ = "BUFFERTUBE"   │
└─────────────────────┘                        └────────┬─────────┘
                                                        │ fiberparent
                                                        ▼
                                               ┌──────────────────┐
                                               │ fiber_optic_cable│
                                               │ THISFIBERCLASS   │
                                               │ = "SHEATH"       │
                                               └──────────────────┘
```

### Pattern 2: Fiber Connectivity (Connection Objects)

```
┌─────────────┐  aconnectionobjectglobalid  ┌───────────────────────────┐
│ f_fiber (A) │ ◄───────────────────────────│ f_fiber_connection_object │
└─────────────┘                              │                           │
┌─────────────┐  bconnectionobjectglobalid  │ containerglobalid ──────────→ splice_point
│ f_fiber (B) │ ◄───────────────────────────│                           │
└─────────────┘                              └───────────────────────────┘
```

### Pattern 3: RF Signal Chain (FEDFROMCOMPONENTID)

```
┌───────────┐  networkid    fedfromcomponentid  ┌─────────────┐
│ rf_node_a │ ─────────────────────────────────→│ rf_cable_a  │
└───────────┘                                    └──────┬──────┘
                                                        │ fedfromcomponentid
                                                        ▼
                                                 ┌─────────────────┐
                                                 │ rf_amplifier_a  │
                                                 └────────┬────────┘
                                                          │ fedfromcomponentid
                                                          ▼
                                                 ┌─────────────────┐
                                                 │ rf_cable_a      │
                                                 └────────┬────────┘
                                                          │
                                                          ▼ ...
```

### Pattern 4: Structure Attachment (Physical Location)

```
┌──────────────────┐   aerialstructureid    ┌───────────────────┐
│ rf_node_a        │ ──────────────────────→│ support_structure  │
│ rf_amplifier_a   │                         └───────────────────┘
│ rf_tap_a         │   ugstructureid        ┌───────────────────────┐
│ splice_point     │ ──────────────────────→│ underground_structure │
│ patch_location   │                         └───────────────────────┘
└──────────────────┘
```

### Pattern 5: Cable-to-Span Routing (Many-to-Many)

```
┌────────────┐                    ┌─────────────────────────────┐                ┌────────────────┐
│ rf_cable_a │◄── rfcablenetworkid│ rf_cable_a_overhead_span    │overheadspan ──→│ overhead_span  │
└────────────┘                    └─────────────────────────────┘                └────────────────┘

┌────────────┐                    ┌─────────────────────────────┐                ┌──────────────────┐
│ rf_cable_a │◄── rfcablenetworkid│ rf_cable_a_underground_span │ugspan ────────→│ underground_span │
└────────────┘                    └─────────────────────────────┘                └──────────────────┘

┌────────────┐                    ┌─────────────────────────────┐                ┌──────┐
│ rf_cable_a │◄── rfcableid       │ rf_cable_a_duct             │ductid ────────→│ duct │
└────────────┘                    └─────────────────────────────┘                └──────┘
```

### Pattern 6: Port Connectivity (RF)

```
┌───────────────────────┐   nodeid = rf_node_a.networkid
│ rf_node_coax_port_a   │──────────────────────────────────→ rf_node_a
│                       │   connecteditemid = rf_cable_a.networkid
│                       │──────────────────────────────────→ rf_cable_a
└───────────────────────┘
```

### Pattern 7: Circuit Tracing

```
┌────────────┐   circuitguid    ┌─────────────────────┐
│ f_circuit  │◄────────────────│ f_circuitcomponent   │
└────────────┘                  │                     │
                                │ elementguid ────────→ port/fiber/connection
                                │ featureguid ────────→ physical feature
                                │ graphid = sequence  │
                                └─────────────────────┘
```

### Pattern 8: Address-to-Tap (Customer Assignment)

```
┌───────────────┐   tapid      ┌────────────┐
│ address_point │─────────────→│ rf_tap_a   │
└───────────────┘              └────────────┘
```

---

## 10. Enumeration Values

### `poletype` (support_structure.poletype)

Numeric codes: -71, -74, -75, -76, -77, -84, -88, 1–22, 99, 121

### `spantype` (underground_span.type)

-   Conduit
-   Conduit Aerial
-   Conduit Tunnel
-   Microtrench
-   Trench

### `structuretype` (underground_structure.structuretype)

-   Amp Ped / AmpPed / AmpPedestal
-   Apt Box
-   Conduit Point
-   Customer Premise
-   Demarcation
-   Flower Pot
-   Handhole
-   LE Ped
-   Large Vault / Large vault
-   Man Hole / Manhole / Manhole Full
-   Node Cabinet
-   Node Cabinet Power Supply
-   Other
-   PON Cabinet
-   PedNul / Pedestal
-   Power Supply
-   Short LE Ped
-   Small Vault
-   Span Mounted
-   Tap Ped
-   UG Lockbox
-   Underground RF Splice
-   Vault

---

## Complete Layer Inventory

| #   | Layer Name                                     | Category       | Geometry   | Record Type                |
| --- | ---------------------------------------------- | -------------- | ---------- | -------------------------- |
| 1   | `address_point`                                | Reference      | Point      | Customer addresses         |
| 2   | `coaxial_cable`                                | Fiber/Coax     | Linestring | Coax cable sheath          |
| 3   | `cx_coaxpower`                                 | Signal Model   | None       | Power signal               |
| 4   | `cx_powerbacksideports`                        | Signal Model   | None       | Power backside port        |
| 5   | `cx_powerfrontsideport`                        | Signal Model   | None       | Power frontside port       |
| 6   | `cx_powerinputport`                            | Signal Model   | None       | Power input port           |
| 7   | `cx_poweroutputport`                           | Signal Model   | None       | Power output port          |
| 8   | `cx_rfbacksideports`                           | Signal Model   | None       | RF backside port           |
| 9   | `cx_rffrontsideport`                           | Signal Model   | None       | RF frontside port          |
| 10  | `cx_rfinputport`                               | Signal Model   | None       | RF input port              |
| 11  | `cx_rfoutputport`                              | Signal Model   | None       | RF output port             |
| 12  | `cx_rfsignal`                                  | Signal Model   | None       | RF signal object           |
| 13  | `device_point`                                 | Fiber          | Point      | Generic device             |
| 14  | `down_guy`                                     | Infrastructure | Point      | Guy wire anchor            |
| 15  | `duct`                                         | Infrastructure | None       | Innerduct                  |
| 16  | `f_backside_port`                              | Fiber Ports    | None       | Patch panel backside       |
| 17  | `f_buffer_tube`                                | Fiber          | None       | Buffer tube                |
| 18  | `f_circuit`                                    | Circuits       | None       | Fiber circuit              |
| 19  | `f_circuitcomponent`                           | Circuits       | None       | Circuit path member        |
| 20  | `f_combiner`                                   | Fiber          | None       | WDM combiner               |
| 21  | `f_combiner_input_port`                        | Fiber Ports    | None       | Combiner input             |
| 22  | `f_combiner_output_port`                       | Fiber Ports    | None       | Combiner output            |
| 23  | `f_device`                                     | Fiber          | None       | Active device              |
| 24  | `f_device_port`                                | Fiber Ports    | None       | Device port                |
| 25  | `f_fiber`                                      | Fiber          | None       | Fiber strand               |
| 26  | `f_fiber_connection_object`                    | Fiber          | None       | Splice/connector           |
| 27  | `f_fiberbacksideports`                         | Fiber Ports    | None       | Node fiber backside        |
| 28  | `f_fiberfrontsideport`                         | Fiber Ports    | None       | Node fiber frontside       |
| 29  | `f_frontside_port`                             | Fiber Ports    | None       | Patch panel frontside      |
| 30  | `f_passivecommonport`                          | Fiber Ports    | None       | Passive common port        |
| 31  | `f_passivedevice`                              | Fiber          | None       | Passive WDM device         |
| 32  | `f_passivesplitport`                           | Fiber Ports    | None       | Passive split port         |
| 33  | `f_patch_panel`                                | Fiber          | None       | Patch panel                |
| 34  | `f_patch_panel_card`                           | Fiber          | None       | Panel card/shelf           |
| 35  | `f_pl_node_input_port`                         | Fiber Ports    | None       | PL node input              |
| 36  | `f_pl_node_output_port`                        | Fiber Ports    | None       | PL node output             |
| 37  | `f_plnode`                                     | Fiber          | None       | Patch location node        |
| 38  | `f_rack`                                       | Fiber          | None       | Equipment rack             |
| 39  | `f_splitter`                                   | Fiber          | None       | Optical splitter           |
| 40  | `f_splitter_input_port`                        | Fiber Ports    | None       | Splitter input             |
| 41  | `f_splitter_output_port`                       | Fiber Ports    | None       | Splitter output            |
| 42  | `f_splitterpanel`                              | Fiber          | None       | Splitter panel             |
| 43  | `f_splitterpanelcard`                          | Fiber          | None       | Splitter panel card        |
| 44  | `fiber_dataset_net_junctions`                  | Topology       | Point      | Network junction           |
| 45  | `fiber_optic_cable`                            | Fiber          | Linestring | Fiber cable                |
| 46  | `fiber_slack_loop`                             | Fiber          | Point      | Slack storage              |
| 47  | `mdu_boundary`                                 | MDU            | Polygon    | MDU boundary               |
| 48  | `mdu_path_element`                             | MDU            | Linestring | MDU path                   |
| 49  | `mdu_polygon_element`                          | MDU            | Polygon    | MDU polygon                |
| 50  | `mdu_text_element`                             | MDU            | Point      | MDU annotation             |
| 51  | `n_1_desc`                                     | Topology       | None       | Fiber network element map  |
| 52  | `n_1_e_desc`                                   | Topology       | None       | Fiber edge descriptors     |
| 53  | `n_1_e_status`                                 | Topology       | None       | Fiber edge status          |
| 54  | `n_1_e_topo`                                   | Topology       | None       | Fiber edge topology        |
| 55  | `n_1_flo_dir`                                  | Topology       | None       | Fiber flow direction       |
| 56  | `n_1_j_desc`                                   | Topology       | None       | Fiber junction descriptors |
| 57  | `n_1_j_status`                                 | Topology       | None       | Fiber junction status      |
| 58  | `n_1_j_topo`                                   | Topology       | None       | Fiber junction topology    |
| 59  | `n_1_j_topo2`                                  | Topology       | None       | Fiber junction topo ext    |
| 60  | `n_1_props`                                    | Topology       | None       | Fiber network properties   |
| 61  | `n_2_desc`                                     | Topology       | None       | RF network element map     |
| 62  | `n_2_e_desc`                                   | Topology       | None       | RF edge descriptors        |
| 63  | `n_2_e_status`                                 | Topology       | None       | RF edge status             |
| 64  | `n_2_e_topo`                                   | Topology       | None       | RF edge topology           |
| 65  | `n_2_flo_dir`                                  | Topology       | None       | RF flow direction          |
| 66  | `n_2_j_desc`                                   | Topology       | None       | RF junction descriptors    |
| 67  | `n_2_j_status`                                 | Topology       | None       | RF junction status         |
| 68  | `n_2_j_topo`                                   | Topology       | None       | RF junction topology       |
| 69  | `n_2_j_topo2`                                  | Topology       | None       | RF junction topo ext       |
| 70  | `n_2_props`                                    | Topology       | None       | RF network properties      |
| 71  | `overhead_span`                                | Infrastructure | Linestring | Aerial span                |
| 72  | `parcel`                                       | Reference      | Polygon    | Property parcel            |
| 73  | `patch_location`                               | Fiber          | Point      | Hub/headend building       |
| 74  | `patch_location__attach`                       | Fiber          | None       | Attachments                |
| 75  | `rf_amplifier`                                 | RF (geometry)  | Point      | Amp geometry               |
| 76  | `rf_amplifier_a`                               | RF Analog      | Point      | Amp (analog)               |
| 77  | `rf_amplifier_d`                               | RF Digital     | Point      | Amp (digital)              |
| 78  | `rf_amplifier_port_a`                          | RF Analog      | None       | Amp port (analog)          |
| 79  | `rf_amplifier_port_d`                          | RF Digital     | None       | Amp port (digital)         |
| 80  | `rf_cable_a`                                   | RF Analog      | Linestring | Cable (analog)             |
| 81  | `rf_cable_a_duct`                              | RF Junction    | None       | Cable-duct link            |
| 82  | `rf_cable_a_overhead_span`                     | RF Junction    | None       | Cable-aerial link          |
| 83  | `rf_cable_a_underground_span`                  | RF Junction    | None       | Cable-UG link              |
| 84  | `rf_cable_d`                                   | RF Digital     | Linestring | Cable (digital)            |
| 85  | `rf_cable_d_duct`                              | RF Junction    | None       | Cable-duct link            |
| 86  | `rf_cable_d_overhead_span`                     | RF Junction    | None       | Cable-aerial link          |
| 87  | `rf_cable_d_underground_span`                  | RF Junction    | None       | Cable-UG link              |
| 88  | `rf_coupler_a`                                 | RF Analog      | Point      | Coupler (analog)           |
| 89  | `rf_coupler_d`                                 | RF Digital     | Point      | Coupler (digital)          |
| 90  | `rf_coupler_port_a`                            | RF Analog      | None       | Coupler port (analog)      |
| 91  | `rf_coupler_port_d`                            | RF Digital     | None       | Coupler port (digital)     |
| 92  | `rf_do_not_build_boundary_a`                   | RF Analog      | Polygon    | DNB zone (analog)          |
| 93  | `rf_do_not_build_boundary_d`                   | RF Digital     | Polygon    | DNB zone (digital)         |
| 94  | `rf_drop`                                      | RF             | Linestring | Customer drop              |
| 95  | `rf_drop_arrow`                                | RF             | Point      | Drop annotation            |
| 96  | `rf_equalizer_a`                               | RF Analog      | Point      | Equalizer (analog)         |
| 97  | `rf_equalizer_d`                               | RF Digital     | Point      | Equalizer (digital)        |
| 98  | `rf_hot_dot_a`                                 | RF Analog      | Point      | Test point (analog)        |
| 99  | `rf_hot_dot_d`                                 | RF Digital     | Point      | Test point (digital)       |
| 100 | `rf_housing_to_housing_a`                      | RF Analog      | None       | Housing link (analog)      |
| 101 | `rf_housing_to_housing_d`                      | RF Digital     | None       | Housing link (digital)     |
| 102 | `rf_in_line_equalizer`                         | RF (geometry)  | Point      | Inline EQ geometry         |
| 103 | `rf_inline_eq_a`                               | RF Analog      | Point      | Inline EQ (analog)         |
| 104 | `rf_inline_eq_d`                               | RF Digital     | Point      | Inline EQ (digital)        |
| 105 | `rf_node`                                      | RF (geometry)  | Point      | Node geometry              |
| 106 | `rf_node_a`                                    | RF Analog      | Point      | Node (analog)              |
| 107 | `rf_node_boundary_a`                           | RF Analog      | Polygon    | Node boundary (analog)     |
| 108 | `rf_node_boundary_d`                           | RF Digital     | Polygon    | Node boundary (digital)    |
| 109 | `rf_node_coax_port_a`                          | RF Analog      | None       | Node port (analog)         |
| 110 | `rf_node_coax_port_d`                          | RF Digital     | None       | Node port (digital)        |
| 111 | `rf_node_d`                                    | RF Digital     | Point      | Node (digital)             |
| 112 | `rf_node_dhfc_a`                               | RF Analog      | Point      | DHFC node                  |
| 113 | `rf_pad_a`                                     | RF Analog      | Point      | Pad (analog)               |
| 114 | `rf_pad_d`                                     | RF Digital     | Point      | Pad (digital)              |
| 115 | `rf_power_block_a`                             | RF Analog      | Point      | Power block (analog)       |
| 116 | `rf_power_block_d`                             | RF Digital     | Point      | Power block (digital)      |
| 117 | `rf_power_inserter`                            | RF (geometry)  | Point      | PI geometry                |
| 118 | `rf_power_inserter_a`                          | RF Analog      | Point      | PI (analog)                |
| 119 | `rf_power_inserter_d`                          | RF Digital     | Point      | PI (digital)               |
| 120 | `rf_power_inserter_port_a`                     | RF Analog      | None       | PI port (analog)           |
| 121 | `rf_power_inserter_port_d`                     | RF Digital     | None       | PI port (digital)          |
| 122 | `rf_power_stop`                                | RF (geometry)  | Point      | Power stop geometry        |
| 123 | `rf_power_supply`                              | RF (geometry)  | Point      | PS geometry                |
| 124 | `rf_power_supply_a`                            | RF Analog      | Point      | PS (analog)                |
| 125 | `rf_power_supply_boundary_a`                   | RF Analog      | Polygon    | PS boundary (analog)       |
| 126 | `rf_power_supply_boundary_a_rf_power_supply_a` | RF Junction    | None       | PS-boundary link (analog)  |
| 127 | `rf_power_supply_boundary_d`                   | RF Digital     | Polygon    | PS boundary (digital)      |
| 128 | `rf_power_supply_boundary_rf_power_supply_d`   | RF Junction    | None       | PS-boundary link (digital) |
| 129 | `rf_power_supply_d`                            | RF Digital     | Point      | PS (digital)               |
| 130 | `rf_signal_dot`                                | RF             | Point      | Signal annotation          |
| 131 | `rf_splice`                                    | RF (geometry)  | Point      | Splice geometry            |
| 132 | `rf_splice_a`                                  | RF Analog      | Point      | Splice (analog)            |
| 133 | `rf_splice_d`                                  | RF Digital     | Point      | Splice (digital)           |
| 134 | `rf_splitter`                                  | RF (geometry)  | Point      | Splitter geometry          |
| 135 | `rf_status_monitor_unit`                       | RF             | Point      | Status monitor             |
| 136 | `rf_tap`                                       | RF (geometry)  | Point      | Tap geometry               |
| 137 | `rf_tap_a`                                     | RF Analog      | Point      | Tap (analog)               |
| 138 | `rf_tap_d`                                     | RF Digital     | Point      | Tap (digital)              |
| 139 | `rf_terminator`                                | RF (geometry)  | Point      | Terminator geometry        |
| 140 | `rf_terminator_a`                              | RF Analog      | Point      | Terminator (analog)        |
| 141 | `rf_terminator_d`                              | RF Digital     | Point      | Terminator (digital)       |
| 142 | `splice_point`                                 | Fiber          | Point      | Splice enclosure           |
| 143 | `splice_point__attach`                         | Fiber          | None       | Attachments                |
| 144 | `structures_net_junctions`                     | Topology       | Point      | Structure net junctions    |
| 145 | `support_structure`                            | Infrastructure | Point      | Poles                      |
| 146 | `transition_point`                             | Infrastructure | Point      | A/U transition             |
| 147 | `underground_span`                             | Infrastructure | Linestring | UG span                    |
| 148 | `underground_structure`                        | Infrastructure | Point      | UG structure               |
| 149 | `underground_structure__attach`                | Infrastructure | None       | Attachments                |

**Total: 149 layers/tables**

---

## 11. Migration Mapping Guidance (Source → NMT)

This section provides the mapping agent with guidance on how each source concept translates to the IQGeo NMT target model.

### Mapping Strategy Summary

| Source Concept                     | NMT Target                                | Key Transform                                                           |
| ---------------------------------- | ----------------------------------------- | ----------------------------------------------------------------------- |
| `support_structure`                | `pole`                                    | Direct geometry copy; poletype → specification                          |
| `underground_structure`            | `manhole`                                 | Direct geometry copy; structuretype → specification                     |
| `overhead_span`                    | `oh_route`                                | MultiLineString → LineString; endpoints snapped to nearest pole         |
| `underground_span`                 | `ug_route`                                | MultiLineString → LineString; endpoints snapped to nearest manhole/pole |
| `fiber_optic_cable`                | `fiber_cable`                             | Direct; fibercount → count                                              |
| `coaxial_cable`                    | `coax_cable`                              | Direct; cablelength (ft→m)                                              |
| `fiber_optic_cable × routes`       | `mywcom_fiber_segment`                    | Derived: cable split at structures along route                          |
| `coaxial_cable × routes`           | `mywcom_coax_segment`                     | Derived: cable split at structures along route                          |
| `f_fiber_connection_object`        | `mywcom_fiber_connection`                 | Strand-level splices grouped into pin ranges                            |
| `splice_point`                     | `splice_closure`                          | Direct geometry; housed in nearest structure                            |
| `rf_tap`                           | `coax_tap`                                | Geometry from parent; attributes from `rf_tap_a`                        |
| `rf_amplifier`                     | `coax_amplifier`                          | Geometry from parent; attributes from `rf_amplifier_a`                  |
| `rf_node`                          | `optical_node`                            | Geometry from parent; attributes from `rf_node_a`                       |
| `rf_splitter`                      | `two_way_splitter` / `three_way_splitter` | Split by splittertype                                                   |
| `rf_terminator`                    | `coax_terminator`                         | Direct                                                                  |
| `rf_in_line_equalizer`             | `inline_equalizer`                        | Direct                                                                  |
| `rf_power_supply`                  | `power_supply`                            | Direct                                                                  |
| `rf_power_inserter`                | `power_inserter`                          | Direct                                                                  |
| `rf_coupler_a`                     | `directional_coupler`                     | Analog only                                                             |
| `rf_power_block_a`                 | `power_block`                             | Analog only                                                             |
| `rf_splice`                        | `splice_closure`                          | ID offset by 10M to avoid collision with splice_point                   |
| `rf_node_boundary_a`               | `node_boundary`                           | Analog only                                                             |
| `rf_power_supply_boundary_a`       | `power_supply_boundary`                   | Analog only                                                             |
| `address_point`                    | `mywcom_address` + `mywcom_sub_address`   | Split: base address + sub-units                                         |
| `rf_drop`                          | _(unmapped)_                              | Could map to `coax_drop_segment`                                        |
| `patch_location`                   | _(unmapped)_                              | Could map to `building` or `cabinet` (requires ISP module)              |
| `device_point`                     | _(unmapped)_                              | Could map to `fiber_ont`                                                |
| `f_splitter`                       | _(unmapped)_                              | Could map to `fiber_splitter`                                           |
| `duct`                             | _(unmapped)_                              | Could map to `mywcom_conduit`                                           |
| `f_circuit` / `f_circuitcomponent` | _(unmapped)_                              | Could map to `logical_circuit` / `circuit_path`                         |

### RF Equipment: Geometry Parent vs. Attribute Detail Tables

For RF equipment, there are two related tables:

-   **Geometry parent** (e.g., `rf_tap`) — has the map geometry (Point) and basic fields
-   **Attribute detail** (e.g., `rf_tap_a`) — has detailed operational attributes (no independent geometry)

**Migration pattern**: Use the geometry parent table as the source for NMT spatial features. JOIN the `_a` (analog) detail table for additional attributes. The `_d` (digital) tables are generally not migrated separately — they represent the same physical device in a different signal network context.

```
SELECT p.id, p.the_geom, a.name, a.manufacturer, a.modelnumber, ...
FROM rf_tap p
LEFT JOIN rf_tap_a a ON p.globalid = a.globalid  -- or by networkid
```

### Coax-Specific Mapping Guidance

#### RF Signal Chain → NMT Connectivity

The DHFC `FEDFROMCOMPONENTID` → `NETWORKID` chain establishes the logical signal path. In NMT, this translates to:

-   **Physical connectivity** is established via `mywcom_coax_segment` (segments between structures)
-   **Signal flow** is implicit from cable/segment connectivity (NMT does not store a separate signal model)
-   The `FEDFROMCOMPONENTID` chain is useful during migration to **validate** segment connectivity and device ordering, but is not directly stored in NMT

#### Coax Port Objects → NMT (Not Directly Mapped)

The `cx_*` port tables (`cx_rfinputport`, `cx_rfoutputport`, `cx_rffrontsideport`, `cx_rfbacksideports`) contain DHFC-calculated signal levels. NMT does not have per-port signal level storage. However:

-   **Port count** → NMT device `port_count` or `tap_count` attribute (derived from `MAX(portnumber)` per device)
-   **Tap value** → Derived from port attenuation: `cx_rfoutputport.rfsignalhighattenuation` → NMT `coax_tap.tap_value`
-   **Connected item** → `cx_rfoutputport.connecteditemid` can validate which cable connects to which device port

```sql
-- Derive tap value from DHFC port attenuation
SELECT t.globalid, MAX(p.rfsignalhighattenuation) as tap_value_db
FROM rf_tap_a t
JOIN cx_rffrontsideport p ON p.fiberparent = t.globalid
GROUP BY t.globalid
```

#### RF Node → Optical Node (Bridge Device)

The `rf_node` is the fiber-coax boundary device. Migration must:

1. Map geometry from parent `rf_node` feature
2. Map coax attributes from `rf_node_a` (analog detail)
3. **Fiber side**: The node's fiber ports (`f_fiberfrontsideport`/`f_fiberbacksideports` with `fiberparent = rf_node.globalid`) establish which fiber strands connect to the node
4. **Coax side**: The node's coax ports (`rf_node_coax_port_a`) establish downstream connectivity
5. In NMT: `optical_node` links to incoming `mywcom_fiber_segment` and outgoing `mywcom_coax_segment`

#### Coax Segment Derivation (Cable → Segments)

Same strategy as fiber segments but using coax-specific sources:

```
Source: coaxial_cable (full-length sheath)
  + rf_cable_a (spans between devices, has FEDFROMCOMPONENTID)
  + Structure locations (from rf_tap/amplifier/coupler aerialstructureid/ugstructureid)
Target: mywcom_coax_segment (one per span between structures)
```

Key differences from fiber segment derivation:

-   `rf_cable_a` already represents device-to-device spans (closer to NMT segments than `fiber_optic_cable`)
-   `rf_cable_a.fedfromcomponentid` establishes ordering along the signal path
-   `rf_cable_a.cablelength` is the physical length (may be in feet — convert to meters)
-   Multiple `rf_cable_a` spans may belong to the same `coaxial_cable` sheath

#### Coax Drop Mapping

`rf_drop` represents the customer drop cable from tap to premises. Options:

| Approach       | NMT Target                        | Pros                                | Cons                             |
| -------------- | --------------------------------- | ----------------------------------- | -------------------------------- |
| Map as segment | `mywcom_coax_segment` (type=drop) | Preserves geometry and connectivity | Mixed with distribution segments |
| Map as drop    | `coax_drop_segment`               | Semantically correct                | May require ISP module           |
| Skip           | _(unmapped)_                      | Simple                              | Loses customer connectivity      |

The drop's upstream device is identified by `FEDFROMCOMPONENTID` → tap's `NETWORKID`.

#### Power Network Mapping

| Source                           | NMT Target              | Notes                                                    |
| -------------------------------- | ----------------------- | -------------------------------------------------------- |
| `rf_power_supply_a`              | `power_supply`          | Map geometry + voltage/amperage attributes               |
| `rf_power_inserter_a`            | `power_inserter`        | Map geometry; parent power supply via FEDFROMCOMPONENTID |
| `rf_power_block_a`               | `power_block`           | Map geometry; marks power zone boundary                  |
| `rf_power_supply_boundary_a`     | `power_supply_boundary` | Polygon boundary of power supply service area            |
| `cx_coaxpower` / `cx_power*port` | _(not mapped)_          | DHFC power signal model; no NMT equivalent               |

#### Analog-Only vs. Digital-Only Decision

For devices that exist in both `_a` and `_d`:

-   **Default**: Map `_a` (analog) only — this represents the primary/legacy network and typically has complete coverage
-   **Exception**: If a device exists ONLY in `_d` (no matching `_a` record), it may represent a digital-only upgrade that should still be migrated
-   **Validation**: Compare record counts between `_a` and `_d` — if `_d` has significantly more records, investigate whether digital-only devices are being missed

```sql
-- Find digital-only devices (exist in _d but not _a)
SELECT d.globalid, d.name
FROM rf_tap_d d
LEFT JOIN rf_tap_a a ON d.networkid = a.networkid
WHERE a.networkid IS NULL
```

### Segment Derivation Strategy

NMT requires explicit **segments** (cable footprint between two structures). The source system does NOT have segments — only cables with full-length geometries. Segments are **derived** by:

1. Identifying structures along a cable's route (via spatial intersection or FK references)
2. Splitting the cable geometry at each structure point
3. Creating one `mywcom_fiber_segment` (or `mywcom_coax_segment`) per span between adjacent structures
4. Chaining segments via `in_segment` / `out_segment` references
5. Setting `in_structure` / `out_structure` to the bounding structures

### Connection Resolution Strategy

Source `f_fiber_connection_object` stores individual **strand-level** splice records (one row per fiber-to-fiber connection). NMT `mywcom_fiber_connection` uses **pin ranges** (one row per group of consecutive strands spliced at the same location between the same cables).

Resolution chain:

```
f_fiber_connection_object
  → aconnectionobjectglobalid → f_fiber.globalid (strand A)
  → bconnectionobjectglobalid → f_fiber.globalid (strand B)
  → f_fiber.fiberparent → f_buffer_tube.globalid
  → f_buffer_tube.fiberparent → fiber_optic_cable.globalid
  → fiber_optic_cable → mywcom_fiber_segment (matched by cable + structure at splice point)
```

Grouping: All strand splices at the same (splice_point, cable_a, cable_b) are grouped into a single `mywcom_fiber_connection` with pin ranges (in_low/in_high, out_low/out_high).

### Tables NOT Mapped (and Why)

| Category            | Tables                                                    | Reason                                                            |
| ------------------- | --------------------------------------------------------- | ----------------------------------------------------------------- |
| ESRI Topology       | `n_1_*`, `n_2_*`                                          | Binary blobs; connectivity derived from feature FKs instead       |
| RF Digital variants | All `*_d` tables                                          | Same physical device, different signal overlay; analog sufficient |
| Signal model        | `cx_*` tables                                             | Logical signals/power objects; no NMT equivalent                  |
| Annotations         | `rf_signal_dot`, `rf_drop_arrow`, `rf_hot_dot_*`          | Visual-only; no NMT equivalent                                    |
| MDU design          | `mdu_*`                                                   | Design overlays; retained as source reference only                |
| Attachments         | `*__attach`                                               | Document/photo links; no NMT equivalent                           |
| Junction points     | `fiber_dataset_net_junctions`, `structures_net_junctions` | Auto-generated by ESRI; not real features                         |
| Internal equipment  | `f_rack`, `f_patch_panel`, `f_patch_panel_card`, ports    | Requires ISP module; out of current scope                         |

### Key Filter Pattern

Most source tables contain both "as-built" (production) and "design" (planned) records. The standard filter for production data is:

```sql
WHERE asbuild_design ILIKE 'asbuild%' OR asbuild_design IS NULL
```

### Key FK Reliability Notes

| FK Field                                             | Populated Rate | Notes                                                                     |
| ---------------------------------------------------- | -------------- | ------------------------------------------------------------------------- |
| `fiberparent` (fiber objects)                        | ~100%          | Reliable hierarchical chain                                               |
| `aerialstructureid` / `ugstructureid` (RF equipment) | ~60-70%        | Inconsistently populated; spatial proximity (ST_DWithin) used as fallback |
| `fedfromcomponentid` (RF signal chain)               | ~95%           | Reliable for tracing signal flow                                          |
| `connecteditemid` (RF ports)                         | ~90%           | Good for port-to-cable links                                              |
| `containerglobalid` (connection objects)             | ~100%          | Always points to splice_point or patch_location                           |
| `a/bconnectionobjectglobalid` (connections)          | ~100%          | Always populated for valid connections                                    |
| `tapid` (address_point)                              | ~85%           | Most addresses linked to a tap                                            |
