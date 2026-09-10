# -*- coding: utf-8 -*-
"""Supabase REST helper for the community feed. No login needed to read."""
from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
SESSION_PATH = ASSETS / ".iris_session.json"
_POST_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_POST_TTL = 180.0


def invalidate_posts_cache(field: str | None = None) -> None:
    if field is None:
        _POST_CACHE.clear()
    else:
        _POST_CACHE.pop(field, None)

# Keep this list small and product-focused: abuse, porn spam, scams.
_WORDS = (
    "迷奸",
    "强奸",
    "嫖娼",
    "冰毒",
    "海洛因",
    "摇头丸",
    "裸体",
    "色情",
    "约炮",
    "加微信领",
    "代开发票",
    "刷单",
    "赌球",
    "博彩",
    "fuck",
    "shit",
    "bitch",
    "nigger",
    "porn",
    "xxx.com",
    "kill yourself",
)
_COMPILED = [re.compile(re.escape(w), re.IGNORECASE) for w in _WORDS]


def find_banned(text: str) -> str | None:
    raw = (text or "").strip()
    if not raw:
        return None
    compact = re.sub(r"\s+", "", raw)
    for pat, word in zip(_COMPILED, _WORDS):
        if pat.search(raw) or pat.search(compact):
            return word
    if re.search(r"(.)\1{8,}", compact):
        return "spam"
    if len(re.findall(r"https?://", raw, flags=re.I)) >= 4:
        return "spam"
    return None


def too_short(text: str, min_chars: int = 8) -> bool:
    return len(re.sub(r"\s+", "", text or "")) < min_chars


def normalize_supabase_url(url: str) -> str:
    raw = (url or "").strip().rstrip("/")
    dash = re.search(r"supabase\.com/dashboard/project/([a-z0-9]+)", raw, re.I)
    if dash:
        return f"https://{dash.group(1)}.supabase.co"
    api = re.search(r"https://([a-z0-9]+)\.supabase\.co", raw, re.I)
    if api:
        return f"https://{api.group(1)}.supabase.co"
    return raw


def supabase_cfg(config: dict) -> tuple[str, str]:
    block = config.get("supabase") or {}
    url = normalize_supabase_url(str(block.get("url") or ""))
    key = str(block.get("anonKey") or "").strip()
    return url, key


def is_configured(config: dict) -> bool:
    url, key = supabase_cfg(config)
    return bool(re.match(r"https://[a-z0-9]+\.supabase\.co$", url, re.I) and key)


def load_session() -> dict:
    old = ROOT / ".iris_session.json"
    if not SESSION_PATH.is_file() and old.is_file():
        SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(old), str(SESSION_PATH))
        except OSError:
            pass
    if not SESSION_PATH.is_file():
        return {}
    try:
        data = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_session(data: dict) -> None:
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    SESSION_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_session() -> None:
    if SESSION_PATH.exists():
        SESSION_PATH.unlink()


def current_user() -> dict | None:
    user = load_session().get("user")
    return user if isinstance(user, dict) and user.get("id") else None


def access_token() -> str:
    return str(load_session().get("access_token") or "")


def _headers(config: dict, *, as_user: bool = False) -> dict[str, str]:
    _url, key = supabase_cfg(config)
    token = access_token() if as_user else ""
    bearer = token or key
    return {
        "apikey": key,
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _raise_for_api(resp: requests.Response) -> None:
    if resp.status_code < 400:
        return
    text = (resp.text or "").strip()
    if "<html" in text.lower() or text.startswith("<!DOCTYPE"):
        raise RuntimeError(
            "Supabase 网址不对。请填 https://你的项目编号.supabase.co ，不要填 dashboard 网页链接。"
        )
    try:
        payload = resp.json()
        msg = payload.get("msg") or payload.get("message") or payload.get("error_description") or str(payload)
    except Exception:
        msg = text[:240] or f"HTTP {resp.status_code}"
    raise RuntimeError(msg)


def sign_up(config: dict, email: str, password: str) -> dict:
    url, _key = supabase_cfg(config)
    resp = requests.post(
        f"{url}/auth/v1/signup",
        headers=_headers(config),
        params={"redirect_to": url},
        json={"email": email, "password": password},
        timeout=30,
    )
    _raise_for_api(resp)
    data = resp.json()
    if data.get("access_token"):
        save_session(
            {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "user": data.get("user") or {},
            }
        )
    return data


def sign_in(config: dict, email: str, password: str) -> dict:
    url, _key = supabase_cfg(config)
    resp = requests.post(
        f"{url}/auth/v1/token?grant_type=password",
        headers=_headers(config),
        json={"email": email, "password": password},
        timeout=30,
    )
    _raise_for_api(resp)
    data = resp.json()
    save_session(
        {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "user": data.get("user") or {},
        }
    )
    return data


def sign_out() -> None:
    clear_session()


def list_cloud_posts(config: dict, field: str, *, force: bool = False) -> list[dict[str, Any]]:
    now = time.time()
    if not force:
        hit = _POST_CACHE.get(field)
        if hit and now - hit[0] < _POST_TTL:
            return hit[1]
    url, _key = supabase_cfg(config)
    resp = requests.get(
        f"{url}/rest/v1/community_posts",
        headers=_headers(config),
        params={
            "select": "*",
            "field": f"eq.{field}",
            "order": "created_at.desc",
            "limit": "80",
        },
        timeout=8,
    )
    _raise_for_api(resp)
    rows = resp.json()
    data = rows if isinstance(rows, list) else []
    _POST_CACHE[field] = (now, data)
    return data


def insert_cloud_post(config: dict, payload: dict[str, Any], *, as_user: bool) -> dict:
    url, _key = supabase_cfg(config)
    resp = requests.post(
        f"{url}/rest/v1/community_posts",
        headers=_headers(config, as_user=as_user),
        json=payload,
        timeout=30,
    )
    _raise_for_api(resp)
    invalidate_posts_cache(str(payload.get("field") or ""))
    data = resp.json()
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    return {}


def delete_cloud_post(config: dict, post_id: str) -> None:
    url, _key = supabase_cfg(config)
    resp = requests.delete(
        f"{url}/rest/v1/community_posts",
        headers=_headers(config, as_user=True),
        params={"id": f"eq.{post_id}"},
        timeout=30,
    )
    _raise_for_api(resp)
    invalidate_posts_cache()
