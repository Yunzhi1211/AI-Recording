[English](README.md) | [简体中文](README_zh.md)

# Iris Studio

> Windows 桌面流水线：用讲稿和 PowerPoint 生成带口播的翻页视频，无需出镜、无需安静录音环境。

## 项目概述

Iris Studio 是面向教师、企业培训讲师、以及需要把既有资料做成可观看成片的用户的 PyQt6 桌面程序。系统**不采集**摄像头或麦克风。口播由云端语音合成（TTS）生成；每一页幻灯片经 Microsoft PowerPoint 导出为图片；口播句子与页面对齐后，由 FFmpeg 拼接成片。

常规输入为一份 `.pptx` 与一份纯文本讲稿。若尚无材料，可在「准备」页按主题与受众（学校 / 职场 / 个人学习）生成初稿。每一课以普通文件夹形式落在 `outputs/` 下。可选的 Supabase 社区用于按领域交流讲授经验；**制作视频不要求登录**。

设计原则：

- **课文件本地优先** — 成片、口播、课件、文稿使用可读文件名；内部中间件放在「工作文件」子目录。
- **步骤可复现** — 同一套六个流水线阶段既可在窗口中运行，也可在命令行运行。
- **密钥隔离** — API 密钥只存在于被 Git 忽略的 `config.json`；仓库仅提供空模板。
- **云端可选** — 社区与成片互不绑定。

## 功能

- **首页** — 产品主句，以及「已有材料」与「从主题开始」入口。
- **准备** — 导入已有讲稿/课件，或按受众从主题生成初稿。
- **生成** — 选择普通话音色、合成音频、按课件自动对齐翻页、编码视频。
- **成片** — 本地作品库（SQLite），打开文件夹或删除条目。
- **社区** — 按领域筛选动态（学校 / 职场 / 个人）。实名发布需登录；匿名发布不需要。制作视频始终不强制登录。
- **设置** — 字节跳动 TTS 凭证、可选的 Supabase 地址与 anon key、当前课路径。
- **中英界面** — 含课文件夹命名（如 `课件.pptx` / `Slides.pptx`）。

## 运行环境

| 项目 | 说明 |
|------|------|
| 操作系统 | **Windows**（依赖 PowerPoint COM 与 `pywin32`） |
| Python | 建议 3.10 及以上 |
| Microsoft PowerPoint | 导出幻灯片 PNG 所必需 |
| FFmpeg | 将 `ffmpeg.exe` 放到 `assets/`（不随仓库分发） |
| 网络 | TTS 提交/查询，以及可选的社区接口 |

Python 依赖见 `requirements.txt`：`PyQt6`、`requests`、`Pillow`、`python-pptx`、`pywin32`。

## 快速开始

1. 克隆仓库；如需隔离环境可自行创建虚拟环境。
2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 将配置模板复制到仓库根目录（填写后该文件已被 `.gitignore` 排除）：

```bash
copy assets\config.template.json config.json
```

