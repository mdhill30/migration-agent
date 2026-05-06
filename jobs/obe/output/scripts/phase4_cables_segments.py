#!/usr/bin/env python3
"""
OBE Migration — Phase 4: Fiber Cable & Segment Generation

Reads FO_CABLE from FO.gpkg + route_index.json from phase 2.
Generates fiber_cable and mywcom_fiber_segment CSVs with proper segment chains.

For each cable, builds the full alternating segment chain:
  internal(start) -> transit(route1) -> internal(mid1) -> transit(route2) -> ... -> internal(end)

Uses route_index.json to determine which route spans each cable traverses.

Output:
  - output/data/fiber_cable.csv
  - output/data/mywcom_fiber_segment.csv
"""
import csv
import json
import os
import sqlite3
import struct
from collections import defaultdict
from pathlib import Path

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

SRID = 31370

cable_ref_cache = {}


def parse_gpkg_linestring(blob):
    """Parse GeoPackage binary linestring to list of (x, y) coords."""
    if not blob or blob[0:2] != b'GP':
        return []
    flags = blob[3]
    envelope_type = (flags >> 1) & 0x07
    envelope_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    header_size = 8 + envelope_sizes.get(envelope_type, 0)
    wkb = blob[header_size:]
    if len(wkb) < 9:
        return []
    bo = '<' if wkb[0] == 1 else '>'
    geom_type = struct.unpack(f'{bo}I', wkb[1:5])[0]
    if geom_type != 2:
        return []
    num_points = struct.unpack(f'{bo}I', wkb[5:9])[0]
    coords = []
    offset = 9
    for _ in range(num_points):
        x, y = struct.unpack(f'{bo}dd', wkb[offset:offset + 16])
        coords.append((x, y))
        offset += 16
    return coords


def coords_to_ewkt(coords):
    """Convert coordinate list to EWKT linestring."""
    if not coords or len(coords) < 2:
        return ''
    pairs = ','.join(f'{x} {y}' for x, y in coords)
    return f'SRID={SRID};LINESTRING({pairs})'


def load_structure_urns(conn):
    """Build structure ID -> URN mapping."""
    cur = conn.cursor()
    cur.execute("SELECT ID, TYPE_SUPPORT FROM INFRA_SUPPORT")
    urns = {}
    for row in cur.fetchall():
        sid = int(row[0])
        stype = STRUCTURE_TYPE_MAP.get(row[1], 'cabinet')
        urns[sid] = f'{stype}/{sid}'
    return urns


def load_cable_refs(conn):
    """Load FO_CABLE_REF for fibre count lookups."""
    cur = conn.cursor()
    cur.execute("SELECT ID, NAME, NB_FIBRE FROM FO_CABLE_REF")
    for row in cur.fetchall():
        cable_ref_cache[str(row[0])] = {'name': row[1], 'nb_fibre': row[2]}


def load_pttech_support(conn):
    """Load FO_PTTECH ID -> SUPPORT mapping."""
    cur = conn.cursor()
    cur.execute("SELECT ID, SUPPORT FROM FO_PTTECH")
    return {int(row[0]): int(row[1]) for row in cur.fetchall()}


def load_cable_way_coords(conn):
    """Load cable_way NAME -> list of (x,y) coords (composited from segments)."""
    cur = conn.cursor()
    cur.execute("SELECT NAME, SEGMENT, geom FROM INFRA_CABLE_WAY_SEGM ORDER BY NAME, SEGMENT")
    segments_by_name = defaultdict(list)
    for name, segment, geom in cur.fetchall():
        coords = parse_gpkg_linestring(geom)
        segments_by_name[name].append((segment, coords))

    result = {}
    for name, segs in segments_by_name.items():
        all_coords = []
        for _, coords in sorted(segs):
            if all_coords and coords and all_coords[-1] == coords[0]:
                coords = coords[1:]
            all_coords.extend(coords)
        if all_coords:
            result[name] = all_coords
    return result


