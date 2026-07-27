# 00_init_check.py
import os
import sys
import json
import subprocess

print("=" * 50)
print("  视频生成工具 - 环境检查")
print("=" * 50)

# 1. 检查 config.json
if not os.path.exists("config.json"):
    print("❌ config.json 不存在，请先创建配置文件。")
    sys.exit(1)
else:
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        print("✅ config.json 格式正确")
    except json.JSONDecodeError:
        print("❌ config.json 格式错误，请检查 JSON 语法。")
        sys.exit(1)

# 2. 检查关键字段
required_keys = ["app", "files", "audio", "video_params", "slide_mapping"]
for key in required_keys:
    if key not in config:
        print(f"⚠️ config.json 缺少 '{key}' 字段")
    else:
        print(f"✅ config.json 包含 '{key}' 字段")

# 3. 检查 app 密钥
app = config.get("app", {})
if not app.get("appID") or app["appID"] == "你的AppID":
    print("⚠️ config.json 中 appID 未填写，请填写后重试。")
else:
    print("✅ appID 已配置")

if not app.get("accessKey") or app["accessKey"] == "你的AccessKey":
    print("⚠️ config.json 中 accessKey 未填写，请填写后重试。")
else:
    print("✅ accessKey 已配置")

# 4. 检查输入文件
files = config.get("files", {})
input_txt = files.get("input_text", "input.txt")
if not os.path.exists(input_txt):
    print(f"⚠️ 输入文本文件 '{input_txt}' 不存在，请放置到当前目录。")
else:
    print(f"✅ 输入文本文件 '{input_txt}' 存在")

ppt_file = files.get("ppt_file", "training.pptx")
if not os.path.exists(ppt_file):
    print(f"⚠️ PPT 文件 '{ppt_file}' 不存在，请放置到当前目录。")
else:
    print(f"✅ PPT 文件 '{ppt_file}' 存在")

# 5. 检查 ffmpeg
ffmpeg_path = os.path.join(os.path.dirname(__file__), "ffmpeg.exe")
if not os.path.exists(ffmpeg_path):
    print("⚠️ ffmpeg.exe 不存在，请放置到当前目录。")
else:
    # 测试运行
    try:
        subprocess.run([ffmpeg_path, "-version"], capture_output=True, check=True)
        print("✅ ffmpeg.exe 可运行")
    except Exception:
        print("⚠️ ffmpeg.exe 无法运行，可能文件损坏。")

# 6. 检查 slide_mapping
slide_mapping = config.get("slide_mapping", [])
if not slide_mapping:
    print("⚠️ slide_mapping 为空，请根据培训内容填写。")
else:
    print(f"✅ slide_mapping 已配置 {len(slide_mapping)} 页")

print("=" * 50)
print("环境检查完成！")
print("请确保以上所有项目均为 ✅，然后运行 01_convert_ppt_to_images.py 开始生成。")
print("=" * 50)