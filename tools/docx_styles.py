"""
docx_styles.py — Professional enterprise-grade Word document styling for NMT migration reports.

Provides a reusable styling system with:
- Modern color palette (dark navy, steel blue, warm accents)
- Professional typography (Segoe UI / Calibri Light headings, Calibri body)
- Consistent spacing and margins
- Custom table styles with colored headers
- Headers/footers with page numbers
- Cover page layout
"""

from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
import copy


# =============================================================================
# Color Palette — Modern Enterprise
# =============================================================================

class Colors:
    """Enterprise color palette."""
    # Primary
    NAVY = RGBColor(0x1B, 0x2A, 0x4A)        # Dark navy — titles, headers
    STEEL_BLUE = RGBColor(0x2E, 0x5C, 0x8A)  # Steel blue — headings
    ACCENT_BLUE = RGBColor(0x3D, 0x7E, 0xAA)  # Lighter accent
    LIGHT_BLUE = RGBColor(0xE8, 0xF1, 0xF8)  # Very light blue tint

    # Neutral
    DARK_GREY = RGBColor(0x33, 0x33, 0x3B)   # Body text
    MID_GREY = RGBColor(0x5A, 0x5A, 0x65)    # Secondary text
    LIGHT_GREY = RGBColor(0xF5, 0xF5, 0xF7)  # Table alternating rows
    BORDER_GREY = RGBColor(0xD0, 0xD0, 0xD8) # Table borders

    # Severity indicators
    CRITICAL = RGBColor(0xC0, 0x39, 0x2B)    # Red
    HIGH = RGBColor(0xE6, 0x7E, 0x22)        # Orange
    MEDIUM = RGBColor(0xF3, 0x9C, 0x12)      # Amber
    LOW = RGBColor(0x27, 0xAE, 0x60)         # Green
    INFO = RGBColor(0x7F, 0x8C, 0x8D)        # Grey

    # Table header backgrounds (hex strings for XML shading)
    TABLE_HEADER_BG = "1B2A4A"
    TABLE_ALT_ROW_BG = "F5F5F7"
    TABLE_ACCENT_BG = "E8F1F8"

    # Status colors
    OPEN = RGBColor(0xC0, 0x39, 0x2B)
    IN_PROGRESS = RGBColor(0xF3, 0x9C, 0x12)
    RESOLVED = RGBColor(0x27, 0xAE, 0x60)
    CLOSED = RGBColor(0x7F, 0x8C, 0x8D)


SEVERITY_COLORS = {
    "blocker": Colors.CRITICAL,
    "critical": Colors.CRITICAL,
    "high": Colors.HIGH,
    "medium": Colors.MEDIUM,
    "low": Colors.LOW,
    "info": Colors.INFO,
}

STATUS_COLORS = {
    "open": Colors.OPEN,
    "in_progress": Colors.IN_PROGRESS,
    "resolved": Colors.RESOLVED,
    "closed": Colors.CLOSED,
    "deferred": Colors.INFO,
}


# =============================================================================
# Document Setup
# =============================================================================

def create_styled_document() -> Document:
    """Create a new Document with professional styling applied."""
    doc = Document()

    # Page setup — A4 with generous margins
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

    # Configure styles
    _configure_styles(doc)

    return doc


def _configure_styles(doc: Document):
    """Configure document styles for professional appearance."""
    # Normal style
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = Colors.DARK_GREY
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    # Heading 1
    h1 = doc.styles["Heading 1"]
    h1.font.name = "Calibri Light"
    h1.font.size = Pt(22)
    h1.font.bold = False
    h1.font.color.rgb = Colors.NAVY
    h1.paragraph_format.space_before = Pt(24)
    h1.paragraph_format.space_after = Pt(8)

    # Heading 2
    h2 = doc.styles["Heading 2"]
    h2.font.name = "Calibri Light"
    h2.font.size = Pt(16)
    h2.font.bold = False
    h2.font.color.rgb = Colors.STEEL_BLUE
    h2.paragraph_format.space_before = Pt(18)
    h2.paragraph_format.space_after = Pt(6)

    # Heading 3
    h3 = doc.styles["Heading 3"]
    h3.font.name = "Calibri"
    h3.font.size = Pt(12)
    h3.font.bold = True
    h3.font.color.rgb = Colors.STEEL_BLUE
    h3.paragraph_format.space_before = Pt(12)
    h3.paragraph_format.space_after = Pt(4)

    # List Bullet
    lb = doc.styles["List Bullet"]
    lb.font.name = "Calibri"
    lb.font.size = Pt(10.5)
    lb.font.color.rgb = Colors.DARK_GREY
    lb.paragraph_format.space_after = Pt(3)


