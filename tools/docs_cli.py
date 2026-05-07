#!/usr/bin/env python3
"""
docs_cli.py — Generate customer-facing documents from migration artefacts.

Usage:
    python tools/docs_cli.py all     --job jobs/<name>
    python tools/docs_cli.py dmdd    --job jobs/<name>
    python tools/docs_cli.py dqr     --job jobs/<name>
    python tools/docs_cli.py profile --job jobs/<name>
"""

import argparse
import os
import sys
from pathlib import Path

import yaml
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re


# =============================================================================
# Helpers
# =============================================================================

def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_migration_yaml(job_dir: Path) -> dict:
    path = job_dir / "migration.yaml"
    if path.exists():
        return load_yaml(path)
    return {}


def ensure_output_dir(job_dir: Path) -> Path:
    out = job_dir / "output"
    out.mkdir(parents=True, exist_ok=True)
    return out


# =============================================================================
# DMDD → Excel
# =============================================================================

# Style constants matching DMDD_HH_v1.1.xlsx template exactly
DATA_FONT = Font(name="Calibri", size=11)
DATA_FONT_BLACK = Font(name="Calibri", size=11, color="FF000000")
SECTION_HEADER_FONT = Font(name="Calibri", size=14, bold=True, color="FFFFFFFF")
COL_HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFFFF")

# Row 1 section header fill: dark grey (theme 1 tint 0.35 ≈ #595959)
SECTION_FILL = PatternFill(start_color="FF595959", end_color="FF595959", fill_type="solid")
# Row 2 column header fills per section
TRACKING_HDR_FILL = PatternFill(start_color="FF808080", end_color="FF808080", fill_type="solid")  # theme 1 tint 0.5
IQGEO_HDR_FILL = PatternFill(start_color="FF548235", end_color="FF548235", fill_type="solid")    # theme 9 tint -0.25 (dark green)
SOURCE_HDR_FILL = PatternFill(start_color="FF4472C4", end_color="FF4472C4", fill_type="solid")   # theme 4 (blue)

# Data row fills per section
TRACKING_DATA_FILL = PatternFill(start_color="FFF2F2F2", end_color="FFF2F2F2", fill_type="solid")  # theme 0 tint -0.05 (light grey)
IQGEO_DATA_FILL = PatternFill(start_color="FFE2EFDA", end_color="FFE2EFDA", fill_type="solid")     # theme 9 tint 0.8 (light green)
SOURCE_DATA_FILL = PatternFill(start_color="FFD9E2F3", end_color="FFD9E2F3", fill_type="solid")    # theme 4 tint 0.8 (light blue)
TRANSFORM_DATA_FILL = PatternFill(start_color="FFFCE4D6", end_color="FFFCE4D6", fill_type="solid") # theme 5 tint 0.8 (light orange)

# Borders: thin top and bottom only (like the template)
ROW_BORDER = Border(
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)

# AttrVal sheet fills
ATTRVAL_HEADER_FILL = PatternFill(start_color="FFA5A5A5", end_color="FFA5A5A5", fill_type="solid")
ATTRVAL_LABEL_FILL = PatternFill(start_color="FFFFCC99", end_color="FFFFCC99", fill_type="solid")
ATTRVAL_COLHDR_FILL = PatternFill(start_color="FFF2F2F2", end_color="FFF2F2F2", fill_type="solid")
ATTRVAL_SRC_FILL = PatternFill(start_color="FFC6EFCE", end_color="FFC6EFCE", fill_type="solid")
ATTRVAL_TGT_FILL = PatternFill(start_color="FFD9E2F3", end_color="FFD9E2F3", fill_type="solid")


def _set_col_widths(ws, widths: dict):
    for col_letter, width in widths.items():
        ws.column_dimensions[col_letter].width = width


def _apply_mapping_section_header(ws, row, col, value, end_col):
    """Write a merged section header (row 1) in mapping sheets."""
    cell = ws.cell(row=row, column=col, value=value)
    cell.font = SECTION_HEADER_FONT
    cell.fill = SECTION_FILL
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = ROW_BORDER
    # Merge and fill remaining cells
    if end_col > col:
        ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=end_col)
    for c in range(col, end_col + 1):
        ws.cell(row=row, column=c).fill = SECTION_FILL
        ws.cell(row=row, column=c).border = ROW_BORDER


