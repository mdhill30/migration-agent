# Job Template

This folder is the template structure for an NMT migration job. Copy it to create a new job:

```bash
cp -r jobs/example jobs/<customer-slug>
```

## Directory Structure

```
jobs/<customer-slug>/
├── migration.yaml       # Job configuration (orchestrator reads this)
├── context.md           # Human-supplied customer/source knowledge
├── dmdd.yaml            # Data Migration Design Document (populated by profile + plan)
├── dqr.yaml             # Data Quality Review (populated by profile)
├── profile_report.md    # Profiling summary (populated by profile)
├── source/              # Source data files (shapefiles, CSVs, etc.)
└── output/              # Generated artefacts (.def files, scripts, value maps)
```

## Workflow

1. Place source data in `source/`
2. Fill in `migration.yaml` (job metadata, source config)
3. Write `context.md` with everything known about the customer and source system
4. Run the orchestrator — it will populate `dmdd.yaml`, `dqr.yaml`, and `profile_report.md`
5. Review at each human gate before proceeding to the next stage
