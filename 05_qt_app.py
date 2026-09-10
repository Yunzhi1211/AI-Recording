# -*- coding: utf-8 -*-
"""Iris Studio — from idea to video."""
from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, QRectF, Qt, QThread, QTimer, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QDesktopServices, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPalette
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

_cloud = importlib.import_module("03_cloud")
_db = importlib.import_module("02_library_db")
_wp = importlib.import_module("00_work_paths")

current_user = _cloud.current_user
delete_cloud_post = _cloud.delete_cloud_post
find_banned = _cloud.find_banned
insert_cloud_post = _cloud.insert_cloud_post
is_configured = _cloud.is_configured
list_cloud_posts = _cloud.list_cloud_posts
normalize_supabase_url = _cloud.normalize_supabase_url
sign_in = _cloud.sign_in
sign_out = _cloud.sign_out
sign_up = _cloud.sign_up
too_short = _cloud.too_short
add_post = _db.add_post
delete_post = _db.delete_post
delete_work = _db.delete_work
get_post = _db.get_post
get_work = _db.get_work
init_db = _db.init_db
list_posts = _db.list_posts
list_works = _db.list_works
save_notes = _db.save_notes
upsert_work = _db.upsert_work
AUDIO_NAME = _wp.AUDIO_NAME
VIDEO_NAME = _wp.VIDEO_NAME
images_dir = _wp.images_dir
load_config = _wp.load_config
materialize_work = _wp.materialize_work
rel_to_root = _wp.rel_to_root
save_config = _wp.save_config
slide_png_name = _wp.slide_png_name
timestamps_path = _wp.timestamps_path
ui_lang = _wp.ui_lang

ROOT = Path(__file__).resolve().parent
STEP_SCRIPTS = ["00", "01", "02", "03", "04", "05"]
STEP_TITLES = {
    "00": "job_00",
    "01": "job_01",
    "02": "job_02",
    "03": "job_03",
    "04": "job_04",
    "05": "job_05",
}
SPEAKERS = [
    "zh_female_vv_uranus_bigtts",
    "zh_female_qingxin",
    "zh_male_chunhou",
    "zh_female_shuangkuai",
]
SPEAKER_LABELS = {
    "zh": {
        "zh_female_vv_uranus_bigtts": "天王星",
        "zh_female_qingxin": "清新",
        "zh_male_chunhou": "醇厚",
        "zh_female_shuangkuai": "爽快",
    },
    "en": {
        "zh_female_vv_uranus_bigtts": "Uranus",
        "zh_female_qingxin": "Fresh",
        "zh_male_chunhou": "Mellow",
        "zh_female_shuangkuai": "Crisp",
    },
}
SPEAKER_HINTS = {
    "zh": {
        "zh_female_vv_uranus_bigtts": "女声",
        "zh_female_qingxin": "女声",
        "zh_male_chunhou": "男声",
        "zh_female_shuangkuai": "女声",
    },
    "en": {
        "zh_female_vv_uranus_bigtts": "Female",
        "zh_female_qingxin": "Female",
        "zh_male_chunhou": "Male",
        "zh_female_shuangkuai": "Female",
    },
}
AUDIENCES = ("school", "corp", "personal")
FIELDS = ("school", "corp", "personal")
# 首页上方痛点滚动区高度（像素）。越大越占画面，建议 90–250。
PAIN_FIELD_HEIGHT = 180
# 中间大字区、底部三列的上下留白比。数字越大，那一块越宽松。
HOME_GAP_ABOVE_HERO = 1
HOME_GAP_BELOW_HERO = 2

I18N = {
    "zh": {
        "title": "Iris Studio",
        "sub": "从想法到视频",
        "home": "首页",
        "prepare": "准备",
        "generate": "生成",
        "library": "成片",
        "community": "社区",
        "posts_loading": "正在读取社区…",
        "settings": "设置",
        "hero": "从想法，到视频。",
        "hero_p": "给要上课的人、要带培训的人、要把资料讲清楚的人。",
        "cta_have": "我有文稿或课件",
        "cta_new": "从主题开始",
        "p1_title": "生成准备",
        "p1_body": "已有文稿或 PPT，无声材料可以直接成片。还没有稿，就从主题生成讲稿和课件，再做成视频。",
        "p2_title": "生成过程",
        "p2_body": "随时改音色，返稿即重生。不必对着稿子录，也不必找安静房间。一键出片。",
        "p3_title": "成片之后",
        "p3_body": "AI 给修改建议。调完可以发到社区，和同领域的老师交换线下讲授经验，下一轮会更准。",
        "audiences": "学校老师  ·  企业培训讲师  ·  个人资料可视化",
        "start": "开始做一课",
        "run03": "合成音频",
        "run45": "合成视频",
        "stop": "停止",
        "stopped": "已停止。",
        "save": "保存",
        "browse": "选择文件",
        "ppt": "课件",
        "script_stat": "文稿",
        "slides": "幻灯片",
        "video": "视频",
        "log": "运行日志",
        "script_p": "改完请先保存。后面的配音只用这一份稿，不必你对着镜头念。",
        "chars": "字数",
        "voice_p": "点选音色，写入这一课。随时可换，换完再合成即可。",
        "api": "API Key",
        "res": "Resource ID",
        "ppt_path": "PPT 路径",
        "script_path": "文稿路径",
        "busy": "已有任务在运行。",
        "saved": "已保存。",
        "yes": "已就绪",
        "no": "还没有",
        "map": "幻灯片对齐",
        "map_p": "每一页对应口播里的哪几句。先合成音频，再自动对齐，微调后出视频。",
        "auto_map": "按课件自动对齐",
        "add_row": "加一行",
        "del_row": "删选中",
        "validate": "校验",
        "save_map": "保存对齐",
        "sentences": "句子",
        "no_ts": "还没有句子时间戳。请先合成音频。",
        "need_ts": "请先合成音频，才会有句子时间戳。",
        "need_ppt": "未找到 PPT 文件。",
        "overwrite": "将用自动匹配覆盖当前对齐表。是否继续？",
        "map_empty": "还没有对齐表。",
        "no_sents": "没有句子数据，无法完整校验。",
        "need_pptx": "自动对齐需要 python-pptx。",
        "lib_p": "成片记在这台电脑上。可以保存、打开文件夹，或去社区交流。",
        "lib_empty": "还没有成片。准备材料后去生成，或做完后点「收入成片」。",
        "save_work": "收入成片",
        "open_folder": "打开文件夹",
        "delete": "删除记录",
        "notes": "讲授备注",
        "save_notes": "保存备注",
        "teach_p": "成片不是结束。先看建议，再把这一课交给同行。",
        "advice_title": "成片建议",
        "advice_p": "根据稿长、页数和对齐，提示哪里该改音色、哪里该拆段、哪里该返稿。打开本页会自动更新。",
        "refresh_advice": "再看这一课",
        "share_title": "发到社区",
        "share_p": "先写标题和你怎么讲。可以注册并登录后点「发布」，名字会显示；也可以不注册，点「匿名发送」，别人看不到是谁。",
        "post_community": "发布",
        "field": "领域",
        "posts": "同领域动态",
        "empty_posts": "这个领域还没有动态。写下你怎么讲、学员卡在哪，发第一条。",
        "posted": "已发到同领域动态。",
        "need_body": "请先写下你怎么讲、学生或学员卡在哪。",
        "post_title_l": "标题",
        "post_body_l": "这一课你怎么讲",
        "post_detail": "这条动态",
        "open_post_video": "打开这条成片",
        "delete_post": "删除这条",
        "confirm_delete_post": "删除这条动态？删掉后同领域的人就看不见了。",
        "no_post_video": "这条动态没有附带成片。",
        "sample_tag": "示例",
        "posts_count": "{n} 条动态",
        "no_script": "还没有口播稿。",
        "ready": "已就绪",
        "missing": "还没有",
        "prepare_p": "两条路，同一处交稿。",
        "have_title": "已有文稿或 PPT",
        "have_p": "无声材料直接转换成视频。选好课件，改好讲稿，去生成即可。",
        "new_title": "还没有文稿或 PPT",
        "new_p": "写下主题和受众，先出一版讲稿和课件，再去做视频。",
        "audience": "受众",
        "topic": "主题",
        "gen_draft": "生成讲稿和课件",
        "go_gen": "去生成视频",
        "save_paths": "保存材料路径",
        "school": "学校老师",
        "corp": "企业培训讲师",
        "personal": "个人资料可视化",
        "generate_p": "改音色、对齐翻页、一键出片。全程不必开口，也不必找安静房间。",
        "draft_ok": "已写入讲稿和课件，可去生成视频。",
        "need_topic": "请先写主题。",
        "untitled_lesson": "未命名一课",
        "to_community": "去社区交流",
        "need_video": "请先生成视频，再发到社区。",
        "job_00": "检查材料",
        "job_01": "把课件变成图片",
        "job_02": "提交配音",
        "job_03": "等待配音",
        "job_04": "对齐翻页",
        "job_05": "合成视频",
        "job_auto": "按课件自动对齐",
        "job_done": "完成",
        "job_fail": "没有完成",
        "map_log": "课件 {pages} 页 / 口播 {sents} 句 / 已对齐 {mapped} 页",
        "video_ready_title": "成片已做好",
        "video_ready": "视频已经生成，可以直接打开观看。",
        "open_video": "打开视频",
        "later": "稍后",
        "audio_ready_title": "口播已做好",
        "audio_ready": "声音已经生成，可以先听一遍。",
        "open_audio": "打开声音",
        "anon_post": "匿名发送",
        "anon_tag": "匿名",
        "need_login": "要实名发布，请先注册或登录。也可以关掉这个窗口，改点「匿名发送」。",
        "login": "注册或登录",
        "logout": "退出登录",
        "register": "注册",
        "email": "邮箱",
        "password": "密码",
        "logged_in": "已登录：{email}",
        "logged_out": "现在是未登录。要实名发布请先注册或登录；不想留名就点「匿名发送」。",
        "cloud_off": "还没接上云端。到设置页填写 Supabase 地址和 anon key，并在网站里运行 supabase/schema.sql。",
        "cloud_ok": "动态来自云端，换电脑登录同一账号也能看见。",
        "banned": "这段文字不能发布。请改掉不合适的内容后再试。",
        "need_supabase": "请先在设置里填写 Supabase 的网址和 anon key。",
        "login_failed": "登录没成功。请核对邮箱和密码，或先注册。",
        "register_ok": "注册已提交。请到邮箱点开确认链接；若浏览器出现 localhost 打不开，可以关掉。账号多半已经确认成功，回到本软件点「登录」即可。",
        "sb_url": "Supabase 网址",
        "sb_key": "Supabase anon key",
        "account": "社区账号",
    },
    "en": {
        "title": "Iris Studio",
        "sub": "From idea to video",
        "home": "Home",
        "prepare": "Prepare",
        "generate": "Make",
        "library": "Films",
        "community": "Community",
        "posts_loading": "Loading the community…",
        "settings": "Settings",
        "hero": "From idea to video.",
        "hero_p": "For classroom teachers, workplace trainers, and anyone turning notes into a film.",
        "cta_have": "I have a script or slides",
        "cta_new": "Start from a topic",
        "p1_title": "Prepare",
        "p1_body": "If you already have a script or slides, we turn silent materials into a film. If not, we draft both, then make the video.",
        "p2_title": "Make",
        "p2_body": "Change the voice anytime. Revise and regenerate. No reading to camera. No quiet room. One click to a film.",
        "p3_title": "After the film",
        "p3_body": "AI suggests what to change. Then share with peers in your field and feed those notes into the next round.",
        "audiences": "Teachers  ·  Trainers  ·  Personal knowledge films",
        "start": "Start",
        "run03": "Make audio",
        "run45": "Make video",
        "stop": "Stop",
        "stopped": "Stopped.",
        "save": "Save",
        "browse": "Browse",
        "ppt": "Slides",
        "script_stat": "Script",
        "slides": "Pages",
        "video": "Video",
        "log": "Log",
        "script_p": "Save first. The voiceover uses this script — you do not have to read it aloud.",
        "chars": "Characters",
        "voice_p": "Click a voice for this lesson. Change it anytime and make the audio again.",
        "api": "API Key",
        "res": "Resource ID",
        "ppt_path": "PPT path",
        "script_path": "Script path",
        "busy": "A job is already running.",
        "saved": "Saved.",
        "yes": "Ready",
        "no": "Not yet",
        "map": "Slide timing",
        "map_p": "Each page covers a few spoken sentences. Make the audio first, auto-align, then tweak before the video.",
        "auto_map": "Align from slides",
        "add_row": "Add row",
        "del_row": "Delete",
        "validate": "Check",
        "save_map": "Save timing",
        "sentences": "Sentences",
        "no_ts": "No sentence timestamps yet. Make the audio first.",
        "need_ts": "Make the audio first so timestamps exist.",
        "need_ppt": "PPT file not found.",
        "overwrite": "Auto-align will replace the current table. Continue?",
        "map_empty": "The timing table is empty.",
        "no_sents": "No sentence data to check against.",
        "need_pptx": "Auto-align needs python-pptx.",
        "lib_p": "Finished films stay on this computer. Save a record, open the folder, or go to Community.",
        "lib_empty": "No films yet. Prepare materials, make a video, or click Save to films.",
        "save_work": "Save to films",
        "open_folder": "Open folder",
        "delete": "Remove record",
        "notes": "Teaching notes",
        "save_notes": "Save notes",
        "teach_p": "The film is not the end. Read the advice, then hand the lesson to peers.",
        "advice_title": "After the film",
        "advice_p": "Based on length, pages, and timing: where to change the voice, split a section, or revise the script. This updates when you open the page.",
        "refresh_advice": "Review this film",
        "share_title": "Post to community",
        "share_p": "Write a title and how you teach it. Sign in or register, then Publish — your name is shown. Or skip an account and Send anonymously.",
        "post_community": "Publish",
        "field": "Field",
        "posts": "From the field",
        "empty_posts": "No posts in this field yet. Write how you teach it, and where people get stuck.",
        "posted": "Posted to your field.",
        "need_body": "Write how you teach it live, and where people get stuck.",
        "post_title_l": "Title",
        "post_body_l": "How you teach this lesson",
        "post_detail": "This post",
        "open_post_video": "Open this film",
        "delete_post": "Remove post",
        "confirm_delete_post": "Remove this post? Others in the field will not see it anymore.",
        "no_post_video": "This post has no film attached.",
        "sample_tag": "Example",
        "posts_count": "{n} posts",
        "no_script": "There is no script yet.",
        "ready": "Ready",
        "missing": "Not yet",
        "prepare_p": "Two ways in. One place to hand over the materials.",
        "have_title": "I already have materials",
        "have_p": "Silent slides and a script become a film. Choose the file, edit the script, then make it.",
        "new_title": "I do not have materials",
        "new_p": "Give a topic and an audience. We draft a script and slides, then you make the video.",
        "audience": "Audience",
        "topic": "Topic",
        "gen_draft": "Draft script and slides",
        "go_gen": "Make the video",
        "save_paths": "Save file paths",
        "school": "School teacher",
        "corp": "Workplace trainer",
        "personal": "Personal knowledge film",
        "generate_p": "Change the voice, align the pages, export. No camera. No quiet room.",
        "draft_ok": "Script and slides are ready. You can make the video.",
        "need_topic": "Write a topic first.",
        "untitled_lesson": "Untitled lesson",
        "to_community": "Open community",
        "need_video": "Make a video before posting to the community.",
        "job_00": "Checking your files",
        "job_01": "Turning slides into pictures",
        "job_02": "Sending the voice job",
        "job_03": "Waiting for the voice",
        "job_04": "Timing the pages",
        "job_05": "Making the video",
        "job_auto": "Align from slides",
        "job_done": "Done",
        "job_fail": "Did not finish",
        "map_log": "{pages} slide pages / {sents} spoken lines / {mapped} pages timed",
        "video_ready_title": "Your film is ready",
        "video_ready": "The video has been made. You can play it now.",
        "open_video": "Play video",
        "later": "Not now",
        "audio_ready_title": "The voice is ready",
        "audio_ready": "The narration has been made. You can listen now.",
        "open_audio": "Play audio",
        "anon_post": "Send anonymously",
        "anon_tag": "Anonymous",
        "need_login": "To publish under your name, sign in or register first. Or close this and use Send anonymously.",
        "login": "Sign in or register",
        "logout": "Sign out",
        "register": "Create account",
        "email": "Email",
        "password": "Password",
        "logged_in": "Signed in as {email}",
        "logged_out": "You are not signed in. Sign in or register to publish under your name, or Send anonymously.",
        "cloud_off": "Cloud is not connected. Add your Supabase URL and anon key in Settings, and run supabase/schema.sql in the dashboard.",
        "cloud_ok": "This feed is in the cloud. Sign in on another computer to see the same posts.",
        "banned": "This text cannot be published. Please remove the blocked words and try again.",
        "need_supabase": "Add the Supabase URL and anon key in Settings first.",
        "login_failed": "Sign-in did not work. Check the email and password, or create an account first.",
        "register_ok": "Account created. Open the email link. If the browser shows localhost and fails, close it — your account is usually already confirmed. Come back here and Sign in.",
        "sb_url": "Supabase URL",
        "sb_key": "Supabase anon key",
        "account": "Community account",
    },
}

