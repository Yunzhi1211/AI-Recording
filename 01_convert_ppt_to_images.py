import os
import pptx2png
import sys
from config_loader import load_config

# 加载配置
config = load_config()
files = config.get("files", {})
PPT_FILE = files.get("ppt_file", "training.pptx")
OUTPUT_DIR = "ppt_images"

# 检查 PPT 文件是否存在
if not os.path.isfile(PPT_FILE):
    print(f"❌ 未找到 PPT 文件: {PPT_FILE}")
    print("💡 请检查 config.json 中的 'ppt_file' 路径是否正确。")
    sys.exit(1)

# --- 转换 ---
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"🔄 正在将 {PPT_FILE} 转换为图片...")

try:
    pptx2png.topng(pptx=PPT_FILE, output_dir=OUTPUT_DIR, scale=2)
    print(f"✅ 图片已保存到: {OUTPUT_DIR}")
except Exception as e:
    print(f"❌ 转换失败: {e}")
    print("💡 请确保 PPT 文件存在且路径正确。")
    sys.exit(1)