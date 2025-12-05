import os
import datetime

# 🎯 目标文件夹路径 (Target Folder Path)
# 注意：Windows路径中的反斜杠 \ 需要转义为 \\ 或使用 r"" 原始字符串，
# 但在 os.walk 中，使用 / 也可以，这里我们沿用你的 r"" 格式。
root_folder = r"C:\Users\Owner\OneDrive\Documents\Paradox Interactive\Hearts of Iron IV\mod\lampgeoplus_lite_local\gfx\models"

# 📅 截止日期 (Cutoff Date) - 2025年11月23日 (包括这一天)
# 注意：你需要将年份设置为正确的年份（例如 2025）。
# 如果用户输入时没有明确年份，我将使用当前年份 2025 作为假设。
cutoff_date = datetime.datetime(2025, 11, 23, 0, 0, 0)

print(f"🔍 正在搜索文件夹: {root_folder}")
print(f"📅 截止日期: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
print("-" * 40)

found_files = []

# 遍历文件夹及其子文件夹
for foldername, subfolders, filenames in os.walk(root_folder):
    for filename in filenames:
        # 构建文件的完整路径
        full_path = os.path.join(foldername, filename)
        
        try:
            # 获取文件的最后修改时间戳 (以秒为单位)
            timestamp = os.path.getmtime(full_path)
            
            # 将时间戳转换为 datetime 对象
            modification_time = datetime.datetime.fromtimestamp(timestamp)
            
            # 检查文件是否在截止日期或之后被修改
            if modification_time >= cutoff_date:
                # 找到符合条件的文件
                # 记录相对路径和修改时间
                relative_path = os.path.relpath(full_path, root_folder)
                found_files.append((relative_path, modification_time))
                
        except Exception as e:
            # 处理无法访问文件或获取信息时可能出现的错误
            print(f"⚠️ 无法处理文件 {full_path}: {e}")

# 🚀 打印结果
if found_files:
    print("✅ 11月23日以后修改的文件:")
    print("-" * 40)
    # 按修改时间排序，最新的排在前面
    found_files.sort(key=lambda x: x[1], reverse=True)
    
    for relative_path, mod_time in found_files:
        print(f"[{mod_time.strftime('%Y-%m-%d %H:%M:%S')}] {relative_path}")
else:
    print("❌ 未找到在 11月23日或之后修改的文件。")