PAINS = {
    "zh": [
        "主题选定",
        "人群确定",
        "反复录制讲稿",
        "录错就要重来",
        "必须在安静环境录",
        "返稿修改困难",
        "今晚又要熬夜补录",
        "孩子一哭，这条废了",
        "对着镜头好别扭",
        "讲顺了，灯却闪了",
        "想改一句，整段重来",
        "晚上十点才敢开口",
        "PPT 有了，口播还没有",
        "同一页讲了三遍还是空",
        "怕自己声音不好听",
        "录到一半忘词了",
        "会议室总有人进出",
        "培训片要赶周五交",
        "领导说再录一遍",
        "出差酒店隔音太差",
        "口径改了，成片作废",
        "笔记一堆，讲不出来",
        "想做片但不会剪",
        "对着空气好尴尬",
        "资料在电脑里吃灰",
        "找不到人帮忙配音",
        "改一页就要重对齐",
        "学生说语速太快了",
        "学员看到一半就关了",
        "录完才发现口误",
    ],
    "en": [
        "Pick a topic",
        "Name the audience",
        "Record the script again",
        "One mistake, start over",
        "Need a quiet room",
        "Hard to revise a take",
        "Another late night recut",
        "A kid cries. That take is gone.",
        "The camera feels wrong",
        "The line was good. The light blinked.",
        "Change one sentence, redo the whole thing",
        "Only dare to speak after ten",
        "Slides are ready. The voice is not.",
        "Same page, three takes, still empty",
        "Don't like my own voice",
        "Forgot the line halfway",
        "People keep walking into the room",
        "The training film is due Friday",
        "The boss wants another take",
        "Hotel walls are thin",
        "The talking points changed. Scrap it.",
        "Notes everywhere. Nothing to say.",
        "Want a film. Can't edit.",
        "Talking to empty air",
        "The files just sit on the drive",
        "No one to do the voiceover",
        "Move one slide, realign everything",
        "They said I spoke too fast",
        "Viewers leave halfway",
        "Heard the slip only after export",
    ],
}

QSS = """
QMainWindow, QWidget#Root {
  background: #243040;
  border: none;
}
QWidget#MainPane {
  background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
    stop:0 	#fbfaf7,
    stop:0.15 #f3efe6,
    stop:0.50 #e6ddd0,
    stop:0.85 #f3efe6,
    stop:1 #fbfaf7);
  border: none;
}
QStackedWidget, QWidget#Page, QScrollArea, QScrollArea > QWidget {
  background: transparent;
  border: none;
}
QWidget#Sidebar {
  background: #243040;
  border: none;
}
QLabel { border: none; background: transparent; }
QLabel#Brand { color: #f6f4ef; font-size: 18px; font-weight: 700; }
QLabel#BrandSub { color: #9aa3ad; font-size: 12px; }
QPushButton#Nav {
  background: transparent;
  color: #d5dbe2;
  border: none;
  border-radius: 6px;
  padding: 9px 12px;
  text-align: center;
  font-size: 14px;
  font-weight: 500;
}
QPushButton#Nav:hover {
  background: #2e3b4d;
  color: #f6f4ef;
}
QPushButton#Nav:checked,
QPushButton#Nav:checked:hover {
  background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
    stop:0 #f6f4ef,
    stop:0.50 #eee8de,
    stop:1 #f6f4ef);
  color: #243040;
}
QLabel#H1 { font-size: 26px; font-weight: 700; color: #243040; }
QLabel#Hero {
  font-size: 72px;
  font-weight: 700;
  color: #243040;
  letter-spacing: -2px;
}
QLabel#Muted { color: #6d7380; font-size: 14px; }
QLabel#Body { color: #3d4552; font-size: 14px; }
QLabel#StatNum { font-size: 14px; font-weight: 600; color: #243040; }
QLabel#StatLab { color: #6d7380; font-size: 14px; }
QLabel#SectionTitle { font-size: 13px; font-weight: 700; color: #6d7380; }
QLabel#StepTitle { font-size: 16px; font-weight: 700; color: #243040; }
QLabel#HomeStep { font-size: 16px; font-weight: 700; color: #243040; }
QLabel#HomeStepBody { color: #3d4552; font-size: 14px; }
QLabel#Audience { color: #5c6570; font-size: 15px; }
QFrame#Hero, QFrame#Stat, QFrame#TeachCard {
  background: transparent;
  border: none;
}
QFrame#Card, QFrame#Section {
  background: #f6f4ef;
  border: none;
  border-radius: 12px;
}
QFrame#Rule { background: #e4ddd2; border: none; max-height: 1px; }
QPushButton#Yellow {
  background-color: #1f5c4f;
  color: #f6f4ef;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  font-weight: 600;
}
QPushButton#Navy {
  background-color: #243040;
  color: #f6f4ef;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  font-weight: 600;
}
QPushButton#Coral {
  background-color: #8a3a3a;
  color: #f6f4ef;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  font-weight: 600;
}
QPushButton#Ghost {
  background-color: #ece7dc;
  color: #243040;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  font-weight: 600;
}
QPushButton#LangOrb {
  background: #243040;
  color: #f6f4ef;
  border: none;
  border-radius: 22px;
  min-width: 44px;
  max-width: 44px;
  min-height: 44px;
  max-height: 44px;
  padding: 0;
  font-weight: 700;
  font-size: 11px;
}
QPushButton#LangOrb:hover { background: #2e3b4d; }
QLineEdit, QTextEdit, QComboBox {
  background: #efece4;
  border: none;
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 14px;
  color: #243040;
}
QTextEdit#Log {
  background: #243040;
  color: #d5dbe2;
  border: none;
  border-radius: 6px;
  font-family: Consolas, monospace;
  font-size: 12px;
}
QFrame#Voice { background: #efece4; border: none; border-radius: 6px; }
QFrame#Voice[selected="true"] { background: #d7e8e3; }
QTableWidget, QListWidget {
  background: #efece4;
  border: none;
  border-radius: 6px;
  color: #243040;
  font-size: 13px;
}
QHeaderView::section {
  background: #ece7dc; color: #243040; border: none; padding: 8px;
  font-weight: 700;
}
QTableWidget::item:selected, QListWidget::item:selected {
  background: #d7e8e3; color: #243040;
}
"""


def hairline() -> QFrame:
    line = QFrame(objectName="Rule")
    line.setFixedHeight(1)
    line.setFrameShape(QFrame.Shape.NoFrame)
    line.setStyleSheet("background:#e4ddd2; border:none;")
    return line


