# -*- coding: utf-8 -*-
"""Numbered pipeline steps: python 04_pipeline.py 00 … 05."""
from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import requests

_wp = importlib.import_module("00_work_paths")
AUDIO_NAME = _wp.AUDIO_NAME
VIDEO_NAME = _wp.VIDEO_NAME
concat_list_path = _wp.concat_list_path
ffmpeg_path = _wp.ffmpeg_path
find_slide_image = _wp.find_slide_image
images_dir = _wp.images_dir
load_config = _wp.load_config
materialize_work = _wp.materialize_work
normalize_slide_pngs = _wp.normalize_slide_pngs
resolve = _wp.resolve
sentence_list_path = _wp.sentence_list_path
slide_png_name = _wp.slide_png_name
task_id_path = _wp.task_id_path
timestamps_path = _wp.timestamps_path
tr = _wp.tr
tts_headers = _wp.tts_headers

HERE = Path(__file__).resolve().parent
STOP_FLAG = "stop_query.flag"
POLL_INTERVAL = 10
TTS_SUBMIT = "https://openspeech.bytedance.com/api/v3/tts/submit"
TTS_QUERY = "https://openspeech.bytedance.com/api/v3/tts/query"
CFG: dict = {}


def T(zh: str, en: str) -> str:
    return tr(zh, en, CFG)


def ffmpeg_exe() -> str:
    return str(ffmpeg_path())


def step_00() -> None:
    config: dict = {}
    if not os.path.exists("config.json"):
        print("缺少设置文件。 / Settings file is missing.")
        sys.exit(1)
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError:
        print(tr("设置文件格式有误，请到设置页重新保存。", "Settings file is damaged. Save again on the Settings page.", config))
        sys.exit(1)

    ok = True
    print("=" * 40)
    print(tr("  开始前检查", "  Before we start", config))
    print("=" * 40)

    required_keys = ["app", "files", "audio", "video_params", "slide_mapping"]
    if all(key in config for key in required_keys):
        print(tr("✅ 设置完整", "✅ Settings look complete", config))
    else:
        ok = False
        print(tr("⚠️ 设置不完整，请到设置页保存一次。", "⚠️ Settings are incomplete. Save once on the Settings page.", config))

    app = config.get("app", {})
    api_key = (app.get("apiKey") or "").strip()
    app_id = (app.get("appID") or "").strip()
    access_key = (app.get("accessKey") or "").strip()
    if api_key or (app_id and access_key and app_id != "你的AppID" and access_key != "你的AccessKey"):
        print(tr("✅ 语音密钥已填写", "✅ Voice key is set", config))
    else:
        ok = False
        print(tr("⚠️ 请到设置页填写语音 API Key。", "⚠️ Add a voice API key on the Settings page.", config))

    files = config.get("files", {})
    input_txt = files.get("input_text", "input.txt")
    if os.path.exists(input_txt):
        print(tr(f"✅ 讲稿已找到：{input_txt}", f"✅ Script found: {input_txt}", config))
    else:
        ok = False
        print(tr(f"⚠️ 找不到讲稿：{input_txt}", f"⚠️ Script not found: {input_txt}", config))

    ppt_file = files.get("ppt_file", "training.pptx")
    if os.path.exists(ppt_file):
        print(tr(f"✅ 课件已找到：{ppt_file}", f"✅ Slides found: {ppt_file}", config))
    else:
        ok = False
        print(tr(f"⚠️ 找不到课件：{ppt_file}", f"⚠️ Slides not found: {ppt_file}", config))

    if not os.path.exists(ffmpeg_exe()):
        ok = False
        print(tr("⚠️ 缺少视频工具 ffmpeg.exe。", "⚠️ ffmpeg.exe is missing.", config))
    else:
        try:
            subprocess.run([ffmpeg_exe(), "-version"], capture_output=True, check=True)
            print(tr("✅ 视频工具可用", "✅ Video tool is ready", config))
        except Exception:
            ok = False
            print(tr("⚠️ 视频工具无法运行。", "⚠️ Video tool could not run.", config))

    slide_mapping = config.get("slide_mapping", [])
    if slide_mapping:
        print(
            tr(
                f"✅ 翻页对齐已设置，共 {len(slide_mapping)} 页",
                f"✅ Page timing is set ({len(slide_mapping)} pages)",
                config,
            )
        )
    else:
        ok = False
        print(tr("⚠️ 还没有翻页对齐，请先合成音频再自动对齐。", "⚠️ Page timing is empty. Make audio, then auto-align.", config))

    print("=" * 40)
    if ok:
        print(tr("检查通过。", "Checks passed.", config))
    else:
        print(tr("还有未完成的项目，请先按上面的提示处理。", "Something is still missing. Fix the items above first.", config))
    print("=" * 40)