def load_route_geometries(output_dir):
    """Load route ID -> EWKT path from generated route CSVs."""
    route_geoms = {}
    for route_file in ['ug_route.csv', 'oh_route.csv']:
        fpath = output_dir / route_file
        if not fpath.exists():
            continue
        with open(fpath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                route_id = int(row['id'])
                route_geoms[route_id] = row.get('path', '')
    return route_geoms


def main():
    source_dir = Path(os.environ.get('OBE_SOURCE_DIR', 'data'))
    output_dir = Path(os.environ.get('OBE_OUTPUT_DIR', 'output/data'))
    output_dir.mkdir(parents=True, exist_ok=True)

    source_db = source_dir / 'FO.gpkg'
    conn = sqlite3.connect(source_db)
    cur = conn.cursor()

    # Load route index from phase 2
    route_index_file = output_dir / 'route_index.json'
    with open(route_index_file, 'r', encoding='utf-8') as f:
        route_index = json.load(f)

    load_cable_refs(conn)
    pttech_support = load_pttech_support(conn)
    structure_urns = load_structure_urns(conn)
    cw_coords = load_cable_way_coords(conn)
    route_geoms = load_route_geometries(output_dir)

    # Query all cables
    cur.execute("""
        SELECT ID, OPER_NAME, CABLE_WAY, ID_START, ID_END,
               STATUS, COLOR_CABLE, LENGTH, LENGTH_TYPE,
               ID_TYPE_CABLE_REF, OWNER, VOO_COMPANY, ID_TUBE
        FROM FO_CABLE
        ORDER BY ID
    """)
    cables = cur.fetchall()

    # --- fiber_cable.csv ---
    cable_file = output_dir / 'fiber_cable.csv'
    with open(cable_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(['id', 'name', 'fiber_count', 'directed', 'path', 'owner'])

        for row in cables:
            cable_id, oper_name, cable_way, id_start, id_end, \
                status, color, length, length_type, \
                cable_ref_id, owner, voo, id_tube = row

            ref = cable_ref_cache.get(str(cable_ref_id), {})
            nb_fibre = ref.get('nb_fibre', '')

            coords = cw_coords.get(cable_way, [])
            path_ewkt = coords_to_ewkt(coords)

            writer.writerow([
                int(cable_id),
                oper_name or '',
                nb_fibre,
                'true',
                path_ewkt,
                owner or '',
            ])

    # --- mywcom_fiber_segment.csv ---
    seg_file = output_dir / 'mywcom_fiber_segment.csv'
    with open(seg_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow([
            'id', 'cable', 'housing', 'root_housing', 'directed', 'forward',
            'in_structure', 'out_structure', 'in_segment', 'out_segment', 'path'
        ])

        seg_count = 0
        skipped_cables = 0

        for row in cables:
            cable_id, oper_name, cable_way, id_start, id_end, *_ = row
            cable_id_int = int(cable_id)

            # Resolve cable start/end structures
            start_pttech = int(id_start) if id_start else None
            end_pttech = int(id_end) if id_end else None
            if not start_pttech or not end_pttech:
                skipped_cables += 1
                continue

            start_struct = pttech_support.get(start_pttech)
            end_struct = pttech_support.get(end_pttech)
            if not start_struct or not end_struct:
                skipped_cables += 1
                continue

            # Get route spans for this cable_way from route_index
            spans = route_index.get(cable_way)
            if not spans:
                skipped_cables += 1
                continue

            # Build the full structure sequence from spans
            cw_struct_sequence = [spans[0]['in_struct']]
            for span in spans:
                cw_struct_sequence.append(span['out_struct'])

            # Find start and end positions in the sequence
            try:
                start_idx = cw_struct_sequence.index(start_struct)
            except ValueError:
                start_idx = 0

            try:
                end_idx = cw_struct_sequence.index(end_struct)
            except ValueError:
                end_idx = len(cw_struct_sequence) - 1

            # Handle reverse direction
            cable_reversed = False
            if start_idx > end_idx:
                start_idx, end_idx = end_idx, start_idx
                cable_reversed = True

            # Get the relevant spans (slice from span list)
            relevant_spans = spans[start_idx:end_idx]

            if not relevant_spans:
                # Cable start == end structure or other edge case
                # Use all spans as fallback
                relevant_spans = spans
                cable_reversed = False

            # Only transit segments — one per route span
            num_segments = len(relevant_spans)

            # Generate segment IDs
            seg_ids = [cable_id_int * 100 + i + 1 for i in range(num_segments)]

            cable_urn = f'fiber_cable/{cable_id_int}'

            # Write transit-only segment chain
            for seg_idx, span in enumerate(relevant_spans):
                route_id = span['route_id']
                route_type = span['route_type']
                span_in = span['in_struct']
                span_out = span['out_struct']

                if cable_reversed:
                    forward = False
                    seg_in_struct = span_out
                    seg_out_struct = span_in
                else:
                    forward = True
                    seg_in_struct = span_in
                    seg_out_struct = span_out

                route_urn = f'{route_type}/{route_id}'
                in_struct_urn = structure_urns.get(seg_in_struct, f'cabinet/{seg_in_struct}')
                out_struct_urn = structure_urns.get(seg_out_struct, f'cabinet/{seg_out_struct}')

                prev_seg = seg_ids[seg_idx - 1] if seg_idx > 0 else ''
                next_seg = seg_ids[seg_idx + 1] if seg_idx < num_segments - 1 else ''

                # Segment path = the exact route geometry it traverses
                # (NMT requires segment.path == route.path regardless of forward flag)
                seg_path = route_geoms.get(route_id, '')

                writer.writerow([
                    seg_ids[seg_idx],
                    cable_urn,
                    route_urn,
                    route_urn,
                    'true',
                    str(forward).lower(),
                    in_struct_urn,
                    out_struct_urn,
                    prev_seg,
                    next_seg,
                    seg_path,
                ])

            seg_count += num_segments

    conn.close()
    print(f"Phase 4 complete: {len(cables)} fiber_cables, {seg_count} mywcom_fiber_segments")
    print(f"  Skipped cables (missing refs): {skipped_cables}")


if __name__ == '__main__':
    main()
