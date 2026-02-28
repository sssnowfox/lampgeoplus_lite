#!/usr/bin/env python3
"""
KR_convert.py  —  LampGeoPlus KR/KX Compatibility Generator
=============================================================

Copies the base mod's text files to the output folder, inserting KR/KX
tag sections immediately after each vanilla tag section.

Each output file (xkr_*) is a complete copy of the source file with KR
additions inline, e.g.:

    #(# SOV Start        ← original, kept as-is
        SOV = { … }
    #)# SOV End
    #(# RUS Start        ← inserted by this script
        RUS = { … }
    #)# RUS End
    #(# TRM Start
        TRM = { … }
    #)# TRM End

Usage:
    python KR_convert.py             # generate output files
    python KR_convert.py --dry-run   # preview only, no files written

Substitution rules by file type
────────────────────────────────
  graphic_db (.txt)  : substitute everywhere; skip quoted strings with '/'
  asset      (.asset): same, plus skip quoted values of  pdxmesh / soundeffect
  interface_gfx (.gfx): same as graphic_db (original file already has wrapper)

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
     'gfx/interface/equipmentdesigner/graphic_db/xkr_dlcplus_plane_icons.txt',
     'graphic_db'),

    ('gfx/interface/equipmentdesigner/graphic_db/#_dlcplus_tank_icons.txt',
     'gfx/interface/equipmentdesigner/graphic_db/xkr_dlcplus_tank_icons.txt',
     'graphic_db'),

    ('gfx/interface/equipmentdesigner/graphic_db/#_dlcplus_ship_icons.txt',
     'gfx/interface/equipmentdesigner/graphic_db/xkr_dlcplus_ship_icons.txt',
     'graphic_db'),

    ('gfx/interface/equipmentdesigner/graphic_db/#_geoplus_plane_icons.txt',
     'gfx/interface/equipmentdesigner/graphic_db/xkr_geoplus_plane_icons.txt',
     'graphic_db'),

    ('gfx/interface/equipmentdesigner/graphic_db/#_geoplus_tank_icons.txt',
     'gfx/interface/equipmentdesigner/graphic_db/xkr_geoplus_tank_icons.txt',
     'graphic_db'),

    # ── Category 2 : entity definitions (.asset) ──────────────────────────────

    ('gfx/entities/mod_replacement/geoplus_units_planes.asset',
     'gfx/entities/mod_replacement/xkr_geoplus_units_planes.asset',
     'asset'),

    ('gfx/entities/mod_replacement/geoplus_units_tanks.asset',
     'gfx/entities/mod_replacement/xkr_geoplus_units_tanks.asset',
     'asset'),

    ('gfx/entities/mod_replacement/geoplus_units_ships.asset',
     'gfx/entities/mod_replacement/xkr_geoplus_units_ships.asset',
     'asset'),

    ('gfx/entities/mod_replacement/geoplus_units_infantry.asset',
     'gfx/entities/mod_replacement/xkr_geoplus_units_infantry.asset',
     'asset'),

    ('gfx/entities/mod_replacement/geoplus_units_vehicles.asset',
     'gfx/entities/mod_replacement/xkr_geoplus_units_vehicles.asset',
     'asset'),

    ('gfx/entities/mod_replacement/reskindlc_units_planes.asset',
     'gfx/entities/mod_replacement/xkr_reskindlc_units_planes.asset',
     'asset'),

    ('gfx/entities/mod_replacement/reskindlc_units_tanks.asset',
     'gfx/entities/mod_replacement/xkr_reskindlc_units_tanks.asset',
     'asset'),

    ('gfx/entities/mod_replacement/reskindlc_units_ships.asset',
     'gfx/entities/mod_replacement/xkr_reskindlc_units_ships.asset',
     'asset'),

    ('gfx/entities/mod_replacement/reskindlc_units_vehicles.asset',
     'gfx/entities/mod_replacement/xkr_reskindlc_units_vehicles.asset',
     'asset'),

    ('gfx/entities/mod_replacement/appendplus_units_planes.asset',
     'gfx/entities/mod_replacement/xkr_appendplus_units_planes.asset',
     'asset'),

    # ── Category 4 : interface sprites (blueprint overlays excluded) ──────────

    ('interface/mod_replacement/lampplus_plane_tech.gfx',
     'interface/mod_replacement/xkr_lampplus_plane_tech.gfx',
     'interface_gfx'),

    ('interface/mod_replacement/lampplus_tank_tech.gfx',
     'interface/mod_replacement/xkr_lampplus_tank_tech.gfx',
     'interface_gfx'),

    ('interface/mod_replacement/lampplus_naval_tech.gfx',
     'interface/mod_replacement/xkr_lampplus_naval_tech.gfx',
     'interface_gfx'),

    ('interface/mod_replacement/lampplus_inf_art_sup.gfx',
     'interface/mod_replacement/xkr_lampplus_inf_art_sup.gfx',
     'interface_gfx'),
]

# Quoted values of these keys are kept unchanged in .asset files
ASSET_SKIP_KEYS: frozenset[str] = frozenset({'pdxmesh', 'soundeffect'})
_ASSET_SKIP_RE = re.compile(
    r'\b(?:' + '|'.join(re.escape(k) for k in ASSET_SKIP_KEYS) + r')\s*=\s*$'
)

# Matches unquoted soundeffect values, e.g.  soundeffect = ITA_light_armour_fire
# Group 1 captures the sound name token (no quotes, braces, or whitespace)
_UNQUOTED_SOUND_RE = re.compile(r'\bsoundeffect\s*=\s*([^\s"{}]+)')

# ──────────────────────────────────────────────────────────────────────────────
# Substitution
# ──────────────────────────────────────────────────────────────────────────────

def _replace_skip_prototype(text: str, src: str, dst: str) -> str:
    """Replace src→dst in unquoted text, but skip any token containing 'prototype'."""
    return ''.join(
        p if 'prototype' in p else p.replace(src, dst)
        for p in re.split(r'(\S+)', text)
    )


def _replace_unquoted_asset(text: str, src: str, dst: str) -> str:
    """Like _replace_skip_prototype but also skips unquoted soundeffect values.

    Handles cases like:
        sound = { soundeffect = ITA_light_armour_fire }
    where the sound name is unquoted and must not be tag-substituted.
    """
    result: list[str] = []
    pos = 0
    for m in _UNQUOTED_SOUND_RE.finditer(text):
        # Process the text before this match normally
        result.append(_replace_skip_prototype(text[pos:m.start()], src, dst))
        # Keep 'soundeffect = ' (the key portion) but preserve the sound name token
        key_part = text[m.start():m.start(1)]   # e.g. 'soundeffect = '
        sound_val = m.group(1)                  # e.g. 'ITA_light_armour_fire'
        result.append(_replace_skip_prototype(key_part, src, dst))
        result.append(sound_val)                # sound name kept as-is
        pos = m.end()
    # Process any remaining text after the last match
    result.append(_replace_skip_prototype(text[pos:], src, dst))
    return ''.join(result)


def substitute(text: str, src: str, dst: str, file_type: str) -> str:
    """
    Replace every occurrence of src with dst in text, respecting these rules:

    • Quoted strings containing '/'  →  kept as-is  (filesystem paths)
    • In 'asset' mode: quoted values of pdxmesh / soundeffect  →  kept as-is
    • In 'asset' mode: unquoted soundeffect values  →  kept as-is
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
            # Unquoted text — substitute, respecting file-type rules
            if file_type == 'asset':
                result.append(_replace_unquoted_asset(part, src, dst))
            else:
                result.append(_replace_skip_prototype(part, src, dst))
        else:
            # Inside a quoted string
            # Rule 1: file paths (contain '/') → preserve
            if '/' in part:
                result.append(f'"{part}"')
                continue

            # Rule 2: prototype GFX / entity names → preserve
            if 'prototype' in part:
                result.append(f'"{part}"')
                continue

            # Rule 3 (asset only): value of pdxmesh / soundeffect → preserve
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