def _win_path(path: Path) -> str:
    return str(path.resolve())


def _com_init() -> None:
    try:
        import pythoncom

        pythoncom.CoInitialize()
    except Exception:
        pass


def _com_uninit() -> None:
    try:
        import pythoncom

        pythoncom.CoUninitialize()
    except Exception:
        pass


def _new_powerpoint():
    import win32com.client

    return win32com.client.DispatchEx("PowerPoint.Application")


def _export_once(ascii_ppt: Path, tmp_root: Path, output_dir: Path, config: dict) -> list[Path]:
    _com_init()
    app = None
    pres = None
    saved: list[Path] = []
    try:
        app = _new_powerpoint()
        try:
            app.Visible = True
        except Exception:
            pass
        try:
            app.DisplayAlerts = 0
        except Exception:
            pass
        print(tr("正在打开课件…", "Opening the slides…", config), flush=True)
        pres = app.Presentations.Open(_win_path(ascii_ppt), True, False, True)
        total = int(pres.Slides.Count)
        width = int(pres.PageSetup.SlideWidth * 2)
        height = int(pres.PageSetup.SlideHeight * 2)
        print(
            tr(f"共 {total} 页，导出尺寸 {width}×{height}", f"{total} pages, {width}×{height}", config),
            flush=True,
        )
        for i in range(1, total + 1):
            tmp_png = tmp_root / f"slide_{i}.png"
            pres.Slides(i).Export(_win_path(tmp_png), "PNG", width, height)
            if not tmp_png.is_file() or tmp_png.stat().st_size < 100:
                raise RuntimeError(tr(f"第 {i} 页导出失败", f"Export failed for page {i}", config))
            dest = output_dir / slide_png_name(i, config)
            if dest.exists():
                dest.unlink()
            shutil.copy2(tmp_png, dest)
            saved.append(dest)
            print(tr(f"已导出 {dest.name}", f"Saved {dest.name}", config), flush=True)
        return saved
    finally:
        if pres is not None:
            try:
                pres.Close()
            except Exception:
                pass
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass
        _com_uninit()


def export_slides(ppt_file: Path, output_dir: Path, config: dict) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_root = Path(tempfile.mkdtemp(prefix="iris_ppt_"))
    ascii_ppt = tmp_root / "lesson.pptx"
    shutil.copy2(ppt_file, ascii_ppt)
    last_error: Exception | None = None
    try:
        for attempt in range(1, 4):
            try:
                return _export_once(ascii_ppt, tmp_root, output_dir, config)
            except Exception as e:
                last_error = e
                print(
                    tr(
                        f"第 {attempt} 次导出未成功，正在重试…",
                        f"Attempt {attempt} did not finish. Trying again…",
                        config,
                    ),
                    flush=True,
                )
                time.sleep(1.5 * attempt)
        assert last_error is not None
        raise last_error
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def step_01() -> None:
    try:
        import pythoncom  # noqa: F401
        import win32com.client  # noqa: F401
    except ImportError:
        print("Missing pywin32. Run: pip install pywin32")
        sys.exit(1)

    config = materialize_work(load_config())
    files = config.get("files", {})
    ppt_file = resolve(files.get("ppt_file", "training.pptx"))
    output_dir = images_dir(config)

    if not ppt_file.is_file():
        print(tr(f"找不到课件：{ppt_file}", f"Slides not found: {ppt_file}", config))
        sys.exit(1)

    print(tr(f"图片将保存到：{output_dir}", f"Pictures will be saved in: {output_dir}", config), flush=True)
    try:
        export_slides(ppt_file, output_dir, config)
    except Exception as e:
        print(tr(f"导出图片失败：{e}", f"Could not export pictures: {e}", config))
        print(
            tr(
                "请先关掉所有 PowerPoint 窗口，再点一次「合成视频」。",
                "Close every PowerPoint window, then click Make video again.",
                config,
            )
        )
        sys.exit(1)

    normalize_slide_pngs(output_dir, config)
    pngs = list(output_dir.glob("*.png"))
    if not pngs:
        print(tr(f"文件夹是空的：{output_dir}", f"Empty folder: {output_dir}", config))
        sys.exit(1)
    print(tr(f"完成，共 {len(pngs)} 张图片。", f"Done. {len(pngs)} pictures.", config))


