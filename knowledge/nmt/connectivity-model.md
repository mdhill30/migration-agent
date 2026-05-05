# NMT Connectivity Model

## Overview

The NMT connectivity model represents signal-level connections between equipment ports and cable strands. It operates at the **strand level** — each individual fiber, copper pair, or coax conductor is trackable.

## Core Concepts

### Pin
A connection point on the signal network — a port on equipment or a potential connection point on a strand. Pins are **not modeled explicitly** (no database record per pin). Their existence is inferred from the port/strand count attributes on the parent object.

### Side
A connection interface on an object — a set of pins. Objects typically have two sides:
- **Equipment (directed)**: IN side (upstream) and OUT side (downstream)
- **Equipment (undirected)**: Front and Back
- **Cable segment (directed)**: IN and OUT (corresponding to upstream/downstream ends)
- **Cable segment (undirected)**: A and Z

### Pin Range
A contiguous set of pins on the same side of an object. Notation: `<side>:<low>:<high>`

Examples:
- `out:1:5` — pins 1 through 5 on the OUT side
- `in:10:15` — pins 10 through 15 on the IN side
- For coax cables, pin range size is always 1

### Modeled (Explicit) Connection
An explicit connection between two pin ranges. Corresponds to a `connection` record in the database.

Example: ports `out:1:5` on a patch panel connected to strands `in:10:15` on a cable segment.

### Implicit Connection
An internal connection within a piece of equipment. Not stored as a record — inferred from the **function** configured for the equipment type.

Example: A 1:2 splitter has one input that is implicitly connected to two outputs based on its configured splitter function.

## Connection Record Structure

```
connection:
  from_object    → equipment or cable_segment
  from_side      → "in" | "out" | "a" | "z" | "front" | "back"
  from_low       → integer (first pin)
  from_high      → integer (last pin)
  to_object      → equipment or cable_segment
  to_side        → "in" | "out" | "a" | "z" | "front" | "back"
  to_low         → integer (first pin)
  to_high        → integer (last pin)
```

## Equipment Functions

Equipment types have a configured **function** that determines implicit internal connections:
- **Pass-through** (e.g., patch panel): 1:1 mapping, in port N connects to out port N
- **Splitter** (e.g., 1:8 splitter): 1 input connects to N outputs
- **Combiner/Mux**: N inputs combine to fewer outputs
- **Amplifier**: Pass-through with signal boost (1:1)

The function determines how signals traverse the equipment without explicit connection records.

## Circuit Model (Fiber)

Circuits (customer services) are modeled as qualified reference sets:
- On `fiber_segment`: field `circuits` stores URNs like `ftth_circuit/1324?fibers=1:1`
- On `equipment`: field `circuits` stores URNs like `ftth_circuit/1324?ports=in=1:1&out=1:1`

A circuit inherits its geometry from participating fiber_segment records.

## Validation Rules (Connectivity)

| Rule | Severity |
|------|----------|
| Connection pin ranges must not exceed the object's port/strand count | Blocker |
| Connection endpoints must reference existing objects | Blocker |
| Directed equipment: connections from OUT can only go to IN of next object | High |
| Pin ranges in a connection must be equal in size (from_high - from_low == to_high - to_low) | Blocker |
| No duplicate connections on the same pin range | High |
| Equipment function must be valid for the equipment type | Medium |

## Migration Implications

When migrating connectivity:
- Source systems may store connections as simple "A connects to B" without pin-level detail → need to infer pin ranges
- Source systems may not distinguish IN/OUT sides → need to determine directionality
- Strand numbering in source may differ from NMT conventions → need strand renumbering rules
- Equipment functions must be assigned based on source equipment type → map source type to NMT function
- If source has no connection data, connections may need to be derived from circuit/service records or left empty