# =============================================================================
# Cover Page
# =============================================================================

def add_cover_page(doc: Document, title: str, subtitle: str, vendor: str, date: str):
    """Add a professional cover page with color block design."""
    # Spacer to push content down
    for _ in range(4):
        doc.add_paragraph()

    # Accent line (thin colored bar via border-bottom on paragraph)
    accent_line = doc.add_paragraph()
    _add_bottom_border(accent_line, color="1B2A4A", size=24)

    # Spacer
    doc.add_paragraph()

    # Title
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = title_para.add_run(title)
    run.font.name = "Calibri Light"
    run.font.size = Pt(36)
    run.font.color.rgb = Colors.NAVY
    run.bold = False

    # Subtitle (customer)
    if subtitle:
        sub_para = doc.add_paragraph()
        sub_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = sub_para.add_run(subtitle)
        run.font.name = "Calibri Light"
        run.font.size = Pt(20)
        run.font.color.rgb = Colors.STEEL_BLUE

    # Spacer
    doc.add_paragraph()
    doc.add_paragraph()

    # Metadata block
    _add_metadata_line(doc, "Prepared by", vendor)
    _add_metadata_line(doc, "Date", date)
    _add_metadata_line(doc, "Classification", "Confidential")

    # Bottom accent line
    doc.add_paragraph()
    accent_line2 = doc.add_paragraph()
    _add_bottom_border(accent_line2, color="2E5C8A", size=8)

    doc.add_page_break()