def _submit_tts(url: str, headers: dict, params: dict, config: dict) -> bool:
    print(tr("正在提交配音任务…", "Sending the voice job…", config), flush=True)
    last_error = None
    for attempt in range(1, 4):
        resp = None
        try:
            resp = requests.post(url, json.dumps(params), headers=headers, timeout=60)
            if resp.status_code != 200:
                print(tr("提交没有成功。", "The voice job was not accepted.", config))
                print(resp.text)
                return False
            resp_data = (resp.json() or {}).get("data")
            if resp_data and resp_data.get("task_id"):
                with open(task_id_path(config), "w", encoding="utf-8") as f:
                    f.write(resp_data["task_id"])
                print(tr("✅ 配音任务已提交", "✅ Voice job submitted", config))
                return True
            print(tr("提交后没有得到任务编号。", "No job id came back.", config))
            return False
        except (requests.RequestException, OSError) as e:
            last_error = e
            print(
                tr(
                    f"网络中断（第 {attempt} 次）。",
                    f"The connection dropped (try {attempt}).",
                    config,
                ),
                flush=True,
            )
            time.sleep(1.5 * attempt)
        finally:
            if resp is not None:
                resp.close()
    print(
        tr(
            f"配音服务暂时连不上：{last_error}\n请检查网络后，再点一次「合成音频」。",
            f"Could not reach the voice service: {last_error}\nCheck your network, then click Make audio again.",
            config,
        )
    )
    return False


def step_02() -> None:
    config = materialize_work(load_config())
    app = config["app"]
    files = config["files"]
    audio = config.get("audio", {})
    input_file = str(resolve(files["input_text"]))
    speaker = audio.get("speaker", "zh_female_vv_uranus_bigtts")
    audio_format = audio.get("format", "mp3")
    sample_rate = int(audio.get("sample_rate", 24000))
    uid = app.get("uid", "123123")

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            text = f.read()
        print(tr(f"✅ 已读取讲稿，共 {len(text)} 个字", f"✅ Script loaded ({len(text)} characters)", config))
    except FileNotFoundError:
        print(tr(f"❌ 找不到讲稿：{input_file}", f"❌ Script not found: {input_file}", config))
        sys.exit(1)

    headers = tts_headers(app)
    body = {
        "user": {"uid": uid},
        "unique_id": str(uuid.uuid4()),
        "req_params": {
            "text": text,
            "speaker": speaker,
            "audio_params": {
                "format": audio_format,
                "sample_rate": sample_rate,
                "enable_timestamp": True,
            },
            "additions": json.dumps({}),
        },
    }
    if not _submit_tts(TTS_SUBMIT, headers, body, config):
        sys.exit(1)


def _should_stop() -> bool:
    return os.path.isfile(STOP_FLAG)


def _sleep_interruptible(seconds: int) -> bool:
    for left in range(seconds, 0, -1):
        if _should_stop():
            return True
        if left == seconds or left % 5 == 0 or left <= 3:
            print(T(f"   …大约还要 {left} 秒（可点「停止」）", f"   …about {left}s left (you can click Stop)"), flush=True)
        time.sleep(1)
    return _should_stop()


