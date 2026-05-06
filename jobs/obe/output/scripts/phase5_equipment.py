#!/usr/bin/env python3
"""
OBE Migration — Phase 5: Equipment Generation (per-type CSVs)
Reads FO_PTTECH from FO.gpkg, splits into separate CSVs per NMT equipment type.

Output:
  - output/data/drop_point.csv
  - output/data/splice_closure.csv

Mapping from TYPE_PTTECH:
  DP, DCP, CCP, FCP, TERM, CLCO → drop_point
  JUNC, SUPERJ, PASS, PASS_FTTPD, HFCJ, POP → splice_closure
  YSPL, YSPL_FTTPT, YSPL_FTTPD → splice_closure (pass-through points, NOT true optical splitters)

NMT fields (from .def):
  drop_point: id, name, location, type, installation_date
  splice_closure: id, name, root_housing, housing, location, installation_date
"""
import csv
import os
import sqlite3
import struct
from pathlib import Path

# TYPE_PTTECH → NMT feature type
EQUIPMENT_TYPE_MAP = {
    'DP': 'drop_point',
    'DCP': 'drop_point',
    'CCP': 'drop_point',
    'FCP': 'drop_point',
    'TERM': 'drop_point',
    'CLCO': 'drop_point',
    'JUNC': 'splice_closure',
    'SUPERJ': 'splice_closure',
    'PASS': 'splice_closure',
    'PASS_FTTPD': 'splice_closure',
    'HFCJ': 'splice_closure',
    'POP': 'splice_closure',
    'YSPL': 'splice_closure',
    'YSPL_FTTPT': 'splice_closure',
    'YSPL_FTTPD': 'splice_closure',
}



# Structure type mapping for URN generation
STRUCTURE_TYPE_MAP = {
    'AP': 'pole',
    'AR': 'cabinet',
    'CV': 'manhole',
    'FA': 'wall_box',
    'LOC': 'building',
    'GEN': 'cabinet',
    'AS': 'cabinet',
    'DER': 'cabinet',
    'AC': 'cabinet',
}


def parse_gpkg_point(blob):
    """Parse GeoPackage binary point geometry to (x, y)."""
    if blob is None:
        return None, None
    magic = blob[0:2]
    if magic != b'GP':
        return None, None
    flags = blob[3]
    envelope_type = (flags >> 1) & 0x07
    envelope_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    header_size = 8 + envelope_sizes.get(envelope_type, 0)
    wkb = blob[header_size:]
    if len(wkb) < 21:
        return None, None
    bo = '<' if wkb[0] == 1 else '>'
    geom_type = struct.unpack(f'{bo}I', wkb[1:5])[0]
    if geom_type != 1:
        return None, None
    x, y = struct.unpack(f'{bo}dd', wkb[5:21])
    return x, y


def format_point_ewkt(x, y, srid=31370):
    """Format point as EWKT for myw_db load."""
    if x is None or y is None:
        return ''
    return f'SRID={srid};POINT({x} {y})'


def main():
    source_dir = Path(os.environ.get('OBE_SOURCE_DIR', 'data'))
    output_dir = Path(os.environ.get('OBE_OUTPUT_DIR', 'output/data'))
    output_dir.mkdir(parents=True, exist_ok=True)

    source_db = source_dir / 'FO.gpkg'
    conn = sqlite3.connect(source_db)
    cur = conn.cursor()

    # Load structure type lookup for URN generation
    cur2 = conn.cursor()
    cur2.execute("SELECT ID, TYPE_SUPPORT FROM INFRA_SUPPORT")
    structure_urns = {}
    for row in cur2.fetchall():
        sid = int(row[0])
        stype = STRUCTURE_TYPE_MAP.get(row[1], 'cabinet')
        structure_urns[sid] = f'{stype}/{sid}'

    # Load structure locations for equipment geometry inheritance
    cur2.execute("SELECT ID, geom FROM INFRA_SUPPORT")
    struct_geom = {}
    for sid, geom in cur2.fetchall():
        x, y = parse_gpkg_point(geom)
        if x is not None:
            struct_geom[int(sid)] = (x, y)

    cur.execute("""
        SELECT ID, OPER_NAME, TYPE_PTTECH, SUPPORT, TYPE_BOITIER,
               STATUS, INSTALL_DATE
        FROM FO_PTTECH
        ORDER BY ID
    """)

    # Headers per equipment type (from .def files)
    HEADERS = {
        'drop_point': ['id', 'name', 'location', 'type', 'installation_date'],
        'splice_closure': ['id', 'name', 'root_housing', 'housing', 'location', 'installation_date'],
    }

    files = {}
    writers = {}
    counts = {}

    for feat_type, header in HEADERS.items():
        f = open(output_dir / f'{feat_type}.csv', 'w', newline='', encoding='utf-8')
        files[feat_type] = f
        writers[feat_type] = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
        writers[feat_type].writerow(header)
        counts[feat_type] = 0

    for row in cur.fetchall():
        pt_id, oper_name, type_pt, support, type_boitier, status, install_date = row
        feat_type = EQUIPMENT_TYPE_MAP.get(type_pt, 'splice_closure')

        support_int = int(support)
        support_urn = structure_urns.get(support_int, f'cabinet/{support_int}')

        # Get geometry from structure (equipment inherits housing location)
        xy = struct_geom.get(support_int)
        location = format_point_ewkt(xy[0], xy[1]) if xy else ''

        name = oper_name or f'EQ-{int(pt_id)}'
        install = str(install_date).split('T')[0] if install_date else ''

        if feat_type == 'drop_point':
            # drop_point is a structure-level object (like a pole/cabinet)
            # It has routes, cables — so it uses `location` as its geometry
            writers[feat_type].writerow([
                int(pt_id), name, location, type_pt, install
            ])
        elif feat_type == 'splice_closure':
            # housing/root_housing reference the structure it's contained in
            writers[feat_type].writerow([
                int(pt_id), name, support_urn, support_urn, location, install
            ])

        counts[feat_type] += 1

    for f in files.values():
        f.close()
    conn.close()

    total = sum(counts.values())
    parts = ', '.join(f'{t}={c}' for t, c in sorted(counts.items()) if c > 0)
    print(f"Phase 5 complete: {total} equipment ({parts})")


if __name__ == '__main__':
    main()
