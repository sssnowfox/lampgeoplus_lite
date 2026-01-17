import re
import shutil
from pathlib import Path

src = Path(r"c:\Users\Owner\OneDrive\Documents\Paradox Interactive\Hearts of Iron IV\mod\lampgeoplus_lite_local\gfx\interface\equipmentdesigner\graphic_db\00_dlcplus_plane_icons.txt")
backup = src.with_suffix(src.suffix + '.whole.bak')
if not backup.exists():
    shutil.copy2(src, backup)

text = src.read_text(encoding='utf-8')

# helper to find matching brace from index of '{'

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

# find all occurrences of NAME = { ... }
items = []
for m in re.finditer(r"([A-Za-z0-9_]+)\s*=\s*\{", text):
    name = m.group(1)
    brace_idx = text.find('{', m.start())
    if brace_idx == -1:
        continue
    end = find_matching(text, brace_idx)
    if end == -1:
        continue
    items.append((name, m.start(), end+1))

changed = 0
new_text = text
# process in reverse order
for name, sidx, eidx in reversed(items):
    item_text = new_text[sidx:eidx]
    # extract inner starting at first '{'
    first_brace = item_text.find('{')
    inner = item_text[first_brace:]
    # find pool positions at level 1 inside inner
    pool_positions = []
    level = 0
    i = 0
    while i < len(inner):
        ch = inner[i]
        if ch == '{':
            level += 1
            i += 1
            continue
        if ch == '}':
            level -= 1
            i += 1
            continue
        # when at level 1, check for 'pool' token
        if level == 1 and inner.startswith('pool', i):
            # ensure 'pool' is a token
            after = i + 4
            # skip whitespace
            k = after
            while k < len(inner) and inner[k].isspace():
                k += 1
            if k < len(inner) and inner[k] == '=':
                # find the brace for this pool
                brace_pos = inner.find('{', k)
                if brace_pos != -1:
                    brace_end = find_matching(inner, brace_pos)
                    if brace_end != -1:
                        pool_positions.append((i, brace_pos, brace_end))
                        i = brace_end + 1
                        continue
        i += 1
    if len(pool_positions) != 2:
        continue
    # extract p1 and p2 full texts (relative to item_text)
    p1_rel_start = first_brace + pool_positions[0][0]
    p1_brace = first_brace + pool_positions[0][1]
    p1_rel_end = first_brace + pool_positions[0][2]
    p2_rel_start = first_brace + pool_positions[1][0]
    p2_brace = first_brace + pool_positions[1][1]
    p2_rel_end = first_brace + pool_positions[1][2]
    p1 = item_text[p1_rel_start:p1_rel_end+1]
    p2 = item_text[p2_rel_start:p2_rel_end+1]
    # find models block in p2
    m_model = re.search(r"models\s*=\s*\{", p2)
    if not m_model:
        continue
    m_brace = p2.find('{', m_model.start())
    m_end = find_matching(p2, m_brace)
    if m_end == -1:
        continue
    models_block = p2[m_model.start():m_end+1]
    models_content = p2[m_brace+1:m_end].strip()
    # split model names (by whitespace/newline), ignore empty and comments
    model_names = [ln.strip().split('#')[0].strip() for ln in re.split(r"\s+", models_content) if ln.strip()]
    to_move = [mn for mn in model_names if not re.search(r"_var_\d+", mn) and not re.search(r"var_\d+", mn)]
    if not to_move:
        continue
    # remaining in p2
    remaining = [mn for mn in model_names if mn not in to_move]
    # build new p2
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
        p2_new = re.sub(r"\n\s*models\s*=\s*\{[\s\S]*?\}", '', p2, count=1)
    # insert into p1 after icons block
    m_icons = re.search(r"icons\s*=\s*\{", p1)
    if m_icons:
        b = p1.find('{', m_icons.start())
        be = find_matching(p1, b)
        insert_pos = be + 1
    else:
        insert_pos = len(p1)-1
    # if p1 has models, append unique
    if re.search(r"models\s*=\s*\{", p1):
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
        # determine indent from p1 lines
        lines = p1.splitlines()
        indent = '                '
        if len(lines) > 1:
            # find indentation of second line as a guess
            m_ind = re.match(r"(\s*)", lines[1])
            if m_ind:
                indent = m_ind.group(1)
        if len(to_move) == 1:
            models_text = '\n' + indent + 'models = { ' + to_move[0] + ' }'
        else:
            models_text = '\n' + indent + 'models = {\n'
            for mn in to_move:
                models_text += indent + '    ' + mn + '\n'
            models_text += indent + '}'
        p1_new = p1[:insert_pos] + models_text + p1[insert_pos:]
    # build new item_text
    item_new = item_text[:p1_rel_start] + p1_new + item_text[p1_rel_end+1:p2_rel_start] + p2_new + item_text[p2_rel_end+1:]
    new_text = new_text[:sidx] + item_new + new_text[eidx:]
    changed += 1

# after all moves, collapse single-entry models blocks across whole file
pattern = re.compile(r"models\s*=\s*\{\s*([A-Za-z0-9_]+)\s*\}", flags=re.DOTALL)
new_text2, cnt = pattern.subn(lambda m: f"models = {{ {m.group(1)} }}", new_text)

if changed or cnt:
    src.write_text(new_text2, encoding='utf-8')
    print(f"Applied transformations: moved in {changed} items, collapsed {cnt} single-entry models. Backup at {backup}")
else:
    print('No changes applied')
