import json
import os


def get_config_path():
    """优先 VIDEO_TOOL_CONFIG，其次当前工作目录，最后脚本同目录。"""
    env = os.environ.get("VIDEO_TOOL_CONFIG")
    if env and os.path.isfile(env):
        return env
    cwd_path = os.path.join(os.getcwd(), "config.json")
    if os.path.isfile(cwd_path):
        return cwd_path
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config():
    config_path = get_config_path()
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config, path=None):
    path = path or get_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return path
