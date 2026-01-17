import re
import shutil
from pathlib import Path

src = Path(r"c:\Users\Owner\OneDrive\Documents\Paradox Interactive\Hearts of Iron IV\mod\lampgeoplus_lite_local\gfx\interface\equipmentdesigner\graphic_db\00_dlcplus_tank_icons.txt")
backup = src.with_suffix(src.suffix + '.bak')
if not backup.exists():
    shutil.copy2(src, backup)

text = src.read_text(encoding='utf-8')

# find default = { block
m = re.search(r"default\s*=\s*\{", text)
if not m:
    print('default block not found')
    raise SystemExit(1)

start = m.start()
idx = m.end()
level = 1
while idx < len(text) and level > 0:
    if text[idx] == '{':
        level += 1
    elif text[idx] == '}':
        level -= 1
    idx += 1
end = idx
default_block = text[start:end]
body = default_block

def find_matching(s, i):
    """find matching closing brace given opening brace position"""
    level = 0
    for j in range(i, len(s)):
        if s[j] == '{':
            level += 1
        elif s[j] == '}':
            level -= 1
            if level == 0:
                return j
    return -1

def is_pow2(n):
    return n and (n & (n - 1)) == 0

# parse tank type items inside default block
items = []  # list of tuples (name, start_idx, end_idx)
pos = body.find('{') + 1
L = len(body)
while pos < L:
    if body[pos].isspace():
        pos += 1
        continue
    m = re.match(r"([A-Za-z0-9_]+)\s*=\s*\{", body[pos:])
    if not m:
        pos += 1
        continue
    name = m.group(1)
    item_start = pos + m.start()
    brace_start = pos + m.end() - 1
    brace_end = find_matching(body, brace_start)
    if brace_end == -1:
        break
    item_end = brace_end + 1
    items.append((name, item_start, item_end))
    pos = item_end

changed = 0
new_body = body

print(f"Found {len(items)} tank types")

# iterate items in reverse so replacements don't shift indices
for idx, (name, sidx, eidx) in enumerate(reversed(items)):
    item_text = new_body[sidx:eidx]
    
    # find pool = { occurrences
    pool_positions = [m.start() for m in re.finditer(r"pool\s*=\s*\{", item_text)]
    if len(pool_positions) != 2:
        continue
    
    if "SWE_light" in name:
        print(f"DEBUG: Processing {name}, found {len(pool_positions)} pools")
    
    # get actual pool blocks
    p1_start = pool_positions[0]
    p1_brace = item_text.find('{', p1_start)
    p1_end = find_matching(item_text, p1_brace)
    
    p2_start = pool_positions[1]
    p2_brace = item_text.find('{', p2_start)
    p2_end = find_matching(item_text, p2_brace)
    
    if p1_end == -1 or p2_end == -1:
        continue
    
    p1 = item_text[p1_start:p1_end+1]
    p2 = item_text[p2_start:p2_end+1]
    
    # extract models in p2
    m_model = re.search(r"models\s*=\s*\{", p2)
    if not m_model:
        continue
    
    m_br = p2.find('{', m_model.start())
    m_end = find_matching(p2, m_br)
    models_content = p2[m_br+1:m_end].strip()
    
    # split model names
    model_names = [ln.strip().split('#')[0].strip() for ln in re.split(r"\s+", models_content) if ln.strip()]
    
    # separate non-alt and alt models
    non_alt = [mn for mn in model_names if not re.search(r"_alt_\d+", mn)]
    alt = [mn for mn in model_names if re.search(r"_alt_\d+", mn)]
    
    if not non_alt:
        # nothing to move
        continue
    
    # p1: add non-alt models
    if re.search(r"models\s*=\s*\{", p1):
        # p1 already has models, append unique non-alt
        mm = re.search(r"models\s*=\s*\{", p1)
        b_p1 = p1.find('{', mm.start())
        e_p1 = find_matching(p1, b_p1)
        existing = p1[b_p1+1:e_p1].strip()
        existing_names = [ln.strip().split('#')[0].strip() for ln in re.split(r"\s+", existing) if ln.strip()]
        merged = existing_names[:]
        for mn in non_alt:
            if mn not in merged:
                merged.append(mn)
        if len(merged) == 1:
            new_models_p1 = 'models = { ' + merged[0] + ' }'
        else:
            new_models_p1 = 'models = {\n'
            for m in merged:
                new_models_p1 += '                    ' + m + '\n'
            new_models_p1 += '                }'
        p1_new = p1[:mm.start()] + new_models_p1 + p1[e_p1+1:]
    else:
        # p1 doesn't have models, create new block
        indent = '                '
        if len(non_alt) == 1:
            models_text = '\n' + indent + 'models = { ' + non_alt[0] + ' }'
        else:
            models_text = '\n' + indent + 'models = {\n'
            for mn in non_alt:
                models_text += indent + '    ' + mn + '\n'
            models_text += indent + '}'
        # insert after icons block if exists, otherwise at start of p1 body
        m_icons = re.search(r"icons\s*=\s*\{", p1)
        if m_icons:
            b_icons = p1.find('{', m_icons.start())
            e_icons = find_matching(p1, b_icons)
            insert_pos = e_icons + 1
        else:
            insert_pos = p1.find('{') + 1
        p1_new = p1[:insert_pos] + models_text + p1[insert_pos:]
    
    # p2: keep only alt models
    if alt:
        if len(alt) == 1:
            new_models_p2 = 'models = { ' + alt[0] + ' }'
        else:
            new_models_p2 = 'models = {\n'
            for m in alt:
                new_models_p2 += '                    ' + m + '\n'
            new_models_p2 += '                }'
        p2_new = re.sub(r"models\s*=\s*\{[\s\S]*?\}", new_models_p2, p2, count=1)
    else:
        # remove models block entirely if no alt models
        p2_new = re.sub(r"\n\s*models\s*=\s*\{[\s\S]*?\}", '', p2, count=1)
    
    # replace both pools in item_text
    item_new = item_text[:p1_start] + p1_new + item_text[p1_end+1:p2_start] + p2_new + item_text[p2_end+1:]
    new_body = new_body[:sidx] + item_new + new_body[eidx:]
    changed += 1

if changed:
    new_default = new_body
    new_text = text[:start] + new_default + text[end:]
    src.write_text(new_text, encoding='utf-8')
    print(f"Modified {changed} tank types. Backup at {backup}")
else:
    print('No changes made')