4. 下载 Windows 版 [FFmpeg](https://ffmpeg.org/)，将 `ffmpeg.exe` 放到 `assets/ffmpeg.exe`。
5. 在「设置」中填写字节跳动 OpenSpeech TTS 的 `apiKey`，或旧控制台的 `appID` + `accessKey`。若控制台资源名不是默认的 `seed-tts-2.0`，请同时修改 `resourceID`。
6. 启动：

   - 双击仓库根目录的 **`Iris Studio.exe`**（推荐，带应用图标），或
   - `python 05_qt_app.py`，或
   - `start.bat`（控制台备用；Windows 无法为 `.bat` 指定图标）。

7. 准备材料 → 合成音频 → 按课件对齐 → 合成视频。成品在 `outputs/<课名>/`。

## 建议流程

```
准备（导入或从主题生成）
    → 生成（音色 → 音频 → 翻页时间 → 视频）
        → 成片（本地复查）
            → 社区（可选，交流讲授经验）
```

成片不依赖 Supabase，也不依赖账号。

## 流水线阶段

界面通过阶段编号调用 `04_pipeline.py`。在仓库根目录、已有 `config.json` 时，也可在终端使用相同编号（必要时设置环境变量 `VIDEO_TOOL_CONFIG`）。

| 阶段 | 命令 | 职责 |
|------|------|------|
| `00` | `python 04_pipeline.py 00` | 检查配置、讲稿、课件、FFmpeg、翻页对齐 |
| `01` | `python 04_pipeline.py 01` | 经 PowerPoint（`DispatchEx`）导出每页 PNG |
| `02` | `python 04_pipeline.py 02` | 提交 TTS 任务（网络中断会重试） |
| `03` | `python 04_pipeline.py 03` | 轮询直至下载音频与句子时间戳 |
| `04` | `python 04_pipeline.py 04` | 按句–页映射生成 FFmpeg concat 时长 |
| `05` | `python 04_pipeline.py 05` | 编码 H.264 + AAC（`libx264`）并与口播混流 |

「合成音频」执行 `00`–`03`。「合成视频」执行 `04`–`05`，且需要有效翻页对齐。

默认编码参数（可在 `config.json` 的 `video_params` 中覆盖）：`854x480`、24 fps、`ultrafast`、CRF 30、音频 `128k`。

## 仓库结构

Python 文件按**依赖顺序**编号。窗口程序为 `05`。

| 路径 | 作用 |
|------|------|
| `00_work_paths.py` | 课文件夹命名、读写 `config.json`、TTS 请求头、FFmpeg 路径 |
| `01_auto_map.py` | PPT 文本与 TTS 句子的顺序对齐 |
| `02_library_db.py` | 本地 SQLite 作品库（`assets/studio.db`） |
| `03_cloud.py` | Supabase REST（登录与动态）、本地敏感词/刷屏检查 |
| `04_pipeline.py` | 阶段 `00`–`05` |
| `05_qt_app.py` | 桌面界面 |
| `Iris Studio.exe` | 精简 Windows 启动器（拉起 Python，并非把应用打包进 exe） |
| `start.bat` | 控制台启动 |
| `assets/` | 图标、`config.template.json`、`launch.cs`、**需自行放入的 `ffmpeg.exe`** |
| `supabase/schema.sql` | 社区表、索引与行级安全策略 |
| `outputs/` | 各课工作副本（Git 忽略） |
| `config.json` | 本地密钥与路径（Git 忽略） |

若根目录仍留有旧的 `ffmpeg.exe`，首次使用时会尽量自动移入 `assets/`。

## 配置说明

`assets/config.template.json` 给出字段结构。主要键：

| 键 | 用途 |
|----|------|
| `app.apiKey` | 字节跳动 OpenSpeech API Key（优先） |
| `app.appID` / `app.accessKey` | 旧控制台凭证 |
| `app.resourceID` | TTS 资源，默认 `seed-tts-2.0` |
| `app.uiLang` | `zh` 或 `en` |
| `files.*` | 讲稿、课件、音频、视频、图片目录（通常在 `outputs/` 下） |
| `audio.speaker` | 音色编号（界面显示为天王星 / 清新 / 醇厚 / 爽快） |
| `video_params` | 分辨率、帧率、预设、CRF、音频码率 |
| `slide_mapping` | 每页对应的句子起止下标 |
| `supabase.url` | `https://<项目编号>.supabase.co`，**不要**填 dashboard 网页地址 |
| `supabase.anonKey` | 可公开的 anon key |

填好的 `config.json` 请勿提交到 Git。

## 社区（可选）

1. 新建 Supabase 项目。
2. 在 SQL 编辑器执行 `supabase/schema.sql`（创建 `community_posts` 与 RLS；不会清空已有帖子）。
3. 在设置中填写 API 网址与 anon key。
4. 若使用邮箱确认，Auth 的 Site URL 应设为项目主机（`.supabase.co`），而不是无关的 localhost 应用。

策略要点：

- 动态**可读**对所有人开放。
- 已登录用户可发**实名**帖（`user_id = auth.uid()`）。
- anon 角色可发**匿名**帖（`user_id` 为空）。
- 作者可删除自己的实名帖。

社区页对动态做内存缓存（约 3 分钟），并在后台线程拉取，避免每次进入页面卡住界面。

## 安全与隐私

- TTS 与 Supabase 密钥仅保存在本机 `config.json`，不进入 Git。
- 登录会话位于 `assets/.iris_session.json`（已忽略）。
- 课媒体（`*.mp3`、`*.mp4`、`*.pptx`）与 `outputs/` 已忽略。
- 发帖前会做长度检查，并用本地敏感词/刷屏规则过滤。
- 除你自行配置的接口外，本仓库不包含额外遥测。

## 故障排除

| 现象 | 常见原因 |
|------|----------|
| 导出幻灯片失败 / COM `0x80080005` | 关闭所有 PowerPoint 窗口后重试；流水线通过 `DispatchEx` 启动独立实例。 |
| TTS 连接重置（WinError 10054） | 网络波动，重新点「合成音频」。 |
| 找不到课件 / 写到错误课文件夹 | 路径以 `outputs/` 下 PPT/讲稿所在目录为准；请在设置或准备页保存路径。 |
| 注册社区 404 或返回 HTML | `supabase.url` 填成了控制台网页，应使用 `https://xxxx.supabase.co`。 |
| 进入社区曾经长时间无响应 | 已改为后台拉取并缓存。 |
| 缺少 `ffmpeg.exe` | 放到 `assets/`。 |
| `Iris Studio.exe` 与快捷方式 | 请使用 **exe**。`.lnk` 只是指针，不是程序本身。 |

## 许可

本仓库尚未附带许可证文件。在另行声明之前，权利归作者所有，请勿默认可用于商业再分发。

## 致谢

口播使用字节跳动 OpenSpeech TTS。幻灯片导出依赖 Microsoft PowerPoint。视频混流使用 FFmpeg。可选社区存储使用 Supabase。
