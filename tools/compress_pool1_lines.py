import re
from pathlib import Path

src = Path(r"c:\Users\Owner\OneDrive\Documents\Paradox Interactive\Hearts of Iron IV\mod\lampgeoplus_lite_local\gfx\interface\equipmentdesigner\graphic_db\00_dlcplus_tank_icons.txt")
backup = src.with_suffix(src.suffix + '.bak4')
if not backup.exists():
    import shutil
    shutil.copy2(src, backup)

text = src.read_text(encoding='utf-8')

def find_matching(s, i):
    """find matching closing brace"""
    level = 0
    for j in range(i, len(s)):
        if s[j] == '{':
            level += 1
        elif s[j] == '}':
            level -= 1
            if level == 0:
                return j
    return -1

def compress_block(block_str):
    """Compress icons/models block to single line, excluding comments"""
    m = re.search(r'(\w+)\s*=\s*\{', block_str)
    if not m:
        return block_str
    
    key = m.group(1)
    start = m.end() - 1
    end = find_matching(block_str, start)
    
    if end == -1:
        return block_str
    
    # Extract content between braces
    content = block_str[start+1:end].strip()
    
    # Split by lines and filter out comments
    lines = []
    for line in content.split('\n'):
        # Remove inline comments but keep non-comment lines
        clean_line = line.split('#')[0].strip()
        if clean_line:
            lines.append(clean_line)
    
    if not lines:
        return f"{key} = {{ }}"
    
    # Join into single line with spaces
    joined = ' '.join(lines)
    return f"{key} = {{ {joined} }}"

# Find and process all tank blocks
tank_pattern = r'(\w+_(?:tank|chassis)_\w+)\s*=\s*\{'
changed = 0

new_text = text
offset = 0

for m in re.finditer(tank_pattern, text):
    tank_name = m.group(1)
    start_pos = m.start()
    brace_start = m.end() - 1
    brace_end = find_matching(text, brace_start)
    
    if brace_end == -1:
        continue
    
    tank_block = text[start_pos:brace_end+1]
    
    # Find first pool
    pool_match = re.search(r'pool\s*=\s*\{', tank_block)
    if not pool_match:
        continue
    
    p1_start = pool_match.start()
    p1_brace = pool_match.end() - 1
    p1_end = find_matching(tank_block, p1_brace)
    
    if p1_end == -1:
        continue
    
    pool1 = tank_block[p1_start:p1_end+1]
    
    # Find icons block in pool1
    icons_match = re.search(r'icons\s*=\s*\{', pool1)
    if icons_match:
        icons_start = icons_match.start()
        icons_brace = icons_match.end() - 1
        icons_end = find_matching(pool1, icons_brace)
        if icons_end != -1:
            icons_block = pool1[icons_start:icons_end+1]
            compressed_icons = compress_block(icons_block)
            # Don't add extra indent - the compressed block goes on the same line where icons starts
            # Replace the entire block with compressed version
            pool1 = pool1[:icons_start] + compressed_icons + pool1[icons_end+1:]
    
    # Find models block in pool1 (note: positions may have changed after icons compression)
    models_match = re.search(r'models\s*=\s*\{', pool1)
    if models_match:
        models_start = models_match.start()
        models_brace = models_match.end() - 1
        models_end = find_matching(pool1, models_brace)
        if models_end != -1:
            models_block = pool1[models_start:models_end+1]
            compressed_models = compress_block(models_block)
            # Replace the entire block with compressed version
            pool1 = pool1[:models_start] + compressed_models + pool1[models_end+1:]
    
    # Replace in tank_block
    tank_new = tank_block[:p1_start] + pool1 + tank_block[p1_end+1:]
    
    # Replace in new_text with offset
    adj_start = start_pos + offset
    adj_end = adj_start + len(tank_block)
    new_text = new_text[:adj_start] + tank_new + new_text[adj_end:]
    offset += len(tank_new) - len(tank_block)
    changed += 1

if changed:
    src.write_text(new_text, encoding='utf-8')
    print(f"✅ Compressed {changed} pool1 blocks. Backup at {backup}")
else:
    print('No changes made')
