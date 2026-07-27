# -*- coding: utf-8 -*-
import time
import uuid
import requests
import json
from config_loader import load_config   # 统一加载配置

# 加载配置
config = load_config()
app = config["app"]
files = config["files"]
audio = config.get("audio", {})

appID = app["appID"]
accessKey = app["accessKey"]
resourceID = app["resourceID"]
input_file = files["input_text"]
speaker = audio.get("speaker", "zh_female_vv_uranus_bigtts")
audio_format = audio.get("format", "mp3")
sample_rate = int(audio.get("sample_rate", 24000))
uid = app.get("uid", "123123")

# 读取文本
try:
    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read()
    print(f"✅ 已读取文本，共 {len(text)} 个字符")
except FileNotFoundError:
    print(f"❌ 文件 {input_file} 不存在，请检查路径。")
    exit(1)

# 请求地址（固定不变）
url = "https://openspeech.bytedance.com/api/v3/tts/submit"

def submit(url, headers, params):
    session = requests.Session()
    try:
        resp = requests.post(url, json.dumps(params), headers=headers)
        logid = resp.headers.get('X-Tt-Logid')
        print(f"X-Tt-Logid: {logid}")

        if resp.status_code != 200:
            print(resp.json())
            print("resp text: ", resp.text)
        else:
            resp_json = resp.json()
            resp_data = resp_json.get("data")
            print("data: ", resp_data)
            # 保存 task_id 到文件，供 query.py 自动读取
            if resp_data and resp_data.get("task_id"):
                task_id = resp_data["task_id"]
                with open("task_id.txt", "w", encoding="utf-8") as f:
                    f.write(task_id)
                print(f"✅ task_id 已保存到 task_id.txt")
            return resp_data
    except Exception as e:
        print(f"请求失败: {e}")
    finally:
        resp.close()
        session.close()

if __name__ == "__main__":
    headers = {
        "X-Api-App-Id": appID,
        "X-Api-Access-Key": accessKey,
        "X-Api-Resource-Id": resourceID,
        "X-Api-Request-Id": str(uuid.uuid1()),
        "Content-Type": "application/json",
        "Connection": "keep-alive",
    }

    task_uuid = str(uuid.uuid4())

    body = {
        "user": {
            "uid": uid,
        },
        "unique_id": task_uuid,
        "req_params": {
            "text": text,
            "speaker": speaker,
            "audio_params": {
                "format": audio_format,
                "sample_rate": sample_rate,
                "enable_timestamp": True,
            },
            "additions": json.dumps({}),
        }
    }
    submit(url, headers, body)