def _apply_col_headers(ws, row, headers, fills):
    """Write column header row (row 2) with per-section fills."""
    for i, (h, fill) in enumerate(zip(headers, fills), start=1):
        cell = ws.cell(row=row, column=i, value=h)
        cell.font = COL_HEADER_FONT
        cell.fill = fill
        cell.alignment = Alignment(horizontal="center", vertical="top", wrap_text=True)
        cell.border = ROW_BORDER


def _apply_data_row(ws, row, values, fills):
    """Write a data row with per-column section fills and borders."""
    for i, (v, fill) in enumerate(zip(values, fills), start=1):
        cell = ws.cell(row=row, column=i, value=v)
        cell.font = DATA_FONT_BLACK
        cell.fill = fill
        cell.border = ROW_BORDER
        cell.alignment = Alignment(vertical="top", wrap_text=True)


def generate_dmdd_excel(job_dir: Path):
    """Generate DMDD Excel from dmdd.yaml matching DMDD_HH_v1.1.xlsx template."""
    dmdd_path = job_dir / "dmdd.yaml"
    if not dmdd_path.exists():
        print(f"ERROR: {dmdd_path} not found")
        return None

    dmdd = load_yaml(dmdd_path)
    migration = load_migration_yaml(job_dir)
    summary = dmdd.get("summary", {})

    wb = Workbook()

    # =========================================================================
    # Summary sheet — plain text, no borders, matches template layout
    # =========================================================================
    ws = wb.active
    ws.title = "Summary"
    _set_col_widths(ws, {"A": 13, "B": 60})

    # Row 2: Vendor, Row 3: Author, Row 4: Date (values in col B)
    ws.cell(row=2, column=2, value=summary.get("vendor", "")).font = DATA_FONT
    ws.cell(row=3, column=2, value=summary.get("customer", "")).font = DATA_FONT
    ws.cell(row=4, column=2, value=summary.get("date", "")).font = DATA_FONT

    # Row 6: Instructions title (bold)
    ws.cell(row=6, column=2, value="Summary and use instructions for this workbook").font = Font(name="Calibri", size=11, bold=True)

    # Instructions text
    row = 7
    for instr in summary.get("instructions", []):
        ws.cell(row=row, column=2, value=instr).font = DATA_FONT
        row += 1

    # Sheet descriptions
    row += 1
    ws.cell(row=row, column=2, value="Below is an explanation of each sheet:").font = DATA_FONT
    row += 1
    ws.cell(row=row, column=2, value="Object Mapping Sheet").font = Font(name="Calibri", size=11, bold=True)
    row += 1
    ws.cell(row=row, column=2, value="The Object level (feature/table level) mapping is in the ObjectMapping sheet.").font = DATA_FONT
    row += 1
    ws.cell(row=row, column=2, value="Attribute Mapping Sheet").font = Font(name="Calibri", size=11, bold=True)
    row += 1
    ws.cell(row=row, column=2, value="The Attribute level (field/column level) mapping is in the AttributeMapping sheet.").font = DATA_FONT
    row += 1
    ws.cell(row=row, column=2, value="Value Mapping Sheets").font = Font(name="Calibri", size=11, bold=True)
    row += 1
    ws.cell(row=row, column=2, value="The Value level (domain/pick-list) mappings are in the AttrVal- sheets.").font = DATA_FONT

    # Status values section
    row += 3
    ws.cell(row=row, column=2, value="Status Values").font = Font(name="Calibri", size=11, bold=True)
    row += 1
    for sv in summary.get("status_values", []):
        ws.cell(row=row, column=2, value=sv).font = DATA_FONT
        row += 1

    # =========================================================================
    # ObjectInventory — plain header row, no fill, no borders (like template)
    # =========================================================================
    ws = wb.create_sheet("ObjectInventory")
    headers = ["Feature", "Count", "Include in Mapping?"]
    for i, h in enumerate(headers, start=1):
        ws.cell(row=1, column=i, value=h).font = DATA_FONT
    for i, obj in enumerate(dmdd.get("object_inventory", []), start=2):
        ws.cell(row=i, column=1, value=obj.get("feature", "")).font = DATA_FONT
        ws.cell(row=i, column=2, value=obj.get("count", "")).font = DATA_FONT
        ws.cell(row=i, column=3, value=obj.get("include_in_mapping", "")).font = DATA_FONT
    _set_col_widths(ws, {"A": 51, "B": 21, "C": 19})

    # =========================================================================
    # AttributeInventory — plain header, auto-filter (like template)
    # =========================================================================
    ws = wb.create_sheet("AttributeInventory")
    attr_hdrs = ["Feature", "Attribute", "Data Type", "Count NULL", "COUNT UNIQUE", "Include In Mapping?"]
    for i, h in enumerate(attr_hdrs, start=1):
        ws.cell(row=1, column=i, value=h).font = DATA_FONT

    attr_inv = dmdd.get("attribute_inventory", [])
    for i, attr in enumerate(attr_inv, start=2):
        ws.cell(row=i, column=1, value=attr.get("feature", "")).font = DATA_FONT
        ws.cell(row=i, column=2, value=attr.get("attribute", "")).font = DATA_FONT
        ws.cell(row=i, column=3, value=attr.get("data_type", "")).font = DATA_FONT
        ws.cell(row=i, column=4, value=attr.get("count_null", "")).font = DATA_FONT
        ws.cell(row=i, column=5, value=attr.get("count_unique", "")).font = DATA_FONT
        ws.cell(row=i, column=6, value=attr.get("include_in_mapping", "")).font = DATA_FONT

    # Auto-filter on header row
    last_row = max(2, len(attr_inv) + 1)
    ws.auto_filter.ref = f"A1:F{last_row}"
    _set_col_widths(ws, {"A": 21, "B": 13, "C": 13, "D": 11, "E": 15, "F": 19})

    # =========================================================================
    # ObjectMapping — merged section headers, coloured columns, borders
    # =========================================================================
    ws = wb.create_sheet("ObjectMapping")

    # Row 1: merged section headers
    _apply_mapping_section_header(ws, 1, 1, "Tracking", 5)       # A1:E1
    _apply_mapping_section_header(ws, 1, 6, "IQGeo Features", 15)  # F1:O1
    _apply_mapping_section_header(ws, 1, 16, "Source Mapping", 19) # P1:S1

    # Row 2: column headers with per-section fills
    obj_map_headers = [
        "Update Person", "Update Date", "Review Comments", "Status", "Jira Ticket",
        "Feature", "Display Name", "Internal Name", "Editable", "Layer",
        "Specifications", "Feature Type", "Function", "Housing", "Style",
        "System", "Table/Layer", "Transformations", "Internal Name",
    ]
    # Map each column to its section fill
    obj_hdr_fills = (
        [TRACKING_HDR_FILL] * 5 +
        [IQGEO_HDR_FILL] * 10 +
        [SOURCE_HDR_FILL] * 4
    )
    _apply_col_headers(ws, 2, obj_map_headers, obj_hdr_fills)

    # Data row fill pattern
    obj_data_fills = (
        [TRACKING_DATA_FILL] * 5 +
        [IQGEO_DATA_FILL] * 10 +
        [SOURCE_DATA_FILL] * 4
    )

    # Auto-filter on row 2
    ws.auto_filter.ref = "A2:S2"

    for i, mapping in enumerate(dmdd.get("object_mapping", []), start=3):
        tracking = mapping.get("tracking", {})
        iqgeo = mapping.get("iqgeo_features", {})
        source = mapping.get("source_mapping", {})
        values = [
            tracking.get("update_person", ""),
            tracking.get("update_date", ""),
            tracking.get("review_comments", ""),
            tracking.get("status", ""),
            tracking.get("jira_ticket", ""),
            iqgeo.get("feature", ""),
            iqgeo.get("display_name", ""),
            iqgeo.get("internal_name", ""),
            iqgeo.get("editable", ""),
            iqgeo.get("layer", ""),
            iqgeo.get("specifications", ""),
            iqgeo.get("feature_type", ""),
            iqgeo.get("function", ""),
            iqgeo.get("housing", ""),
            iqgeo.get("style", ""),
            source.get("system", ""),
            source.get("table_layer", ""),
            source.get("transformations", ""),
            source.get("internal_name", ""),
        ]
        _apply_data_row(ws, i, values, obj_data_fills)
        # Source "System" column centered
        ws.cell(row=i, column=16).alignment = Alignment(horizontal="center", vertical="top")

    _set_col_widths(ws, {
        "A": 24, "B": 22, "C": 32, "D": 33, "E": 13,
        "F": 28, "G": 28, "H": 28, "I": 13, "J": 10,
        "K": 18, "L": 19, "M": 17, "N": 13, "O": 14,
        "P": 15, "Q": 28, "R": 26, "S": 25,
    })

    # =========================================================================
    # AttributeMapping — same pattern, 4 merged sections
    # =========================================================================
    ws = wb.create_sheet("AttributeMapping")

    # Row 1: merged section headers
    _apply_mapping_section_header(ws, 1, 1, "Tracking", 4)         # A1:D1
    _apply_mapping_section_header(ws, 1, 5, "IQGeo Internal", 6)   # E1:F1
    _apply_mapping_section_header(ws, 1, 7, "IQGeo Fields", 15)    # G1:O1
    _apply_mapping_section_header(ws, 1, 16, "Source Mapping", 24) # P1:X1

    attr_map_headers = [
        "Update Person", "Update Date", "Review Comments", "Status",
        "IQGeo Version Tested", "Jira Ticket",
        "Table", "Table Type", "Display Name", "Internal Name", "Data Type",
        "Default Value", "Pick List", "Visible", "Other",
        "System", "Table/Layer", "Attribute", "Transformations",
        "Internal Name", "Data Type", "Length", "Domain", "Sample Value",
    ]
    attr_hdr_fills = (
        [TRACKING_HDR_FILL] * 4 +
        [TRACKING_HDR_FILL] * 2 +  # IQGeo Internal uses same grey
        [IQGEO_HDR_FILL] * 9 +
        [SOURCE_HDR_FILL] * 9
    )
    _apply_col_headers(ws, 2, attr_map_headers, attr_hdr_fills)

    # Data row fills
    attr_data_fills = (
        [TRACKING_DATA_FILL] * 4 +
        [TRACKING_DATA_FILL] * 2 +
        [IQGEO_DATA_FILL] * 9 +
        [SOURCE_DATA_FILL] * 9
    )

    # Auto-filter
    attr_mappings = dmdd.get("attribute_mapping", [])
    last_data_row = max(2, len(attr_mappings) + 2)
    ws.auto_filter.ref = f"A2:X{last_data_row}"

    for i, mapping in enumerate(attr_mappings, start=3):
        tracking = mapping.get("tracking", {})
        iqgeo_int = mapping.get("iqgeo_internal", {})
        iqgeo_f = mapping.get("iqgeo_fields", {})
        source = mapping.get("source_mapping", {})
        values = [
            tracking.get("update_person", ""),
            tracking.get("update_date", ""),
            tracking.get("review_comments", ""),
            tracking.get("status", ""),
            iqgeo_int.get("iqgeo_version_tested", ""),
            iqgeo_int.get("jira_ticket", ""),
            iqgeo_f.get("table", ""),
            iqgeo_f.get("table_type", ""),
            iqgeo_f.get("display_name", ""),
            iqgeo_f.get("internal_name", ""),
            iqgeo_f.get("data_type", ""),
            iqgeo_f.get("default_value", ""),
            iqgeo_f.get("pick_list", ""),
            iqgeo_f.get("visible", ""),
            iqgeo_f.get("other", ""),
            source.get("system", ""),
            source.get("table_layer", ""),
            source.get("attribute", ""),
            source.get("transformations", ""),
            source.get("internal_name", ""),
            source.get("data_type", ""),
            source.get("length", ""),
            source.get("domain", ""),
            source.get("sample_value", ""),
        ]
        _apply_data_row(ws, i, values, attr_data_fills)
        # Source "System" column centered
        ws.cell(row=i, column=16).alignment = Alignment(horizontal="center", vertical="top")

    _set_col_widths(ws, {
        "A": 24, "B": 22, "C": 32, "D": 33,
        "E": 15, "F": 18,
        "G": 28, "H": 28, "I": 28, "J": 13, "K": 10,
        "L": 18, "M": 17, "N": 17, "O": 27,
        "P": 15, "Q": 28, "R": 26, "S": 57,
        "T": 30, "U": 13, "V": 10, "W": 18, "X": 27,
    })

    # =========================================================================
    # Value mapping sheets (AttrVal-*) — green source, blue target
    # =========================================================================
    for key, val in dmdd.items():
        if key.startswith("value_mapping_"):
            domain_name = key.replace("value_mapping_", "")
            sheet_name = f"AttrVal-{domain_name}"[:31]
            ws = wb.create_sheet(sheet_name)

            # Row 3: Section labels
            bold_font = Font(name="Calibri", size=11, bold=True)
            c = ws.cell(row=3, column=2, value="Source System")
            c.font = bold_font
            c.fill = ATTRVAL_HEADER_FILL
            c = ws.cell(row=3, column=3, value=summary.get("customer", ""))
            c.font = DATA_FONT
            c.fill = ATTRVAL_LABEL_FILL
            c = ws.cell(row=3, column=5, value="Target System")
            c.font = bold_font
            c.fill = ATTRVAL_HEADER_FILL
            c = ws.cell(row=3, column=6, value="IQGeo NMT")
            c.font = DATA_FONT
            c.fill = ATTRVAL_LABEL_FILL

            # Row 5: Attribute labels
            c = ws.cell(row=5, column=2, value="Attribute")
            c.font = bold_font
            c.fill = ATTRVAL_HEADER_FILL
            c = ws.cell(row=5, column=3, value=domain_name)
            c.font = DATA_FONT
            c.fill = ATTRVAL_LABEL_FILL
            c = ws.cell(row=5, column=5, value="Attribute")
            c.font = bold_font
            c.fill = ATTRVAL_HEADER_FILL
            c = ws.cell(row=5, column=6, value=domain_name)
            c.font = DATA_FONT
            c.fill = ATTRVAL_LABEL_FILL

            # Row 6: Column headers
            for col, hdr in [(2, "Value"), (3, "Count"), (5, "Value"), (6, "Description")]:
                c = ws.cell(row=6, column=col, value=hdr)
                c.font = bold_font
                c.fill = ATTRVAL_COLHDR_FILL

            # Data rows
            if isinstance(val, list):
                for j, entry in enumerate(val, start=7):
                    c = ws.cell(row=j, column=2, value=entry.get("source_value", ""))
                    c.font = DATA_FONT
                    c.fill = ATTRVAL_SRC_FILL
                    c = ws.cell(row=j, column=3, value=entry.get("count", ""))
                    c.font = DATA_FONT
                    c.fill = ATTRVAL_SRC_FILL
                    c = ws.cell(row=j, column=5, value=entry.get("target_value", ""))
                    c.font = DATA_FONT
                    c.fill = ATTRVAL_TGT_FILL
                    c = ws.cell(row=j, column=6, value=entry.get("notes", ""))
                    c.font = DATA_FONT
                    c.fill = ATTRVAL_TGT_FILL

            _set_col_widths(ws, {"A": 13, "B": 21, "C": 18, "D": 13, "E": 18, "F": 19})

    # Save
    out_dir = ensure_output_dir(job_dir)
    out_path = out_dir / "dmdd.xlsx"
    wb.save(out_path)
    print(f"Generated: {out_path}")
    return out_path


