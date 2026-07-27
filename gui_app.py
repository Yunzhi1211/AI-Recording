# -*- coding: utf-8 -*-
"""
培训视频生成工具 - 无代码 GUI
运行: python gui_app.py
"""
from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from config_loader import load_config, save_config

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

STEPS = [
    ("00_init_check.py", "0. 环境检查"),
    ("01_convert_ppt_to_images.py", "1. 转换 PPT"),
    ("02_submit.py", "2. 提交 TTS"),
    ("03_query.py", "3. 下载音频/句子"),
    ("04_generate_slide_timings.py", "4. 生成时间表"),
    ("05_create_video_ffmpeg.py", "5. 合成视频"),
]

SPEAKER_PRESETS = [
    "zh_female_vv_uranus_bigtts",
    "zh_female_qingxin",
    "zh_male_chunhou",
    "zh_female_shuangkuai",
]

RESOURCE_PRESETS = [
    "seed-tts-2.0",
    "volc.service_type.10029",
]


def default_config() -> dict[str, Any]:
    return {
        "app": {
            "appID": "",
            "accessKey": "",
            "resourceID": "seed-tts-2.0",
            "uid": "123123",
        },
        "files": {
            "input_text": "input.txt",
            "ppt_file": "training.pptx",
            "audio_output": "output.mp3",
            "video_output": "output_video_ffmpeg.mp4",
        },
        "audio": {
            "speaker": "zh_female_vv_uranus_bigtts",
            "sample_rate": 24000,
            "format": "mp3",
        },
        "video_params": {
            "resolution": "854x480",
            "fps": 24,
            "preset": "ultrafast",
            "crf": 30,
            "audio_bitrate": "128k",
        },
        "slide_mapping": [],
    }


class VideoToolApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("培训视频生成工具")
        self.geometry("1180x780")
        self.minsize(960, 640)

        self.project_dir = tk.StringVar(value=SCRIPT_DIR)
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.current_proc: subprocess.Popen | None = None
        self._stop_requested = threading.Event()
        self.status_var = tk.StringVar(value="就绪")
        self._photo = None  # 保持幻灯片预览引用
        self._enlarge_win: tk.Toplevel | None = None
        self._enlarge_photo = None
        self._enlarge_label: ttk.Label | None = None
        self._enlarge_title: tk.StringVar | None = None
        self._enlarge_body: tk.Widget | None = None
        self._preview_resize_job: str | None = None
        self._enlarge_resize_job: str | None = None
        self._preview_last_size = (0, 0)
        self._enlarge_last_size = (0, 0)
        self._ui_syncing = False
        self._rendering_preview = False
        self._shown_slide_path: str | None = None
        self._shown_slide_size = (0, 0)

        self.var_app_id = tk.StringVar()
        self.var_access_key = tk.StringVar()
        self.var_resource = tk.StringVar()
        self.var_speaker = tk.StringVar()
        self.var_ppt = tk.StringVar()
        self.var_input = tk.StringVar()
        self.var_audio_out = tk.StringVar()
        self.var_video_out = tk.StringVar()
        self.var_resolution = tk.StringVar()
        self.var_fps = tk.StringVar()

        self.sentences: list[dict[str, Any]] = []
        self.slide_images: list[str] = []
        self.current_slide_idx = 0
        self.mapping_rows: list[dict[str, Any]] = []

        self._build_ui()
        self._load_project_config()
        self.after(100, self._drain_log_queue)

    # ---------- UI ----------
    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.X)
        ttk.Label(top, text="项目目录:").pack(side=tk.LEFT)
        ttk.Entry(top, textvariable=self.project_dir).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=6
        )
        ttk.Button(top, text="浏览…", command=self._choose_project).pack(side=tk.LEFT)
        ttk.Button(top, text="重新加载", command=self._load_project_config).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        ttk.Button(top, text="保存配置", command=self._save_all).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        ttk.Button(top, text="⏹ 停止等待", command=self._stop_current).pack(
            side=tk.LEFT, padx=(12, 0)
        )
        ttk.Label(top, textvariable=self.status_var).pack(side=tk.LEFT, padx=(12, 0))

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.notebook = notebook

        self.tab_settings = ttk.Frame(notebook, padding=10)
        self.tab_run = ttk.Frame(notebook, padding=10)
        self.tab_map = ttk.Frame(notebook, padding=8)
        notebook.add(self.tab_settings, text="设置")
        notebook.add(self.tab_run, text="运行")
        notebook.add(self.tab_map, text="映射编辑")

        self._build_settings_tab()
        self._build_run_tab()
        self._build_map_tab()

    def _build_settings_tab(self) -> None:
        f = self.tab_settings

        acct = ttk.LabelFrame(f, text="账号与音色（每人不同）", padding=10)
        acct.pack(fill=tk.X, pady=(0, 10))
        self._row(acct, 0, "App ID", self.var_app_id)
        self._row(acct, 1, "Access Key", self.var_access_key, show="*")
        self._combo_row(acct, 2, "Resource ID", self.var_resource, RESOURCE_PRESETS)
        self._combo_row(acct, 3, "音色 speaker", self.var_speaker, SPEAKER_PRESETS)

        files = ttk.LabelFrame(f, text="输入 / 输出文件", padding=10)
        files.pack(fill=tk.X, pady=(0, 10))
        self._file_row(files, 0, "PPT 文件", self.var_ppt, [("PPT", "*.pptx;*.ppt")])
        self._file_row(files, 1, "文稿 TXT", self.var_input, [("Text", "*.txt")])
        self._row(files, 2, "音频输出名", self.var_audio_out)
        self._row(files, 3, "视频输出名", self.var_video_out)

        vid = ttk.LabelFrame(f, text="视频参数（可选）", padding=10)
        vid.pack(fill=tk.X)
        self._row(vid, 0, "分辨率", self.var_resolution)
        self._row(vid, 1, "FPS", self.var_fps)

        tip = ttk.Label(
            f,
            text="提示：\n"
            "1. 请先点「选择…」指定本机真实的 PPT / 文稿路径（不要用默认不存在的 training.pptx）。\n"
            "2. task_id 由「提交 TTS」自动生成，无需手填。\n"
            "3. 步骤 3 轮询较久（状态1=合成中，2=完成）；要改文稿请先点「停止等待」再重新提交。",
            justify=tk.LEFT,
        )
        tip.pack(anchor=tk.W, pady=12)

    def _build_run_tab(self) -> None:
        f = self.tab_run
        btns = ttk.Frame(f)
        btns.pack(fill=tk.X)

        for script, label in STEPS:
            ttk.Button(
                btns,
                text=label,
                command=lambda s=script, l=label: self._run_step(s, l),
            ).pack(side=tk.LEFT, padx=(0, 6), pady=4)

        row2 = ttk.Frame(f)
        row2.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(
            row2,
            text="一键跑到下载(0→3)",
            command=self._run_until_query,
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            row2,
            text="从时间表跑完(4→5)",
            command=self._run_from_timings,
        ).pack(side=tk.LEFT, padx=6)
        ttk.Button(
            row2,
            text="⏹ 停止等待 / 取消任务",
            command=self._stop_current,
        ).pack(side=tk.LEFT, padx=(18, 6))

        ttk.Label(
            f,
            text="建议流程：设置保存 → 一键跑到下载 → 映射编辑 → 从时间表跑完\n"
            "步骤 3 会轮询 API（状态1=合成中，2=完成）。长文稿需等待；改文稿请先「停止」再重新提交。\n"
            "重新打开 GUI 不会丢失已生成文件；日志清空是正常的。若音频/句子已有，直接去「映射编辑」，再点「从时间表跑完」。",
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(8, 4))

        prog = ttk.LabelFrame(f, text="已有产物（重新打开 GUI 后看这里）", padding=6)
        prog.pack(fill=tk.X, pady=(4, 4))
        self.progress_var = tk.StringVar(value="检测中…")
        ttk.Label(prog, textvariable=self.progress_var, justify=tk.LEFT).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(prog, text="刷新检测", command=self._refresh_progress).pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(
            prog,
            text="打开映射编辑",
            command=self._goto_map_tab,
        ).pack(side=tk.RIGHT)

        log_frame = ttk.LabelFrame(f, text="运行日志", padding=6)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=24)
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_map_tab(self) -> None:
        f = self.tab_map
        toolbar = ttk.Frame(f)
        toolbar.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(toolbar, text="刷新句子/幻灯片", command=self._refresh_map_data).pack(
            side=tk.LEFT
        )
        ttk.Button(toolbar, text="将选中句子赋给当前页", command=self._assign_selection).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(toolbar, text="添加映射行", command=self._add_mapping_row).pack(
            side=tk.LEFT
        )
        ttk.Button(toolbar, text="删除选中行", command=self._delete_mapping_row).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(toolbar, text="校验映射", command=self._validate_mapping).pack(
            side=tk.LEFT
        )
        ttk.Button(
            toolbar,
            text="⚡ 按PPT文字自动映射",
            command=self._auto_map_from_ppt,
        ).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="保存映射到配置", command=self._save_mapping_only).pack(
            side=tk.LEFT, padx=6
        )

        paned = ttk.Panedwindow(f, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # 左：句子
        left = ttk.LabelFrame(paned, text="句子列表（编号从 0 开始）", padding=4)
        paned.add(left, weight=2)
        self.sentence_list = tk.Listbox(left, selectmode=tk.EXTENDED, exportselection=False)
        sent_scroll = ttk.Scrollbar(left, command=self.sentence_list.yview)
        self.sentence_list.configure(yscrollcommand=sent_scroll.set)
        self.sentence_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sent_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 中：映射表
        mid = ttk.LabelFrame(paned, text="slide_mapping", padding=4)
        paned.add(mid, weight=2)
        cols = ("page", "start", "end", "slide")
        self.map_tree = ttk.Treeview(mid, columns=cols, show="headings", height=18)
        for c, w, t in (
            ("page", 50, "页"),
            ("start", 60, "start"),
            ("end", 60, "end"),
            ("slide", 140, "图片"),
        ):
            self.map_tree.heading(c, text=t)
            self.map_tree.column(c, width=w, anchor=tk.CENTER)
        map_scroll = ttk.Scrollbar(mid, command=self.map_tree.yview)
        self.map_tree.configure(yscrollcommand=map_scroll.set)
        self.map_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        map_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.map_tree.bind("<<TreeviewSelect>>", self._on_map_select)
        self.map_tree.bind("<Double-1>", self._edit_mapping_cell)

        edit = ttk.Frame(mid)
        edit.pack(fill=tk.X, pady=4)
        ttk.Label(edit, text="start").pack(side=tk.LEFT)
        self.edit_start = ttk.Entry(edit, width=6)
        self.edit_start.pack(side=tk.LEFT, padx=2)
        ttk.Label(edit, text="end").pack(side=tk.LEFT)
        self.edit_end = ttk.Entry(edit, width=6)
        self.edit_end.pack(side=tk.LEFT, padx=2)
        ttk.Button(edit, text="更新选中行", command=self._apply_edit_row).pack(
            side=tk.LEFT, padx=6
        )

        # 右：幻灯片预览
        right = ttk.LabelFrame(paned, text="PPT 预览", padding=4)
        paned.add(right, weight=2)
        nav = ttk.Frame(right)
        nav.pack(fill=tk.X)
        ttk.Button(nav, text="◀", width=3, command=self._prev_slide).pack(side=tk.LEFT)
        self.slide_label_var = tk.StringVar(value="无幻灯片")
        ttk.Label(nav, textvariable=self.slide_label_var).pack(side=tk.LEFT, padx=8)
        ttk.Button(nav, text="▶", width=3, command=self._next_slide).pack(side=tk.LEFT)
        ttk.Button(nav, text="放大查看", command=self._enlarge_slide).pack(
            side=tk.LEFT, padx=(10, 0)
        )
        # 用可伸缩 Frame 承载预览，否则 Label 会跟着图片固定大小不随窗口变
        self.preview_frame = tk.Frame(right, bg="#e8e8e8", highlightthickness=0)
        self.preview_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        self.preview_label = tk.Label(
            self.preview_frame, cursor="hand2", anchor=tk.CENTER, bg="#e8e8e8"
        )
        self.preview_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.preview_frame.bind("<Configure>", self._on_preview_configure)
        self.preview_frame.bind("<Double-Button-1>", lambda _e: self._enlarge_slide())
        self.preview_label.bind("<Double-Button-1>", lambda _e: self._enlarge_slide())
        self.range_preview = tk.Text(right, height=4, wrap=tk.WORD)
        self.range_preview.pack(fill=tk.X)

        hint = ttk.Label(
            f,
            text="用法：在左侧多选句子 → 右侧切到对应 PPT 页 → 点「将选中句子赋给当前页」。"
            "也可双击映射表单元格，或用下方 start/end 编辑后点「更新选中行」。"
            "右侧「放大查看」或双击预览图可打开大图（←/→ 翻页，Esc 关闭）。"
            "若口播与 PPT 文案基本一致，可点「按PPT文字自动映射」再微调。",
            wraplength=1000,
        )
        hint.pack(anchor=tk.W, pady=(6, 0))

    # ---------- helpers ----------
    def _row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        var: tk.StringVar,
        show: str | None = None,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=3)
        ttk.Entry(parent, textvariable=var, show=show or "", width=56).grid(
            row=row, column=1, sticky=tk.EW, padx=6, pady=3
        )
        parent.columnconfigure(1, weight=1)

    def _combo_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        var: tk.StringVar,
        values: list[str],
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=3)
        cb = ttk.Combobox(parent, textvariable=var, values=values, width=54)
        cb.grid(row=row, column=1, sticky=tk.EW, padx=6, pady=3)
        parent.columnconfigure(1, weight=1)

    def _file_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        var: tk.StringVar,
        filetypes: list[tuple[str, str]],
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=3)
        ttk.Entry(parent, textvariable=var, width=48).grid(
            row=row, column=1, sticky=tk.EW, padx=6, pady=3
        )
        ttk.Button(
            parent,
            text="选择…",
            command=lambda: self._pick_file(var, filetypes),
        ).grid(row=row, column=2, pady=3)
        parent.columnconfigure(1, weight=1)

    def _pick_file(self, var: tk.StringVar, filetypes: list[tuple[str, str]]) -> None:
        path = filedialog.askopenfilename(
            initialdir=self.project_dir.get(),
            filetypes=filetypes + [("All", "*.*")],
        )
        if path:
            # 尽量存相对项目目录的路径
            proj = self.project_dir.get()
            try:
                rel = os.path.relpath(path, proj)
                if not rel.startswith(".."):
                    path = rel
            except ValueError:
                pass
            var.set(path.replace("\\", "/"))

    def _choose_project(self) -> None:
        path = filedialog.askdirectory(initialdir=self.project_dir.get())
        if path:
            self.project_dir.set(path)
            self._load_project_config()

    def _config_path(self) -> str:
        return os.path.join(self.project_dir.get(), "config.json")

    def _log(self, msg: str) -> None:
        self.log_queue.put(msg)

    def _drain_log_queue(self) -> None:
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, msg + "\n")
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        self.after(100, self._drain_log_queue)

    # ---------- config ----------
    def _load_project_config(self) -> None:
        path = self._config_path()
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        else:
            cfg = default_config()
            messagebox.showinfo(
                "提示",
                f"未找到 {path}，已加载空白模板。请填写后点「保存配置」。",
            )

        app = cfg.get("app", {})
        files = cfg.get("files", {})
        audio = cfg.get("audio", {})
        video = cfg.get("video_params", {})

        self.var_app_id.set(app.get("appID", ""))
        self.var_access_key.set(app.get("accessKey", ""))
        self.var_resource.set(app.get("resourceID", "seed-tts-2.0"))
        self.var_speaker.set(audio.get("speaker", SPEAKER_PRESETS[0]))
        self.var_ppt.set(files.get("ppt_file", "training.pptx"))
        self.var_input.set(files.get("input_text", "input.txt"))
        self.var_audio_out.set(files.get("audio_output", "output.mp3"))
        self.var_video_out.set(files.get("video_output", "output_video_ffmpeg.mp4"))
        self.var_resolution.set(str(video.get("resolution", "854x480")))
        self.var_fps.set(str(video.get("fps", 24)))

        self.mapping_rows = []
        for i, item in enumerate(cfg.get("slide_mapping", [])):
            if isinstance(item, dict):
                self.mapping_rows.append(
                    {
                        "start": int(item["start"]),
                        "end": int(item["end"]),
                        "slide": item.get("slide") or f"slide_{i + 1}.png",
                    }
                )
            else:
                self.mapping_rows.append(
                    {
                        "start": int(item[0]),
                        "end": int(item[1]),
                        "slide": item[2] if len(item) > 2 else f"slide_{i + 1}.png",
                    }
                )

        self._refresh_map_data()
        self._refresh_progress()
        self._log(f"已加载配置: {path}")

    def _goto_map_tab(self) -> None:
        self.notebook.select(self.tab_map)
        self._refresh_map_data()
        self._refresh_progress()

    def _refresh_progress(self) -> None:
        """根据磁盘上已有文件提示当前可从哪一步继续。"""
        if not hasattr(self, "progress_var"):
            return
        proj = self.project_dir.get()
        files_cfg = {
            "ppt": self._resolve_path(self.var_ppt.get().strip()),
            "txt": self._resolve_path(self.var_input.get().strip()),
            "audio": self._resolve_path(self.var_audio_out.get().strip() or "output.mp3"),
            "video": self._resolve_path(
                self.var_video_out.get().strip() or "output_video_ffmpeg.mp4"
            ),
        }
        checks = [
            ("PPT", os.path.isfile(files_cfg["ppt"])),
            ("文稿", os.path.isfile(files_cfg["txt"])),
            (
                "PPT图片",
                os.path.isdir(os.path.join(proj, "ppt_images"))
                and any(
                    n.lower().endswith(".png")
                    for n in os.listdir(os.path.join(proj, "ppt_images"))
                )
                if os.path.isdir(os.path.join(proj, "ppt_images"))
                else False,
            ),
            ("task_id", os.path.isfile(os.path.join(proj, "task_id.txt"))),
            ("音频", os.path.isfile(files_cfg["audio"])),
            ("句子时间戳", os.path.isfile(os.path.join(proj, "timestamps.json"))),
            ("映射", bool(self.mapping_rows)),
            ("时间表", os.path.isfile(os.path.join(proj, "concat_list_timed.txt"))),
            ("视频", os.path.isfile(files_cfg["video"])),
        ]
        parts = [f"{'✅' if ok else '⬜'}{name}" for name, ok in checks]
        has_audio = os.path.isfile(files_cfg["audio"]) and os.path.isfile(
            os.path.join(proj, "timestamps.json")
        )
        if has_audio and self.mapping_rows:
            tip = "→ 可直接点「从时间表跑完(4→5)」；若要改映射先打开「映射编辑」。"
        elif has_audio:
            tip = "→ 音频已有，请打开「映射编辑」设置映射，再点「从时间表跑完(4→5)」。无需重跑 TTS。"
        elif os.path.isfile(os.path.join(proj, "task_id.txt")):
            tip = "→ 已有 task_id，可只点「3. 下载音频/句子」。"
        else:
            tip = "→ 请从「一键跑到下载(0→3)」开始。"
        self.progress_var.set("  ".join(parts) + "\n" + tip)
    def _collect_config(self) -> dict[str, Any]:
        # 保留原 config 中未编辑的字段
        path = self._config_path()
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        else:
            cfg = default_config()

        cfg.setdefault("app", {})
        cfg.setdefault("files", {})
        cfg.setdefault("audio", {})
        cfg.setdefault("video_params", {})

        cfg["app"]["appID"] = self.var_app_id.get().strip()
        cfg["app"]["accessKey"] = self.var_access_key.get().strip()
        cfg["app"]["resourceID"] = self.var_resource.get().strip()
        cfg["app"].setdefault("uid", "123123")

        cfg["files"]["ppt_file"] = self.var_ppt.get().strip()
        cfg["files"]["input_text"] = self.var_input.get().strip()
        cfg["files"]["audio_output"] = self.var_audio_out.get().strip()
        cfg["files"]["video_output"] = self.var_video_out.get().strip()

        cfg["audio"]["speaker"] = self.var_speaker.get().strip()
        cfg["audio"].setdefault("sample_rate", 24000)
        cfg["audio"].setdefault("format", "mp3")

        cfg["video_params"]["resolution"] = self.var_resolution.get().strip()
        try:
            cfg["video_params"]["fps"] = int(self.var_fps.get().strip())
        except ValueError:
            cfg["video_params"]["fps"] = 24

        cfg["slide_mapping"] = [
            {
                "start": int(r["start"]),
                "end": int(r["end"]),
                "slide": r["slide"],
            }
            for r in self.mapping_rows
        ]
        return cfg

    def _save_all(self) -> None:
        cfg = self._collect_config()
        path = self._config_path()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        save_config(cfg, path)
        self._log(f"✅ 配置已保存: {path}")
        messagebox.showinfo("保存成功", f"已写入\n{path}")

    def _save_mapping_only(self) -> None:
        self._save_all()

    # ---------- run pipeline ----------
    def _busy(self) -> bool:
        return self.worker is not None and self.worker.is_alive()

    def _resolve_path(self, name: str) -> str:
        if not name:
            return ""
        if os.path.isabs(name):
            return name
        return os.path.join(self.project_dir.get(), name)

    def _ensure_input_files(self, need_ppt: bool = False, need_text: bool = False) -> bool:
        """缺文件时弹窗让用户选择；成功则写回变量并保存。"""
        if need_ppt:
            ppt = self._resolve_path(self.var_ppt.get().strip())
            if not os.path.isfile(ppt):
                messagebox.showwarning(
                    "缺少 PPT",
                    f"未找到 PPT：\n{ppt or '(空)'}\n\n请选择实际的 .pptx 文件。",
                )
                path = filedialog.askopenfilename(
                    title="选择 PPT 文件",
                    initialdir=self.project_dir.get(),
                    filetypes=[
                        ("PowerPoint", "*.pptx;*.ppt"),
                        ("All", "*.*"),
                    ],
                )
                if not path:
                    return False
                proj = self.project_dir.get()
                try:
                    rel = os.path.relpath(path, proj)
                    path = rel if not rel.startswith("..") else path
                except ValueError:
                    pass
                self.var_ppt.set(path.replace("\\", "/"))
                self._save_all_silent()
                self._log(f"✅ 已选择 PPT: {self.var_ppt.get()}")

        if need_text:
            txt = self._resolve_path(self.var_input.get().strip())
            if not os.path.isfile(txt):
                messagebox.showwarning(
                    "缺少文稿",
                    f"未找到文稿：\n{txt or '(空)'}\n\n请选择 input.txt。",
                )
                path = filedialog.askopenfilename(
                    title="选择文稿 TXT",
                    initialdir=self.project_dir.get(),
                    filetypes=[("Text", "*.txt"), ("All", "*.*")],
                )
                if not path:
                    return False
                proj = self.project_dir.get()
                try:
                    rel = os.path.relpath(path, proj)
                    path = rel if not rel.startswith("..") else path
                except ValueError:
                    pass
                self.var_input.set(path.replace("\\", "/"))
                self._save_all_silent()
                self._log(f"✅ 已选择文稿: {self.var_input.get()}")
        return True

    def _needs_for_steps(self, steps: list[tuple[str, str]]) -> tuple[bool, bool]:
        scripts = {s for s, _ in steps}
        need_ppt = bool(scripts & {"00_init_check.py", "01_convert_ppt_to_images.py"})
        need_text = bool(scripts & {"00_init_check.py", "02_submit.py"})
        return need_ppt, need_text

    def _clear_stop_flag(self) -> None:
        flag = os.path.join(self.project_dir.get(), "stop_query.flag")
        if os.path.isfile(flag):
            try:
                os.remove(flag)
            except OSError:
                pass

    def _stop_current(self) -> None:
        """停止当前等待/任务（写停止标记 + 终止子进程）。"""
        if not self._busy() and self.current_proc is None:
            messagebox.showinfo("提示", "当前没有正在运行的任务。")
            return

        self._stop_requested.set()
        flag = os.path.join(self.project_dir.get(), "stop_query.flag")
        try:
            with open(flag, "w", encoding="utf-8") as f:
                f.write("stop")
            self._log("⏹ 已写入停止标记 stop_query.flag")
        except OSError as e:
            self._log(f"⚠️ 无法写停止标记: {e}")

        proc = self.current_proc
        if proc is not None and proc.poll() is None:
            self._log("⏹ 正在终止当前进程…")
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception as e:
                self._log(f"⚠️ 终止进程失败: {e}")

        self.status_var.set("已请求停止")
        self._log("⏹ 已请求停止。改完文稿后可重新「2. 提交 TTS」再「3. 下载」。")

    def _run_step(self, script: str, label: str) -> None:
        if self._busy():
            messagebox.showwarning("忙", "已有任务在运行，请先「停止等待」或稍候。")
            return
        need_ppt, need_text = self._needs_for_steps([(script, label)])
        if not self._ensure_input_files(need_ppt=need_ppt, need_text=need_text):
            return
        self._save_all_silent()
        self._stop_requested.clear()
        self._clear_stop_flag()
        self.status_var.set(f"运行中: {label}")
        self.worker = threading.Thread(
            target=self._run_scripts, args=([(script, label)],), daemon=True
        )
        self.worker.start()

    def _run_until_query(self) -> None:
        if self._busy():
            messagebox.showwarning("忙", "已有任务在运行，请先「停止等待」或稍候。")
            return
        if not self._ensure_input_files(need_ppt=True, need_text=True):
            return
        self._save_all_silent()
        self._stop_requested.clear()
        self._clear_stop_flag()
        self.status_var.set("运行中: 0→3")
        self.worker = threading.Thread(
            target=self._run_scripts, args=(STEPS[:4],), daemon=True
        )
        self.worker.start()

    def _run_from_timings(self) -> None:
        if self._busy():
            messagebox.showwarning("忙", "已有任务在运行，请先「停止等待」或稍候。")
            return
        ok, msg = self._validate_mapping(silent=True)
        if not ok:
            messagebox.showerror("映射无效", msg)
            return
        self._save_all_silent()
        self._stop_requested.clear()
        self._clear_stop_flag()
        self.status_var.set("运行中: 4→5")
        self.worker = threading.Thread(
            target=self._run_scripts, args=(STEPS[4:],), daemon=True
        )
        self.worker.start()

    def _save_all_silent(self) -> None:
        cfg = self._collect_config()
        save_config(cfg, self._config_path())
        self._log(f"已自动保存配置: {self._config_path()}")

    def _run_scripts(self, steps: list[tuple[str, str]]) -> None:
        proj = self.project_dir.get()
        env = os.environ.copy()
        env["VIDEO_TOOL_CONFIG"] = self._config_path()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"

        for script, label in steps:
            if self._stop_requested.is_set():
                self._log("⏹ 后续步骤已取消")
                self.after(0, lambda: self.status_var.set("已停止"))
                return

            script_path = os.path.join(SCRIPT_DIR, script)
            if not os.path.isfile(script_path):
                self._log(f"❌ 找不到脚本: {script_path}")
                self.after(0, lambda: self.status_var.set("失败"))
                return

            self._log(f"\n========== {label} ==========")
            self.after(0, lambda l=label: self.status_var.set(f"运行中: {l}"))
            try:
                proc = subprocess.Popen(
                    [sys.executable, "-u", script_path],
                    cwd=proj,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.current_proc = proc
                assert proc.stdout is not None
                for line in proc.stdout:
                    self._log(line.rstrip())
                code = proc.wait()
                self.current_proc = None

                if self._stop_requested.is_set() or code == 130:
                    self._log(f"⏹ {label} 已停止")
                    self.after(0, lambda: self.status_var.set("已停止"))
                    return
                if code != 0:
                    self._log(f"❌ {label} 失败，退出码 {code}")
                    self.after(0, lambda: self.status_var.set("失败"))
                    return
                self._log(f"✅ {label} 完成")
            except Exception as e:
                self.current_proc = None
                self._log(f"❌ 执行异常: {e}")
                self.after(0, lambda: self.status_var.set("失败"))
                return

        if any(s == "03_query.py" for s, _ in steps):
            self.after(0, self._refresh_map_data)
        self._log("\n🎉 所选步骤全部完成")
        self.after(0, lambda: self.status_var.set("就绪"))
        self.after(0, self._refresh_progress)
    # ---------- mapping ----------
    def _refresh_map_data(self) -> None:
        proj = self.project_dir.get()
        ts_path = os.path.join(proj, "timestamps.json")
        self.sentences = []
        if os.path.isfile(ts_path):
            with open(ts_path, "r", encoding="utf-8") as f:
                self.sentences = json.load(f)

        self.sentence_list.delete(0, tk.END)
        if not self.sentences:
            self.sentence_list.insert(
                tk.END, "（尚无 timestamps.json，请先运行「3. 下载音频/句子」）"
            )
        else:
            for i, s in enumerate(self.sentences):
                text = s.get("text", "").replace("\n", " ").strip()
                preview = text[:50] + ("…" if len(text) > 50 else "")
                st = s.get("startTime", 0)
                et = s.get("endTime", 0)
                self.sentence_list.insert(
                    tk.END, f"{i:>4}: {preview}  ({st:.2f}s–{et:.2f}s)"
                )

        img_dir = os.path.join(proj, "ppt_images")
        self.slide_images = []
        if os.path.isdir(img_dir):
            names = sorted(
                n
                for n in os.listdir(img_dir)
                if n.lower().endswith(".png") and n.lower().startswith("slide_")
            )
            # 按页码数字排序
            def page_num(name: str) -> int:
                try:
                    return int(os.path.splitext(name)[0].split("_")[1])
                except Exception:
                    return 0

            names.sort(key=page_num)
            self.slide_images = [os.path.join(img_dir, n) for n in names]

        if self.current_slide_idx >= len(self.slide_images):
            self.current_slide_idx = 0
        self._reload_map_tree()
        # 延后渲染预览，避免启动时布局未完成引发 Configure 循环卡死
        self.after(50, self._show_slide)

    def _reload_map_tree(self) -> None:
        for item in self.map_tree.get_children():
            self.map_tree.delete(item)
        for i, row in enumerate(self.mapping_rows):
            self.map_tree.insert(
                "",
                tk.END,
                iid=str(i),
                values=(i + 1, row["start"], row["end"], row["slide"]),
            )

    def _show_slide(self) -> None:
        if self._ui_syncing:
            return
        if not self.slide_images:
            self.slide_label_var.set("无幻灯片（请先转换 PPT）")
            self.preview_label.configure(image="", text="暂无预览")
            self._photo = None
            return

        path = self.slide_images[self.current_slide_idx]
        name = os.path.basename(path)
        self.slide_label_var.set(
            f"{self.current_slide_idx + 1} / {len(self.slide_images)}  {name}"
        )
        self._render_preview_image(force=True)
        self._sync_range_preview_for_slide()

        if self._enlarge_win is not None and self._enlarge_win.winfo_exists():
            self._refresh_enlarge_view()

    def _slide_page_num(self, name: str) -> int | None:
        """从 slide_12.png / Slide_12.PNG 解析页码。"""
        base = os.path.splitext(os.path.basename(name))[0]
        parts = base.replace("-", "_").split("_")
        for part in reversed(parts):
            if part.isdigit():
                return int(part)
        return None

    def _find_slide_index(self, slide_name: str) -> int | None:
        """按文件名（忽略大小写）或页码数字匹配幻灯片。"""
        if not slide_name or not self.slide_images:
            return None
        target = os.path.basename(slide_name).lower()
        for i, path in enumerate(self.slide_images):
            if os.path.basename(path).lower() == target:
                return i
        want = self._slide_page_num(slide_name)
        if want is not None:
            for i, path in enumerate(self.slide_images):
                if self._slide_page_num(path) == want:
                    return i
            # 页码按 1-based，列表下标 0-based
            if 1 <= want <= len(self.slide_images):
                return want - 1
        return None

    def _sync_range_preview_for_slide(self) -> None:
        """根据当前 PPT 页，更新下方句子栏，并尽量选中对应映射行。"""
        if self._ui_syncing or not self.slide_images:
            return
        slide_name = os.path.basename(self.slide_images[self.current_slide_idx])
        page_no = self._slide_page_num(slide_name)

        matched_row = None
        matched_idx = None
        for i, row in enumerate(self.mapping_rows):
            row_slide = str(row.get("slide", ""))
            if os.path.basename(row_slide).lower() == slide_name.lower():
                matched_row, matched_idx = row, i
                break
            if page_no is not None and self._slide_page_num(row_slide) == page_no:
                matched_row, matched_idx = row, i
                break

        self.range_preview.delete("1.0", tk.END)
        self.sentence_list.selection_clear(0, tk.END)

        if matched_row is None:
            self.range_preview.insert(
                "1.0",
                f"（当前 {slide_name} 尚无映射。左侧多选句子后点「将选中句子赋给当前页」）",
            )
            return

        if matched_idx is not None:
            iid = str(matched_idx)
            if self.map_tree.exists(iid):
                cur = self.map_tree.selection()
                if not cur or cur[0] != iid:
                    self._ui_syncing = True
                    try:
                        self.map_tree.selection_set(iid)
                        self.map_tree.see(iid)
                    finally:
                        self._ui_syncing = False
                self.edit_start.delete(0, tk.END)
                self.edit_start.insert(0, str(matched_row["start"]))
                self.edit_end.delete(0, tk.END)
                self.edit_end.insert(0, str(matched_row["end"]))

        start, end = int(matched_row["start"]), int(matched_row["end"])
        lines = []
        if self.sentences:
            for i in range(start, end + 1):
                if 0 <= i < len(self.sentences):
                    self.sentence_list.selection_set(i)
                    self.sentence_list.see(i)
                    lines.append(f"[{i}] {self.sentences[i].get('text', '')}")
        if lines:
            self.range_preview.insert("1.0", "\n".join(lines))
        else:
            self.range_preview.insert(
                "1.0", f"（映射句子 {start}–{end}，但尚未加载 timestamps.json）"
            )

    def _preview_target_size(self) -> tuple[int, int]:
        # 不要调用 update_idletasks，否则会触发 Configure 死循环导致 Not Responding
        w = self.preview_frame.winfo_width()
        h = self.preview_frame.winfo_height()
        if w < 50 or h < 50:
            return 420, 280
        return max(80, w - 8), max(60, h - 8)

    def _render_preview_image(self, force: bool = False) -> None:
        if self._rendering_preview or not self.slide_images:
            return
        path = self.slide_images[self.current_slide_idx]
        max_w, max_h = self._preview_target_size()
        if (
            not force
            and self._shown_slide_path == path
            and abs(max_w - self._shown_slide_size[0]) < 24
            and abs(max_h - self._shown_slide_size[1]) < 24
        ):
            return

        self._rendering_preview = True
        self._preview_last_size = (max_w, max_h)
        try:
            img = self._load_slide_photo(path, max_w=max_w, max_h=max_h)
            self._photo = img
            self.preview_label.configure(image=self._photo, text="")
            self._shown_slide_path = path
            self._shown_slide_size = (max_w, max_h)
        except Exception as e:
            self._photo = None
            self._shown_slide_path = None
            self.preview_label.configure(image="", text=f"无法预览:\n{e}")
        finally:
            self._rendering_preview = False

    def _on_preview_configure(self, event: tk.Event) -> None:
        if event.widget is not self.preview_frame:
            return
        if self._rendering_preview or self._ui_syncing:
            return
        if event.width < 40 or event.height < 40:
            return
        size = (max(80, event.width - 8), max(60, event.height - 8))
        if abs(size[0] - self._preview_last_size[0]) < 24 and abs(
            size[1] - self._preview_last_size[1]
        ) < 24:
            return
        self._preview_last_size = size
        if self._preview_resize_job is not None:
            try:
                self.after_cancel(self._preview_resize_job)
            except Exception:
                pass
        self._preview_resize_job = self.after(
            150, lambda: self._render_preview_image(force=False)
        )

    def _load_slide_photo(
        self, path: str, max_w: int, max_h: int
    ) -> tk.PhotoImage:
        max_w = max(40, int(max_w))
        max_h = max(40, int(max_h))
        try:
            from PIL import Image, ImageTk

            with Image.open(path) as im:
                im = im.convert("RGB")
                try:
                    # BILINEAR 比 LANCZOS 快很多，避免大图反复缩放卡死界面
                    resample = Image.Resampling.BILINEAR
                except AttributeError:
                    resample = Image.BILINEAR  # type: ignore[attr-defined]
                im.thumbnail((max_w, max_h), resample)
                return ImageTk.PhotoImage(im)
        except Exception:
            # 无 Pillow 时退回整数缩小（精度较差但可随窗口变）
            img = tk.PhotoImage(file=path)
            w, h = img.width(), img.height()
            factor = max(1, (w + max_w - 1) // max_w, (h + max_h - 1) // max_h)
            if factor > 1:
                img = img.subsample(factor, factor)
            # 若仍偏小且可 zoom（整数倍），尽量贴近目标宽度
            if img.width() * 2 <= max_w and img.height() * 2 <= max_h:
                zoom = min(max_w // max(img.width(), 1), max_h // max(img.height(), 1))
                zoom = max(1, min(zoom, 4))
                if zoom > 1:
                    img = img.zoom(zoom, zoom)
            return img

    def _enlarge_slide(self) -> None:
        if not self.slide_images:
            messagebox.showinfo("提示", "暂无幻灯片，请先转换 PPT。")
            return

        if self._enlarge_win is not None and self._enlarge_win.winfo_exists():
            self._enlarge_win.lift()
            self._enlarge_win.focus_force()
            self._refresh_enlarge_view()
            return

        win = tk.Toplevel(self)
        win.title("PPT 放大预览（可拖动窗口边缘缩放）")
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        win.geometry(f"{min(sw - 80, 1280)}x{min(sh - 100, 860)}")
        win.transient(self)

        bar = ttk.Frame(win, padding=6)
        bar.pack(fill=tk.X)
        ttk.Button(bar, text="◀ 上一页", command=self._prev_slide).pack(side=tk.LEFT)
        title = tk.StringVar()
        ttk.Label(bar, textvariable=title).pack(side=tk.LEFT, padx=12)
        ttk.Button(bar, text="下一页 ▶", command=self._next_slide).pack(side=tk.LEFT)
        ttk.Button(bar, text="关闭", command=win.destroy).pack(side=tk.RIGHT)

        tip = ttk.Label(bar, text="拖动窗口边缘可放大缩小图片")
        tip.pack(side=tk.RIGHT, padx=12)

        body = tk.Frame(win, bg="#222222")
        body.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        label = tk.Label(body, anchor=tk.CENTER, bg="#222222")
        label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self._enlarge_win = win
        self._enlarge_label = label
        self._enlarge_title = title
        self._enlarge_body = body
        self._enlarge_last_size = (0, 0)

        def on_close() -> None:
            self._enlarge_win = None
            self._enlarge_label = None
            self._enlarge_title = None
            self._enlarge_photo = None
            self._enlarge_body = None
            win.destroy()

        def on_body_configure(event: tk.Event) -> None:
            if event.widget is not body:
                return
            if event.width < 40 or event.height < 40:
                return
            size = (event.width, event.height)
            if abs(size[0] - self._enlarge_last_size[0]) < 12 and abs(
                size[1] - self._enlarge_last_size[1]
            ) < 12:
                return
            if self._enlarge_resize_job is not None:
                try:
                    self.after_cancel(self._enlarge_resize_job)
                except Exception:
                    pass
            self._enlarge_resize_job = self.after(80, self._refresh_enlarge_view)

        win.protocol("WM_DELETE_WINDOW", on_close)
        win.bind("<Left>", lambda _e: self._prev_slide())
        win.bind("<Right>", lambda _e: self._next_slide())
        win.bind("<Escape>", lambda _e: on_close())
        body.bind("<Configure>", on_body_configure)

        self._refresh_enlarge_view()

    def _refresh_enlarge_view(self) -> None:
        if (
            self._enlarge_win is None
            or not self._enlarge_win.winfo_exists()
            or self._enlarge_label is None
            or not self.slide_images
        ):
            return

        path = self.slide_images[self.current_slide_idx]
        name = os.path.basename(path)
        if self._enlarge_title is not None:
            self._enlarge_title.set(
                f"{self.current_slide_idx + 1} / {len(self.slide_images)}  {name}"
            )

        if self._enlarge_body is not None:
            max_w = max(200, self._enlarge_body.winfo_width() - 8)
            max_h = max(150, self._enlarge_body.winfo_height() - 8)
        else:
            max_w = max(600, self._enlarge_win.winfo_width() - 40)
            max_h = max(400, self._enlarge_win.winfo_height() - 100)

        if max_w < 50 or max_h < 50:
            max_w, max_h = 1000, 700

        self._enlarge_last_size = (max_w, max_h)
        try:
            self._enlarge_photo = self._load_slide_photo(path, max_w=max_w, max_h=max_h)
            self._enlarge_label.configure(image=self._enlarge_photo, text="")
        except Exception as e:
            self._enlarge_photo = None
            self._enlarge_label.configure(image="", text=f"无法预览:\n{e}")

    def _prev_slide(self) -> None:
        if not self.slide_images:
            return
        self.current_slide_idx = (self.current_slide_idx - 1) % len(self.slide_images)
        self._show_slide()

    def _next_slide(self) -> None:
        if not self.slide_images:
            return
        self.current_slide_idx = (self.current_slide_idx + 1) % len(self.slide_images)
        self._show_slide()

    def _on_map_select(self, _event=None) -> None:
        if self._ui_syncing:
            return
        sel = self.map_tree.selection()
        if not sel:
            return
        try:
            idx = int(sel[0])
        except (TypeError, ValueError):
            return
        if idx < 0 or idx >= len(self.mapping_rows):
            return
        row = self.mapping_rows[idx]
        self.edit_start.delete(0, tk.END)
        self.edit_start.insert(0, str(row["start"]))
        self.edit_end.delete(0, tk.END)
        self.edit_end.insert(0, str(row["end"]))

        found = self._find_slide_index(str(row.get("slide", "")))
        if found is None:
            found = min(idx, len(self.slide_images) - 1) if self.slide_images else None
        if found is not None:
            if found == self.current_slide_idx:
                # 页未变，只刷新句子栏，避免重复重绘大图
                self._sync_range_preview_for_slide()
            else:
                self.current_slide_idx = found
                self._show_slide()
        else:
            self.range_preview.delete("1.0", tk.END)
            self.sentence_list.selection_clear(0, tk.END)
            start, end = int(row["start"]), int(row["end"])
            lines = []
            if self.sentences:
                for i in range(start, end + 1):
                    if 0 <= i < len(self.sentences):
                        self.sentence_list.selection_set(i)
                        self.sentence_list.see(i)
                        lines.append(f"[{i}] {self.sentences[i].get('text', '')}")
            self.range_preview.insert("1.0", "\n".join(lines) if lines else "（无句子）")

    def _edit_mapping_cell(self, _event=None) -> None:
        # 双击时用右侧输入框编辑即可
        self._on_map_select()

    def _apply_edit_row(self) -> None:
        sel = self.map_tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选中一行映射。")
            return
        try:
            start = int(self.edit_start.get().strip())
            end = int(self.edit_end.get().strip())
        except ValueError:
            messagebox.showerror("错误", "start/end 必须是整数。")
            return
        if start > end:
            messagebox.showerror("错误", "start 不能大于 end。")
            return
        idx = int(sel[0])
        self.mapping_rows[idx]["start"] = start
        self.mapping_rows[idx]["end"] = end
        self._reload_map_tree()
        self.map_tree.selection_set(str(idx))
        self._on_map_select()

    def _assign_selection(self) -> None:
        if not self.sentences:
            messagebox.showwarning("提示", "请先下载句子时间戳。")
            return
        if not self.slide_images:
            messagebox.showwarning("提示", "请先转换 PPT 图片。")
            return
        idxs = sorted(int(i) for i in self.sentence_list.curselection())
        if not idxs:
            messagebox.showinfo("提示", "请在左侧多选句子。")
            return
        start, end = idxs[0], idxs[-1]
        slide_name = os.path.basename(self.slide_images[self.current_slide_idx])
        page_no = self.current_slide_idx  # 0-based → 映射行优先按页序

        # 若已有该 slide 行则更新，否则插入到对应位置
        found = None
        for i, row in enumerate(self.mapping_rows):
            if row["slide"] == slide_name:
                found = i
                break
        new_row = {"start": start, "end": end, "slide": slide_name}
        if found is not None:
            self.mapping_rows[found] = new_row
            target = found
        else:
            # 按页码插入
            insert_at = len(self.mapping_rows)
            for i, row in enumerate(self.mapping_rows):
                try:
                    n = int(os.path.splitext(row["slide"])[0].split("_")[1])
                except Exception:
                    n = i + 1
                if page_no + 1 < n:
                    insert_at = i
                    break
            self.mapping_rows.insert(insert_at, new_row)
            target = insert_at

        self._reload_map_tree()
        self.map_tree.selection_set(str(target))
        self._on_map_select()
        self._log(f"已映射 {slide_name}: 句子 {start}–{end}")

    def _auto_map_from_ppt(self) -> None:
        """根据 PPT 每页文字与口播句子自动生成 slide_mapping。"""
        if not self.sentences:
            messagebox.showwarning(
                "提示", "请先完成「3. 下载音频/句子」，确保有 timestamps.json。"
            )
            return

        ppt = self._resolve_path(self.var_ppt.get().strip())
        if not ppt or not os.path.isfile(ppt):
            if not self._ensure_input_files(need_ppt=True, need_text=False):
                return
            ppt = self._resolve_path(self.var_ppt.get().strip())
        if not os.path.isfile(ppt):
            messagebox.showerror("错误", "未找到 PPT 文件。")
            return

        if self.mapping_rows:
            ok = messagebox.askyesno(
                "确认",
                "将用自动匹配结果覆盖当前映射表（可先保存配置备份）。\n是否继续？",
            )
            if not ok:
                return

        self.status_var.set("自动映射中…")
        self.update_idletasks()
        try:
            from auto_map import auto_map_sentences, extract_slide_texts

            slide_texts = extract_slide_texts(ppt)
            detailed, warnings = auto_map_sentences(slide_texts, self.sentences)
            clean = [
                {
                    "start": int(m["start"]),
                    "end": int(m["end"]),
                    "slide": m["slide"],
                }
                for m in detailed
            ]
        except ImportError:
            self.status_var.set("就绪")
            messagebox.showerror(
                "缺少依赖",
                "需要安装 python-pptx：\n\npip install python-pptx",
            )
            return
        except Exception as e:
            self.status_var.set("就绪")
            messagebox.showerror("自动映射失败", str(e))
            self._log(f"❌ 自动映射失败: {e}")
            return

        if not clean:
            self.status_var.set("就绪")
            msg = "\n".join(warnings) if warnings else "未生成映射。"
            messagebox.showwarning("无结果", msg)
            return

        # 若已有 ppt 图片数量与页数不一致，给出提示，仍按 PPT 页数建映射
        n_img = len(self.slide_images)
        n_map = len(clean)
        if n_img and n_img != n_map:
            warnings.append(
                f"PPT 页数={n_map}，ppt_images 图片数={n_img}，请确认已重新「转换 PPT」。"
            )

        self.mapping_rows = clean
        self._reload_map_tree()
        self.current_slide_idx = 0
        self._show_slide()
        self._refresh_progress()

        weak = [m for m in detailed if m.get("weak")]
        lines = [
            f"已生成 {len(clean)} 页映射（句子共 {len(self.sentences)} 句）。",
            f"弱匹配页数: {len(weak)}（建议优先检查）。",
        ]
        if warnings:
            lines.append("")
            lines.extend(warnings[:12])
            if len(warnings) > 12:
                lines.append(f"…另有 {len(warnings) - 12} 条提示")
        # 分数摘要
        if detailed:
            scores = [float(m.get("score") or 0) for m in detailed]
            lines.append("")
            lines.append(
                f"匹配分: 平均 {sum(scores)/len(scores):.2f}，"
                f"最低 {min(scores):.2f}（第 {scores.index(min(scores))+1} 页）"
            )

        summary = "\n".join(lines)
        self._log("⚡ 自动映射完成\n" + summary)
        self.status_var.set("就绪")
        messagebox.showinfo("自动映射完成", summary + "\n\n请在映射表中微调后「保存映射到配置」。")

    def _add_mapping_row(self) -> None:
        n = len(self.mapping_rows) + 1
        slide = f"slide_{n}.png"
        if self.slide_images and self.current_slide_idx < len(self.slide_images):
            slide = os.path.basename(self.slide_images[self.current_slide_idx])
        self.mapping_rows.append({"start": 0, "end": 0, "slide": slide})
        self._reload_map_tree()
        self.map_tree.selection_set(str(len(self.mapping_rows) - 1))

    def _delete_mapping_row(self) -> None:
        sel = self.map_tree.selection()
        if not sel:
            return
        idxs = sorted((int(i) for i in sel), reverse=True)
        for i in idxs:
            del self.mapping_rows[i]
        self._reload_map_tree()

    def _validate_mapping(self, silent: bool = False) -> tuple[bool, str]:
        if not self.mapping_rows:
            msg = "slide_mapping 为空。"
            if not silent:
                messagebox.showerror("校验失败", msg)
            return False, msg

        n = len(self.sentences)
        if n == 0:
            msg = "没有句子数据（timestamps.json），无法完整校验索引范围。"
            # 仍允许保存结构，但跑 4 前需要句子
            if not silent:
                messagebox.showwarning("校验警告", msg)
            return False, msg

        covered = [-1] * n
        for page_i, row in enumerate(self.mapping_rows):
            s, e = int(row["start"]), int(row["end"])
            if s < 0 or e >= n or s > e:
                msg = f"第 {page_i + 1} 行索引非法: {s}–{e}（共 {n} 句）"
                if not silent:
                    messagebox.showerror("校验失败", msg)
                return False, msg
            for i in range(s, e + 1):
                if covered[i] >= 0:
                    msg = f"句子 {i} 被第 {covered[i] + 1} 页和第 {page_i + 1} 页重复覆盖"
                    if not silent:
                        messagebox.showerror("校验失败", msg)
                    return False, msg
                covered[i] = page_i

        gaps = [i for i, v in enumerate(covered) if v < 0]
        if gaps:
            preview = gaps[:12]
            more = "…" if len(gaps) > 12 else ""
            msg = f"有 {len(gaps)} 个句子未覆盖: {preview}{more}"
            if not silent:
                messagebox.showwarning("校验警告", msg)
            return False, msg

        msg = f"✅ 映射有效：{len(self.mapping_rows)} 页，覆盖 {n} 句，无重叠无空洞。"
        if not silent:
            messagebox.showinfo("校验通过", msg)
        return True, msg


def main() -> None:
    app = VideoToolApp()
    app.mainloop()


if __name__ == "__main__":
    main()
