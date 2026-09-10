[English](README.md) | [简体中文](README_zh.md)

# Iris Studio

> A Windows desktop pipeline that turns a teaching script and PowerPoint deck into a narrated slide video—without camera recording or a quiet room.

![Iris Studio demo](assets/demo.gif)

## Project Overview

Iris Studio is a PyQt6 application for instructors, corporate trainers, and anyone who needs to convert existing course materials into a watchable film. The system does **not** capture webcam or microphone audio. It synthesizes narration with a cloud text-to-speech (TTS) API, exports each slide as an image through Microsoft PowerPoint, aligns spoken sentences to pages, and concatenates the result with FFmpeg.

Typical inputs are a `.pptx` file and a plain-text script. If those files do not exist yet, the Prepare page can draft both from a topic and an audience (school, workplace, or personal learning). Finished lessons are stored as ordinary folders under `outputs/`. An optional Supabase-backed community feed lets practitioners share teaching notes by field; **login is not required to generate video**.

The design goals are:

- **Local-first lesson files** — readable names (script, slides, video) plus a working-files subfolder the user can ignore.
- **Reproducible steps** — the same six pipeline stages can be run from the UI or from the command line.
- **Secret hygiene** — API keys live in a gitignored `config.json`; the repository ships only an empty template.
- **Optional cloud** — community posting is independent of video production.

## Features

- **Home** — product statement and entry points for “I already have materials” versus “start from a topic”.
- **Prepare** — import an existing script/PPT, or generate a first draft for a chosen audience.
- **Make** — choose a Mandarin voice, synthesize audio, auto-align slides to sentences, then encode video.
- **Films** — local library of finished lessons (SQLite), open the folder, remove an entry.
- **Community** — field-filtered feed (school / workplace / personal). Named posts require sign-in; anonymous posts do not. Login is never required to make a video.
- **Settings** — ByteDance TTS credentials, optional Supabase URL and anon key, current lesson paths.
- **Bilingual UI** — Chinese and English, including lesson folder naming (`课件.pptx` / `Slides.pptx`, and so on).

## Requirements

| Component | Notes |
|-----------|--------|
| OS | **Windows** (PowerPoint COM automation and `pywin32`) |
| Python | 3.10 or newer recommended |
| Microsoft PowerPoint | Required to export slide PNGs |
| FFmpeg | Place `ffmpeg.exe` in `assets/` (not distributed with this repository) |
| Network | Required for TTS submit/query and for the optional community API |

Python packages are listed in `requirements.txt`: `PyQt6`, `requests`, `Pillow`, `python-pptx`, `pywin32`.

## Quick Start

1. Clone the repository and create a virtual environment if you prefer isolation.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy the configuration template to the project root (this file is gitignored once filled in):

```bash
copy assets\config.template.json config.json
```