def _add_metadata_line(doc: Document, label: str, value: str):
    """Add a label: value metadata line."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    run_label = p.add_run(f"{label}:  ")
    run_label.font.name = "Calibri"
    run_label.font.size = Pt(11)
    run_label.font.color.rgb = Colors.MID_GREY
    run_label.bold = True
    run_value = p.add_run(value)
    run_value.font.name = "Calibri"
    run_value.font.size = Pt(11)
    run_value.font.color.rgb = Colors.DARK_GREY


def _add_bottom_border(paragraph, color: str = "1B2A4A", size: int = 12):
    """Add a bottom border to a paragraph (acts as a divider line)."""
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}>'
        f'  <w:bottom w:val="single" w:sz="{size}" w:space="1" w:color="{color}"/>'
        f'</w:pBdr>'
    )
    pPr.append(pBdr)


# =============================================================================
# Headers & Footers
# =============================================================================

def add_header_footer(doc: Document, title: str, subtitle: str = ""):
    """Add professional header and footer with page numbers."""
    section = doc.sections[0]

    # Header
    header = section.header
    header_para = header.paragraphs[0]
    header_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = header_para.add_run(title)
    run.font.name = "Calibri"
    run.font.size = Pt(8)
    run.font.color.rgb = Colors.MID_GREY
    if subtitle:
        run2 = header_para.add_run(f"  |  {subtitle}")
        run2.font.name = "Calibri"
        run2.font.size = Pt(8)
        run2.font.color.rgb = Colors.BORDER_GREY
    # Add bottom border to header
    _add_bottom_border(header_para, color="D0D0D8", size=4)

    # Footer with page number
    footer = section.footer
    footer_para = footer.paragraphs[0]
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    run = footer_para.add_run("Page ")
    run.font.name = "Calibri"
    run.font.size = Pt(8)
    run.font.color.rgb = Colors.MID_GREY

    # Page number field
    fldChar1 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="begin"/>')
    run1 = footer_para.add_run()
    run1._r.append(fldChar1)

    instrText = parse_xml(f'<w:instrText {nsdecls("w")} xml:space="preserve"> PAGE </w:instrText>')
    run2 = footer_para.add_run()
    run2._r.append(instrText)
    run2.font.name = "Calibri"
    run2.font.size = Pt(8)
    run2.font.color.rgb = Colors.MID_GREY

    fldChar2 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="end"/>')
    run3 = footer_para.add_run()
    run3._r.append(fldChar2)

    run4 = footer_para.add_run(" of ")
    run4.font.name = "Calibri"
    run4.font.size = Pt(8)
    run4.font.color.rgb = Colors.MID_GREY

    # Total pages field
    fldChar3 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="begin"/>')
    run5 = footer_para.add_run()
    run5._r.append(fldChar3)

    instrText2 = parse_xml(f'<w:instrText {nsdecls("w")} xml:space="preserve"> NUMPAGES </w:instrText>')
    run6 = footer_para.add_run()
    run6._r.append(instrText2)
    run6.font.name = "Calibri"
    run6.font.size = Pt(8)
    run6.font.color.rgb = Colors.MID_GREY

    fldChar4 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="end"/>')
    run7 = footer_para.add_run()
    run7._r.append(fldChar4)


# =============================================================================
# Tables
# =============================================================================

def add_styled_table(doc: Document, headers: list, rows: list,
                     col_widths: list = None, accent_col: int = None) -> None:
    """Add a professionally styled table with dark header and alternating rows.

    Args:
        doc: Document to add table to
        headers: list of header strings
        rows: list of row data (each row is a list of strings)
        col_widths: optional list of column widths in cm
        accent_col: optional column index to highlight (0-based)
    """
    if not headers:
        return

    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Set column widths
    if col_widths:
        for i, width in enumerate(col_widths):
            if i < len(table.columns):
                table.columns[i].width = Cm(width)

    # Style header row
    for i, header_text in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = ""
        p = cell.paragraphs[0]
        run = p.add_run(header_text)
        run.font.name = "Calibri"
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        run.bold = True
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        # Dark header background
        _set_cell_shading(cell, Colors.TABLE_HEADER_BG)

    # Style data rows
    for r_idx, row_data in enumerate(rows):
        for c_idx, cell_val in enumerate(row_data):
            if c_idx >= len(headers):
                break
            cell = table.cell(r_idx + 1, c_idx)
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(str(cell_val) if cell_val else "")
            run.font.name = "Calibri"
            run.font.size = Pt(9.5)
            run.font.color.rgb = Colors.DARK_GREY
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)

            # Alternating row shading
            if r_idx % 2 == 1:
                _set_cell_shading(cell, Colors.TABLE_ALT_ROW_BG)

            # Accent column
            if accent_col is not None and c_idx == accent_col:
                run.bold = True
                run.font.color.rgb = Colors.STEEL_BLUE

    # Remove default borders, add subtle ones
    _set_table_borders(table)

    # Spacer after table
    doc.add_paragraph().paragraph_format.space_after = Pt(6)


def add_kv_table(doc: Document, data: list, key_width: float = 4.0, val_width: float = 12.0):
    """Add a key-value detail table (2 columns, label on left, value on right).

    Args:
        doc: Document to add table to
        data: list of (label, value) tuples
    """
    table = doc.add_table(rows=len(data), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.columns[0].width = Cm(key_width)
    table.columns[1].width = Cm(val_width)

    for i, (label, value) in enumerate(data):
        # Label cell
        cell_l = table.cell(i, 0)
        cell_l.text = ""
        p = cell_l.paragraphs[0]
        run = p.add_run(label)
        run.font.name = "Calibri"
        run.font.size = Pt(9.5)
        run.font.color.rgb = Colors.MID_GREY
        run.bold = True
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        _set_cell_shading(cell_l, Colors.TABLE_ACCENT_BG)

        # Value cell
        cell_v = table.cell(i, 1)
        cell_v.text = ""
        p = cell_v.paragraphs[0]
        run = p.add_run(str(value) if value else "—")
        run.font.name = "Calibri"
        run.font.size = Pt(9.5)
        run.font.color.rgb = Colors.DARK_GREY
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)

        # Alternating row
        if i % 2 == 1:
            _set_cell_shading(cell_v, Colors.TABLE_ALT_ROW_BG)

    _set_table_borders(table)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def _set_cell_shading(cell, color: str):
    """Set cell background color."""
    shading_elm = parse_xml(
        f'<w:shd {nsdecls("w")} w:fill="{color}" w:val="clear"/>'
    )
    cell._tc.get_or_add_tcPr().append(shading_elm)


def _set_table_borders(table):
    """Set subtle table borders."""
    tbl = table._tbl
    tblPr = tbl.tblPr if tbl.tblPr is not None else parse_xml(f'<w:tblPr {nsdecls("w")}/>')
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="4" w:space="0" w:color="D0D0D8"/>'
        f'  <w:left w:val="single" w:sz="4" w:space="0" w:color="D0D0D8"/>'
        f'  <w:bottom w:val="single" w:sz="4" w:space="0" w:color="D0D0D8"/>'
        f'  <w:right w:val="single" w:sz="4" w:space="0" w:color="D0D0D8"/>'
        f'  <w:insideH w:val="single" w:sz="2" w:space="0" w:color="E0E0E5"/>'
        f'  <w:insideV w:val="single" w:sz="2" w:space="0" w:color="E0E0E5"/>'
        f'</w:tblBorders>'
    )
    # Remove existing borders if any
    existing = tblPr.find(qn('w:tblBorders'))
    if existing is not None:
        tblPr.remove(existing)
    tblPr.append(borders)
    if tbl.tblPr is None:
        tbl.append(tblPr)


# =============================================================================
# Content Helpers
# =============================================================================

def add_section_divider(doc: Document):
    """Add a subtle horizontal divider between sections."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(12)
    _add_bottom_border(p, color="D0D0D8", size=4)


