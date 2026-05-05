# NMT Knowledge

Comprehensive reference documentation for the IQGeo Network Management Toolkit (NMT) platform, including data model definitions, validation rules, structural transformation patterns, and tool references.

## Documents

### [nmt-data-model.md](nmt-data-model.md)
**Core reference for all NMT object types and relationships.**

Complete guide to:
- Feature hierarchy (Structures, Routes, Equipment, Cables, Segments, Circuits, Connections)
- Attributes and Foreign Keys for each object type
- Containment rules and inheritance patterns
- Connectivity patterns (splices, patches, cross-connects, terminations)
- Topology construction algorithm
- Validation checklist

**Use this when**:
- Understanding what object types exist in NMT
- Learning object attributes and their semantics
- Designing source-to-target mappings
- Building validation checks

---

### [containment-model.md](containment-model.md)
**Detailed guide to NMT's explicit containment hierarchy.**

Covers:
- Containment hierarchy diagram and attributes (housing, rootHousing)
- Containment inference rules:
  - Distance-based spatial proximity
  - Naming conventions (hierarchical codes)
  - Topology-based derivation (from cable endpoints)
  - Synthetic generation for missing parents
- Containment validation checks
- Migration workflow for containment phase
- Complete worked examples

**Use this when**:
- Inferring parent-child relationships from source data
- Handling orphaned or unstructured source objects
- Validating containment integrity post-migration
- Understanding how to handle placement-based source models

---

### [connectivity-model.md](connectivity-model.md)
**Strand-level connection mapping and signal tracing.**

Details:
- Pin, Side, Pin Range concepts
- Connection record structure and semantics
- Four main connection patterns:
  1. Cable splices (segment-to-segment)
  2. Equipment cross-connects (patch cords)
  3. Terminations (segment-to-equipment)
  4. Fan-out/fan-in (splitters, mergers)
- Circuit tracing algorithm (end-to-end service paths)
- Connectivity inference rules and validation
- Migration workflow for connectivity phase

**Use this when**:
- Mapping source splice/patch records to NMT Connections
- Tracing service paths through the network
- Building circuit definitions
- Validating strand-level connectivity

---

### [topology-rules.md](topology-rules.md)
**Derivation rules for Routes, Segments, and cable segmentation.**

Covers:
- Route synthesis from cable endpoints and network flow
- Cable segmentation algorithm (multi-pole span → per-pole segments)
- Conduit chain construction and ConduitRun grouping
- Route geometry handling (shortest-path, actual paths, multi-path scenarios)
- Validation of topological integrity

**Use this when**:
- Creating Routes and Segments from source cable data
- Handling cables that span multiple structures
- Deriving cable paths from sparse endpoint data
- Validating continuity of cable chains

---

### [placement-to-containment.md](placement-to-containment.md)
**Transformation guide: moving from spatial placement model to explicit containment.**

Key insights:
- Differences between placement-based systems and NMT's explicit model
- Common pitfalls when migrating from proximity-based systems
- Strategies for inferring containment from placement data
- Handling ambiguous or conflicting placement signals

**Use this when**:
- Migrating from a GIS system that uses spatial proximity
- Converting implicit relationships to explicit ForeignKeys
- Dealing with edge cases (near-miss placements, overlapping buffers)

---

### [myw_db-tools.md](myw_db-tools.md)
**Reference for the myw_db command-line utility.**

Complete reference:
- All myw_db operations (create, install, upgrade, list, load, import, dump, run, validate, etc.)
- Connection parameters and security
- Output formats (JSON, CSV, XML)
- Common SQL queries for validation and analysis
- Migration workflow integration
- Troubleshooting

**Use this when**:
- Running NMT CLI commands
- Querying the NMT database
- Loading or exporting data
- Validating database integrity

---

### [nmt-model-schema.json](nmt-model-schema.json)
**Formal JSON Schema definitions for all NMT objects.**

Includes:
- Feature (base type)
- Structure, Equipment, Route, Conduit
- Cable, Segment, Circuit, Connection
- GeoJSON Point and LineString types
- Required fields and constraints

**Use this when**:
- Validating JSON/API payloads against NMT schema
- Generating code or data loaders
- Documenting expected field types
- Integrating with external systems

---

## Versioning

Documents are versioned by NMT platform release. Current target: **NMT v7.x**

Check the platform deployment version to ensure compatibility.

---

## Migration Context

These documents are designed to support the **NMT Migration Orchestrator** workflow:

1. **Profile** → Understand source data model, assess structural type
2. **Plan** → Propose object/attribute mappings using this knowledge
3. **Generate** → Apply structural and connectivity rules from these docs
4. **Validate** → Use validation rules and myw_db checks
5. **Review** → Verify against reference patterns and examples

See [AGENTS.md](../../AGENTS.md) for orchestrator workflow.

---

## Quick Reference

| Question | Document |
|----------|----------|
| What are all the NMT object types? | [nmt-data-model.md](nmt-data-model.md#core-object-types) |
| How does containment hierarchy work? | [containment-model.md](containment-model.md) |
| What is a Segment? | [nmt-data-model.md](nmt-data-model.md#cables-transmission-media) |
| How do I infer parent objects from source data? | [containment-model.md](containment-model.md#containment-inference-rules) |
| How do I build Connections from splice records? | [connectivity-model.md](connectivity-model.md#inference-1-connection-from-explicit-fk) |
| How do I validate the database? | [myw_db-tools.md](myw_db-tools.md#validation--quality) |
| How do I query the NMT database? | [myw_db-tools.md](myw_db-tools.md#common-sql-queries-with-myw_db-run) |
| How are cables segmented across structures? | [topology-rules.md](topology-rules.md) |
| Which fields are calculated vs mapped? | [nmt-data-model.md](nmt-data-model.md#calculated-fields) |

---

## External Resources

- IQGeo Platform Documentation: https://docs.iqgeo.io/
- Network Management Toolkit API: `/opt/iqgeo/platform/WebApps/myworldapp/modules/comms/api/nmt_api.json`
- TMForum Schemas: https://github.com/tmforum-rand/schemas
