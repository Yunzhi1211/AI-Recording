# -*- coding: utf-8 -*-
"""
轮询 TTS 任务状态并下载音频 / 句子时间戳。

task_status:
  1 = 合成中（继续等待）
  2 = 成功（下载）
  3 = 失败
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid

import requests
from config_loader import load_config

STOP_FLAG = "stop_query.flag"
POLL_INTERVAL = 10  # 秒


def log(msg: str) -> None:
    print(msg, flush=True)


def should_stop() -> bool:
    return os.path.isfile(STOP_FLAG)


def sleep_interruptible(seconds: int) -> bool:
    """分段休眠；若出现停止标记则返回 True（表示应退出）。"""
    for left in range(seconds, 0, -1):
        if should_stop():
            return True
        if left == seconds or left % 5 == 0 or left <= 3:
            log(f"   …还需约 {left} 秒后再次查询（可点界面「停止等待」取消）")
        time.sleep(1)
    return should_stop()


def save_sentences(sentences, audio_output: str) -> None:
    sentences_simple = []
    for s in sentences:
        sentences_simple.append(
            {
                "text": s["text"],
                "startTime": s["startTime"],
                "endTime": s["endTime"],
            }
        )
    with open("timestamps.json", "w", encoding="utf-8") as f:
        json.dump(sentences_simple, f, ensure_ascii=False, indent=2)
    log("📝 句子级时间戳已保存为 timestamps.json")

    log("\n📋 句子列表（编号从0开始，可用于映射）：")
    lines = ["句子列表（编号从0开始，可用于映射）：\n"]
    for idx, s in enumerate(sentences_simple):
        preview = s["text"][:60].replace("\n", " ").strip()
        if len(s["text"]) > 60:
            preview += "..."
        line = f"  {idx}: {preview} ({s['startTime']:.2f}s - {s['endTime']:.2f}s)\n"
        lines.append(line)
        log(line.rstrip())
    with open("sentence_list.txt", "w", encoding="utf-8") as f:
        f.writelines(lines)
    log("📄 句子编号列表已保存为 sentence_list.txt")
    log(f"📌 共 {len(sentences_simple)} 句，可到「映射编辑」页对照 PPT")


def query(uri: str, headers: dict, params: dict, audio_output: str) -> int:
    """返回进程退出码：0 成功，1 失败，130 用户取消。"""
    attempt = 0
    started = time.time()
    status_text = {1: "合成中(未完成)", 2: "已完成", 3: "失败"}

    log("⏳ 开始轮询：状态 1=合成中，2=完成，3=失败。长文稿可能需要数分钟。")
    log("💡 若要改文稿重提，请点界面「停止等待」，再重新「2. 提交 TTS」。")

    while True:
        if should_stop():
            log("⏹ 已停止等待（用户取消）")
            return 130

        attempt += 1
        elapsed = int(time.time() - started)
        log(f"\n—— 第 {attempt} 次查询（已等待 {elapsed // 60}分{elapsed % 60}秒）——")

        try:
            resp = requests.post(uri, data=json.dumps(params), headers=headers, timeout=60)
        except requests.RequestException as e:
            log(f"❌ 请求失败: {e}")
            if sleep_interruptible(POLL_INTERVAL):
                log("⏹ 已停止等待（用户取消）")
                return 130
            continue

        try:
            logid = resp.headers.get("X-Tt-Logid")
            log(f"X-Tt-Logid: {logid}")

            if resp.status_code != 200:
                log(f"❌ HTTP {resp.status_code}")
                try:
                    log(str(resp.json()))
                except Exception:
                    log(resp.text)
                return 1

            resp_json = resp.json()
            resp_data = resp_json.get("data") or {}
            status = resp_data.get("task_status")
            label = status_text.get(status, f"未知({status})")
            log(f"📊 task_status = {status} → {label}")

            if status == 1:
                log("⏳ 音频尚未生成完成，继续等待…")
                if sleep_interruptible(POLL_INTERVAL):
                    log("⏹ 已停止等待（用户取消）")
                    return 130
                continue

            if status == 2:
                log("✅ 合成成功，开始下载…")
                audio_url = resp_data.get("audio_url")
                if not audio_url:
                    log("❌ 响应中无 audio_url")
                    return 1

                log("📥 正在下载音频…")
                audio_resp = requests.get(audio_url, timeout=300)
                audio_resp.raise_for_status()
                with open(audio_output, "wb") as f:
                    f.write(audio_resp.content)
                log(f"🎉 音频已保存为 {audio_output}（{len(audio_resp.content)} 字节）")

                sentences = resp_data.get("sentences")
                if sentences:
                    save_sentences(sentences, audio_output)
                else:
                    log("⚠️ 未找到时间戳，请确认 submit 时 enable_timestamp=True")
                return 0

            if status == 3:
                log("❌ 合成失败（task_status=3）")
                log(str(resp_data))
                return 1

            log(f"⚠️ 未知状态: {status}，停止轮询")
            return 1
        finally:
            resp.close()


def main() -> None:
    # 清理上次残留的停止标记
    if os.path.isfile(STOP_FLAG):
        try:
            os.remove(STOP_FLAG)
        except OSError:
            pass

    config = load_config()
    app = config["app"]
    files = config["files"]
    appID = app["appID"]
    accessKey = app["accessKey"]
    resourceID = app["resourceID"]
    audio_output = files.get("audio_output", "output.mp3")
    url = "https://openspeech.bytedance.com/api/v3/tts/query"

    try:
        with open("task_id.txt", "r", encoding="utf-8") as f:
            task_id = f.read().strip()
        log(f"📌 读取到 task_id: {task_id}")
    except FileNotFoundError:
        log("❌ 未找到 task_id.txt，请先运行「2. 提交 TTS」。")
        sys.exit(1)

    if not task_id:
        log("❌ task_id 为空，请重新提交 TTS。")
        sys.exit(1)

    headers = {
        "X-Api-App-Id": appID,
        "X-Api-Access-Key": accessKey,
        "X-Api-Resource-Id": resourceID,
        "X-Api-Request-Id": str(uuid.uuid1()),
        "Content-Type": "application/json",
        "Connection": "keep-alive",
    }
    payload = {"task_id": task_id}
    log(f"payload: {json.dumps(payload, ensure_ascii=False)}")

    code = query(uri=url, headers=headers, params=payload, audio_output=audio_output)
    sys.exit(code)


if __name__ == "__main__":
    main()