# =============================================================================
# DQR → Word
# =============================================================================

SEVERITY_COLORS = {
    "blocker": RGBColor(0xC0, 0x00, 0x00),
    "high": RGBColor(0xE0, 0x60, 0x00),
    "medium": RGBColor(0xBF, 0x8F, 0x00),
    "low": RGBColor(0x2E, 0x74, 0xB5),
    "info": RGBColor(0x70, 0x70, 0x70),
}


def generate_dqr_word(job_dir: Path):
    """Generate DQR Word document from dqr.yaml."""
    dqr_path = job_dir / "dqr.yaml"
    if not dqr_path.exists():
        print(f"ERROR: {dqr_path} not found")
        return None

    dqr = load_yaml(dqr_path)
    migration = load_migration_yaml(job_dir)
    issues = dqr.get("issues", [])

    # Count by severity
    severity_counts = {}
    for issue in issues:
        sev = issue.get("severity", "info")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # Get metadata
    summary = dqr.get("summary", {}) or {}
    customer = summary.get("customer") or migration.get("customer", "")
    vendor = summary.get("vendor") or migration.get("vendor", "IQGeo")
    date = summary.get("date") or migration.get("date", "")

    doc = Document()

    # Default font
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    # Title page
    doc.add_paragraph()
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Data Quality Review")
    run.bold = True
    run.font.size = Pt(28)
    run.font.color.rgb = RGBColor(0x2E, 0x74, 0xB5)

    doc.add_paragraph()
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run(customer)
    run.font.size = Pt(18)
    run.font.color.rgb = RGBColor(0x59, 0x59, 0x59)

    doc.add_paragraph()
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run(f"Prepared by: {vendor}").font.size = Pt(12)
    meta2 = doc.add_paragraph()
    meta2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta2.add_run(f"Date: {date}").font.size = Pt(12)

    doc.add_page_break()

    # Executive Summary
    doc.add_heading("Executive Summary", level=1)
    total = len(issues)
    open_count = sum(1 for i in issues if i.get("status", "open") == "open")
    doc.add_paragraph(
        f"This document presents the Data Quality Review findings for the {customer} "
        f"data migration project. A total of {total} issues were identified, "
        f"of which {open_count} remain open."
    )

    # Summary table
    doc.add_heading("Issue Summary by Severity", level=2)
    table = doc.add_table(rows=1, cols=3)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    hdr[0].text = "Severity"
    hdr[1].text = "Count"
    hdr[2].text = "Open"

    for sev in ["blocker", "high", "medium", "low", "info"]:
        count = severity_counts.get(sev, 0)
        open_c = sum(1 for i in issues if i.get("severity") == sev and i.get("status", "open") == "open")
        row = table.add_row().cells
        row[0].text = sev.capitalize()
        row[1].text = str(count)
        row[2].text = str(open_c)

    # Treatment summary
    doc.add_heading("Issue Summary by Treatment", level=2)
    treatment_counts = {}
    for issue in issues:
        t = issue.get("treatment", "unknown")
        treatment_counts[t] = treatment_counts.get(t, 0) + 1

    table = doc.add_table(rows=1, cols=2)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    hdr[0].text = "Treatment"
    hdr[1].text = "Count"
    for t, c in sorted(treatment_counts.items()):
        row = table.add_row().cells
        row[0].text = t.replace("_", " ").title()
        row[1].text = str(c)

    doc.add_page_break()

    # Issues Detail
    doc.add_heading("Issues Detail", level=1)

    for issue in issues:
        issue_id = issue.get("id", "")
        check = issue.get("check", "")
        severity = issue.get("severity", "info")

        heading = doc.add_heading(f"{issue_id} — {check}", level=2)
        # Color the heading by severity
        for run in heading.runs:
            color = SEVERITY_COLORS.get(severity)
            if color:
                run.font.color.rgb = color

        # Issue details table
        table = doc.add_table(rows=0, cols=2)
        table.style = "Light Grid Accent 1"

        fields = [
            ("Category", issue.get("category", "")),
            ("Source Object", issue.get("source_object", "")),
            ("Source Attribute", issue.get("source_attribute", "")),
            ("Severity", severity.capitalize()),
            ("Affected Count", str(issue.get("affected_count", ""))),
            ("Affected %", f"{issue.get('affected_percent', '')}%"),
            ("Examples", issue.get("examples", "")),
            ("Treatment", issue.get("treatment", "").replace("_", " ").title()),
            ("Target Area", issue.get("target_area", "")),
            ("Status", issue.get("status", "")),
            ("Owner", issue.get("owner", "")),
        ]

        for label, value in fields:
            row = table.add_row().cells
            row[0].text = label
            p = row[0].paragraphs[0]
            p.runs[0].bold = True
            row[1].text = str(value) if value else ""

        # Impact
        impact = issue.get("impact_if_unresolved", "")
        if impact:
            p = doc.add_paragraph()
            p.add_run("Impact if unresolved: ").bold = True
            p.add_run(impact)

        # Resolution
        resolution = issue.get("resolution", "")
        if resolution:
            p = doc.add_paragraph()
            p.add_run("Resolution: ").bold = True
            p.add_run(resolution)

        doc.add_paragraph()  # spacer

    # Save
    out_dir = ensure_output_dir(job_dir)
    out_path = out_dir / "dqr.docx"
    doc.save(out_path)
    print(f"Generated: {out_path}")
    return out_path


