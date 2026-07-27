# -*- coding: utf-8 -*-
"""
根据 PPT 每页文字与 TTS 句子做顺序自动映射。
适用于「口播基本照着 PPT 念」的场景。
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any


def normalize_text(text: str) -> str:
    """去掉空白与常见标点，便于比对。"""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(
        r"[，。！？、；：,.!?;:\"'“”‘’（）()【】\[\]《》<>…—\-_/\\|=+*~`@#$%^&]",
        "",
        text,
    )
    return text


def extract_slide_texts(pptx_path: str) -> list[str]:
    """从 pptx 按页提取可见文字。"""
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    def shape_text(shape) -> str:
        parts: list[str] = []
        try:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    t = "".join(run.text for run in para.runs) or para.text
                    if t and t.strip():
                        parts.append(t.strip())
        except Exception:
            pass
        try:
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        t = (cell.text or "").strip()
                        if t:
                            parts.append(t)
        except Exception:
            pass
        try:
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                for child in shape.shapes:
                    parts.append(shape_text(child))
        except Exception:
            pass
        return "\n".join(p for p in parts if p)

    prs = Presentation(pptx_path)
    slides: list[str] = []
    for slide in prs.slides:
        chunks: list[str] = []
        for shape in slide.shapes:
            t = shape_text(shape)
            if t:
                chunks.append(t)
        # notes 一般不参与口播对齐，这里不用
        slides.append("\n".join(chunks))
    return slides


def _similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _coverage(needle: str, haystack: str) -> float:
    """needle 有多少比例能被 haystack 覆盖（按最长公共子序列近似）。"""
    if not needle:
        return 1.0
    if not haystack:
        return 0.0
    # 快速路径：子串
    if needle in haystack or haystack in needle:
        return min(len(needle), len(haystack)) / max(len(needle), 1)
    return SequenceMatcher(None, needle, haystack).ratio()


def auto_map_sentences(
    slide_texts: list[str],
    sentences: list[dict[str, Any]] | list[str],
    *,
    min_score: float = 0.45,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    顺序贪婪匹配：每页从当前句子游标向后吞句子，直到覆盖该页文字。

    返回:
      mapping: [{start, end, slide, score, slide_preview}, ...]
      warnings: 提示信息
    """
    sent_texts: list[str] = []
    for s in sentences:
        if isinstance(s, dict):
            sent_texts.append(str(s.get("text", "")))
        else:
            sent_texts.append(str(s))

    n = len(sent_texts)
    n_slides = len(slide_texts)
    warnings: list[str] = []
    if n == 0:
        return [], ["没有句子数据（timestamps.json 为空）。"]
    if n_slides == 0:
        return [], ["PPT 没有页面。"]

    norm_sents = [normalize_text(t) for t in sent_texts]
    cursor = 0
    mapping: list[dict[str, Any]] = []

    for si, raw in enumerate(slide_texts):
        slide_name = f"slide_{si + 1}.png"
        target = normalize_text(raw)
        preview = re.sub(r"\s+", " ", raw).strip()[:40]

        if cursor >= n:
            warnings.append(f"第 {si + 1} 页及之后：句子已用完，无法分配。")
            break

        # 几乎无文字的页：先占 1 句，后续可手改
        if len(target) < 4:
            mapping.append(
                {
                    "start": cursor,
                    "end": cursor,
                    "slide": slide_name,
                    "score": 0.0,
                    "slide_preview": preview or "(几乎无文字)",
                    "weak": True,
                }
            )
            warnings.append(f"第 {si + 1} 页文字很少，暂各分 1 句，请手调。")
            cursor += 1
            continue

        best_end = cursor
        best_score = -1.0
        acc = ""
        # 后面还要留给剩余页，至少各留 0 句；宽松上限
        remaining_slides = max(0, n_slides - si - 1)
        max_end = n - 1 - remaining_slides
        if max_end < cursor:
            max_end = cursor

        for j in range(cursor, max_end + 1):
            acc += norm_sents[j]
            score = _coverage(target, acc)
            # 略微惩罚「句子明显长于幻灯片」
            length_pen = 1.0
            if len(acc) > len(target) * 1.35:
                length_pen = len(target) / max(len(acc), 1)
            adj = score * (0.7 + 0.3 * length_pen)
            if adj >= best_score:
                best_score = adj
                best_end = j
            # 已经很像了，且长度够了就停
            if score >= 0.88 and len(acc) >= len(target) * 0.85:
                break
            if len(acc) > len(target) * 1.8 and best_score >= min_score:
                break

        # 若匹配很差，至少吃 1 句，避免卡死
        if best_score < min_score:
            best_end = cursor
            warnings.append(
                f"第 {si + 1} 页自动匹配较弱（score={best_score:.2f}），请重点检查。"
            )

        mapping.append(
            {
                "start": cursor,
                "end": best_end,
                "slide": slide_name,
                "score": round(float(best_score), 3),
                "slide_preview": preview,
                "weak": best_score < min_score,
            }
        )
        cursor = best_end + 1

    # 剩余句子并入最后一页
    if mapping and cursor < n:
        mapping[-1]["end"] = n - 1
        warnings.append(
            f"剩余句子 {cursor}–{n - 1} 已并入最后一页 {mapping[-1]['slide']}，请检查。"
        )
        # 重算最后一页分数（示意）
        last = mapping[-1]
        acc = "".join(norm_sents[last["start"] : last["end"] + 1])
        tgt = normalize_text(slide_texts[len(mapping) - 1]) if slide_texts else ""
        last["score"] = round(_coverage(tgt, acc), 3)

    if not mapping:
        warnings.append("未能生成任何映射。")

    return mapping, warnings


def auto_map_from_files(
    pptx_path: str,
    sentences: list[dict[str, Any]] | list[str],
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """
    返回 (mapping, warnings, slide_texts)。
    mapping 项含 start/end/slide，可直接写入 config。
    """
    slide_texts = extract_slide_texts(pptx_path)
    mapping, warnings = auto_map_sentences(slide_texts, sentences)
    # 精简为 config 需要的字段
    clean = [
        {"start": int(m["start"]), "end": int(m["end"]), "slide": m["slide"]}
        for m in mapping
    ]
    return clean, warnings, slide_texts