4. Download a Windows build of [FFmpeg](https://ffmpeg.org/) and copy `ffmpeg.exe` to `assets/ffmpeg.exe`.
5. In **Settings**, paste a ByteDance OpenSpeech TTS API key (`apiKey`), or the older `appID` + `accessKey` pair. Set `resourceID` if your console uses a value other than `seed-tts-2.0`.
6. Launch the application:

   - Double-click **`Iris Studio.exe`** in the repository root (recommended; carries the app icon), or
   - `python 05_qt_app.py`, or
   - `start.bat` (console fallback; `.bat` files cannot carry a custom icon on Windows).

7. Prepare a lesson → Make audio → Align from slides → Make video. Outputs appear under `outputs/<lesson name>/`.

## Recommended Workflow

```
Prepare (import or draft)
    → Make (voice → audio → page timing → video)
        → Films (review locally)
            → Community (optional teaching notes)
```

Video generation does not depend on Supabase or on an account.

## Pipeline Stages

The UI invokes `04_pipeline.py` with a stage id. The same ids can be run in a terminal from the repository root (with `config.json` present and `VIDEO_TOOL_CONFIG` pointing at it if needed).

| Stage | Command | Responsibility |
|-------|---------|----------------|
| `00` | `python 04_pipeline.py 00` | Validate config, script, PPT, FFmpeg, and page mapping |
| `01` | `python 04_pipeline.py 01` | Export each slide to PNG via PowerPoint (`DispatchEx`) |
| `02` | `python 04_pipeline.py 02` | Submit TTS job (retries on transient network errors) |
| `03` | `python 04_pipeline.py 03` | Poll until audio and sentence timestamps are downloaded |
| `04` | `python 04_pipeline.py 04` | Build FFmpeg concat timings from sentence–slide mapping |
| `05` | `python 04_pipeline.py 05` | Encode H.264 + AAC video (`libx264`), muxed with narration |

Make audio runs stages `00`–`03`. Make video runs `04`–`05` and requires a valid mapping.

Default encode parameters (overridable in `config.json` → `video_params`) are `854x480`, 24 fps, `ultrafast` preset, CRF 30, audio `128k`.

## Repository Layout

Python modules are numbered in **dependency order**. The window is module `05`.

| Path | Role |
|------|------|
| `00_work_paths.py` | Lesson folder names, `config.json` load/save, TTS header helper, FFmpeg path |
| `01_auto_map.py` | Sequential alignment of PPT text to TTS sentences |
| `02_library_db.py` | Local SQLite library (`assets/studio.db`) |
| `03_cloud.py` | Supabase REST (auth, feed), local profanity/spam checks |
| `04_pipeline.py` | Stages `00`–`05` |
| `05_qt_app.py` | Desktop UI |
| `Iris Studio.exe` | Thin Windows launcher (starts Python; not a frozen copy of the app) |
| `start.bat` | Console launcher |
| `assets/` | Icons, `config.template.json`, `launch.cs`, **`ffmpeg.exe` (you provide)** |
| `supabase/schema.sql` | Community table, indexes, and row-level security |
| `outputs/` | Per-lesson working copies (gitignored) |
| `config.json` | Local secrets and paths (gitignored) |

A leftover `ffmpeg.exe` in the repository root is moved into `assets/` on first use when possible.

## Configuration

`assets/config.template.json` documents the schema. Important keys:

| Key | Purpose |
|-----|---------|
| `app.apiKey` | ByteDance OpenSpeech API key (preferred) |
| `app.appID` / `app.accessKey` | Legacy console credentials |
| `app.resourceID` | TTS resource, default `seed-tts-2.0` |
| `app.uiLang` | `zh` or `en` |
| `files.*` | Script, PPT, audio, video, and image directory (usually under `outputs/`) |
| `audio.speaker` | Voice id (Uranus / Fresh / Mellow / Crisp in the UI) |
| `video_params` | Resolution, fps, preset, CRF, audio bitrate |
| `slide_mapping` | Sentence index ranges per page |
| `supabase.url` | `https://<project-ref>.supabase.co` — **not** the dashboard HTML URL |
| `supabase.anonKey` | Publishable anon key |

Never commit a filled `config.json`.

## Community (optional)

1. Create a Supabase project.
2. Run `supabase/schema.sql` in the SQL editor (creates `community_posts` and RLS policies; it does not wipe existing rows).
3. Paste the API URL and anon key in Settings.
4. Site URL in Supabase Auth should be the project host (`.supabase.co`), not an unrelated localhost app, if email confirmation is used.

Policies in the schema:

- Anyone may **read** posts.
- Authenticated users may insert **named** posts (`user_id = auth.uid()`).
- The anon role may insert **anonymous** posts (`user_id` null).
- Authors may delete their own named posts.

The community page caches the feed in memory (~3 minutes) and loads it off the UI thread so switching tabs does not block on the network.

## Security and Privacy

- TTS keys and Supabase keys stay on the machine in `config.json` and are excluded from Git.
- Session tokens are stored under `assets/.iris_session.json` (gitignored).
- Lesson media (`*.mp3`, `*.mp4`, `*.pptx`) and `outputs/` are gitignored.
- Posts are length-checked and scanned against a small local banned-word / spam heuristic before upload.
- This repository does not include telemetry beyond the APIs you configure.

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| Slide export fails / COM `0x80080005` | Close every PowerPoint window and retry; the pipeline starts a private instance via `DispatchEx`. |
| TTS connection reset (WinError 10054) | Transient network; retry Make audio. |
| “Slides not found” / wrong lesson folder | Paths are taken from the PPT/script location under `outputs/`; save paths on Settings or Prepare. |
| Community sign-up 404 or HTML error | `supabase.url` is a dashboard page; use `https://xxxx.supabase.co`. |
| Community tab used to freeze | Fixed: feed is fetched in the background and cached. |
| Missing `ffmpeg.exe` | Place it in `assets/`. |
| `Iris Studio.exe` vs shortcut | Use the **.exe**. A `.lnk` is only a pointer and is not required. |

## License

No license file is included in this repository. All rights remain with the author unless a license is added later. Do not treat the source as open for commercial reuse until that is stated explicitly.

## Acknowledgements

Narration uses ByteDance OpenSpeech TTS. Slide export requires Microsoft PowerPoint. Video muxing uses FFmpeg. Optional community storage uses Supabase.