class CreamNav(QPushButton):
    """Selected item: light at the sides, deeper beige in the middle."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Nav")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    def enterEvent(self, event) -> None:  # noqa: N802
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 6, 6)
        if self.isChecked():
            grad = QLinearGradient(rect.left(), 0, rect.right(), 0)
            grad.setColorAt(0.0, QColor("#fbfaf7"))
            grad.setColorAt(0.5, QColor("#f7f4ee"))
            grad.setColorAt(1.0, QColor("#fbfaf7"))
            painter.fillPath(path, grad)
            painter.setPen(QColor("#243040"))
        else:
            if self.underMouse():
                painter.fillPath(path, QColor("#2e3b4d"))
            painter.setPen(QColor("#f6f4ef") if self.underMouse() else QColor("#d5dbe2"))
        font = self.font()
        font.setPixelSize(14)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())


class CreamTile(QFrame):
    """Home step cards: light at the sides, deeper beige in the middle."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(False)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        grad = QLinearGradient(rect.left(), 0, rect.right(), 0)
        grad.setColorAt(0.0, QColor("#fbfaf7"))
        grad.setColorAt(0.5, QColor("#f7f4ee"))
        grad.setColorAt(1.0, QColor("#fbfaf7"))
        painter.fillPath(path, grad)


def paint_card(widget: QWidget, name: str, radius: int = 6, shadow: bool = False) -> None:
    widget.setAutoFillBackground(False)
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    if isinstance(widget, QFrame):
        widget.setFrameShape(QFrame.Shape.NoFrame)
        widget.setLineWidth(0)
    if shadow:
        glow = QGraphicsDropShadowEffect(widget)
        glow.setBlurRadius(28)
        glow.setOffset(0, 6)
        glow.setColor(QColor(36, 48, 64, 38))
        widget.setGraphicsEffect(glow)


def _exists(name: str) -> bool:
    if not name:
        return False
    p = Path(name)
    if not p.is_absolute():
        p = ROOT / name
    return p.is_file()


def _slug(text: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|]+", "", text).strip()
    return text[:24] or "draft"


def build_draft(topic: str, audience: str, lang: str) -> tuple[Path, Path]:
    from pptx import Presentation
    from pptx.util import Pt

    topic = topic.strip()
    pack = _wp.PACKS["en" if lang == "en" else "zh"]
    slug = _slug(topic) if _slug(topic) != "draft" else pack["untitled"]
    folder = _wp.OUTPUTS / slug
    folder.mkdir(parents=True, exist_ok=True)
    script_path = folder / pack["script"]
    ppt_path = folder / pack["ppt"]
    if lang == "zh":
        greet = {
            "school": "各位同学",
            "corp": "各位同事",
            "personal": "各位",
        }.get(audience, "各位")
        close = {
            "school": "课后把这一页的例子再用自己的话讲一遍。",
            "corp": "回到岗位上，先选一件事按今天的步骤做一次。",
            "personal": "合上这一课之前，用三句话写下你记住的部分。",
        }.get(audience, "我们下次继续。")
        lines = [
            f"{greet}，今天只讲一件事：{topic}。",
            "先说它为什么值得现在讲，而不是以后再讲。",
            "接着只留三个要点，每个要点配一个能当场用的例子。",
            "中间如果有一处容易混，我会停下来，把容易错的地方单独说清楚。",
            f"最后收束：{close}",
        ]
        slides = [
            topic,
            "为什么现在讲",
            "三个要点",
            "一个当场能用的例子",
            "容易混的地方",
            "收束与下一步",
        ]
    else:
        greet = {
            "school": "Students",
            "corp": "Colleagues",
            "personal": "Hello",
        }.get(audience, "Hello")
        close = {
            "school": "Retell today's example in your own words.",
            "corp": "Pick one task at work and try today's steps once.",
            "personal": "Before you close, write three sentences you will keep.",
        }.get(audience, "We will continue next time.")
        lines = [
            f"{greet}. Today we cover one thing: {topic}.",
            "First, why this is worth saying now.",
            "Then three points, each with an example you can use immediately.",
            "If one place is easy to mix up, we stop and name the mistake.",
            f"We close here: {close}",
        ]
        slides = [
            topic,
            "Why now",
            "Three points",
            "An example you can use",
            "The easy mistake",
            "Close and next step",
        ]
    script_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    prs = Presentation()
    body_layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
    title_layout = prs.slide_layouts[0]
    bodies = lines + [lines[-1]] * max(0, len(slides) - len(lines))
    for i, heading in enumerate(slides):
        layout = title_layout if i == 0 else body_layout
        slide = prs.slides.add_slide(layout)
        slide.shapes.title.text = heading
        if len(slide.placeholders) > 1:
            tf = slide.placeholders[1].text_frame
            tf.text = bodies[i]
            for p in tf.paragraphs:
                p.font.size = Pt(18)
    prs.save(str(ppt_path))
    return script_path, ppt_path