# =============================================================================
# Profile Report → Word
# =============================================================================

def _parse_markdown_table(lines: list) -> list:
    """Parse markdown table lines into list of rows (each row is list of cells)."""
    rows = []
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        # Skip separator rows
        if re.match(r"^\|[\s\-:|]+\|$", line):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        rows.append(cells)
    return rows


def generate_profile_word(job_dir: Path):
    """Generate profile report Word document from profile_report.md."""
    report_path = job_dir / "profile_report.md"
    if not report_path.exists():
        print(f"ERROR: {report_path} not found")
        return None

    migration = load_migration_yaml(job_dir)
    customer = migration.get("customer", "")
    vendor = migration.get("vendor", "IQGeo")
    date = migration.get("date", "")

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    doc = Document()

    # Default font
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    # Title page
    doc.add_paragraph()
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Source Data Profile Report")
    run.bold = True
    run.font.size = Pt(28)
    run.font.color.rgb = RGBColor(0x2E, 0x74, 0xB5)

    doc.add_paragraph()
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run(customer)
    run.font.size = Pt(18)
    run.font.color.rgb = RGBColor(0x59, 0x59, 0x59)

    doc.add_paragraph()
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run(f"Prepared by: {vendor}").font.size = Pt(12)
    meta2 = doc.add_paragraph()
    meta2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta2.add_run(f"Date: {date}").font.size = Pt(12)

    doc.add_page_break()

    # Parse markdown and convert to Word
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # Headings
        if line.startswith("# "):
            # Skip the first H1 (it's the title, already on title page)
            if i == 0 or (i > 0 and not any(l.startswith("# ") for l in lines[:i])):
                i += 1
                continue
            doc.add_heading(line[2:].strip(), level=1)
            i += 1
            continue
        elif line.startswith("## "):
            doc.add_heading(line[3:].strip(), level=2)
            i += 1
            continue
        elif line.startswith("### "):
            doc.add_heading(line[4:].strip(), level=3)
            i += 1
            continue

        # Horizontal rule
        if line.strip() == "---":
            i += 1
            continue

        # Tables
        if line.strip().startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            rows = _parse_markdown_table(table_lines)
            if rows:
                table = doc.add_table(rows=len(rows), cols=len(rows[0]))
                table.style = "Light Grid Accent 1"
                for r_idx, row_data in enumerate(rows):
                    for c_idx, cell_val in enumerate(row_data):
                        if c_idx < len(table.columns):
                            table.cell(r_idx, c_idx).text = cell_val
                            if r_idx == 0:
                                p = table.cell(r_idx, c_idx).paragraphs[0]
                                if p.runs:
                                    p.runs[0].bold = True
                doc.add_paragraph()  # spacer after table
            continue

        # Code blocks
        if line.strip().startswith("```"):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            p = doc.add_paragraph()
            run = p.add_run("\n".join(code_lines))
            run.font.name = "Consolas"
            run.font.size = Pt(9)
            continue

        # Bold text, bullet points, regular paragraphs
        if line.strip().startswith("- ") or line.strip().startswith("* "):
            text = line.strip()[2:]
            p = doc.add_paragraph(style="List Bullet")
            _add_formatted_text(p, text)
            i += 1
            continue

        if line.strip():
            p = doc.add_paragraph()
            _add_formatted_text(p, line.strip())
            i += 1
            continue

        i += 1

    # Save
    out_dir = ensure_output_dir(job_dir)
    out_path = out_dir / "profile_report.docx"
    doc.save(out_path)
    print(f"Generated: {out_path}")
    return out_path


