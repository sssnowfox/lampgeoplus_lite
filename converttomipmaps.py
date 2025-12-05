import os
import subprocess
import shutil

# --- 1. 设置路径 ---
#root_folder = r"C:\Users\Owner\OneDrive\Documents\Paradox Interactive\Hearts of Iron IV\mod\lampgeoplus_lite_local\gfx\models\units\planes\GEN"
root_folder = r"C:\Users\Owner\OneDrive\Documents\Paradox Interactive\Hearts of Iron IV\mod\old\temp"

# --- 2. 设置工具 ---
texconv_path = r"texconv.exe"

def recursive_convert_diffuse_bc3():
    # 检查 texconv 是否存在
    if not os.path.exists(texconv_path) and not shutil.which(texconv_path):
        print("❌ 错误：找不到 texconv.exe。请确保它和脚本在同一个文件夹里。")
        return

    if not os.path.exists(root_folder):
        print(f"❌ 错误：找不到目标文件夹: {root_folder}")
        return

    print(f"📂 目标路径: {root_folder}")
    print("🛡️  模式: 仅处理包含 '_diffuse' 的文件")
    print("⚙️  操作: 转换为 BC3 (DXT5) + 生成 Mipmaps")
    print("⚠️  注意: BC3 文件体积是 BC1 的两倍，但支持半透明。\n")

    processed_count = 0
    skipped_count = 0

    # 递归遍历
    for current_root, dirs, files in os.walk(root_folder):
        for filename in files:
            if filename.lower().endswith(".dds"):
                
                # --- 核心过滤逻辑 ---
                # 只有文件名包含 "_diffuse" 才处理
                if "_diffuse" not in filename.lower():
                    skipped_count += 1
                    continue
                # --------------------

                file_path = os.path.join(current_root, filename)
                
                # texconv 命令
                cmd = [
                    texconv_path,
                    "-f", "BC3_UNORM",  # <--- 这里改成了 BC3 (DXT5)
                    "-m", "0",          # 自动生成 Mipmaps
                    "-y",               # 覆盖原文件
                    "-o", current_root, # 输出回原目录
                    "-nologo",
                    file_path
                ]

                try:
                    # 执行转换
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                    
                    # 显示相对路径
                    rel_path = os.path.relpath(file_path, root_folder)
                    print(f"✅ [BC3转换完成] {rel_path}")
                    processed_count += 1
                    
                except subprocess.CalledProcessError:
                    print(f"❌ [转换失败] {filename}")
                except Exception as e:
                    print(f"❌ [未知错误] {e}")

    print("-" * 30)
    print(f"统计结果:")
    print(f"✅ 成功处理 (Diffuse -> BC3): {processed_count} 个文件")
    print(f"⏭️ 跳过其他文件: {skipped_count} 个文件")

if __name__ == "__main__":
    recursive_convert_diffuse_bc3()
    input("\n按回车键退出...")