def _save_sentences(sentences, config) -> None:
    sentences_simple = []
    for s in sentences:
        sentences_simple.append(
            {
                "text": s["text"],
                "startTime": s["startTime"],
                "endTime": s["endTime"],
            }
        )
    ts = timestamps_path(config)
    with ts.open("w", encoding="utf-8") as f:
        json.dump(sentences_simple, f, ensure_ascii=False, indent=2)
    print(T("句子时间已保存。", "Sentence times saved."), flush=True)
    print(T("\n句子列表：", "\nSentences:"), flush=True)
    lines = [T("句子列表\n", "Sentences\n")]
    for idx, s in enumerate(sentences_simple):
        preview = s["text"][:60].replace("\n", " ").strip()
        if len(s["text"]) > 60:
            preview += "..."
        line = f"  {idx}: {preview} ({s['startTime']:.2f}s - {s['endTime']:.2f}s)\n"
        lines.append(line)
        print(line.rstrip(), flush=True)
    lst = sentence_list_path(config)
    with lst.open("w", encoding="utf-8") as f:
        f.writelines(lines)
    print(T(f"共 {len(sentences_simple)} 句。", f"{len(sentences_simple)} sentences."), flush=True)


def _query_tts(uri: str, headers: dict, params: dict, audio_output: str, config) -> int:
    attempt = 0
    started = time.time()
    status_text = {
        1: T("正在合成", "Still making"),
        2: T("已完成", "Done"),
        3: T("失败", "Failed"),
    }
    print(T("开始等待配音。长文稿可能需要几分钟。", "Waiting for the voice. A long script can take a few minutes."), flush=True)

    while True:
        if _should_stop():
            print(T("已停止。", "Stopped."), flush=True)
            return 130

        attempt += 1
        elapsed = int(time.time() - started)
        print(
            T(
                f"\n—— 第 {attempt} 次查看（已等 {elapsed // 60} 分 {elapsed % 60} 秒）——",
                f"\n—— Check {attempt} (waited {elapsed // 60}m {elapsed % 60}s) ——",
            ),
            flush=True,
        )

        try:
            resp = requests.post(uri, data=json.dumps(params), headers=headers, timeout=60)
        except requests.RequestException as e:
            print(T(f"网络出错：{e}", f"Network error: {e}"), flush=True)
            if _sleep_interruptible(POLL_INTERVAL):
                print(T("已停止。", "Stopped."), flush=True)
                return 130
            continue

        try:
            if resp.status_code != 200:
                print(T(f"服务器返回 {resp.status_code}", f"Server returned {resp.status_code}"), flush=True)
                try:
                    print(str(resp.json()), flush=True)
                except Exception:
                    print(resp.text, flush=True)
                return 1

            resp_json = resp.json()
            resp_data = resp_json.get("data") or {}
            status = resp_data.get("task_status")
            label = status_text.get(status, T(f"未知({status})", f"unknown ({status})"))
            print(T(f"状态：{label}", f"Status: {label}"), flush=True)

            if status == 1:
                print(T("还在合成，继续等…", "Still making the voice. Waiting…"), flush=True)
                if _sleep_interruptible(POLL_INTERVAL):
                    print(T("已停止。", "Stopped."), flush=True)
                    return 130
                continue

            if status == 2:
                print(T("合成成功，正在保存音频…", "Voice is ready. Saving the audio…"), flush=True)
                audio_url = resp_data.get("audio_url")
                if not audio_url:
                    print(T("没有拿到音频地址。", "No audio address in the reply."), flush=True)
                    return 1
                print(T("正在下载音频…", "Downloading the audio…"), flush=True)
                audio_resp = requests.get(audio_url, timeout=300)
                audio_resp.raise_for_status()
                with open(audio_output, "wb") as f:
                    f.write(audio_resp.content)
                print(T(f"音频已保存：{audio_output}", f"Audio saved: {audio_output}"), flush=True)
                sentences = resp_data.get("sentences")
                if sentences:
                    _save_sentences(sentences, config)
                else:
                    print(T("没有句子时间。请重新合成音频。", "No sentence times. Make the audio again."), flush=True)
                return 0

            if status == 3:
                print(T("配音失败。", "Voice job failed."), flush=True)
                print(str(resp_data), flush=True)
                return 1

            print(T(f"未知状态：{status}", f"Unknown status: {status}"), flush=True)
            return 1
        finally:
            resp.close()


