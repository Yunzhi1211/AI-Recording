# 培训视频生成工具

把 PPT + 口播文稿，经火山引擎 TTS 合成音频，再按句子时间戳对齐翻页并导出视频。

## 功能

- GUI 分步运行（检查 → 转图 → 提交 TTS → 下载 → 映射 → 合成）
- 映射编辑：句子列表 / slide_mapping / PPT 预览
- 按 PPT 文字与口播句子自动映射（可再微调）

## 准备

1. Python 3.10+（建议）
2. 安装依赖：`pip install -r requirements.txt`
3. 将 `ffmpeg.exe` 放到项目目录（自行下载，不随仓库分发）
4. 复制配置模板并填写密钥：

```bash
copy config.template.json config.json
```

编辑 `config.json` 中的 `appID` / `accessKey`（**不要把填好的 config.json 提交到 Git**）。

5. 放入自己的 `input.txt` 与 `.pptx`，在 GUI「设置」里选好路径。

## 运行

```bash
python gui_app.py
```

或双击 `start_gui.bat`。

## 建议流程

设置保存 → 一键跑到下载(0→3) → 映射编辑（可点「按PPT文字自动映射」）→ 从时间表跑完(4→5)

## 安全说明

- 仓库只包含 `config.template.json`（空密钥）
- 本地 `config.json`、音频、视频、PPT、文稿均已在 `.gitignore` 中忽略