def extract_kr_sections(content: str, file_type: str) -> tuple[str, dict[str, int]]:
    """
    Find every  #(# TAG … #)# TAG  block in content.
    For each source tag, generate substituted copies for every KR target tag.

    Returns ONLY the new KR/KX sections as a single string (original vanilla
    blocks are NOT included — they already exist in the source #_dlcplus file).
    """
    sections: list[str] = []
    tag_hits: dict[str, int] = {}

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
                tag_hits[dst_tag] = tag_hits.get(dst_tag, 0) + 1

            pos = me.end()

    return ''.join(sections), tag_hits


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
    output, tag_hits = extract_kr_sections(content, file_type)

    if not tag_hits:
        print(f'  (no target-tag sections found — skipping)')
        return

    # .gfx files need the top-level spriteTypes wrapper
    if file_type == 'interface_gfx':
        output = 'spriteTypes = {\n' + output + '}\n'

    summary = ', '.join(f'{t}×{n}' for t, n in tag_hits.items())
    print(f'  inserted: {summary}')

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
        '\nNOTE: each xkr_* file contains ONLY the new KR/KX sections.\n'
        'The original vanilla-tag sections (SOV, ENG, etc.) remain in\n'
        'the source #_dlcplus / geoplus files and are NOT duplicated here.\n'
        'Remember to create a descriptor.mod in the output folder.'
    )


if __name__ == '__main__':
    main()