def step_03() -> None:
    global CFG
    if os.path.isfile(STOP_FLAG):
        try:
            os.remove(STOP_FLAG)
        except OSError:
            pass

    config = materialize_work(load_config())
    CFG = config
    app = config["app"]
    files = config["files"]
    audio_output = str(resolve(files.get("audio_output", AUDIO_NAME)))
    Path(audio_output).parent.mkdir(parents=True, exist_ok=True)

    tid = task_id_path(config)
    try:
        task_id = tid.read_text(encoding="utf-8").strip()
        print(T("已读到配音任务。", "Voice job id loaded."), flush=True)
    except FileNotFoundError:
        print(T("还没有配音任务。请先点「合成音频」。", "No voice job yet. Click Make audio first."), flush=True)
        sys.exit(1)

    if not task_id:
        print(T("配音任务是空的，请重新合成音频。", "The voice job is empty. Make audio again."), flush=True)
        sys.exit(1)

    headers = tts_headers(app)
    payload = {"task_id": task_id}
    print(T("开始查询配音进度。", "Checking voice progress."), flush=True)
    code = _query_tts(TTS_QUERY, headers, payload, audio_output, config)
    sys.exit(code)


def _normalize_mapping(slide_mapping):
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


def step_04() -> None:
    config = materialize_work(load_config())
    files = config.get("files", {})
    slide_mapping_raw = config.get("slide_mapping", [])
    audio_file = files.get("audio_output", AUDIO_NAME)
    ts_file = timestamps_path(config)
    image_folder = images_dir(config)
    normalize_slide_pngs(image_folder, config)

    if not os.path.exists(audio_file):
        print(tr(f"❌ 还没有口播音频：{audio_file}", f"❌ Narration not found: {audio_file}", config))
        sys.exit(1)
    if not slide_mapping_raw:
        print(tr("❌ 还没有翻页对齐。", "❌ Page timing is empty.", config))
        sys.exit(1)

    slide_mapping = _normalize_mapping(slide_mapping_raw)
    if not ts_file.is_file():
        print(tr("❌ 还没有句子时间。请先合成音频。", "❌ No sentence times yet. Make the audio first.", config))
        sys.exit(1)
    with ts_file.open("r", encoding="utf-8") as f:
        sentences = json.load(f)
    if not sentences:
        print(tr("❌ 句子时间为空。", "❌ Sentence times are empty.", config))
        sys.exit(1)

    total_duration = float(sentences[-1].get("endTime") or 0)
    valid_rows = []
    for start_idx, end_idx, slide in slide_mapping:
        if start_idx >= len(sentences) or end_idx >= len(sentences) or start_idx > end_idx:
            print(
                tr(
                    f"⚠️ 第 {start_idx}–{end_idx} 句超出范围（共 {len(sentences)} 句），已跳过",
                    f"⚠️ Sentences {start_idx}–{end_idx} are out of range ({len(sentences)} sentences). Skipped.",
                    config,
                )
            )
            continue
        valid_rows.append((start_idx, end_idx, slide))
    if not valid_rows:
        print(tr("❌ 翻页对齐无效。", "❌ Page timing is not valid.", config))
        sys.exit(1)

    slide_timings = []
    valid_out = []
    idx = 0
    while idx < len(valid_rows):
        start_idx, end_idx, slide = valid_rows[idx]
        group = [valid_rows[idx]]
        j = idx + 1
        while j < len(valid_rows) and valid_rows[j][0] == start_idx and valid_rows[j][1] == end_idx:
            group.append(valid_rows[j])
            j += 1
        t0 = float(sentences[start_idx]["startTime"])
        t1 = float(sentences[end_idx]["endTime"])
        if idx == 0:
            t0 = 0.0
        span = max(t1 - t0, 0.001 * len(group))
        piece = span / len(group)
        for _row in group:
            slide_timings.append({"duration": piece})
            valid_out.append(_row)
        idx = j
    valid_rows = valid_out

    list_file = concat_list_path(config)
    missing = 0
    entries: list[tuple[str, float]] = []
    with list_file.open("w", encoding="utf-8") as f:
        for i, timing in enumerate(slide_timings):
            slide_name = valid_rows[i][2] or slide_png_name(i + 1, config)
            found = find_slide_image(image_folder, slide_name)
            if not found:
                print(tr(f"找不到图片：{image_folder / slide_name}", f"Picture not found: {image_folder / slide_name}", config))
                missing += 1
                found = image_folder / slide_name
            try:
                img_path = found.resolve().relative_to(list_file.parent.resolve()).as_posix()
            except ValueError:
                img_path = found.resolve().as_posix()
            entries.append((img_path, timing["duration"]))
            f.write(f"file '{img_path}'\n")
            f.write(f"duration {timing['duration']:.6f}\n")
        if entries:
            f.write(f"file '{entries[-1][0]}'\n")

    if missing:
        print(tr(f"❌ 有 {missing} 页找不到图片，已停止。", f"❌ {missing} page(s) have no picture. Stopped.", config))
        sys.exit(1)

    total_video_duration = sum(t["duration"] for t in slide_timings)
    print(tr(f"✅ 翻页时间已算好，共 {len(slide_timings)} 页", f"✅ Page timing ready ({len(slide_timings)} pages)", config))
    print(
        tr(
            f"视频约 {total_video_duration:.1f} 秒，口播约 {total_duration:.1f} 秒",
            f"Video ~{total_video_duration:.1f}s, narration ~{total_duration:.1f}s",
            config,
        )
    )