def add_callout_box(doc: Document, text: str, style: str = "info"):
    """Add a highlighted callout/info box."""
    colors = {
        "info": ("E8F1F8", "2E5C8A"),
        "warning": ("FFF3E0", "E67E22"),
        "success": ("E8F5E9", "27AE60"),
        "danger": ("FFEBEE", "C0392B"),
    }
    bg, border_color = colors.get(style, colors["info"])

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(8)

    # Left border + background via paragraph borders
    pPr = p._p.get_or_add_pPr()
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}>'
        f'  <w:left w:val="single" w:sz="24" w:space="8" w:color="{border_color}"/>'
        f'</w:pBdr>'
    )
    pPr.append(pBdr)

    # Shading
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg}" w:val="clear"/>')
    pPr.append(shd)

    # Indentation for visual padding
    ind = parse_xml(f'<w:ind {nsdecls("w")} w:left="180" w:right="180"/>')
    pPr.append(ind)

    run = p.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(10)
    run.font.color.rgb = Colors.DARK_GREY


def add_stat_block(doc: Document, stats: list):
    """Add a row of statistics (label + large number pairs).

    Args:
        stats: list of (label, value) tuples, e.g. [("Total Issues", "24"), ("Open", "12")]
    """
    # Use a table for layout
    table = doc.add_table(rows=2, cols=len(stats))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for i, (label, value) in enumerate(stats):
        # Value row (large number)
        cell = table.cell(0, i)
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(str(value))
        run.font.name = "Calibri Light"
        run.font.size = Pt(28)
        run.font.color.rgb = Colors.NAVY
        run.bold = True

        # Label row
        cell = table.cell(1, i)
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(label)
        run.font.name = "Calibri"
        run.font.size = Pt(9)
        run.font.color.rgb = Colors.MID_GREY

    # Remove all borders from stat block
    tbl = table._tbl
    tblPr = tbl.tblPr if tbl.tblPr is not None else parse_xml(f'<w:tblPr {nsdecls("w")}/>')
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'  <w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'  <w:bottom w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'  <w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'  <w:insideH w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'  <w:insideV w:val="single" w:sz="4" w:space="0" w:color="D0D0D8"/>'
        f'</w:tblBorders>'
    )
    existing = tblPr.find(qn('w:tblBorders'))
    if existing is not None:
        tblPr.remove(existing)
    tblPr.append(borders)
    if tbl.tblPr is None:
        tbl.append(tblPr)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)


def add_severity_badge(paragraph, severity: str):
    """Add a colored severity indicator inline."""
    color = SEVERITY_COLORS.get(severity.lower(), Colors.INFO)
    run = paragraph.add_run(f"  [{severity.upper()}]")
    run.font.name = "Calibri"
    run.font.size = Pt(9)
    run.font.color.rgb = color
    run.bold = True
