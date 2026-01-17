import os
import struct
import sys

# --- 配置路径 ---
#root_folder = r"C:\Users\Owner\OneDrive\Documents\Paradox Interactive\Hearts of Iron IV\mod\lampgeoplus_lite_local\gfx\models\units"
#root_folder = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\394360\3132985068\gfx\models\units"
root_folder = r"C:\Users\Owner\OneDrive\Documents\Paradox Interactive\Hearts of Iron IV\mod\GEO_ww2_model_local\gfx"
# ---------------

def get_dds_info(file_path):
    """
    读取 DDS 文件的 Mipmap 数量、压缩格式以及宽高
    """
    try:
        with open(file_path, 'rb') as f:
            # 1. 验证 Magic Number
            if f.read(4) != b'DDS ':
                return None, "Not DDS", False, False, None, None

            # 2. 读取高度/宽度和 Mipmap 数量
            # height 在文件偏移 12, width 在 16, mipmap 在 28 (以字节为单位，文件从 0 开始)
            f.seek(12)
            height = struct.unpack('<I', f.read(4))[0]
            width = struct.unpack('<I', f.read(4))[0]
            f.seek(28)
            mip_data = f.read(4)
            mipmap_count = struct.unpack('<I', mip_data)[0]

            # 3. 读取像素格式 (ddspf starts at 80, dwFourCC is at 84)
            f.seek(84)
            fourcc = f.read(4)

            format_name = "Unknown"
            is_bc1 = False
            is_bc3 = False

            # 判断 DXT1/DXT5 (Legacy)
            if fourcc == b'DXT1':
                format_name = "DXT1 (BC1)"
                is_bc1 = True
            elif fourcc == b'DXT5':
                format_name = "DXT5 (BC3)"
                is_bc3 = True
            
            # 判断 DX10 扩展头 (BC1/BC3/BC5/BC7 etc.)
            elif fourcc == b'DX10':
                # DX10 header 位于 128 字节处
                f.seek(128)
                dxgi_format = struct.unpack('<I', f.read(4))[0]

                # DXGI_FORMAT_BC1_UNORM = 71 (and variants), BC3 = 77, BC5 = 83, BC7 = 98
                if dxgi_format in [70, 71, 72]:
                    format_name = "BC1 (DX10)"
                    is_bc1 = True
                elif dxgi_format == 77:
                    format_name = "BC3/DXT5 (DX10)"
                    is_bc3 = True
                elif dxgi_format == 83:
                    format_name = "BC5"
                elif dxgi_format == 98:
                    format_name = "BC7"
                else:
                    format_name = f"DXGI_{dxgi_format}"
            else:
                try:
                    format_name = fourcc.decode('utf-8', errors='ignore')
                except:
                    format_name = str(fourcc)

            return mipmap_count, format_name, is_bc1, is_bc3, width, height

    except Exception as e:
        return None, f"Error: {e}", False, False, None, None

