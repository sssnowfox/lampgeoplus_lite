import re
import shutil
from pathlib import Path

src = Path(r"c:\Users\Owner\OneDrive\Documents\Paradox Interactive\Hearts of Iron IV\mod\lampgeoplus_lite_local\gfx\interface\equipmentdesigner\graphic_db\00_dlcplus_tank_icons.txt")
backup = src.with_suffix(src.suffix + '.bak')
if not backup.exists():
    shutil.copy2(src, backup)

text = src.read_text(encoding='utf-8')

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

# find all tank type blocks that have exactly 2 pools
# Pattern: tankname = { ... pool ... pool ... }
changed = 0
new_text = text
offset = 0  # track cumulative offset from replacements

# Find all potential tank blocks
tank_pattern = r'(\w+_(?:tank|chassis)_\w+)\s*=\s*\{'
for m in re.finditer(tank_pattern, text):
    tank_name = m.group(1)
    start_pos = m.start()
    brace_start = m.end() - 1
    
    # Find closing brace
    brace_end = find_matching(text, brace_start)
    if brace_end == -1:
        continue
    
    tank_block = text[start_pos:brace_end+1]
    
    # Count pools
    pool_matches = list(re.finditer(r'pool\s*=\s*\{', tank_block))
    if len(pool_matches) != 2:
        continue
    
    # Get pool positions
    p1_start_in_block = pool_matches[0].start()
    p1_brace_in_block = pool_matches[0].end() - 1
    p1_end_in_block = find_matching(tank_block, p1_brace_in_block)
    
    p2_start_in_block = pool_matches[1].start()
    p2_brace_in_block = pool_matches[1].end() - 1
    p2_end_in_block = find_matching(tank_block, p2_brace_in_block)
    
    if p1_end_in_block == -1 or p2_end_in_block == -1:
        continue
    
    p1 = tank_block[p1_start_in_block:p1_end_in_block+1]
    p2 = tank_block[p2_start_in_block:p2_end_in_block+1]
    
    # Check if p2 has models
    m_model = re.search(r'models\s*=\s*\{', p2)
    if not m_model:
        continue
    
    # Extract models from p2
    m_br = p2.find('{', m_model.start())
    m_end = find_matching(p2, m_br)
    models_content = p2[m_br+1:m_end].strip()
    
    # Parse model names
    model_names = [ln.strip().split('#')[0].strip() for ln in re.split(r'\s+', models_content) if ln.strip()]
    
    # Separate alt and non-alt
    non_alt = [mn for mn in model_names if not re.search(r'_alt_\d+', mn)]
    alt = [mn for mn in model_names if re.search(r'_alt_\d+', mn)]
    
    if not non_alt:
        continue
    
    print(f"Processing {tank_name}: found non_alt={non_alt}, alt={alt}")
    
    # Now rebuild the tank block
    # Pool 1: add non-alt models
    if re.search(r'models\s*=\s*\{', p1):
        # merge
        mm = re.search(r'models\s*=\s*\{', p1)
        b_p1 = p1.find('{', mm.start())
        e_p1 = find_matching(p1, b_p1)
        existing = p1[b_p1+1:e_p1].strip()
        existing_names = [ln.strip().split('#')[0].strip() for ln in re.split(r'\s+', existing) if ln.strip()]
        merged = existing_names[:]
        for mn in non_alt:
            if mn not in merged:
                merged.append(mn)
        if len(merged) == 1:
            new_models = 'models = { ' + merged[0] + ' }'
        else:
            new_models = 'models = {\n' + '\n'.join([' ' * 20 + m for m in merged]) + '\n' + ' ' * 16 + '}'
        p1_new = p1[:mm.start()] + new_models + p1[e_p1+1:]
    else:
        # create new
        indent = ' ' * 16
        if len(non_alt) == 1:
            models_text = '\n' + indent + 'models = { ' + non_alt[0] + ' }'
        else:
            models_text = '\n' + indent + 'models = {\n' + '\n'.join([' ' * 20 + m for m in non_alt]) + '\n' + indent + '}'
        m_icons = re.search(r'icons\s*=\s*\{', p1)
        if m_icons:
            b_icons = p1.find('{', m_icons.start())
            e_icons = find_matching(p1, b_icons)
            insert_pos = e_icons + 1
        else:
            insert_pos = p1.find('{') + 1
        p1_new = p1[:insert_pos] + models_text + p1[insert_pos:]
    
    # Pool 2: keep only alt
    if alt:
        if len(alt) == 1:
            new_models_p2 = 'models = { ' + alt[0] + ' }'
        else:
            new_models_p2 = 'models = {\n' + '\n'.join([' ' * 20 + m for m in alt]) + '\n' + ' ' * 16 + '}'
        p2_new = re.sub(r'models\s*=\s*\{[\s\S]*?\}', new_models_p2, p2, count=1)
    else:
        p2_new = re.sub(r'\n\s*models\s*=\s*\{[\s\S]*?\}', '', p2, count=1)
    
    # Rebuild tank block
    tank_new = tank_block[:p1_start_in_block] + p1_new + tank_block[p1_end_in_block+1:p2_start_in_block] + p2_new + tank_block[p2_end_in_block+1:]
    
    # Replace in the main text (accounting for offset)
    adj_start = start_pos + offset
    adj_end = adj_start + len(tank_block)
    new_text = new_text[:adj_start] + tank_new + new_text[adj_end:]
    offset += len(tank_new) - len(tank_block)
    changed += 1

if changed:
    src.write_text(new_text, encoding='utf-8')
    print(f"\n✅ Modified {changed} tank types. Backup at {backup}")
else:
    print('No changes made')