def _add_formatted_text(paragraph, text: str):
    """Add text to paragraph with basic markdown formatting (bold, italic, code)."""
    # Process **bold**, *italic*, `code` inline formatting
    pattern = r"(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`|([^*`]+))"
    for match in re.finditer(pattern, text):
        if match.group(2):  # bold
            run = paragraph.add_run(match.group(2))
            run.bold = True
        elif match.group(3):  # italic
            run = paragraph.add_run(match.group(3))
            run.italic = True
        elif match.group(4):  # code
            run = paragraph.add_run(match.group(4))
            run.font.name = "Consolas"
            run.font.size = Pt(10)
        elif match.group(5):  # plain text
            paragraph.add_run(match.group(5))


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate customer-facing documents from migration artefacts")
    parser.add_argument("command", choices=["all", "dmdd", "dqr", "profile"],
                        help="Which document(s) to generate")
    parser.add_argument("--job", required=True, help="Path to job directory")

    args = parser.parse_args()
    job_dir = Path(args.job)

    if not job_dir.exists():
        print(f"ERROR: Job directory not found: {job_dir}")
        sys.exit(1)

    if args.command in ("all", "dmdd"):
        generate_dmdd_excel(job_dir)
    if args.command in ("all", "dqr"):
        generate_dqr_word(job_dir)
    if args.command in ("all", "profile"):
        generate_profile_word(job_dir)


if __name__ == "__main__":
    main()