def step_05() -> None:
    config = materialize_work(load_config())
    files = config.get("files", {})
    video_params = config.get("video_params", {})
    audio_file = str(resolve(files.get("audio_output", AUDIO_NAME)))
    output_video = str(resolve(files.get("video_output", VIDEO_NAME)))
    os.makedirs(os.path.dirname(output_video) or ".", exist_ok=True)
    video_size = video_params.get("resolution", "854x480")
    fps = video_params.get("fps", 24)
    preset = video_params.get("preset", "ultrafast")
    crf = video_params.get("crf", 30)
    audio_bitrate = video_params.get("audio_bitrate", "128k")

    if not os.path.isfile(ffmpeg_exe()):
        print(tr("❌ 缺少视频工具 ffmpeg.exe。", "❌ ffmpeg.exe is missing.", config))
        sys.exit(1)
    if not os.path.exists(audio_file):
        print(tr(f"❌ 还没有口播音频：{audio_file}", f"❌ Narration not found: {audio_file}", config))
        sys.exit(1)

    timed_list = str(concat_list_path(config))
    if not os.path.exists(timed_list):
        print(tr("❌ 还没有翻页时间。请先对齐幻灯片。", "❌ Page timing file is missing. Align the slides first.", config))
        sys.exit(1)

    total_duration = 0.0
    with open(timed_list, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("duration "):
                total_duration += float(line.split()[1])
    print(tr(f"视频时长约 {total_duration:.1f} 秒", f"Video length about {total_duration:.1f}s", config))

    width, height = video_size.split("x")
    ffmpeg_cmd = [
        ffmpeg_exe(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        timed_list,
        "-i",
        audio_file,
        "-vf",
        f"scale={video_size}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-c:a",
        "aac",
        "-b:a",
        audio_bitrate,
        "-to",
        str(total_duration),
        "-y",
        output_video,
    ]
    print(tr("正在合成视频…", "Making the video…", config))
    try:
        subprocess.run(ffmpeg_cmd, check=True, cwd=os.path.dirname(timed_list) or None)
        print(tr(f"视频已生成：{output_video}", f"Video saved: {output_video}", config))
        print(tr(f"时长约 {total_duration:.1f} 秒", f"Length about {total_duration:.1f}s", config))
    except subprocess.CalledProcessError as e:
        print(tr(f"合成失败（代码 {e.returncode}）", f"Could not make the video (code {e.returncode})", config))
        sys.exit(1)


STEPS = {
    "00": step_00,
    "01": step_01,
    "02": step_02,
    "03": step_03,
    "04": step_04,
    "05": step_05,
}


def main() -> None:
    step = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if step not in STEPS:
        print("Usage: python 04_pipeline.py 00|01|02|03|04|05")
        sys.exit(2)
    STEPS[step]()


if __name__ == "__main__":
    main()
