import json
import os
import sys
from config_loader import load_config
from moviepy.editor import AudioFileClip


def normalize_mapping(slide_mapping):
    """支持 {"start","end","slide"} 对象，或 [start, end] / [start, end, slide] 列表。"""
    result = []
    for item in slide_mapping:
        if isinstance(item, dict):
            start_idx = int(item["start"])
            end_idx = int(item["end"])
            slide = item.get("slide")
        else:
            start_idx = int(item[0])
            end_idx = int(item[1])
            slide = item[2] if len(item) > 2 else None
        result.append((start_idx, end_idx, slide))
    return result


config = load_config()
files = config.get("files", {})
slide_mapping_raw = config.get("slide_mapping", [])
audio_file = files.get("audio_output", "output.mp3")

if not os.path.exists(audio_file):
    print(f"❌ 音频文件 {audio_file} 不存在，请先运行 query.py。")
    sys.exit(1)

if not slide_mapping_raw:
    print("❌ config.json 中未配置 slide_mapping，请填写。")
    sys.exit(1)

slide_mapping = normalize_mapping(slide_mapping_raw)

if not os.path.exists("timestamps.json"):
    print("❌ 未找到 timestamps.json，请先运行 query.py。")
    sys.exit(1)

with open("timestamps.json", "r", encoding="utf-8") as f:
    sentences = json.load(f)

audio = AudioFileClip(audio_file)
total_duration = audio.duration
audio.close()

# 每页开始时间 = 该页第一句的 startTime
start_times = []
valid_rows = []
for start_idx, end_idx, slide in slide_mapping:
    if start_idx >= len(sentences):
        print(f"⚠️ 警告：索引 {start_idx} 超出范围（共 {len(sentences)} 句），跳过")
        continue
    start_times.append(sentences[start_idx]["startTime"])
    valid_rows.append((start_idx, end_idx, slide))

if not valid_rows:
    print("❌ 没有有效的 slide_mapping 行。")
    sys.exit(1)

if start_times:
    start_times[0] = 0.0

last_end_idx = valid_rows[-1][1]
if last_end_idx >= len(sentences):
    print(f"❌ 最后一页 end 索引 {last_end_idx} 超出范围（共 {len(sentences)} 句）。")
    sys.exit(1)
last_sentence_end = sentences[last_end_idx]["endTime"]
end_times = start_times[1:] + [last_sentence_end]

slide_timings = []
for start, end in zip(start_times, end_times):
    duration = end - start
    if duration < 0.001:
        duration = 0.001
    slide_timings.append({"start": start, "end": end, "duration": duration})

image_dir = "ppt_images"
list_file = "concat_list_timed.txt"
with open(list_file, "w", encoding="utf-8") as f:
    for i, timing in enumerate(slide_timings):
        slide_name = valid_rows[i][2] or f"slide_{i + 1}.png"
        img_path = f"{image_dir}/{slide_name}"
        if not os.path.exists(img_path):
            print(f"⚠️ 警告：图片 {img_path} 不存在，请先运行 convert_ppt_to_images.py")
        f.write(f"file '{img_path}'\n")
        f.write(f"duration {timing['duration']:.6f}\n")

total_video_duration = sum(t["duration"] for t in slide_timings)
print(f"✅ 已生成 {list_file}，共 {len(slide_timings)} 页幻灯片")
print(f"总视频时长 = {total_video_duration:.2f} 秒，音频时长 = {total_duration:.2f} 秒")
