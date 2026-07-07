# Ericsson Network Engineer (ENE) → NMT Migration

Source system: Ericsson Network Engineer (ENE / PIPeR).  
Previously migrated to NMT in the Openreach PNI POC project.

## Reference Project

-   **Repository**: https://github.com/IQGeo/project-openreach-pni-poc (private)
-   **Customer**: Openreach (PNI POC)
-   **Source system**: Ericsson Network Engineer (data exported as "PIPeR" CSVs)
-   **Target**: IQGeo NMT (Comms module)
-   **Coordinate system**: EPSG:27700 (British National Grid)

## Builder Framework

The migration uses a **builder framework** module (`builder_framework/`) that provides a structured approach to organising migration code. Full documentation in [`builder_framework/doc/builder_framework.docx`](https://github.com/IQGeo/project-openreach-pni-poc/blob/main/builder_framework/doc/builder_framework.docx).

### Core Concepts

-   **Builder classes**: Each feature category gets its own builder (e.g. `StructBuilder`, `RouteBuilder`, `CableBuilder`). Each builder has methods decorated with `@build_step`.
-   **BuildConfig**: Declares builder import order (which defines step execution order), data root path, coordinate system, and table mappings.
-   **Build tool CLI**: A single command (`builder`) to run the full migration or individual steps.
-   **Steps**: Named operations (e.g. `piper.raw.structs`, `piper.nm.routes`). Steps declare dependencies via `requires=[...]`.

### Key Capabilities

| Feature                   | Description                                                    |
| ------------------------- | -------------------------------------------------------------- |
| Sequential build          | `builder build --commit` runs all steps in order               |
| Parallel build            | `builder build --workers 4` runs steps respecting dependencies |
| Selective testing         | `builder build route_connections ug_route id=17 --verbosity 6` |
| Spatial filtering         | `builder build step location=within:exch_area/1`               |
| Chunking                  | `chunk_on='id'` splits large tables across workers             |
| Performance analysis      | `builder analyse` shows waterfall diagrams                     |
| Resume interrupted builds | Tasks stored as DB records with status tracking                |

### Builder Helper Classes

-   **BulkOpsTable**: Fast SQL bulk operations (COPY, insertFrom, updateFrom, recode). Typically 10x+ faster than procedural iteration.
-   **ConstrainedNetworkEngine**: Shortest-path trace constrained to near a linear geometry (useful for cable routing).
-   **Graph**: Extract chains from unordered link sets.
-   **RecordFilter**: Flexible record filtering (by ID, subset, spatial, predicates).

### Build Step Patterns

```python
from myworldapp.modules.builder_framework.framework.builder import Builder, build_step

class StructBuilder(Builder):
    @build_step('piper.raw.structs', sub_steps='struct_file_names', requires=['piper.raw.models'])
    def loadRawStructs(self):
        for ne_table in self.filteredFeatureTypes(self.struct_file_names):
            file_path = self.dataFile('data', self.struct_file_names[ne_table])
            with self.progress.operation(ne_table, ':', 'Loading', file_path):
                n_recs, msg = self.db.data_loader.loadFile(file_path)
                self.progress(0, msg, recs=n_recs)
```

### Sectioned Build Order

Steps use dot-notation sections to enforce ordering:

1. `piper.raw.*` — Load raw NE data from CSVs
2. `piper.nm.*` — Transform NE records into NM (NMT) feature types
3. `piper.build.*` — Derive geometry, connections, references
4. `bert.*` — BERT-specific processing (optional)

## Source Data (PIPeR CSVs)

ENE exports data as large CSV files with naming like `ITT PoC_structure000000000000.csv`. Key source tables:

| NE Table               | Content                                              |
| ---------------------- | ---------------------------------------------------- |
| `ne_structure`         | All structure types (EXCH, POLE, CAB, MH, JB, etc.)  |
| `ne_span`              | Route/span geometry (overhead + underground)         |
| `ne_splice_closure`    | Splice closures (copper, fiber, mechanical, etc.)    |
| `ne_equipment`         | Equipment (MDFs, splitters, customer premises, etc.) |
| `ne_equipment_chassis` | Chassis records                                      |
| `ne_equipment_plugin`  | Plugins and splitters                                |
| `ne_transmedia`        | Cables                                               |
| `ne_connection`        | Fiber connections                                    |

## NMT Target Mapping (Openreach)

Source NE types are split into specific NMT feature types based on a discriminator field:

| NE Type Code       | NMT Feature Type          |
| ------------------ | ------------------------- |
| EXCH               | `bt_struct_exchange`      |
| POLE               | `bt_struct_pole`          |
| CAB                | `bt_struct_cabinet`       |
| MH                 | `bt_struct_manhole`       |
| JB                 | `bt_struct_junction_box`  |
| BOXC               | `bt_struct_box_connexion` |
| CCA                | `bt_struct_dist_location` |
| (overhead span)    | `oh_route`                |
| (underground span) | `ug_route`                |

## Key Project Files

```
custom/utils/
├── build_config.py          # PiperBuildConfig - main orchestration config
├── builder.py               # CLI entry point
├── piper/
│   ├── struct_builder.py    # Structure loading & transformation
│   ├── route_builder.py     # Route loading & connection
│   ├── conduit_builder.py   # Conduit processing
│   ├── cable_builder.py     # Cable loading
│   ├── segment_builder.py   # Segment generation
│   ├── equip_builder.py     # Equipment transformation
│   ├── connection_builder.py # Fiber connection building
│   ├── splice_closure_builder.py
│   ├── rme_builder.py       # RME processing
│   └── bf_tube_builder.py   # Blown fiber tubes
├── bert/
│   ├── bert_struct_builder.py
│   ├── bert_equip_builder.py
│   └── bert_connection_builder.py
└── fallout_report.py        # Post-build quality reporting

builder_framework/
├── framework/
│   ├── builder.py           # Base Builder class + @build_step decorator
│   ├── build_config.py      # BuildConfig base class
│   ├── build_command.py     # CLI command implementation
│   ├── build_manager.py     # Parallel task scheduling
│   ├── build_worker.py      # Worker process management
│   └── build_task.py        # Task record persistence
└── server/base/
    ├── bulk_ops_table.py    # BulkOpsTable (fast SQL ops)
    ├── record_filter.py     # RecordFilter (spatial/ID/subset filters)
    ├── graph.py             # Graph (chain extraction)
    └── sql_expr.py          # SQL expression building
```

## Notes

-   The builder framework is a reusable module — not specific to Openreach/ENE. It can be used for any NMT migration that needs structured, parallelisable build steps.
-   The `ensureModel()` helper installs NMT data models on demand during the build.
-   Performance: parallel builds with 4+ workers achieved ~57% CPU utilisation on the test dataset.
-   Post-build quality is assessed via a "fallout report" (`build_fallout_report.py`).
