# -*- coding: utf-8 -*-
"""Lesson folders use readable names; internals go in a working-files subfolder."""
from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
OUTPUTS = ROOT / "outputs"
CONFIG_TEMPLATE = ASSETS / "config.template.json"


def ffmpeg_path() -> Path:
    """Prefer assets/ffmpeg.exe; move a leftover root copy there if needed."""
    dest = ASSETS / "ffmpeg.exe"
    leftover = ROOT / "ffmpeg.exe"
    ASSETS.mkdir(parents=True, exist_ok=True)
    if not dest.is_file() and leftover.is_file():
        try:
            shutil.move(str(leftover), str(dest))
        except OSError:
            return leftover
    if dest.is_file():
        return dest
    if leftover.is_file():
        return leftover
    return dest


def get_config_path():
    env = os.environ.get("VIDEO_TOOL_CONFIG")
    if env and os.path.isfile(env):
        return env
    cwd_path = os.path.join(os.getcwd(), "config.json")
    if os.path.isfile(cwd_path):
        return cwd_path
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config():
    with open(get_config_path(), "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config, path=None):
    path = path or get_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return path


def tts_headers(app: dict) -> dict:
    resource_id = app.get("resourceID") or "seed-tts-2.0"
    request_id = str(uuid.uuid1())
    api_key = (app.get("apiKey") or "").strip()
    headers = {
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": request_id,
        "Content-Type": "application/json",
        "Connection": "keep-alive",
    }
    if api_key:
        headers["X-Api-Key"] = api_key
        return headers
    headers["X-Api-App-Id"] = (app.get("appID") or "").strip()
    headers["X-Api-Access-Key"] = (app.get("accessKey") or "").strip()
    return headers

PACKS = {
    "zh": {
        "ppt": "课件.pptx",
        "script": "口播文稿.txt",
        "audio": "口播.mp3",
        "video": "成片.mp4",
        "images": "幻灯片图片",
        "work": "工作文件",
        "timestamps": "句子时间.json",
        "task_id": "任务编号.txt",
        "sentences": "句子列表.txt",
        "concat": "翻页清单.txt",
        "readme": "请先看.txt",
        "untitled": "未命名一课",
        "slide": "第{n}页.png",
        "readme_body": (
            "这一课你可以直接用的文件\n"
            "========================\n\n"
            "成片.mp4          做好的视频，双击播放，可以发给别人\n"
            "口播.mp3          只有声音\n"
            "课件.pptx         幻灯片（用 PowerPoint 打开）\n"
            "口播文稿.txt      要讲的文字\n"
            "幻灯片图片        每一页导出的图片\n\n"
            "「工作文件」是软件自己用的，不用打开。\n"
        ),
    },
    "en": {
        "ppt": "Slides.pptx",
        "script": "Script.txt",
        "audio": "Narration.mp3",
        "video": "Video.mp4",
        "images": "Slide images",
        "work": "Working files",
        "timestamps": "Sentence times.json",
        "task_id": "Task id.txt",
        "sentences": "Sentence list.txt",
        "concat": "Page timing.txt",
        "readme": "Read me first.txt",
        "untitled": "Untitled lesson",
        "slide": "Slide {n}.png",
        "readme_body": (
            "Files you can use for this lesson\n"
            "=================================\n\n"
            "Video.mp4         The finished film. Double-click to play or send it.\n"
            "Narration.mp3     Voice only\n"
            "Slides.pptx       PowerPoint file\n"
            "Script.txt        The spoken text\n"
            "Slide images      One picture per slide\n\n"
            "The Working files folder is for the app only. You can ignore it.\n"
        ),
    },
}

# Keep old import sites working (Chinese defaults).
PPT_NAME = PACKS["zh"]["ppt"]
SCRIPT_NAME = PACKS["zh"]["script"]
AUDIO_NAME = PACKS["zh"]["audio"]
VIDEO_NAME = PACKS["zh"]["video"]
IMAGES_DIR_NAME = PACKS["zh"]["images"]

_RESERVED_STEMS = {
    "课件",
    "口播文稿",
    "Slides",
    "Script",
    "input",
    "training",
    "请先看",
    "Read me first",
}


def ui_lang(config: dict | None = None) -> str:
    app = (config or {}).get("app") or {}
    lang = str(app.get("uiLang") or "zh").lower()
    return "en" if lang.startswith("en") else "zh"


def tr(zh: str, en: str, config: dict | None = None) -> str:
    return en if ui_lang(config) == "en" else zh


def pack(config: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(**PACKS[ui_lang(config)])


def slide_png_name(index: int, config: dict | None = None, lang: str | None = None) -> str:
    key = lang or ui_lang(config)
    key = "en" if str(key).startswith("en") else "zh"
    return PACKS[key]["slide"].format(n=int(index))


def resolve(path: str | Path | None) -> Path:
    if not path:
        return ROOT
    p = Path(str(path))
    return p if p.is_absolute() else ROOT / p


def _slug(text: str, untitled: str = "未命名一课") -> str:
    text = re.sub(r"[\\/:*?\"<>|]+", "", text).strip()
    return text[:24] or untitled


def lesson_from_path(path: str | Path | None) -> str | None:
    """If a file already lives in outputs/<lesson>/..., that lesson wins."""
    if not path:
        return None
    try:
        rel = resolve(path).resolve().relative_to(OUTPUTS.resolve())
    except ValueError:
        return None
    if not rel.parts:
        return None
    name = rel.parts[0]
    if name in {"幻灯片图片", "Slide images", "工作文件", "Working files", "ppt_images"}:
        return None
    return name


def lesson_slug(files: dict, untitled: str = "未命名一课") -> str:
    for key in ("ppt_file", "input_text", "audio_output", "video_output"):
        found = lesson_from_path(files.get(key))
        if found:
            return found
    for key in ("ppt_file", "input_text"):
        value = (files.get(key) or "").strip()
        if not value:
            continue
        stem = Path(value).stem
        if stem not in _RESERVED_STEMS:
            return _slug(stem, untitled)
        parent = Path(value).parent.name
        if parent and parent not in {"outputs", "幻灯片图片", "Slide images", "工作文件", "Working files"}:
            return _slug(parent, untitled)
        return _slug(stem, untitled)
    explicit = (files.get("work_dir") or "").strip()
    if explicit:
        name = Path(explicit).name
        if name and name not in {"lesson", "outputs"}:
            return name
    return untitled


def work_dir(config: dict) -> Path:
    files = config.get("files") or {}
    p = pack(config)
    folder = OUTPUTS / lesson_slug(files, p.untitled)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / p.images).mkdir(parents=True, exist_ok=True)
    (folder / p.work).mkdir(parents=True, exist_ok=True)
    return folder


def _copy_into(src: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not src.is_file():
        return dest
    if src.resolve() == dest.resolve():
        return dest
    shutil.copy2(src, dest)
    return dest


def _relocate(src: Path, dest: Path) -> None:
    if not src.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and src.resolve() == dest.resolve():
        return
    if src.is_dir():
        if dest.exists():
            for item in src.iterdir():
                target = dest / item.name
                if item.is_file():
                    _copy_into(item, target)
                elif item.is_dir() and not target.exists():
                    shutil.copytree(item, target)
            shutil.rmtree(src, ignore_errors=True)
        else:
            shutil.move(str(src), str(dest))
        return
    if dest.exists() and src.resolve() != dest.resolve():
        dest.unlink()
    shutil.move(str(src), str(dest))


def rel_to_root(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _all_names(key: str) -> list[str]:
    names: list[str] = []
    for pack_data in PACKS.values():
        names.append(pack_data[key])
    extras = {
        "images": ["ppt_images"],
        "audio": ["output.mp3"],
        "video": ["output.mp4", "output_video_ffmpeg.mp4"],
        "timestamps": ["timestamps.json"],
        "task_id": ["task_id.txt"],
        "sentences": ["sentence_list.txt"],
        "concat": ["concat_list_timed.txt", "翻页清单.txt"],
        "work": ["工作文件", "Working files"],
        "readme": ["请先看.txt", "Read me first.txt"],
        "ppt": ["课件.pptx", "Slides.pptx"],
        "script": ["口播文稿.txt", "Script.txt"],
    }
    names.extend(extras.get(key, []))
    # unique, keep order
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def write_readme(folder: Path, config: dict) -> None:
    p = pack(config)
    for other in _all_names("readme"):
        old = folder / other
        if old.exists() and old.name != p.readme:
            old.unlink()
    (folder / p.readme).write_text(p.readme_body, encoding="utf-8")


def migrate_readable_names(folder: Path, config: dict) -> None:
    p = pack(config)
    work = folder / p.work
    work.mkdir(parents=True, exist_ok=True)

    for old in _all_names("work"):
        if old == p.work:
            continue
        _relocate(folder / old, work)

    for old in _all_names("images"):
        _relocate(folder / old, folder / p.images)

    user_files = {
        "audio": p.audio,
        "video": p.video,
        "ppt": p.ppt,
        "script": p.script,
    }
    for key, dest_name in user_files.items():
        dest = folder / dest_name
        for old in _all_names(key):
            src = folder / old
            if src.exists() and src.name != dest_name:
                _relocate(src, dest)

    internal = {
        "timestamps": p.timestamps,
        "task_id": p.task_id,
        "sentences": p.sentences,
        "concat": p.concat,
    }
    for key, dest_name in internal.items():
        dest = work / dest_name
        for old in _all_names(key):
            for base in (folder, work):
                src = base / old
                if src.exists() and src.resolve() != dest.resolve():
                    _relocate(src, dest)

    images = folder / p.images
    if images.is_dir():
        normalize_slide_pngs(images, config)

    skip_txt = set(_all_names("script") + _all_names("sentences") + _all_names("task_id") + _all_names("concat") + _all_names("readme"))
    extras_ppt = [x for x in folder.glob("*.pptx") if x.name != p.ppt]
    if extras_ppt and not (folder / p.ppt).exists():
        _relocate(extras_ppt[0], folder / p.ppt)
    extras_txt = [x for x in folder.glob("*.txt") if x.name not in skip_txt]
    if extras_txt and not (folder / p.script).exists():
        _relocate(extras_txt[0], folder / p.script)

    write_readme(folder, config)


def materialize_work(config: dict, *, persist: bool = True) -> dict:
    files = config.setdefault("files", {})
    p = pack(config)
    previous = Path((files.get("work_dir") or "").strip()).name
    folder = work_dir(config)
    if previous and previous != folder.name:
        config["slide_mapping"] = []
    migrate_readable_names(folder, config)

    ppt_src = resolve(files.get("ppt_file") or "")
    txt_src = resolve(files.get("input_text") or "")
    ppt_dest = folder / p.ppt
    txt_dest = folder / p.script
    skip_txt = set(_all_names("sentences") + _all_names("task_id") + _all_names("concat") + _all_names("readme"))
    if ppt_src.is_file():
        if ppt_src.parent.resolve() == folder.resolve() and ppt_src.name != p.ppt:
            _relocate(ppt_src, ppt_dest)
        else:
            _copy_into(ppt_src, ppt_dest)
    if txt_src.is_file() and txt_src.name not in skip_txt:
        if txt_src.parent.resolve() == folder.resolve() and txt_src.name != p.script:
            _relocate(txt_src, txt_dest)
        else:
            _copy_into(txt_src, txt_dest)

    migrate_readable_names(folder, config)

    dest_images = folder / p.images
    dest_images.mkdir(parents=True, exist_ok=True)
    try:
        ppt_src.resolve().relative_to(OUTPUTS.resolve())
        ppt_in_outputs = ppt_src.is_file()
    except ValueError:
        ppt_in_outputs = False
    if not ppt_in_outputs and not any(dest_images.glob("*.png")):
        legacy_images = ROOT / "ppt_images"
        if legacy_images.is_dir():
            for png in legacy_images.glob("*.png"):
                _copy_into(png, dest_images / png.name)
    normalize_slide_pngs(dest_images, config)

    files["work_dir"] = rel_to_root(folder)
    files["ppt_file"] = rel_to_root(ppt_dest)
    files["input_text"] = rel_to_root(txt_dest)
    files["audio_output"] = rel_to_root(folder / p.audio)
    files["video_output"] = rel_to_root(folder / p.video)
    files["images_dir"] = rel_to_root(dest_images)

    if persist:
        save_config(config, get_config_path())
    return config


def images_dir(config: dict) -> Path:
    p = pack(config)
    files = config.get("files") or {}
    custom = (files.get("images_dir") or "").strip()
    folder = resolve(custom) if custom else work_dir(config) / p.images
    for old in _all_names("images"):
        alt = work_dir(config) / old
        if not folder.is_dir() and alt.is_dir():
            folder = alt
            break
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _lookup(config: dict, key: str, extra_old: list[str] | None = None) -> Path:
    p = pack(config)
    folder = work_dir(config)
    work = folder / p.work
    preferred = work / getattr(p, key)
    candidates = [preferred, folder / getattr(p, key)]
    for old in _all_names(key) + list(extra_old or []):
        candidates.append(work / old)
        candidates.append(folder / old)
    for cand in candidates:
        if cand.exists():
            return cand
    return preferred


def timestamps_path(config: dict) -> Path:
    return _lookup(config, "timestamps", ["timestamps.json"])


def task_id_path(config: dict) -> Path:
    return _lookup(config, "task_id", ["task_id.txt"])


def concat_list_path(config: dict) -> Path:
    return _lookup(config, "concat", ["concat_list_timed.txt"])


def sentence_list_path(config: dict) -> Path:
    return _lookup(config, "sentences", ["sentence_list.txt"])


def normalize_slide_pngs(folder: Path, config: dict | None = None) -> int:
    count = 0
    for path in list(folder.glob("*.png")):
        match = re.search(r"(\d+)", path.stem)
        if not match:
            continue
        if not re.search(r"(?i)slide|第|页", path.stem):
            continue
        dest = folder / slide_png_name(int(match.group(1)), config)
        count += 1
        if dest.resolve() == path.resolve():
            continue
        if dest.exists():
            dest.unlink()
        path.rename(dest)
    return count


def find_slide_image(folder: Path, name: str) -> Path | None:
    direct = folder / name
    if direct.is_file():
        return direct
    match = re.search(r"(\d+)", Path(name).stem)
    if match:
        n = int(match.group(1))
        for cand in (
            folder / slide_png_name(n, lang="zh"),
            folder / slide_png_name(n, lang="en"),
            folder / f"slide_{n}.png",
            folder / f"Slide_{n}.png",
        ):
            if cand.is_file():
                return cand
    stem = Path(name).stem.lower().replace("-", "_")
    for cand in folder.glob("*.png"):
        if cand.stem.lower().replace("-", "_") == stem:
            return cand
    return None