def run_post_check():
    print(f"🕵️  正在质检: {root_folder}")
    print("---------------------------------------------------")

    missing_mips = []
    not_bc1_diffuse = [] # 重点检查：本来应该是BC1但是却不是的文件
    not_bc1_others = []  # 普通检查：法线等文件
    bc3_diffuse = []     # 新：列出属于 BC3/DXT5 的 diffuse 文件
    non_pow2 = []        # 列出宽或高不是 2 的幂次的文件

    scanned_count = 0

    for root, dirs, files in os.walk(root_folder):
        for filename in files:
            if filename.lower().endswith(".dds"):
                scanned_count += 1
                file_path = os.path.join(root, filename)
                
                mips, fmt, is_bc1, is_bc3, width, height = get_dds_info(file_path)

                if mips is None:
                    print(f"⚠️  无法读取: {filename} ({fmt})")
                    continue

                # 检查逻辑 1: 是否缺少 Mipmaps (所有文件都必须有)
                if mips <= 1:
                    missing_mips.append((filename, fmt))

                # 检查逻辑 X: 宽高是否为 2 的幂
                def is_pow2(n):
                    return n and (n & (n - 1)) == 0

                if width is None or height is None:
                    # 无法读取宽高，跳过此检查
                    pass
                else:
                    if not (is_pow2(width) and is_pow2(height)):
                        non_pow2.append((filename, width, height))

                # 检查逻辑 2: 是否不是 BC1
                if not is_bc1:
                    if "_diffuse" in filename.lower():
                        # 这是严重问题：Diffuse贴图不是BC1，体积会大
                        not_bc1_diffuse.append((filename, fmt))
                    else:
                        # 这是正常现象：法线/高光贴图本来就不该是BC1
                        not_bc1_others.append((filename, fmt))

                # 额外收集：哪些 diffuse 是 BC3/DXT5（无论是否属于 DX10）
                if is_bc3 and "_diffuse" in filename.lower():
                    bc3_diffuse.append((filename, fmt))

    # --- 输出报告 ---
    print(f"\n✅ 扫描完成，共检查 {scanned_count} 个文件。\n")

    # 1. 汇报 Mipmap 缺失 (最重要，必须修)
    if missing_mips:
        print(f"🔴 [严重警告] 发现 {len(missing_mips)} 个文件缺少 Mipmaps (会导致闪烁):")
        for name, f_fmt in missing_mips:
            print(f"   - {name} [格式: {f_fmt}]")
    else:
        print("✅ Mipmaps 检查通过：所有文件均包含 Mipmaps。")

    print("-" * 30)

    # 2. 汇报 Diffuse 格式错误 (建议修)
    if not_bc1_diffuse:
        print(f"🟠 [警告] 发现 {len(not_bc1_diffuse)} 个 Diffuse 贴图不是 BC1 格式 (建议压缩):")
        for name, f_fmt in not_bc1_diffuse:
            print(f"   - {name} [当前: {f_fmt}]")
    else:
        print("✅ Diffuse 格式检查通过：所有 _diffuse 均为 BC1/DXT1。")

    print("-" * 30)

    # 3. 信息展示其他文件
    if not_bc1_others:
        print(f"ℹ️  发现 {len(not_bc1_others)} 个非 BC1 文件 (法线/高光/未知 - 通常无需处理):")
        # 仅显示前5个作为示例，避免刷屏
        for i, (name, f_fmt) in enumerate(not_bc1_others):
            if i < 5:
                print(f"   - {name} [{f_fmt}]")
        if len(not_bc1_others) > 5:
            print(f"   ... 以及其他 {len(not_bc1_others) - 5} 个文件")

    # 3. 列出属于 BC3/DXT5 的 diffuse（可帮助排查误压缩为 BC3 的 diffuse）
    print("-" * 30)
    if bc3_diffuse:
        print(f"🔵 发现 {len(bc3_diffuse)} 个 _diffuse 为 BC3/DXT5：")
        for name, f_fmt in bc3_diffuse:
            print(f"   - {name} [当前: {f_fmt}]")
    else:
        print("✅ 未发现 _diffuse 为 BC3/DXT5 的文件。")

    print("-" * 30)
    if non_pow2:
        print(f"🚨 发现 {len(non_pow2)} 个文件的宽或高不是 2 的幂：")
        for name, w, h in non_pow2:
            print(f"   - {name} [{w}x{h}] —— 建议: 调整为 2 的幂（例如 512x128）")
    else:
        print("✅ 所有 DDS 的宽高均为 2 的幂。")

if __name__ == "__main__":
    # 支持从命令行传入路径
    if len(sys.argv) > 1:
        root = sys.argv[1]
        if os.path.isdir(root):
            root_folder = root
        else:
            print(f"指定路径不存在: {root}")
            sys.exit(1)

    run_post_check()
    input("\n按回车键退出...")