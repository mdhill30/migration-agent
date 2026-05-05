# {Customer} — Profiling Report

**Date**: {YYYY-MM-DD}  
**Stage**: profile  
**Source**: `{path_to_source_data}` ({N} shapefiles/tables)  
**CRS**: {CRS description} — closest EPSG: {code}

## Summary Statistics

| Layer        | Geometry                    | Count   | Key Fields                   |
| ------------ | --------------------------- | ------- | ---------------------------- |
| {LAYER_NAME} | {Point/Line String/Polygon} | {count} | {comma-separated key fields} |

**Total features**: {total}

## Coded Domain Analysis

### {LAYER} {ATTRIBUTE} ({description}, {N} distinct values)

| Value   | Count   | Interpretation         |
| ------- | ------- | ---------------------- |
| {value} | {count} | {meaning or "Unknown"} |

**Pattern**: {describe value pattern if one exists, e.g. "<fiber_count>CT <placement>"}

<!-- Repeat ### block for each significant coded domain -->

## Common Fields Across Layers

| Field        | Purpose       | Layers                                 |
| ------------ | ------------- | -------------------------------------- |
| {field_name} | {description} | {list of layers containing this field} |

## Connectivity Model

-   **{LINK_FIELD}** ({layers}): {description of what the field references}

<!-- Document all fields that establish relationships between layers -->

## Data Quality Observations

1. **{Observation title}**: {Description of finding}

<!-- Number each observation; these feed into dqr.yaml issues -->

## Recommended Exclusions

-   {LAYER_NAME} ({count} {description} — {reason for exclusion})

<!-- List layers with no migration value -->

## Open Questions for Customer

1. {Question about ambiguous data, coded values, or missing documentation}

<!-- Number each question; answers feed back into DMDD and DQR -->

---

## Template Usage Notes

-   Replace all `{placeholder}` values with job-specific data
-   Add/remove table rows and sections as needed for the source data
-   Coded Domain Analysis: include one subsection per attribute with >5 distinct coded values
-   Common Fields: document fields appearing in 3+ layers
-   Connectivity Model: document all foreign-key/link relationships between layers
-   Data Quality Observations: one numbered item per finding (cross-reference to DQR issues)
-   Recommended Exclusions: layers that are annotation-only or have no network asset value
-   Open Questions: items requiring customer clarification before mapping can proceed
