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
# find matching closing brace for default
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

# helper to find matching brace in a substring given start index

def find_matching(s, i):
    level = 0
    for j in range(i, len(s)):
        if s[j] == '{':
            level += 1
        elif s[j] == '}':
            level -= 1
            if level == 0:
                return j
    return -1

# parse top-level items inside default: scan chars
items = []  # list of tuples (name, start_idx_in_body, end_idx_in_body)
pos = body.find('{') + 1  # position after 'default = {'
L = len(body)
while pos < L:
    # skip whitespace and comments
    if body[pos].isspace():
        pos += 1
        continue
    # find possible identifier
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
# iterate items in reverse so replacements don't shift indices
for name, sidx, eidx in reversed(items):
    item_text = new_body[sidx:eidx]
    # find pool = { occurrences
    pool_positions = [m.start() for m in re.finditer(r"pool\s*=\s*\{", item_text)]
    if len(pool_positions) != 2:
        continue
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
    models_block = p2[m_model.start():m_end+1]
    models_content = p2[m_br+1:m_end].strip()
    # split model names by whitespace/newlines, ignoring comments and empty lines
    model_names = [ln.strip().split('#')[0].strip() for ln in re.split(r"\s+", models_content) if ln.strip()]
    # filter out alt_\d
    to_move = [mn for mn in model_names if not re.search(r"_alt_\d+", mn) and not re.search(r"alt_\d+", mn)]
    if not to_move:
        continue
    # remove to_move from p2 models
    remaining = [mn for mn in model_names if mn not in to_move]
    # build new models block for p2
    if remaining:
        if len(remaining) == 1:
            new_models_p2 = 'models = { ' + remaining[0] + ' }'
        else:
            new_models_p2 = 'models = {\n'
            for mn in remaining:
                new_models_p2 += '                    ' + mn + '\n'
            new_models_p2 += '                }'
        p2_new = re.sub(r"models\s*=\s*\{[\s\S]*?\}", new_models_p2, p2, count=1)
    else:
        # remove entire models = { ... } line/block
        p2_new = re.sub(r"\n\s*models\s*=\s*\{[\s\S]*?\}", '', p2, count=1)
    # insert or merge into p1 after icons = { ... }
    m_icons = re.search(r"icons\s*=\s*\{", p1)
    if not m_icons:
        # if no icons, append models at start of p1
        insert_pos = 0
    else:
        b = p1.find('{', m_icons.start())
        be = find_matching(p1, b)
        insert_pos = be + 1
    # check if p1 already has models
    if re.search(r"models\s*=\s*\{", p1):
        # append unique to existing models
        def append_to_models(p1_text, adds):
            mm = re.search(r"models\s*=\s*\{", p1_text)
            b2 = p1_text.find('{', mm.start())
            e2 = find_matching(p1_text, b2)
            existing = p1_text[b2+1:e2].strip()
            existing_names = [ln.strip().split('#')[0].strip() for ln in re.split(r"\s+", existing) if ln.strip()]
            merged = existing_names[:]
            for a in adds:
                if a not in merged:
                    merged.append(a)
            if len(merged) == 1:
                new_block = 'models = { ' + merged[0] + ' }'
            else:
                new_block = 'models = {\n'
                for mn in merged:
                    new_block += '                    ' + mn + '\n'
                new_block += '                }'
            return p1_text[:mm.start()] + new_block + p1_text[e2+1:]
        p1_new = append_to_models(p1, to_move)
    else:
        # create models block with proper indentation
        indent = '                '
        if len(to_move) == 1:
            models_text = '\n' + indent + 'models = { ' + to_move[0] + ' }'
        else:
            models_text = '\n' + indent + 'models = {\n'
            for mn in to_move:
                models_text += indent + '    ' + mn + '\n'
            models_text += indent + '}'
        p1_new = p1[:insert_pos] + models_text + p1[insert_pos:]
    # replace p1 and p2 in item_text
    item_new = item_text[:p1_start] + p1_new + item_text[p1_end+1:p2_start] + p2_new + item_text[p2_end+1:]
    # put back into new_body
    new_body = new_body[:sidx] + item_new + new_body[eidx:]
    changed += 1

if changed:
    new_default = new_body
    new_text = text[:start] + new_default + text[end:]
    src.write_text(new_text, encoding='utf-8')
    print(f"Modified {changed} items in default block. Backup at {backup}")
else:
    print('No changes made')
