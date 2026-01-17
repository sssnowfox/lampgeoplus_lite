import re
import shutil
from pathlib import Path

src = Path(r"c:\Users\Owner\OneDrive\Documents\Paradox Interactive\Hearts of Iron IV\mod\lampgeoplus_lite_local\gfx\interface\equipmentdesigner\graphic_db\00_dlcplus_plane_icons.txt")
backup = src.with_suffix(src.suffix + '.collapse_single.bak')
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

# pattern: models = { single_identifier }
pattern = re.compile(r"models\s*=\s*\{\s*([A-Za-z0-9_]+)\s*\}", flags=re.DOTALL)
new_block, count = pattern.subn(lambda m: f"models = {{ {m.group(1)} }}", default_block)

if count:
    new_text = text[:start] + new_block + text[end:]
    src.write_text(new_text, encoding='utf-8')
    print(f"Collapsed {count} single-entry models blocks in default (backup at {backup})")
else:
    print('No single-entry models blocks found to collapse')
