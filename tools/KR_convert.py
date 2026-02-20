#!/usr/bin/env python3
"""
KR_convert.py  —  LampGeoPlus KR/KX Compatibility Generator
=============================================================

Reads country-tag sections from the base mod's text files and generates
KR/KX-compatible equivalents in an output submod folder.

The output ("LampGeoPlus KR") contains ONLY new krkx_* files with the KR
entries.  Load it ALONGSIDE lampgeoplus_lite in the HOI4 launcher.

Usage:
    python KR_convert.py             # generate output files
    python KR_convert.py --dry-run   # preview only, no files written

Substitution rules by file type
────────────────────────────────
  graphic_db (.txt)  : substitute everywhere; skip quoted strings with '/'
  asset      (.asset): same, plus skip quoted values of  pdxmesh / soundeffect
  interface_gfx (.gfx): same as graphic_db; wrap output in spriteTypes { }

The '/' rule preserves file-system paths like "gfx/interface/.../SOV/..."
so the KR entries still point at the existing SOV texture/mesh files on disk.
The pdxmesh rule means RUS entities keep pointing at SOV_xxx_mesh (which
already exists), so Category 3 mesh .gfx files need no changes at all.
"""

import re
import sys
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Paths  (auto-derived from this script's location)
# ──────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent          # …/lampgeoplus_lite_local/tools/
SOURCE_DIR = SCRIPT_DIR.parent                         # …/lampgeoplus_lite_local/
OUTPUT_DIR = SOURCE_DIR.parent / "LampGeoPlus KR"

# ──────────────────────────────────────────────────────────────────────────────
# Tag mapping: vanilla tag → list of KR/KX replacement tags
# ──────────────────────────────────────────────────────────────────────────────

TAG_MAPPINGS: dict[str, list[str]] = {
    'FRA': ['NFA'],
    'ENG': ['CAN', 'GBR'],
    'TUR': ['OTT'],
    'SOV': ['RUS', 'TRM'],
    'USA': ['CSA', 'TEX', 'NEE', 'PSA'],
    'ITA': ['SRD', 'SIC', 'PAP', 'SRI'],
    'RAJ': ['HND', 'PRF'],
    'POL': ['GAL'],
}

# ──────────────────────────────────────────────────────────────────────────────
# Files to process:  (source_relative, output_relative, file_type)
# ──────────────────────────────────────────────────────────────────────────────

PROCESS_FILES: list[tuple[str, str, str]] = [

    # ── Category 1 : equipment designer icon pools (graphic_db) ──────────────

    ('gfx/interface/equipmentdesigner/graphic_db/#_dlcplus_plane_icons.txt',
     'gfx/interface/equipmentdesigner/graphic_db/krkx_dlcplus_plane_icons.txt',
     'graphic_db'),

    ('gfx/interface/equipmentdesigner/graphic_db/#_dlcplus_tank_icons.txt',
     'gfx/interface/equipmentdesigner/graphic_db/krkx_dlcplus_tank_icons.txt',
     'graphic_db'),

    ('gfx/interface/equipmentdesigner/graphic_db/#_dlcplus_ship_icons.txt',
     'gfx/interface/equipmentdesigner/graphic_db/krkx_dlcplus_ship_icons.txt',
     'graphic_db'),

    ('gfx/interface/equipmentdesigner/graphic_db/#_geoplus_plane_icons.txt',
     'gfx/interface/equipmentdesigner/graphic_db/krkx_geoplus_plane_icons.txt',
     'graphic_db'),

    ('gfx/interface/equipmentdesigner/graphic_db/#_geoplus_tank_icons.txt',
     'gfx/interface/equipmentdesigner/graphic_db/krkx_geoplus_tank_icons.txt',
     'graphic_db'),

    # ── Category 2 : entity definitions (.asset) ──────────────────────────────

    ('gfx/entities/mod_replacement/geoplus_units_planes.asset',
     'gfx/entities/mod_replacement/krkx_geoplus_units_planes.asset',
     'asset'),

    ('gfx/entities/mod_replacement/geoplus_units_tanks.asset',
     'gfx/entities/mod_replacement/krkx_geoplus_units_tanks.asset',
     'asset'),

    ('gfx/entities/mod_replacement/geoplus_units_ships.asset',
     'gfx/entities/mod_replacement/krkx_geoplus_units_ships.asset',
     'asset'),

    ('gfx/entities/mod_replacement/geoplus_units_infantry.asset',
     'gfx/entities/mod_replacement/krkx_geoplus_units_infantry.asset',
     'asset'),

    ('gfx/entities/mod_replacement/geoplus_units_vehicles.asset',
     'gfx/entities/mod_replacement/krkx_geoplus_units_vehicles.asset',
     'asset'),

    ('gfx/entities/mod_replacement/reskindlc_units_planes.asset',
     'gfx/entities/mod_replacement/krkx_reskindlc_units_planes.asset',
     'asset'),

    ('gfx/entities/mod_replacement/reskindlc_units_tanks.asset',
     'gfx/entities/mod_replacement/krkx_reskindlc_units_tanks.asset',
     'asset'),

    ('gfx/entities/mod_replacement/reskindlc_units_ships.asset',
     'gfx/entities/mod_replacement/krkx_reskindlc_units_ships.asset',
     'asset'),

    ('gfx/entities/mod_replacement/reskindlc_units_vehicles.asset',
     'gfx/entities/mod_replacement/krkx_reskindlc_units_vehicles.asset',
     'asset'),

    ('gfx/entities/mod_replacement/appendplus_units_planes.asset',
     'gfx/entities/mod_replacement/krkx_appendplus_units_planes.asset',
     'asset'),

    # ── Category 4 : interface sprites (blueprint overlays excluded) ──────────

    ('interface/mod_replacement/lampplus_plane_tech.gfx',
     'interface/mod_replacement/krkx_lampplus_plane_tech.gfx',
     'interface_gfx'),

    ('interface/mod_replacement/lampplus_tank_tech.gfx',
     'interface/mod_replacement/krkx_lampplus_tank_tech.gfx',
     'interface_gfx'),

    ('interface/mod_replacement/lampplus_naval_tech.gfx',
     'interface/mod_replacement/krkx_lampplus_naval_tech.gfx',
     'interface_gfx'),

    ('interface/mod_replacement/lampplus_inf_art_sup.gfx',
     'interface/mod_replacement/krkx_lampplus_inf_art_sup.gfx',
     'interface_gfx'),
]

# Quoted values of these keys are kept unchanged in .asset files
ASSET_SKIP_KEYS: frozenset[str] = frozenset({'pdxmesh', 'soundeffect'})
_ASSET_SKIP_RE = re.compile(
    r'\b(?:' + '|'.join(re.escape(k) for k in ASSET_SKIP_KEYS) + r')\s*=\s*$'
)

# ──────────────────────────────────────────────────────────────────────────────
# Substitution
# ──────────────────────────────────────────────────────────────────────────────

def substitute(text: str, src: str, dst: str, file_type: str) -> str:
    """
    Replace every occurrence of src with dst in text, respecting these rules:

    • Quoted strings containing '/'  →  kept as-is  (filesystem paths)
    • In 'asset' mode: quoted values of pdxmesh / soundeffect  →  kept as-is
    • Unquoted text and all other quoted strings  →  substituted freely

    Implementation uses re.split on quoted strings so we can inspect each
    token without writing a full parser.
    """
    # re.split with one capturing group returns:
    #   [unquoted₀, inner₁, unquoted₂, inner₃, …]
    # where odd-indexed elements are the content *inside* the quotes.
    parts = re.split(r'"([^"]*)"', text)
    result: list[str] = []

    for i, part in enumerate(parts):
        if i % 2 == 0:
            # Unquoted text — substitute freely
            result.append(part.replace(src, dst))
        else:
            # Inside a quoted string
            # Rule 1: file paths (contain '/') → preserve
            if '/' in part:
                result.append(f'"{part}"')
                continue

            # Rule 2 (asset only): value of pdxmesh / soundeffect → preserve
            if file_type == 'asset' and i > 0:
                preceding = parts[i - 1]          # unquoted text before this string
                if _ASSET_SKIP_RE.search(preceding):
                    result.append(f'"{part}"')
                    continue

            # Default: substitute
            result.append(f'"{part.replace(src, dst)}"')

    return ''.join(result)


# ──────────────────────────────────────────────────────────────────────────────
# Section finding
# ──────────────────────────────────────────────────────────────────────────────

# Pattern explanation
# -------------------
# We match   " #(# TAG anything"   (one '#' before the '(')
# but NOT    " ##(# anything"      (two '#' before the '(')
#
# Why the distinction works:
#   ^[ \t]*   — consume leading spaces/tabs
#   #         — match the '#' that precedes '('
#   \(        — must be a literal '(' next
#   In "##(#…":  after spaces we have '#'; '#' matches, then '\(' expects
#                '(' but finds '#'  →  no match.  ✓
#   In " #(# SOV":  '#' matches, '\(' matches '(', '#' matches '#'.  ✓

_START_TMPL = r'^([ \t]*#\(#[ \t]+{tag}\b[^\n]*\n)'
_END_TMPL   = r'([ \t]*#\)#[ \t]+{tag}\b[^\n]*(?:\n|$))'


def extract_kr_sections(content: str, file_type: str) -> list[str]:
    """
    Find every  #(# TAG … #)# TAG  block in content.
    For each source tag present, generate a substituted copy for every
    KR target tag.  Returns a flat list of new section strings.

    Handles multiple occurrences of the same tag (e.g. two SOV blocks
    in geoplus_units_infantry.asset).
    """
    sections: list[str] = []

    for src_tag, dst_tags in TAG_MAPPINGS.items():
        s_pat = re.compile(_START_TMPL.format(tag=re.escape(src_tag)), re.MULTILINE)
        e_pat = re.compile(_END_TMPL.format(tag=re.escape(src_tag)),   re.MULTILINE)

        pos = 0
        while True:
            ms = s_pat.search(content, pos)
            if not ms:
                break

            me = e_pat.search(content, ms.end())
            if not me:
                print(f'    WARNING: unmatched  #(# {src_tag}  at offset {ms.start()}')
                pos = ms.end()
                continue

            block = content[ms.start(): me.end()]

            for dst_tag in dst_tags:
                sections.append(substitute(block, src_tag, dst_tag, file_type))

            pos = me.end()

    return sections


# ──────────────────────────────────────────────────────────────────────────────
# Per-file processing
# ──────────────────────────────────────────────────────────────────────────────

def process_file(src_rel: str, dst_rel: str, file_type: str, dry_run: bool) -> None:
    src_path = SOURCE_DIR / src_rel
    dst_path = OUTPUT_DIR / dst_rel

    if not src_path.exists():
        print(f'  SKIP — file not found: {src_path}')
        return

    content = src_path.read_text(encoding='utf-8')
    sections = extract_kr_sections(content, file_type)

    if not sections:
        print(f'  (no target-tag sections found — skipping)')
        return

    # Build a summary line: which KR tags were generated and how many blocks each
    tag_hits: dict[str, int] = {}
    for dst_tags in TAG_MAPPINGS.values():
        for dt in dst_tags:
            n = sum(
                1 for s in sections
                if re.search(r'#\(#[ \t]+' + re.escape(dt) + r'\b', s)
            )
            if n:
                tag_hits[dt] = n
    summary = ', '.join(f'{t}×{n}' for t, n in tag_hits.items())
    print(f'  sections: {summary}')

    # Assemble output
    header = '# Auto-generated by KR_convert.py — do not edit manually\n'
    body   = '\n'.join(sections) + '\n'

    if file_type == 'interface_gfx':
        output = header + 'spriteTypes = {\n' + body + '}\n'
    else:
        output = header + body

    if dry_run:
        print(f'  [DRY RUN] would write {len(output):,} chars → {dst_path.name}')
        return

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_text(output, encoding='utf-8')
    print(f'  written {len(output):,} chars → {dst_path.name}')


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    dry_run = '--dry-run' in sys.argv

    print('=' * 60)
    print('LampGeoPlus KR/KX Compatibility Generator')
    print('=' * 60)
    if dry_run:
        print('[DRY RUN — no files will be written]\n')
    print(f'Source : {SOURCE_DIR}')
    print(f'Output : {OUTPUT_DIR}\n')

    if not SOURCE_DIR.exists():
        print(f'ERROR: source directory not found:\n  {SOURCE_DIR}')
        sys.exit(1)

    for src_rel, dst_rel, file_type in PROCESS_FILES:
        print(f'[{file_type}] {Path(src_rel).name}')
        process_file(src_rel, dst_rel, file_type, dry_run)

    print('\nDone.')
    print(
        '\nNOTE: "LampGeoPlus KR" is a submod — it needs a descriptor.mod\n'
        'and should be loaded ALONGSIDE lampgeoplus_lite in the HOI4 launcher.\n'
        'The krkx_* files add KR/KX tag entries; the original files in the\n'
        'base mod continue to provide vanilla-tag content.'
    )


if __name__ == '__main__':
    main()