class PainTicker(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(PAIN_FIELD_HEIGHT)
        self._items: list[str] = []
        self._t = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(24)

    def set_items(self, items: list[str]) -> None:
        self._items = items
        self._t = 0.0
        self.update()

    def _tick(self) -> None:
        self._t += 1.0
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._items:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        font = QFont(self.font())
        font.setPointSize(12)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        row_h = metrics.height() + 18
        rows = max(2, self.height() // row_h)
        gap = "      ·      "
        for i in range(rows):
            rotated = self._items[i % len(self._items) :] + self._items[: i % len(self._items)]
            text = gap.join(rotated) + gap
            width = metrics.horizontalAdvance(text)
            if width <= 0:
                continue
            speed = 0.55 + (i % 5) * 0.28
            offset = int(self._t * speed) % width
            x = offset - width if i % 2 else -offset
            y = (i * row_h) + metrics.ascent() + 8
            painter.setPen(QColor(138, 127, 112, 118 + (i % 3) * 22))
            while x < self.width():
                painter.drawText(x, y, text)
                x += width


class JobWorker(QObject):
    line = pyqtSignal(str)
    done = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._stop = threading.Event()
        self._proc: subprocess.Popen | None = None
        self.scripts: list[str] = []
        self.lang = "zh"

    def _title(self, script: str) -> str:
        key = STEP_TITLES.get(script)
        pack = I18N.get(self.lang) or I18N["zh"]
        if key and key in pack:
            return pack[key]
        return script

    def request_stop(self) -> None:
        self._stop.set()
        (ROOT / "stop_query.flag").write_text("stop", encoding="utf-8")
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except Exception:
                pass

    @pyqtSlot()
    def run(self) -> None:
        self._stop.clear()
        env = os.environ.copy()
        env["VIDEO_TOOL_CONFIG"] = str(ROOT / "config.json")
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"
        for script in self.scripts:
            if self._stop.is_set():
                self.done.emit("stopped")
                return
            self.line.emit(f"—— {self._title(script)} ——")
            try:
                proc = subprocess.Popen(
                    [sys.executable, "-u", str(ROOT / "04_pipeline.py"), script],
                    cwd=str(ROOT),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self._proc = proc
                assert proc.stdout is not None
                for raw in proc.stdout:
                    self.line.emit(raw.rstrip())
                code = proc.wait()
                self._proc = None
                if self._stop.is_set() or code == 130:
                    self.done.emit("stopped")
                    return
                if code != 0:
                    pack = I18N.get(self.lang) or I18N["zh"]
                    self.line.emit(f"{pack.get('job_fail', 'Failed')} · {self._title(script)}")
                    self.done.emit("failed")
                    return
                pack = I18N.get(self.lang) or I18N["zh"]
                self.line.emit(f"{pack.get('job_done', 'Done')} · {self._title(script)}")
            except Exception as e:
                self._proc = None
                self.line.emit(str(e))
                self.done.emit("failed")
                return
        self.done.emit("ok")


def _rows_to_posts(rows: list[dict], field: str) -> list[dict]:
    posts: list[dict] = []
    for row in rows:
        when = str(row.get("created_at") or "").replace("T", " ")[:16]
        posts.append(
            {
                "id": row.get("id"),
                "cloud": True,
                "title": row.get("title") or "",
                "title_en": row.get("title_en") or "",
                "body": row.get("body") or "",
                "body_en": row.get("body_en") or "",
                "field": row.get("field") or field,
                "created_at": when,
                "is_anonymous": bool(row.get("is_anonymous")),
                "user_id": row.get("user_id"),
                "video_path": "",
            }
        )
    return posts


class CommunityFetchWorker(QObject):
    finished = pyqtSignal(str, list, str)

    def __init__(self) -> None:
        super().__init__()
        self.cfg: dict = {}
        self.field = "school"
        self.force = False

    @pyqtSlot()
    def run(self) -> None:
        try:
            rows = list_cloud_posts(self.cfg, self.field, force=self.force)
            self.finished.emit(self.field, _rows_to_posts(rows, self.field), "")
        except Exception as e:
            self.finished.emit(self.field, [], str(e))


class AccountDialog(QDialog):
    def __init__(self, studio: Studio) -> None:
        super().__init__(studio)
        self.studio = studio
        self.setWindowTitle(studio.t("account"))
        layout = QVBoxLayout(self)
        self.email = QLineEdit()
        self.email.setPlaceholderText(studio.t("email"))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText(studio.t("password"))
        hint = QLabel(studio.t("need_login"))
        hint.setWordWrap(True)
        hint.setObjectName("Muted")
        layout.addWidget(hint)
        layout.addWidget(self.email)
        layout.addWidget(self.password)
        box = QDialogButtonBox()
        self.login_btn = box.addButton(studio.t("login"), QDialogButtonBox.ButtonRole.ActionRole)
        self.reg_btn = box.addButton(studio.t("register"), QDialogButtonBox.ButtonRole.ActionRole)
        box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.login_btn.clicked.connect(self._login)
        self.reg_btn.clicked.connect(self._register)
        box.rejected.connect(self.reject)
        layout.addWidget(box)

    def _login(self) -> None:
        cfg = self.studio._cfg()
        try:
            sign_in(cfg, self.email.text().strip(), self.password.text())
            self.accept()
        except Exception:
            QMessageBox.warning(self, self.studio.t("title"), self.studio.t("login_failed"))

    def _register(self) -> None:
        cfg = self.studio._cfg()
        try:
            data = sign_up(cfg, self.email.text().strip(), self.password.text())
            if data.get("access_token"):
                self.accept()
                return
            QMessageBox.information(self, self.studio.t("title"), self.studio.t("register_ok"))
            self.reject()
        except Exception as e:
            QMessageBox.warning(self, self.studio.t("title"), str(e) or self.studio.t("login_failed"))


class Studio(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.lang = "zh"
        self.busy = False
        self.thread: QThread | None = None
        self.worker: JobWorker | None = None
        self.nav_btns: list[QPushButton] = []
        self.selected_work_id: int | None = None
        self._community_cache: dict[str, list] = {}
        self._community_thread: QThread | None = None
        self._community_worker: CommunityFetchWorker | None = None
        self._community_fetching: str | None = None
        init_db()
        try:
            self.lang = ui_lang(load_config())
        except OSError:
            self.lang = "zh"
        self.setWindowTitle("Iris Studio")
        icon = ROOT / "assets" / "iris.ico"
        if icon.is_file():
            self.setWindowIcon(QIcon(str(icon)))
        self.resize(1280, 820)
        self.setMinimumSize(980, 640)

        root = QWidget(objectName="Root")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = QWidget(objectName="Sidebar")
        self.sidebar.setFixedWidth(208)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(16, 22, 16, 22)
        side.setSpacing(4)
        self.brand = QLabel("Iris Studio", objectName="Brand")
        self.brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.brand_sub = QLabel(objectName="BrandSub")
        self.brand_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side.addWidget(self.brand)
        side.addWidget(self.brand_sub)
        side.addSpacing(18)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_keys = ["home", "prepare", "generate", "library", "community", "settings"]
        for i, key in enumerate(self.nav_keys):
            btn = CreamNav()
            if i == 0:
                btn.setChecked(True)
            self.nav_group.addButton(btn, i)
            self.nav_btns.append(btn)
            side.addWidget(btn)
        side.addStretch(1)
        layout.addWidget(self.sidebar)

        right = QWidget(objectName="MainPane")
        right.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(36, 22, 36, 28)
        header = QHBoxLayout()
        self.header_titles = QWidget()
        titles = QVBoxLayout(self.header_titles)
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(4)
        self.h1 = QLabel(objectName="H1")
        self.h1.setWordWrap(True)
        self.h1.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.sub = QLabel(objectName="Muted")
        self.sub.setWordWrap(True)
        self.sub.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        titles.addWidget(self.h1)
        titles.addWidget(self.sub)
        header.addWidget(self.header_titles, 1)
        self.btn_lang = QPushButton("ENG", objectName="LangOrb")
        self.btn_lang.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lang.setToolTip("中文 / English")
        header.addWidget(self.btn_lang, 0, Qt.AlignmentFlag.AlignTop)
        right_l.addLayout(header)

        self.stack = QStackedWidget(objectName="Page")
        right_l.addWidget(self.stack, 1)
        layout.addWidget(right, 1)

        self._build_pages()
        self.nav_group.idClicked.connect(self._on_nav)
        self.btn_lang.clicked.connect(self._toggle_lang)
        self._apply_lang()
        self.refresh_home()

    def t(self, key: str) -> str:
        return I18N[self.lang].get(key, key)

    def card(self, name: str = "Card", *, shadow: bool = False, radius: int = 6) -> QFrame:
        f = QFrame()
        f.setObjectName(name)
        f.setFrameShape(QFrame.Shape.NoFrame)
        f.setLineWidth(0)
        f.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        paint_card(f, name, radius=radius, shadow=shadow)
        return f

    def section(self) -> QFrame:
        return self.card("Section", shadow=True)

    def _build_home(self) -> None:
        self.ticker = PainTicker()
        self.home_box.addWidget(self.ticker)
        self.home_box.addStretch(HOME_GAP_ABOVE_HERO)

        hero_wrap = QWidget()
        hero_l = QVBoxLayout(hero_wrap)
        hero_l.setContentsMargins(0, 8, 0, 12)
        hero_l.setSpacing(12)
        hero_l.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.hero_title = QLabel(objectName="Hero")
        self.hero_title.setWordWrap(True)
        self.hero_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.audiences_lab = QLabel(objectName="Audience")
        self.audiences_lab.setWordWrap(True)
        self.audiences_lab.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.hero_p = QLabel(objectName="Body")
        self.hero_p.setWordWrap(True)
        self.hero_p.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.hero_p.hide()
        cta = QHBoxLayout()
        cta.setSpacing(12)
        cta.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.hero_have = QPushButton(objectName="Yellow")
        self.hero_new = QPushButton(objectName="Navy")
        self.hero_have.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hero_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hero_have.clicked.connect(lambda: self._go_prepare(False))
        self.hero_new.clicked.connect(lambda: self._go_prepare(True))
        cta.addWidget(self.hero_have)
        cta.addWidget(self.hero_new)
        hero_l.addWidget(self.hero_title)
        hero_l.addWidget(self.audiences_lab)
        hero_l.addWidget(self.hero_p)
        hero_l.addSpacing(4)
        hero_l.addLayout(cta)
        self.home_box.addWidget(hero_wrap)
        self.home_box.addStretch(HOME_GAP_BELOW_HERO)

        steps = QHBoxLayout()
        steps.setSpacing(16)
        steps.setContentsMargins(0, 8, 0, 4)
        self.step_titles: list[QLabel] = []
        self.step_bodies: list[QLabel] = []
        for _ in range(3):
            col_f = CreamTile()
            paint_card(col_f, "HomeTile", radius=12, shadow=True)
            col = QVBoxLayout(col_f)
            col.setContentsMargins(16, 16, 16, 16)
            col.setSpacing(8)
            title = QLabel(objectName="HomeStep")
            title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            body = QLabel(objectName="HomeStepBody")
            body.setWordWrap(True)
            body.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            col.addWidget(title)
            col.addWidget(body)
            steps.addWidget(col_f, 1)
            self.step_titles.append(title)
            self.step_bodies.append(body)
        self.home_box.addLayout(steps)

    def _build_pages(self) -> None:
        self.page_home = QWidget(objectName="Page")
        self.home_box = QVBoxLayout(self.page_home)
        self.home_box.setContentsMargins(8, 8, 8, 8)
        self.home_box.setSpacing(4)
        self._build_home()
        self.stack.addWidget(self.page_home)

        self.page_prepare = QWidget(objectName="Page")
        prep = QVBoxLayout(self.page_prepare)
        prep.setContentsMargins(8, 8, 8, 8)
        prep.setSpacing(16)
        self.prepare_hint = QLabel(self.page_prepare, objectName="Muted")
        self.prepare_hint.setWordWrap(True)
        self.prepare_hint.hide()
        tracks = QHBoxLayout()
        tracks.setSpacing(16)

        have = self.section()
        left = QVBoxLayout(have)
        left.setContentsMargins(16, 16, 16, 16)
        left.setSpacing(8)
        self.have_title = QLabel(objectName="StepTitle")
        self.have_p = QLabel(objectName="Muted")
        self.have_p.setWordWrap(True)
        left.addWidget(self.have_title)
        left.addWidget(self.have_p)
        self.l_ppt = QLabel()
        ppt_row = QHBoxLayout()
        self.ppt_edit = QLineEdit()
        self.b_ppt = QPushButton(objectName="Ghost")
        self.b_ppt.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_ppt.clicked.connect(self.pick_ppt)
        ppt_row.addWidget(self.ppt_edit, 1)
        ppt_row.addWidget(self.b_ppt)
        left.addWidget(self.l_ppt)
        left.addLayout(ppt_row)
        self.l_txt = QLabel()
        txt_row = QHBoxLayout()
        self.txt_edit = QLineEdit()
        self.b_txt = QPushButton(objectName="Ghost")
        self.b_txt.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_txt.clicked.connect(self.pick_txt)
        txt_row.addWidget(self.txt_edit, 1)
        txt_row.addWidget(self.b_txt)
        left.addWidget(self.l_txt)
        left.addLayout(txt_row)
        self.b_save_paths = QPushButton(objectName="Ghost")
        self.b_save_paths.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_save_paths.clicked.connect(self.save_paths)
        left.addWidget(self.b_save_paths, 0, Qt.AlignmentFlag.AlignLeft)
        self.script_hint = QLabel(objectName="Muted")
        self.script_hint.setWordWrap(True)
        self.script_edit = QTextEdit()
        self.b_save_script = QPushButton(objectName="Yellow")
        self.b_save_script.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_save_script.clicked.connect(self.save_script)
        left.addWidget(self.script_hint)
        left.addWidget(self.script_edit, 1)
        left.addWidget(self.b_save_script, 0, Qt.AlignmentFlag.AlignLeft)

        fresh = self.section()
        right_track = QVBoxLayout(fresh)
        right_track.setContentsMargins(16, 16, 16, 16)
        right_track.setSpacing(8)
        self.new_title = QLabel(objectName="StepTitle")
        self.new_p = QLabel(objectName="Muted")
        self.new_p.setWordWrap(True)
        right_track.addWidget(self.new_title)
        right_track.addWidget(self.new_p)
        self.l_topic = QLabel()
        self.topic_edit = QLineEdit()
        self.l_audience = QLabel()
        self.audience_box = QComboBox()
        self.b_gen_draft = QPushButton(objectName="Navy")
        self.b_gen_draft.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_gen_draft.clicked.connect(self.generate_draft)
        right_track.addWidget(self.l_topic)
        right_track.addWidget(self.topic_edit)
        right_track.addWidget(self.l_audience)
        right_track.addWidget(self.audience_box)
        right_track.addWidget(self.b_gen_draft, 0, Qt.AlignmentFlag.AlignLeft)
        right_track.addStretch(1)
        self.b_go_gen = QPushButton(objectName="Yellow")
        self.b_go_gen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_go_gen.clicked.connect(lambda: self.nav_btns[2].click())
        right_track.addWidget(self.b_go_gen, 0, Qt.AlignmentFlag.AlignLeft)

        tracks.addWidget(have, 1)
        tracks.addWidget(fresh, 1)
        prep.addLayout(tracks, 1)
        self.stack.addWidget(self.page_prepare)

        self.page_course = QWidget(objectName="Page")
        c = QVBoxLayout(self.page_course)
        c.setContentsMargins(8, 8, 8, 8)
        c.setSpacing(16)
        self.generate_hint = QLabel(self.page_course, objectName="Muted")
        self.generate_hint.setWordWrap(True)
        self.generate_hint.hide()

        voice_sec = self.section()
        voice_l = QVBoxLayout(voice_sec)
        voice_l.setContentsMargins(16, 16, 16, 16)
        voice_l.setSpacing(8)
        self.voice_hint = QLabel(objectName="Muted")
        self.voice_hint.setWordWrap(True)
        voice_l.addWidget(self.voice_hint)
        voice_row = QHBoxLayout()
        voice_row.setSpacing(8)
        self.voice_cards: list[QFrame] = []
        self.voice_title_labs: list[QLabel] = []
        self.voice_code_labs: list[QLabel] = []
        cfg = self._cfg()
        current = (cfg.get("audio") or {}).get("speaker")
        for sp in SPEAKERS:
            card = QFrame(objectName="Voice")
            card.setFrameShape(QFrame.Shape.NoFrame)
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            card.setAutoFillBackground(True)
            card.setProperty("selected", sp == current)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            vl = QVBoxLayout(card)
            vl.setSpacing(4)
            title = QLabel(SPEAKER_LABELS["zh"].get(sp, sp))
            title.setObjectName("StepTitle")
            title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            code = QLabel()
            code.setObjectName("Muted")
            code.setWordWrap(True)
            code.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            code.setStyleSheet("font-size:11px; color:#6d7380;")
            code.setText(SPEAKER_HINTS["zh"].get(sp, ""))
            vl.addWidget(title)
            vl.addWidget(code)
            card.mousePressEvent = lambda _e, name=sp: self.pick_voice(name)
            self.voice_cards.append(card)
            self.voice_title_labs.append(title)
            self.voice_code_labs.append(code)
            voice_row.addWidget(card, 1)
        voice_l.addLayout(voice_row)
        row = QHBoxLayout()
        self.b_run03 = QPushButton(objectName="Yellow")
        self.b_run45 = QPushButton(objectName="Navy")
        self.b_stop = QPushButton(objectName="Coral")
        for b, fn in (
            (self.b_run03, lambda: self.start_job(STEP_SCRIPTS[:4])),
            (self.b_run45, lambda: self.start_job(STEP_SCRIPTS[4:], need_map=True)),
            (self.b_stop, self.stop_job),
        ):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _checked=False, f=fn: f())
            row.addWidget(b)
        row.addStretch(1)
        voice_l.addLayout(row)
        c.addWidget(voice_sec)

        split = QSplitter(Qt.Orientation.Vertical)
        log_sec = self.section()
        log_l = QVBoxLayout(log_sec)
        log_l.setContentsMargins(16, 16, 16, 16)
        self.log = QTextEdit(objectName="Log")
        self.log.setReadOnly(True)
        log_l.addWidget(self.log)
        split.addWidget(log_sec)

        map_sec = self.section()
        ml = QVBoxLayout(map_sec)
        ml.setContentsMargins(16, 16, 16, 16)
        ml.setSpacing(8)
        self.map_hint = QLabel(objectName="Muted")
        self.map_hint.setWordWrap(True)
        ml.addWidget(self.map_hint)
        map_btns = QHBoxLayout()
        self.b_auto_map = QPushButton(objectName="Navy")
        self.b_add_row = QPushButton(objectName="Ghost")
        self.b_del_row = QPushButton(objectName="Ghost")
        self.b_validate = QPushButton(objectName="Ghost")
        self.b_save_map = QPushButton(objectName="Ghost")
        for b, fn in (
            (self.b_auto_map, self.auto_map),
            (self.b_add_row, self.add_map_row),
            (self.b_del_row, self.delete_map_row),
            (self.b_validate, lambda: self.validate_mapping(silent=False)),
            (self.b_save_map, lambda: self.save_mapping()),
        ):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _checked=False, f=fn: f())
            map_btns.addWidget(b)
        map_btns.addStretch(1)
        ml.addLayout(map_btns)
        map_split = QSplitter(Qt.Orientation.Horizontal)
        self.sent_list = QListWidget()
        self.sent_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.map_table = QTableWidget(0, 3)
        self.map_table.setHorizontalHeaderLabels(["起始句", "结束句", "图片"])
        self.map_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.map_table.verticalHeader().setVisible(False)
        map_split.addWidget(self.sent_list)
        map_split.addWidget(self.map_table)
        map_split.setStretchFactor(0, 1)
        map_split.setStretchFactor(1, 1)
        ml.addWidget(map_split, 1)
        split.addWidget(map_sec)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        c.addWidget(split, 1)
        self.stack.addWidget(self.page_course)

        self.page_lib = QWidget(objectName="Page")
        lib = QVBoxLayout(self.page_lib)
        lib.setContentsMargins(8, 8, 8, 8)
        lib.setSpacing(16)
        self.lib_hint = QLabel(self.page_lib, objectName="Muted")
        self.lib_hint.setWordWrap(True)
        self.lib_hint.hide()
        works_sec = self.section()
        works_l = QVBoxLayout(works_sec)
        works_l.setContentsMargins(16, 16, 16, 16)
        works_l.setSpacing(8)
        lib_btns = QHBoxLayout()
        self.b_save_work = QPushButton(objectName="Yellow")
        self.b_save_work.clicked.connect(lambda: self.snapshot_work(manual=True))
        self.b_del_work = QPushButton(objectName="Coral")
        self.b_del_work.clicked.connect(self.delete_selected_work)
        self.b_open_work = QPushButton(objectName="Ghost")
        self.b_open_work.clicked.connect(self.open_selected_work)
        self.b_to_community = QPushButton(objectName="Ghost")
        self.b_to_community.clicked.connect(lambda: self.nav_btns[4].click())
        for b in (self.b_save_work, self.b_del_work, self.b_open_work, self.b_to_community):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            lib_btns.addWidget(b)
        lib_btns.addStretch(1)
        works_l.addLayout(lib_btns)
        self.work_list = QListWidget()
        self.work_list.currentRowChanged.connect(self._on_work_row)
        works_l.addWidget(self.work_list, 1)
        lib.addWidget(works_sec, 1)
        notes_sec = self.section()
        notes_l = QVBoxLayout(notes_sec)
        notes_l.setContentsMargins(16, 16, 16, 16)
        notes_l.setSpacing(8)
        self.l_notes = QLabel(objectName="Body")
        self.notes_edit = QTextEdit()
        self.b_save_notes = QPushButton(objectName="Yellow")
        self.b_save_notes.clicked.connect(self.save_work_notes)
        notes_l.addWidget(self.l_notes)
        notes_l.addWidget(self.notes_edit)
        notes_l.addWidget(self.b_save_notes, 0, Qt.AlignmentFlag.AlignLeft)
        lib.addWidget(notes_sec)
        self.stack.addWidget(self.page_lib)

        self.page_teach = QWidget(objectName="Page")
        teach = QHBoxLayout(self.page_teach)
        teach.setContentsMargins(8, 8, 12, 12)
        teach.setSpacing(16)
        self.teach_hint = QLabel(self.page_teach, objectName="Muted")
        self.teach_hint.setWordWrap(True)
        self.teach_hint.hide()

        feed_card = self.section()
        feed_l = QVBoxLayout(feed_card)
        feed_l.setContentsMargins(16, 16, 16, 16)
        feed_l.setSpacing(8)
        self.posts_title = QLabel(objectName="StepTitle")
        self.posts_count = QLabel(objectName="Muted")
        self.post_list = QListWidget()
        self.post_list.setMinimumHeight(160)
        self.post_list.currentRowChanged.connect(self._on_post_row)
        self.post_detail = QTextEdit()
        self.post_detail.setReadOnly(True)
        self.post_detail.setMinimumHeight(140)
        post_btns = QHBoxLayout()
        self.b_open_post_video = QPushButton(objectName="Navy")
        self.b_open_post_video.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_open_post_video.clicked.connect(self.open_post_video)
        self.b_open_post_folder = QPushButton(objectName="Ghost")
        self.b_open_post_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_open_post_folder.clicked.connect(self.open_post_folder)
        self.b_del_post = QPushButton(objectName="Coral")
        self.b_del_post.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_del_post.clicked.connect(self.remove_post)
        post_btns.addWidget(self.b_open_post_video)
        post_btns.addWidget(self.b_open_post_folder)
        post_btns.addWidget(self.b_del_post)
        post_btns.addStretch(1)
        feed_l.addWidget(self.posts_title)
        feed_l.addWidget(self.posts_count)
        feed_l.addWidget(self.post_list, 2)
        feed_l.addWidget(self.post_detail, 3)
        feed_l.addLayout(post_btns)

        right = QVBoxLayout()
        right.setSpacing(16)
        advice_card = self.section()
        advice_l = QVBoxLayout(advice_card)
        advice_l.setContentsMargins(16, 16, 16, 16)
        advice_l.setSpacing(8)
        self.advice_title = QLabel(objectName="StepTitle")
        self.advice_p = QLabel(objectName="Body")
        self.advice_p.setWordWrap(True)
        self.advice_view = QTextEdit()
        self.advice_view.setReadOnly(True)
        self.advice_view.setMinimumHeight(110)
        self.advice_view.setMaximumHeight(180)
        for w in (self.advice_title, self.advice_p, self.advice_view):
            advice_l.addWidget(w)

        share_card = self.section()
        share_l = QVBoxLayout(share_card)
        share_l.setContentsMargins(16, 16, 16, 16)
        share_l.setSpacing(8)
        self.share_title = QLabel(objectName="StepTitle")
        self.share_p = QLabel(objectName="Body")
        self.share_p.setWordWrap(True)
        self.l_field = QLabel()
        self.field_box = QComboBox()
        self.field_box.currentIndexChanged.connect(lambda _i: self.refresh_community())
        self.l_post_title = QLabel()
        self.post_title_edit = QLineEdit()
        self.l_post_body = QLabel()
        self.share_edit = QTextEdit()
        self.share_edit.setPlaceholderText("")
        share_row = QHBoxLayout()
        self.account_lab = QLabel(objectName="Muted")
        self.account_lab.setWordWrap(True)
        self.b_post = QPushButton(objectName="Yellow")
        self.b_post.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_post.clicked.connect(self.publish_post)
        self.b_login = QPushButton(objectName="Ghost")
        self.b_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_login.clicked.connect(self.open_login)
        self.b_anon = QPushButton(objectName="Ghost")
        self.b_anon.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_anon.clicked.connect(self.publish_anonymous)
        for b in (self.b_post, self.b_login, self.b_anon):
            b.setMinimumHeight(36)
        share_row.addWidget(self.b_post)
        share_row.addWidget(self.b_login)
        share_row.addWidget(self.b_anon)
        share_row.addStretch(1)
        share_l.addWidget(self.share_title)
        share_l.addWidget(self.share_p)
        share_l.addWidget(self.account_lab)
        share_l.addWidget(self.l_field)
        share_l.addWidget(self.field_box)
        share_l.addWidget(self.l_post_title)
        share_l.addWidget(self.post_title_edit)
        share_l.addWidget(self.l_post_body)
        share_l.addWidget(self.share_edit, 1)
        share_l.addLayout(share_row)

        right.addWidget(advice_card, 0)
        right.addWidget(share_card, 1)
        teach.addWidget(feed_card, 1)
        teach.addLayout(right, 1)
        self.stack.addWidget(self.page_teach)

        self.page_set = QWidget(objectName="Page")
        st = QVBoxLayout(self.page_set)
        st.setContentsMargins(8, 8, 8, 8)
        form = self.section()
        fl = QVBoxLayout(form)
        fl.setContentsMargins(16, 16, 16, 16)
        fl.setSpacing(8)
        self.l_api = QLabel()
        self.api_edit = QLineEdit()
        self.api_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.l_res = QLabel()
        self.res_edit = QLineEdit()
        self.l_sb_url = QLabel()
        self.sb_url_edit = QLineEdit()
        self.sb_url_edit.setPlaceholderText("https://xxxxxxxx.supabase.co")
        self.l_sb_key = QLabel()
        self.sb_key_edit = QLineEdit()
        self.sb_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.b_save_cfg = QPushButton(objectName="Yellow")
        self.b_save_cfg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_save_cfg.clicked.connect(self.save_settings)
        for w in (
            self.l_api,
            self.api_edit,
            self.l_res,
            self.res_edit,
            self.l_sb_url,
            self.sb_url_edit,
            self.l_sb_key,
            self.sb_key_edit,
        ):
            fl.addWidget(w)
        fl.addWidget(self.b_save_cfg, 0, Qt.AlignmentFlag.AlignLeft)
        st.addWidget(form)
        st.addStretch(1)
        self.stack.addWidget(self.page_set)
        self.load_settings_fields()
        self.load_script()
        self.load_mapping()
        self.refresh_library()

    def _scroll(self, inner: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.viewport().setAutoFillBackground(False)
        inner.setAutoFillBackground(False)
        area.setStyleSheet("background: transparent; border: none;")
        area.setWidget(inner)
        return area

    def _cfg(self) -> dict:
        try:
            return load_config()
        except OSError:
            return {}

    def _toggle_lang(self) -> None:
        self._set_lang("en" if self.lang == "zh" else "zh")

    def _set_lang(self, lang: str) -> None:
        self.lang = lang
        cfg = self._cfg() or {"app": {}, "files": {}, "audio": {}, "video_params": {}, "slide_mapping": []}
        cfg.setdefault("app", {})["uiLang"] = lang
        try:
            materialize_work(cfg)
            files = cfg.get("files") or {}
            self.ppt_edit.setText(files.get("ppt_file") or "")
            self.txt_edit.setText(files.get("input_text") or "")
        except OSError:
            save_config(cfg, str(ROOT / "config.json"))
        self._apply_lang()
        self.refresh_home()
        self.refresh_library()
        if self.stack.currentIndex() == 4:
            self.refresh_community()

    def _fill_combo(self, box: QComboBox, keys: tuple[str, ...]) -> None:
        current = box.currentData()
        box.blockSignals(True)
        box.clear()
        for key in keys:
            box.addItem(self.t(key), key)
        if current:
            idx = box.findData(current)
            if idx >= 0:
                box.setCurrentIndex(idx)
        box.blockSignals(False)

    def _apply_lang(self) -> None:
        titles = {
            0: "home",
            1: "prepare",
            2: "generate",
            3: "library",
            4: "community",
            5: "settings",
        }
        for i, btn in enumerate(self.nav_btns):
            btn.setText(self.t(self.nav_keys[i]))
        idx = self.stack.currentIndex()
        self.h1.setText(self.t(titles.get(idx, "home")))
        hints = {
            1: "prepare_p",
            2: "generate_p",
            3: "lib_p",
            4: "teach_p",
            5: "sub",
        }
        self.sub.setText(self.t(hints.get(idx, "sub")))
        self.header_titles.setVisible(idx != 0)
        self.btn_lang.setVisible(idx == 0)
        self.btn_lang.setText("ENG" if self.lang == "zh" else "中")
        self.brand_sub.setText(self.t("sub"))
        self.b_run03.setText(self.t("run03"))
        self.b_run45.setText(self.t("run45"))
        self.b_stop.setText(self.t("stop"))
        self.script_hint.setText(self.t("script_p"))
        self.b_save_script.setText(self.t("save"))
        self.voice_hint.setText(self.t("voice_p"))
        labels = SPEAKER_LABELS.get(self.lang) or SPEAKER_LABELS["zh"]
        hints = SPEAKER_HINTS.get(self.lang) or SPEAKER_HINTS["zh"]
        for lab, sp in zip(self.voice_title_labs, SPEAKERS):
            lab.setText(labels.get(sp, sp))
        for lab, sp in zip(self.voice_code_labs, SPEAKERS):
            lab.setText(hints.get(sp, ""))
        self.generate_hint.setText(self.t("generate_p"))
        self.l_api.setText(self.t("api"))
        self.l_res.setText(self.t("res"))
        self.l_sb_url.setText(self.t("sb_url"))
        self.l_sb_key.setText(self.t("sb_key"))
        self.l_ppt.setText(self.t("ppt_path"))
        self.l_txt.setText(self.t("script_path"))
        self.b_ppt.setText(self.t("browse"))
        self.b_txt.setText(self.t("browse"))
        self.b_save_cfg.setText(self.t("save"))
        self.b_save_paths.setText(self.t("save_paths"))
        self.map_hint.setText(self.t("map_p"))
        self.b_auto_map.setText(self.t("auto_map"))
        self.b_add_row.setText(self.t("add_row"))
        self.b_del_row.setText(self.t("del_row"))
        self.b_validate.setText(self.t("validate"))
        self.b_save_map.setText(self.t("save_map"))
        self.hero_title.setText(self.t("hero"))
        self.hero_p.setText(self.t("hero_p"))
        self.hero_have.setText(self.t("cta_have"))
        self.hero_new.setText(self.t("cta_new"))
        for lab, key in zip(self.step_titles, ("p1_title", "p2_title", "p3_title")):
            lab.setText(self.t(key))
        for lab, key in zip(self.step_bodies, ("p1_body", "p2_body", "p3_body")):
            lab.setText(self.t(key))
        self.audiences_lab.setText(self.t("audiences"))
        self.ticker.set_items(PAINS[self.lang])
        self.prepare_hint.setText(self.t("prepare_p"))
        self.have_title.setText(self.t("have_title"))
        self.have_p.setText(self.t("have_p"))
        self.new_title.setText(self.t("new_title"))
        self.new_p.setText(self.t("new_p"))
        self.l_topic.setText(self.t("topic"))
        self.l_audience.setText(self.t("audience"))
        self.b_gen_draft.setText(self.t("gen_draft"))
        self.b_go_gen.setText(self.t("go_gen"))
        self._fill_combo(self.audience_box, AUDIENCES)
        self._fill_combo(self.field_box, FIELDS)
        self.lib_hint.setText(self.t("lib_p"))
        self.b_save_work.setText(self.t("save_work"))
        self.b_del_work.setText(self.t("delete"))
        self.b_open_work.setText(self.t("open_folder"))
        self.b_to_community.setText(self.t("to_community"))
        self.l_notes.setText(self.t("notes"))
        self.b_save_notes.setText(self.t("save_notes"))
        self.teach_hint.setText(self.t("teach_p"))
        self.share_title.setText(self.t("share_title"))
        self.share_p.setText(self.t("share_p"))
        self.l_field.setText(self.t("field"))
        self.l_post_title.setText(self.t("post_title_l"))
        self.l_post_body.setText(self.t("post_body_l"))
        self.b_post.setText(self.t("post_community"))
        self.b_anon.setText(self.t("anon_post"))
        self.b_login.setText(self.t("login"))
        self.advice_title.setText(self.t("advice_title"))
        self.advice_p.setText(self.t("advice_p"))
        self.posts_title.setText(self.t("posts"))
        self.b_open_post_video.setText(self.t("open_post_video"))
        self.b_open_post_folder.setText(self.t("open_folder"))
        self.b_del_post.setText(self.t("delete_post"))
        self.share_edit.setPlaceholderText(self.t("need_body"))
        self._refresh_account_label()

    def _on_nav(self, idx: int) -> None:
        self.stack.setCurrentIndex(idx)
        self._apply_lang()
        if idx == 0:
            self.refresh_home()
        if idx == 2:
            self.refresh_sentences()
        if idx == 3:
            self.refresh_library()
        if idx == 4:
            self.refresh_community(force=False)

    def _go_prepare(self, from_topic: bool) -> None:
        self.nav_btns[1].click()
        if from_topic:
            self.topic_edit.setFocus()
        else:
            self.script_edit.setFocus()

    def _abs(self, name: str) -> Path:
        p = Path(name)
        return p if p.is_absolute() else ROOT / name

    def refresh_home(self) -> None:
        return

    def refresh_library(self) -> None:
        current = self.selected_work_id
        self.work_list.blockSignals(True)
        self.work_list.clear()
        works = list_works()
        restore = 0
        if not works:
            self.work_list.addItem(self.t("lib_empty"))
            self.notes_edit.clear()
            self.selected_work_id = None
            self.work_list.blockSignals(False)
            return
        for i, work in enumerate(works):
            mark = "●" if work.get("video_path") and _exists(str(work.get("video_path"))) else "○"
            title = work.get("title") or self.t("title")
            when = work.get("updated_at") or work.get("created_at") or ""
            item_text = f"{mark}  {title}    {when}"
            self.work_list.addItem(item_text)
            self.work_list.item(i).setData(Qt.ItemDataRole.UserRole, int(work["id"]))
            if current is not None and int(work["id"]) == current:
                restore = i
        self.work_list.setCurrentRow(restore)
        self.work_list.blockSignals(False)
        self._on_work_row(restore)

    def refresh_community(self, force: bool = False) -> None:
        self.refresh_advice()
        self._refresh_account_label()
        if not self.post_title_edit.text().strip():
            self.post_title_edit.setText(self._lesson_title())
        works = list_works()
        note = (works[0].get("notes") or "") if works else ""
        if not self.share_edit.toPlainText().strip() and note:
            self.share_edit.setPlainText(note)
        field = str(self.field_box.currentData() or "school")
        cfg = self._cfg()
        cached = self._community_cache.get(field)
        if cached is not None and not force:
            self._paint_community_posts(field, cached)
        elif not is_configured(cfg):
            self._paint_community_posts(field, list_posts(field))
            return
        else:
            self.posts_title.setText(f"{self.t(field)}  ·  {self.t('posts')}")
            self.posts_count.setText(self.t("posts_loading"))
        if is_configured(cfg):
            self._fetch_community(cfg, field, force=force)

    def _fetch_community(self, cfg: dict, field: str, *, force: bool) -> None:
        if self._community_fetching == field and not force:
            return
        if self._community_thread is not None:
            try:
                self._community_thread.quit()
            except Exception:
                pass
        self._community_fetching = field
        worker = CommunityFetchWorker()
        worker.cfg = cfg
        worker.field = field
        worker.force = force
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_community_fetched)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        self._community_worker = worker
        self._community_thread = thread
        thread.start()

    def _on_community_fetched(self, field: str, posts: list, error: str) -> None:
        self._community_fetching = None
        current = str(self.field_box.currentData() or "school")
        if error:
            self.account_lab.setText(f"{self.t('cloud_off')}\n{error}")
            posts = list_posts(field)
        else:
            self._community_cache[field] = posts
        if field != current:
            return
        self._paint_community_posts(field, posts)

    def _paint_community_posts(self, field: str, posts: list) -> None:
        self.posts_title.setText(f"{self.t(field)}  ·  {self.t('posts')}")
        self.posts_count.setText(self.t("posts_count").format(n=len(posts)))
        self.post_list.blockSignals(True)
        self.post_list.clear()
        if not posts:
            empty = QListWidgetItem(self.t("empty_posts"))
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.post_list.addItem(empty)
            self.post_list.blockSignals(False)
            self.post_detail.setPlainText(self.t("empty_posts"))
            return
        for post in posts:
            title = self._post_title(post)
            when = post.get("created_at") or ""
            if post.get("is_anonymous"):
                tag = f"[{self.t('anon_tag')}]  "
            elif post.get("is_sample"):
                tag = f"[{self.t('sample_tag')}]  "
            else:
                tag = ""
            item = QListWidgetItem(f"{tag}{title}    {when}")
            item.setData(Qt.ItemDataRole.UserRole, post)
            self.post_list.addItem(item)
        self.post_list.blockSignals(False)
        if self.post_list.count():
            self.post_list.setCurrentRow(0)
            self._on_post_row(0)

    def _refresh_account_label(self) -> None:
        cfg = self._cfg()
        user = current_user()
        if not is_configured(cfg):
            self.account_lab.setText(self.t("cloud_off"))
            self.b_login.setText(self.t("login"))
            return
        if user:
            email = str(user.get("email") or "").strip()
            self.account_lab.setText(self.t("logged_in").format(email=email) + "\n" + self.t("cloud_ok"))
            self.b_login.setText(self.t("logout"))
        else:
            self.account_lab.setText(self.t("logged_out"))
            self.b_login.setText(self.t("login"))

    def _post_title(self, post: dict) -> str:
        if self.lang == "en":
            return (post.get("title_en") or post.get("title") or "").strip() or self.t("title")
        return (post.get("title") or post.get("title_en") or "").strip() or self.t("title")

    def _post_body(self, post: dict) -> str:
        if self.lang == "en":
            return (post.get("body_en") or post.get("body") or "").strip()
        return (post.get("body") or post.get("body_en") or "").strip()

    def _current_post(self) -> dict | None:
        item = self.post_list.currentItem()
        if not item:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(value, dict):
            return value
        if value is not None:
            return get_post(int(value))
        return None

    def _on_post_row(self, _row: int) -> None:
        post = self._current_post()
        if not post:
            self.post_detail.setPlainText(self.t("empty_posts"))
            return
        field = self.t(post.get("field") or "school")
        when = post.get("created_at") or ""
        extra = ""
        if post.get("is_anonymous"):
            extra = f"\n{self.t('anon_tag')}"
        elif post.get("is_sample"):
            extra = f"\n{self.t('sample_tag')}"
        body = self._post_body(post)
        video = (post.get("video_path") or "").strip()
        video_line = video if video else self.t("no_post_video")
        self.post_detail.setPlainText(
            f"{self._post_title(post)}\n{field}  ·  {when}{extra}\n\n{body}\n\n{video_line}"
        )

    def open_post_video(self) -> None:
        post = self._current_post()
        if not post:
            return
        path = self._abs(post.get("video_path") or "")
        if not path.is_file():
            QMessageBox.information(self, self.t("title"), self.t("no_post_video"))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def open_post_folder(self) -> None:
        post = self._current_post()
        if not post:
            return
        path = self._abs(post.get("video_path") or "")
        folder = path.parent if path.suffix else path
        if not folder.is_dir():
            QMessageBox.information(self, self.t("title"), self.t("no_post_video"))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def remove_post(self) -> None:
        post = self._current_post()
        if not post:
            return
        if QMessageBox.question(
            self, self.t("title"), self.t("confirm_delete_post")
        ) != QMessageBox.StandardButton.Yes:
            return
        cfg = self._cfg()
        if post.get("cloud"):
            try:
                delete_cloud_post(cfg, str(post.get("id")))
            except Exception as e:
                QMessageBox.warning(self, self.t("title"), str(e))
                return
        else:
            delete_post(int(post["id"]))
        self._community_cache.pop(str(self.field_box.currentData() or "school"), None)
        self.refresh_community(force=True)

    def _current_work_id(self) -> int | None:
        item = self.work_list.currentItem()
        if not item:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        return int(value) if value is not None else None

    def _on_work_row(self, _row: int) -> None:
        work_id = self._current_work_id()
        self.selected_work_id = work_id
        if work_id is None:
            self.notes_edit.clear()
            return
        work = get_work(work_id)
        self.notes_edit.setPlainText((work or {}).get("notes") or "")

    def _lesson_title(self) -> str:
        cfg = self._cfg()
        files = cfg.get("files") or {}
        folder = (files.get("work_dir") or "").strip()
        if folder:
            name = Path(folder).name
            if name:
                return name
        ppt = (files.get("ppt_file") or "").strip()
        if ppt:
            parent = Path(ppt).parent.name
            if parent and parent not in {"outputs", "."}:
                return parent
            stem = Path(ppt).stem
            if stem not in {"Slides", "课件", "training"}:
                return stem
        topic = self.topic_edit.text().strip()
        return topic or self.t("untitled_lesson")

    def _slide_png_count(self) -> int:
        folder = images_dir(self._cfg())
        if not folder.is_dir():
            return 0
        return len({p.stem.lower() for p in folder.glob("*.png")})

    def _timestamps_file(self) -> Path:
        return timestamps_path(self._cfg())

    def _work_payload(self, notes: str | None = None, status: str = "draft") -> dict:
        cfg = self._cfg()
        files = cfg.get("files") or {}
        n_slides = self._slide_png_count()
        video = files.get("video_output") or VIDEO_NAME
        audio = files.get("audio_output") or AUDIO_NAME
        if _exists(video):
            status = "ready"
        payload = {
            "title": self._lesson_title(),
            "ppt_path": files.get("ppt_file") or "",
            "script_path": files.get("input_text") or "",
            "audio_path": audio if _exists(audio) else "",
            "video_path": video if _exists(video) else "",
            "slide_count": n_slides,
            "status": status,
        }
        if notes is not None:
            payload["notes"] = notes
        return payload

    def snapshot_work(self, manual: bool = False) -> None:
        upsert_work(self._work_payload())
        self.refresh_library()
        if manual:
            QMessageBox.information(self, self.t("title"), self.t("saved"))

    def open_selected_work(self) -> None:
        work_id = self._current_work_id()
        work = get_work(work_id) if work_id else None
        if not work:
            return
        for key in ("video_path", "ppt_path", "script_path"):
            name = work.get(key) or ""
            if name and _exists(name):
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._abs(name).parent)))
                return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(ROOT)))

    def delete_selected_work(self) -> None:
        work_id = self._current_work_id()
        if work_id is None:
            return
        delete_work(work_id)
        self.selected_work_id = None
        self.refresh_library()

    def save_work_notes(self) -> None:
        work_id = self._current_work_id()
        if work_id is None:
            self.snapshot_work(manual=False)
            work_id = self._current_work_id()
        if work_id is None:
            return
        save_notes(work_id, self.notes_edit.toPlainText())
        QMessageBox.information(self, self.t("title"), self.t("saved"))

    def _script_text(self) -> str:
        if self.script_edit.toPlainText().strip():
            return self.script_edit.toPlainText()
        cfg = self._cfg()
        name = (cfg.get("files") or {}).get("input_text") or "input.txt"
        path = self._abs(name)
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def _split_script(self, text: str) -> list[str]:
        parts = [p.strip() for p in text.replace("\r\n", "\n").split("\n") if p.strip()]
        if len(parts) <= 1:
            parts = [p.strip() for p in text.replace("。", "。\n").split("\n") if p.strip()]
        return parts or ([text.strip()] if text.strip() else [])

    def _draft_post_texts(self) -> tuple[str, str] | None:
        body = self.share_edit.toPlainText().strip()
        title = self.post_title_edit.text().strip() or self._lesson_title()
        if too_short(body):
            QMessageBox.warning(self, self.t("title"), self.t("need_body"))
            return None
        if find_banned(f"{title}\n{body}"):
            QMessageBox.warning(self, self.t("title"), self.t("banned"))
            return None
        return title, body

    def open_login(self) -> None:
        if current_user():
            sign_out()
            self._refresh_account_label()
            return
        cfg = self._cfg()
        if not is_configured(cfg):
            QMessageBox.warning(self, self.t("title"), self.t("need_supabase"))
            self.nav_btns[5].click()
            return
        dlg = AccountDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_account_label()

    def publish_anonymous(self) -> None:
        self._publish(anonymous=True)

    def publish_post(self) -> None:
        self._publish(anonymous=False)

    def _publish(self, *, anonymous: bool) -> None:
        texts = self._draft_post_texts()
        if not texts:
            return
        title, body = texts
        cfg = self._cfg()
        if not is_configured(cfg):
            QMessageBox.warning(self, self.t("title"), self.t("need_supabase"))
            self.nav_btns[5].click()
            return
        if not anonymous and not current_user():
            QMessageBox.information(self, self.t("title"), self.t("need_login"))
            self.open_login()
            if not current_user():
                return
        payload_work = self._work_payload(notes=body)
        work_id = upsert_work(payload_work)
        save_notes(work_id, body)
        cloud_row = {
            "field": self.field_box.currentData() or "school",
            "title": title,
            "body": body,
            "is_anonymous": anonymous,
        }
        if not anonymous:
            cloud_row["user_id"] = current_user()["id"]
        try:
            insert_cloud_post(cfg, cloud_row, as_user=not anonymous)
        except Exception as e:
            QMessageBox.warning(self, self.t("title"), str(e))
            return
        add_post(
            {
                "work_id": work_id,
                "title": title,
                "title_en": title if self.lang == "en" else "",
                "body_en": body if self.lang == "en" else "",
                "field": cloud_row["field"],
                "body": body,
                "video_path": payload_work.get("video_path") or "",
            }
        )
        self.refresh_library()
        self._community_cache.pop(str(self.field_box.currentData() or "school"), None)
        self.refresh_community(force=True)
        QMessageBox.information(self, self.t("title"), self.t("posted"))

    def refresh_advice(self) -> None:
        text = self._script_text()
        sents = self._split_script(text)
        n_chars = len(text.replace(" ", "").replace("\n", ""))
        n_slides = self._slide_png_count()
        mapping = self.mapping_from_table()
        tips: list[str] = []
        zh = self.lang == "zh"
        video_ready = _exists((self._cfg().get("files") or {}).get("video_output") or VIDEO_NAME)
        if video_ready:
            tips.append(
                "成片已经在。改音色或改稿后，到「生成」里重新合成即可，不必重录、也不必再找安静房间。"
                if zh
                else "The film is ready. Change the voice or the script, then remake it — no re-recording, no quiet room."
            )
        if not text.strip():
            tips.append("还没有口播稿。可以到「准备」里导入材料，或从主题生成一版。" if zh else "There is no script yet. Import materials in Prepare, or draft from a topic.")
        else:
            long_sents = [s for s in sents if len(s) > 42]
            if long_sents:
                tips.append(
                    f"有 {len(long_sents)} 句超过 40 字，画面会显得赶。比如：「{long_sents[0][:28]}…」可以拆成两句再出一版。"
                    if zh
                    else f"{len(long_sents)} line(s) run longer than 40 characters. Split a line such as “{long_sents[0][:28]}…” and remake."
                )
            if n_slides and len(sents) and len(sents) > n_slides * 4:
                tips.append(
                    "口播比幻灯片密很多。有的页只留一句标题，把例子放到下一页，下一轮生成会更跟得上。"
                    if zh
                    else "The narration is denser than the slides. One idea per page will make the next film easier to follow."
                )
            if n_slides and len(sents) and n_slides > len(sents):
                tips.append(
                    "页数比句子还多，有的页可能会一闪而过。可以把相近的两页并在同一句口播里。"
                    if zh
                    else "There are more pages than spoken lines. Pair similar pages with the same sentence."
                )
            if n_chars < 80:
                tips.append(
                    "稿子偏短。可以在中间加一个给听众的问题，返稿后再生成。"
                    if zh
                    else "The script is quite short. Add a question in the middle, then remake."
                )
            if sents:
                pause_at = max(1, len(sents) // 3)
                tips.append(
                    f"建议在第 {pause_at} 句附近留一个停顿，方便线下讲授时插问，再把这一版发到社区。"
                    if zh
                    else f"Leave a pause around line {pause_at} for a live question, then share that version with peers."
                )
        if not mapping:
            tips.append(
                "幻灯片还没有和口播对齐。音频做好后，到「生成」点「按课件自动对齐」。"
                if zh
                else "Slides are not aligned yet. After the audio is ready, use Align from slides."
            )
        if n_chars:
            minutes = max(1, round(n_chars / 180))
            tips.append(
                f"整课大约 {minutes} 分钟。超过 8 分钟的自学视频很少被看完，可以拆成两段再发社区。"
                if zh
                else f"About {minutes} minute(s). Clips longer than eight minutes are often abandoned; split before sharing."
            )
        self.advice_view.setPlainText("\n\n".join(f"{i + 1}. {t}" for i, t in enumerate(tips)))

    def load_script(self) -> None:
        cfg = self._cfg()
        name = (cfg.get("files") or {}).get("input_text") or "input.txt"
        path = ROOT / name
        if not path.is_file():
            path = self._abs(name)
        self.script_edit.setPlainText(path.read_text(encoding="utf-8") if path.is_file() else "")

    def save_script(self) -> None:
        cfg = self._cfg() or {"app": {}, "files": {}, "audio": {}, "video_params": {}, "slide_mapping": []}
        cfg.setdefault("files", {})
        name = self.txt_edit.text().strip() or cfg["files"].get("input_text") or "input.txt"
        cfg["files"]["input_text"] = name
        if self.ppt_edit.text().strip():
            cfg["files"]["ppt_file"] = self.ppt_edit.text().strip()
        materialize_work(cfg)
        self.txt_edit.setText(cfg["files"]["input_text"])
        self.ppt_edit.setText(cfg["files"]["ppt_file"])
        path = self._abs(cfg["files"]["input_text"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.script_edit.toPlainText(), encoding="utf-8")
        save_config(cfg, str(ROOT / "config.json"))
        QMessageBox.information(self, self.t("title"), self.t("saved"))

    def generate_draft(self) -> None:
        topic = self.topic_edit.text().strip()
        if not topic:
            QMessageBox.warning(self, self.t("title"), self.t("need_topic"))
            return
        audience = self.audience_box.currentData() or "school"
        try:
            script_path, ppt_path = build_draft(topic, audience, self.lang)
        except Exception as e:
            QMessageBox.warning(self, self.t("title"), str(e))
            return
        cfg = self._cfg() or {"app": {}, "files": {}, "audio": {}, "video_params": {}, "slide_mapping": []}
        cfg.setdefault("files", {})
        cfg["files"]["input_text"] = rel_to_root(script_path)
        cfg["files"]["ppt_file"] = rel_to_root(ppt_path)
        cfg["files"]["work_dir"] = rel_to_root(script_path.parent)
        for stale in ("audio_output", "video_output", "images_dir"):
            cfg["files"].pop(stale, None)
        materialize_work(cfg)
        self.txt_edit.setText(cfg["files"]["input_text"])
        self.ppt_edit.setText(cfg["files"]["ppt_file"])
        self.load_script()
        QMessageBox.information(self, self.t("title"), self.t("draft_ok"))

    def pick_voice(self, name: str) -> None:
        cfg = self._cfg()
        cfg.setdefault("audio", {})["speaker"] = name
        save_config(cfg, str(ROOT / "config.json"))
        for card, sp in zip(self.voice_cards, SPEAKERS):
            card.setProperty("selected", sp == name)
            card.style().unpolish(card)
            card.style().polish(card)

    def load_settings_fields(self) -> None:
        cfg = self._cfg()
        app = cfg.get("app") or {}
        files = cfg.get("files") or {}
        self.api_edit.setText(app.get("apiKey") or "")
        self.res_edit.setText(app.get("resourceID") or "seed-tts-2.0")
        supabase = cfg.get("supabase") or {}
        self.sb_url_edit.setText(supabase.get("url") or "")
        self.sb_key_edit.setText(supabase.get("anonKey") or "")
        self.ppt_edit.setText(files.get("ppt_file") or "")
        self.txt_edit.setText(files.get("input_text") or "")

    def pick_ppt(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.t("ppt"), str(ROOT), "PPT (*.pptx *.ppt)")
        if path:
            try:
                rel = os.path.relpath(path, ROOT)
                path = rel if not rel.startswith("..") else path
            except ValueError:
                pass
            self.ppt_edit.setText(path.replace("\\", "/"))

    def pick_txt(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.t("script_stat"), str(ROOT), "Text (*.txt)")
        if path:
            try:
                rel = os.path.relpath(path, ROOT)
                path = rel if not rel.startswith("..") else path
            except ValueError:
                pass
            self.txt_edit.setText(path.replace("\\", "/"))
            self.load_script()

    def save_paths(self) -> None:
        cfg = self._cfg() or {"app": {}, "files": {}, "audio": {}, "video_params": {}, "slide_mapping": []}
        cfg.setdefault("files", {})
        cfg["files"]["ppt_file"] = self.ppt_edit.text().strip()
        cfg["files"]["input_text"] = self.txt_edit.text().strip()
        for stale in ("work_dir", "audio_output", "video_output", "images_dir"):
            cfg["files"].pop(stale, None)
        materialize_work(cfg)
        self.ppt_edit.setText(cfg["files"]["ppt_file"])
        self.txt_edit.setText(cfg["files"]["input_text"])
        self.load_script()
        QMessageBox.information(self, self.t("title"), self.t("saved"))

    def save_settings(self) -> None:
        cfg = self._cfg() or {"app": {}, "files": {}, "audio": {}, "video_params": {}, "slide_mapping": []}
        cfg.setdefault("app", {})
        cfg.setdefault("files", {})
        key = self.api_edit.text().strip()
        if key:
            cfg["app"]["apiKey"] = key
        cfg["app"]["resourceID"] = self.res_edit.text().strip() or "seed-tts-2.0"
        cfg.setdefault("supabase", {})
        cfg["supabase"]["url"] = normalize_supabase_url(self.sb_url_edit.text().strip())
        cfg["supabase"]["anonKey"] = self.sb_key_edit.text().strip()
        cfg["files"]["ppt_file"] = self.ppt_edit.text().strip()
        cfg["files"]["input_text"] = self.txt_edit.text().strip()
        cfg["slide_mapping"] = self.mapping_from_table()
        materialize_work(cfg)
        self.ppt_edit.setText(cfg["files"]["ppt_file"])
        self.txt_edit.setText(cfg["files"]["input_text"])
        QMessageBox.information(self, self.t("title"), self.t("saved"))

    def mapping_from_table(self) -> list[dict]:
        rows: list[dict] = []
        for i in range(self.map_table.rowCount()):
            start_item = self.map_table.item(i, 0)
            end_item = self.map_table.item(i, 1)
            slide_item = self.map_table.item(i, 2)
            try:
                start = int((start_item.text() if start_item else "0").strip())
                end = int((end_item.text() if end_item else "0").strip())
            except ValueError:
                continue
            slide = (slide_item.text() if slide_item else slide_png_name(i + 1, lang=self.lang)).strip()
            rows.append({"start": start, "end": end, "slide": slide or slide_png_name(i + 1, lang=self.lang)})
        return rows

    def fill_mapping_table(self, rows: list[dict]) -> None:
        self.map_table.setRowCount(0)
        for row in rows:
            i = self.map_table.rowCount()
            self.map_table.insertRow(i)
            self.map_table.setItem(i, 0, QTableWidgetItem(str(int(row["start"]))))
            self.map_table.setItem(i, 1, QTableWidgetItem(str(int(row["end"]))))
            self.map_table.setItem(i, 2, QTableWidgetItem(str(row.get("slide") or slide_png_name(i + 1, lang=self.lang))))

    def load_mapping(self) -> None:
        cfg = self._cfg()
        rows: list[dict] = []
        for i, item in enumerate(cfg.get("slide_mapping") or []):
            if isinstance(item, dict):
                rows.append(
                    {
                        "start": int(item["start"]),
                        "end": int(item["end"]),
                        "slide": item.get("slide") or slide_png_name(i + 1, lang=self.lang),
                    }
                )
            else:
                rows.append(
                    {
                        "start": int(item[0]),
                        "end": int(item[1]),
                        "slide": item[2] if len(item) > 2 else slide_png_name(i + 1, lang=self.lang),
                    }
                )
        self.fill_mapping_table(rows)
        self.refresh_sentences()

    def refresh_sentences(self) -> None:
        self.sent_list.clear()
        ts = self._timestamps_file()
        if not ts.is_file():
            self.sent_list.addItem(self.t("no_ts"))
            return
        try:
            sentences = json.loads(ts.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.sent_list.addItem(self.t("no_ts"))
            return
        for i, s in enumerate(sentences):
            text = str(s.get("text", "")).replace("\n", " ").strip()
            preview = text[:50] + ("…" if len(text) > 50 else "")
            st = s.get("startTime", 0)
            et = s.get("endTime", 0)
            try:
                span = f"({float(st):.2f}s–{float(et):.2f}s)"
            except (TypeError, ValueError):
                span = ""
            self.sent_list.addItem(f"{i:>4}: {preview}  {span}")

    def _load_sentences(self) -> list[dict]:
        ts = self._timestamps_file()
        if not ts.is_file():
            return []
        try:
            data = json.loads(ts.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return data if isinstance(data, list) else []

    def add_map_row(self) -> None:
        n = self.map_table.rowCount() + 1
        self.fill_mapping_table(self.mapping_from_table() + [{"start": 0, "end": 0, "slide": slide_png_name(n, lang=self.lang)}])

    def delete_map_row(self) -> None:
        rows = sorted({idx.row() for idx in self.map_table.selectedIndexes()}, reverse=True)
        table = self.mapping_from_table()
        for i in rows:
            if 0 <= i < len(table):
                del table[i]
        self.fill_mapping_table(table)

    def save_mapping(self, silent: bool = False) -> bool:
        cfg = self._cfg() or {"app": {}, "files": {}, "audio": {}, "video_params": {}, "slide_mapping": []}
        cfg["slide_mapping"] = self.mapping_from_table()
        save_config(cfg, str(ROOT / "config.json"))
        if not silent:
            QMessageBox.information(self, self.t("title"), self.t("saved"))
        return True

    def validate_mapping(self, silent: bool = False) -> tuple[bool, str]:
        rows = self.mapping_from_table()
        if not rows:
            msg = self.t("map_empty")
            if not silent:
                QMessageBox.warning(self, self.t("title"), msg)
            return False, msg
        sentences = self._load_sentences()
        n = len(sentences)
        if n == 0:
            msg = self.t("no_sents")
            if not silent:
                QMessageBox.warning(self, self.t("title"), msg)
            return False, msg
        covered = [-1] * n
        for page_i, row in enumerate(rows):
            s, e = int(row["start"]), int(row["end"])
            if s < 0 or e >= n or s > e:
                msg = f"row {page_i + 1}: {s}–{e} (n={n})"
                if not silent:
                    QMessageBox.warning(self, self.t("title"), msg)
                return False, msg
            for i in range(s, e + 1):
                if covered[i] < 0:
                    covered[i] = page_i
        gaps = [i for i, v in enumerate(covered) if v < 0]
        if gaps:
            preview = gaps[:12]
            extra = "…" if len(gaps) > 12 else ""
            msg = f"{len(gaps)} uncovered: {preview}{extra}"
            if not silent:
                QMessageBox.warning(self, self.t("title"), msg)
            return False, msg
        msg = f"{len(rows)} slides / {n} sentences"
        if not silent:
            QMessageBox.information(self, self.t("title"), msg)
        return True, msg

    def auto_map(self) -> None:
        sentences = self._load_sentences()
        if not sentences:
            QMessageBox.warning(self, self.t("title"), self.t("need_ts"))
            return
        cfg = self._cfg()
        ppt_name = ((cfg.get("files") or {}).get("ppt_file") or "").strip()
        ppt = Path(ppt_name)
        if not ppt.is_absolute():
            ppt = ROOT / ppt_name
        if not ppt.is_file():
            QMessageBox.warning(self, self.t("title"), self.t("need_ppt"))
            return
        if self.map_table.rowCount() and QMessageBox.question(
            self, self.t("title"), self.t("overwrite")
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            mapper = importlib.import_module("01_auto_map")
            slide_texts = mapper.extract_slide_texts(str(ppt))
            detailed, warnings = mapper.auto_map_sentences(slide_texts, sentences, lang=self.lang)
            clean = [
                {"start": int(m["start"]), "end": int(m["end"]), "slide": m["slide"]}
                for m in detailed
            ]
        except ImportError:
            QMessageBox.warning(self, self.t("title"), self.t("need_pptx"))
            return
        except Exception as e:
            QMessageBox.warning(self, self.t("title"), str(e))
            return
        if not clean:
            QMessageBox.warning(self, self.t("title"), "\n".join(warnings) or self.t("map_empty"))
            return
        self.fill_mapping_table(clean)
        self.save_mapping(silent=True)
        self.log.append(f"—— {self.t('job_auto')} ——")
        self.log.append(
            self.t("map_log").format(
                pages=len(slide_texts), sents=len(sentences), mapped=len(clean)
            )
        )
        for w in warnings[:12]:
            self.log.append(w)
        QMessageBox.information(self, self.t("title"), self.t("saved"))

    def _remember_lesson_paths(self) -> None:
        cfg = self._cfg() or {"app": {}, "files": {}, "audio": {}, "video_params": {}, "slide_mapping": []}
        files = cfg.setdefault("files", {})
        ppt = self.ppt_edit.text().strip()
        txt = self.txt_edit.text().strip()
        if ppt:
            files["ppt_file"] = ppt
        if txt:
            files["input_text"] = txt
        for stale in ("work_dir", "audio_output", "video_output", "images_dir"):
            files.pop(stale, None)
        materialize_work(cfg)
        self.ppt_edit.setText(files.get("ppt_file") or "")
        self.txt_edit.setText(files.get("input_text") or "")

    def start_job(self, scripts: list[str], need_map: bool = False) -> None:
        if self.busy:
            QMessageBox.warning(self, self.t("title"), self.t("busy"))
            return
        if need_map:
            self.save_mapping(silent=True)
            ok, msg = self.validate_mapping(silent=True)
            if not ok:
                QMessageBox.warning(self, self.t("title"), msg)
                return
        self._remember_lesson_paths()
        self.busy = True
        self._job_scripts = list(scripts)
        self.worker = JobWorker()
        self.worker.scripts = scripts
        self.worker.lang = self.lang
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.line.connect(self.log.append)
        self.worker.done.connect(self._job_done)
        self.thread.start()
        self.nav_btns[2].click()

    def _job_done(self, status: str) -> None:
        scripts = getattr(self, "_job_scripts", [])
        self.busy = False
        if self.thread:
            self.thread.quit()
            self.thread.wait(3000)
        if status == "ok":
            self.snapshot_work(manual=False)
        self.refresh_library()
        self.refresh_sentences()
        if status == "ok":
            if "05" in scripts:
                self._offer_media("video")
            elif "03" in scripts:
                self._offer_media("audio")

    def _offer_media(self, kind: str) -> None:
        cfg = self._cfg()
        files = cfg.get("files") or {}
        key = "video_output" if kind == "video" else "audio_output"
        path = self._abs(files.get(key) or "")
        if not path.is_file():
            return
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle(self.t("video_ready_title" if kind == "video" else "audio_ready_title"))
        box.setText(self.t("video_ready" if kind == "video" else "audio_ready"))
        box.setInformativeText(str(path))
        play = box.addButton(
            self.t("open_video" if kind == "video" else "open_audio"),
            QMessageBox.ButtonRole.AcceptRole,
        )
        folder = box.addButton(self.t("open_folder"), QMessageBox.ButtonRole.ActionRole)
        box.addButton(self.t("later"), QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(play)
        box.exec()
        clicked = box.clickedButton()
        if clicked is play:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        elif clicked is folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))

    def stop_job(self, *, silent: bool = False) -> None:
        if self.worker:
            self.worker.request_stop()
        self.busy = False
        if not silent:
            QMessageBox.information(self, self.t("title"), self.t("stopped"))

    def closeEvent(self, event) -> None:  # noqa: N802
        self.stop_job(silent=True)
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait(2000)
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    icon = ROOT / "assets" / "iris.ico"
    if icon.is_file():
        app.setWindowIcon(QIcon(str(icon)))
    app.setStyle("Fusion")
    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor("#f6f4ef"))
    pal.setColor(QPalette.ColorRole.Base, QColor("#efece4"))
    pal.setColor(QPalette.ColorRole.Text, QColor("#243040"))
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#243040"))
    pal.setColor(QPalette.ColorRole.Button, QColor("#1f5c4f"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor("#f6f4ef"))
    app.setPalette(pal)
    app.setFont(QFont("Microsoft YaHei UI", 10))
    app.setStyleSheet(QSS)
    win = Studio()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
