import os
import subprocess
import sys
from config_loader import load_config

config = load_config()
files = config.get("files", {})
video_params = config.get("video_params", {})

AUDIO_FILE = files.get("audio_output", "output.mp3")
OUTPUT_VIDEO = files.get("video_output", "output_video_ffmpeg.mp4")
VIDEO_SIZE = video_params.get("resolution", "854x480")
FPS = video_params.get("fps", 24)
PRESET = video_params.get("preset", "ultrafast")
CRF = video_params.get("crf", 30)
AUDIO_BITRATE = video_params.get("audio_bitrate", "128k")

FFMPEG_EXE = os.path.join(os.path.dirname(__file__), "ffmpeg.exe")
if not os.path.isfile(FFMPEG_EXE):
    print(f"❌ 未找到 ffmpeg.exe，请将其放在脚本同目录下。")
    sys.exit(1)

# 检查必要文件
if not os.path.exists(AUDIO_FILE):
    print(f"❌ 音频文件 {AUDIO_FILE} 不存在，请先运行 query.py。")
    sys.exit(1)

timed_list = "concat_list_timed.txt"
if not os.path.exists(timed_list):
    print(f"❌ 未找到 {timed_list}，请先运行 generate_slide_timings.py。")
    sys.exit(1)

# 读取总时长
total_duration = 0.0
with open(timed_list, "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("duration "):
            total_duration += float(line.split()[1])
print(f"📊 视频流总时长: {total_duration:.2f} 秒")

# 构建 FFmpeg 命令（使用 -to 精确控制）
width, height = VIDEO_SIZE.split('x')
ffmpeg_cmd = [
    FFMPEG_EXE,
    "-f", "concat",
    "-safe", "0",
    "-i", timed_list,
    "-i", AUDIO_FILE,
    "-vf", f"scale={VIDEO_SIZE}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
    "-map", "0:v",
    "-map", "1:a",
    "-c:v", "libx264",
    "-preset", PRESET,
    "-crf", str(CRF),
    "-pix_fmt", "yuv420p",
    "-r", str(FPS),
    "-c:a", "aac",
    "-b:a", AUDIO_BITRATE,
    "-to", str(total_duration),
    "-y",
    OUTPUT_VIDEO
]

print("🎬 正在合成视频...")
print("命令: " + " ".join(ffmpeg_cmd))

try:
    subprocess.run(ffmpeg_cmd, check=True)
    print(f"🎉 视频已生成: {OUTPUT_VIDEO}")
    print(f"📌 输出时长: {total_duration:.2f} 秒")
except subprocess.CalledProcessError as e:
    print(f"❌ FFmpeg 执行失败，返回码: {e.returncode}")
    sys.exit(1)