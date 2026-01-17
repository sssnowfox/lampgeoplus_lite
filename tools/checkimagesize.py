import os
import struct
import sys

"""
checkimagesize.py

递归扫描指定文件夹（或当前文件夹）下的 .dds 文件，读取 DDS 头部宽高，
并列出宽或高不是 2 的幂的文件。

用法:
    python checkimagesize.py [path]

如果未提供路径，则使用当前工作目录。
"""


def get_dds_size(path):
    try:
        with open(path, 'rb') as f:
            if f.read(4) != b'DDS ':
                return None, None, "NotDDS"
            f.seek(12)
            height = struct.unpack('<I', f.read(4))[0]
            width = struct.unpack('<I', f.read(4))[0]
            return width, height, None
    except Exception as e:
        return None, None, str(e)


def is_pow2(n):
    return n and (n & (n - 1)) == 0


def scan_folder(root):
    non_pow2 = []
    unreadable = []
    scanned = 0

    for r, _, files in os.walk(root):
        for fn in files:
            if fn.lower().endswith('.dds'):
                scanned += 1
                fp = os.path.join(r, fn)
                w, h, err = get_dds_size(fp)
                if err:
                    unreadable.append((os.path.relpath(fp, root), err))
                    continue
                if not (is_pow2(w) and is_pow2(h)):
                    non_pow2.append((os.path.relpath(fp, root), w, h))

    return scanned, non_pow2, unreadable


def main():
    # 默认扫描路径（用户指定的路径）
    DEFAULT_ROOT = r"C:\Users\Owner\OneDrive\Documents\Paradox Interactive\Hearts of Iron IV\mod\lampgeoplus_lite_local\gfx\models\units\planes"

    root = DEFAULT_ROOT
    if len(sys.argv) > 1:
        root = sys.argv[1]
        if not os.path.isdir(root):
            print(f"指定路径不存在: {root}")
            sys.exit(1)

    print(f"Scanning: {root}")
    scanned, non_pow2, unreadable = scan_folder(root)

    print(f"\n已扫描 DDS 文件: {scanned}\n")

    if non_pow2:
        print(f"发现 {len(non_pow2)} 个宽或高不是 2 的幂的文件:")
        for name, w, h in non_pow2:
            print(f" - {name}  => {w}x{h}")
    else:
        print("✅ 所有 DDS 的宽高均为 2 的幂。")

    if unreadable:
        print('\n无法读取头部的文件:')
        for name, err in unreadable:
            print(f" - {name}  ({err})")


if __name__ == '__main__':
    main()
