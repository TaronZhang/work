"""TechToExcel 技能集成 — 从招标文件中提取技术章节，生成点对点技术偏离表 Excel.

整合了 techtoexcel 技能的完整管线：
1. 从原始 docx 文件提取指定章节的段落和表格
2. LLM 按规则智能拆条
3. C 列措辞清洗（投标人→我司, 去除★等）
4. 专业格式 Excel 输出
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from app.services.techtoexcel_utils import (
    clean_resp,
    ensure_docx,
    extract_paragraphs,
    extract_tables,
    verify,
    write_excel,
)

# ── Entry splitting prompt (from techtoexcel's prompt.tpl) ──

ENTRY_SPLIT_PROMPT = """你是一个招标文件技术偏离表生成专家。请根据以下规则，将提供的技术章节内容拆分为逐条偏离表条目。

## 输入
- 技术章节的段落列表和表格内容

## 条目结构
每条包含三个字段：
- bid: 招标文件技术条款（B列）— 完全复制原文，一字不改，不得截断或省略
- resp: 投标文件技术条款（C列）— 应答：完全满足且无偏离。+ 完整原文（措辞自动清理）
- deviation: 偏离说明（D列）— 固定为"无偏离"

## 条目划分规则
1. **表格**：每行一个条目，格式为"字段名：内容；字段名：内容"，表头行跳过
2. **标题下多段落**：一标题一段落为一条
3. **"以下"合并**：文本出现"以下"→后续连续子内容合并为一条，子项保留 a) b) c) 标签
4. **"内容包括但不限于以下范围"** → 合并为一条
5. **"涵盖以下功能"** → 合并为一条
6. **备注/说明**：跳过
7. **纯标题行**：跳过（无实质内容的标题不单独成条）
8. **长段落**：完整保留，不得截断

## 输出格式 (JSON)
{
  "entries": [
    {
      "bid": "原文技术条款内容（一字不改）",
      "resp": "应答：完全满足且无偏离。+ [build_resp 逻辑由代码处理]",
      "deviation": "无偏离"
    }
  ],
  "total": 条目总数
}

## 重要
- B列必须完整复制原文，不得截断、省略或改写
- 每条 bid 长度不限，长段落必须完整包含
- 表格内容按行生成条目
- 不要自行添加或删减内容"""


@dataclass
class TechToExcelResult:
    """Result of the techtoexcel pipeline."""

    filepath: str = ""
    filename: str = ""
    entry_count: int = 0
    issues: list[str] = field(default_factory=list)
    success: bool = False
    error: str = ""


async def run_techtoexcel_pipeline(
    source_docx_path: str,
    chapter_name: str,
    output_dir: str,
    project_name: str,
    base_url: str = "",
    api_key: str = "",
    model: str = "",
) -> TechToExcelResult:
    """Execute the full techtoexcel pipeline.

    Args:
        source_docx_path: Path to the original bid .docx file
        chapter_name: Target chapter name (e.g. "第三章 采购需求")
        output_dir: Output directory for the Excel file
        project_name: Project name for filename
        base_url: LLM base URL (for entry splitting)
        api_key: LLM API key
        model: LLM model name

    Returns:
        TechToExcelResult with filepath and entry count
    """
    # 1. Ensure .docx format
    try:
        actual_path = ensure_docx(source_docx_path)
    except Exception as e:
        return TechToExcelResult(success=False, error=f"格式转换失败: {e}")

    # 2. Extract paragraphs and tables
    try:
        paragraphs = extract_paragraphs(actual_path)
        tables = extract_tables(actual_path)
    except Exception as e:
        return TechToExcelResult(success=False, error=f"文档读取失败: {e}")

    if not paragraphs:
        return TechToExcelResult(success=False, error="文档无内容")

    # 3. Locate chapter
    ch_start, ch_end = _locate_chapter(paragraphs, chapter_name)

    if ch_start is None:
        return TechToExcelResult(
            success=False,
            error=f"未找到章节: {chapter_name}",
        )

    chapter_paragraphs = paragraphs[ch_start:ch_end]

    # 4. Find chapter-associated tables
    chapter_tables = _find_chapter_tables(tables, chapter_paragraphs)

    # 5. Build chapter context text for LLM entry splitting
    chapter_context = _build_chapter_context(chapter_name, chapter_paragraphs, chapter_tables)

    # 6. LLM-based entry splitting (or fallback)
    entries = []
    if api_key and base_url:
        entries = await _llm_split_entries(chapter_context, base_url, api_key, model)

    if not entries:
        # Fallback: rule-based splitting
        entries = _rule_based_split(chapter_paragraphs, chapter_tables)

    if not entries:
        return TechToExcelResult(success=False, error="未能生成任何条目，请确认章节内容")

    # 7. Clean C-column text
    for entry in entries:
        raw_bid = entry.get("bid", "")
        cleaned = clean_resp(raw_bid)
        entry["resp"] = f"应答：完全满足且无偏离。{cleaned}"
        entry["deviation"] = "无偏离"

    # 8. Verify
    issues = verify(entries)

    # 9. Write Excel
    from app.services.file_service import sanitize_filename

    name_safe = sanitize_filename(project_name) if project_name else "项目"
    filename = f"{name_safe}_技术偏离表.xlsx"
    filepath = os.path.join(output_dir, filename)
    os.makedirs(output_dir, exist_ok=True)

    count = write_excel(entries, filepath)

    return TechToExcelResult(
        filepath=filepath,
        filename=filename,
        entry_count=count,
        issues=issues,
        success=True,
    )


# ── Chapter location ──────────────────────────────────────


def _locate_chapter(
    paragraphs: list[tuple[int, str, str]],
    chapter_name: str,
) -> tuple[int | None, int | None]:
    """Find start and end indices of a chapter in paragraphs.

    Args:
        paragraphs: List of (index, style_name, text) tuples
        chapter_name: Target chapter name

    Returns:
        (start_index, end_index) — end_index is exclusive
    """
    ch_start = None
    ch_end = None

    # Chinese chapter number patterns
    all_chapters = [
        "第一章", "第二章", "第三章", "第四章", "第五章",
        "第六章", "第七章", "第八章", "第九章", "第十章",
        "一、", "二、", "三、", "四、", "五、",
        "六、", "七、", "八、", "九、", "十、",
    ]

    for i, (idx, style, text) in enumerate(paragraphs):
        if chapter_name in text and ch_start is None:
            ch_start = i
            continue

        if ch_start is not None and ch_end is None:
            # Check if this paragraph starts a new chapter
            for ch in all_chapters:
                if ch != chapter_name and ch in text and ("第" in text or "、" in text[:3]):
                    ch_end = i
                    break

        if ch_end is not None:
            break

    if ch_end is None:
        ch_end = len(paragraphs)

    return ch_start, ch_end


def _find_chapter_tables(
    tables: list[list[list[str]]],
    chapter_paragraphs: list[tuple[int, str, str]],
) -> list[list[list[str]]]:
    """Find tables that belong to the chapter (heuristic: return all for now).

    In a full implementation, we'd match table positions to paragraph indices.
    For simplicity, return all tables — the LLM will determine which belong.
    """
    return tables


def _build_chapter_context(
    chapter_name: str,
    paragraphs: list[tuple[int, str, str]],
    tables: list[list[list[str]]],
) -> str:
    """Build a text representation of chapter content for LLM processing."""
    lines = [f"=== 章节: {chapter_name} ===\n"]

    lines.append("## 段落内容:\n")
    for idx, style, text in paragraphs:
        prefix = f"[{style}]" if style and "Heading" in style else ""
        lines.append(f"{prefix}{text}")

    if tables:
        lines.append("\n## 表格内容:\n")
        for ti, table in enumerate(tables):
            lines.append(f"\n表格 {ti + 1}:")
            for ri, row in enumerate(table):
                row_text = " | ".join(str(c) for c in row)
                lines.append(f"  行{ri + 1}: {row_text}")

    return "\n".join(lines)


# ── LLM-based entry splitting ────────────────────────────


async def _llm_split_entries(
    chapter_context: str,
    base_url: str,
    api_key: str,
    model: str,
) -> list[dict]:
    """Use LLM to intelligently split chapter content into deviation table entries."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    # Truncate if too long
    context = chapter_context if len(chapter_context) < 100000 else chapter_context[:100000]

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": ENTRY_SPLIT_PROMPT},
                {"role": "user", "content": f"请将以下技术章节拆分为偏离表条目：\n\n{context}"},
            ],
            temperature=0.05,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        data = json.loads(raw) if raw else {}
        return data.get("entries", [])

    except Exception:
        return []


# ── Rule-based fallback splitting ─────────────────────────


def _rule_based_split(
    paragraphs: list[tuple[int, str, str]],
    tables: list[list[list[str]]],
) -> list[dict]:
    """Fallback: split by headings and paragraphs when LLM is unavailable."""

    entries: list[dict] = []

    # Process tables first
    for table in tables:
        for row in table:
            if any(keyword in str(c).lower() for c in row for keyword in ["序号", "字段", "名称"]):
                continue  # Skip header rows
            row_text = "；".join(f"{row[0] if len(row) > 0 else ''}: {c}" for c in row[1:] if c)
            if row_text:
                entries.append({"bid": row_text, "resp": "", "deviation": "无偏离"})

    # Process paragraphs: group consecutive non-heading paragraphs under their heading
    current_heading = ""
    current_content: list[str] = []

    for idx, style, text in paragraphs:
        is_heading = "Heading" in (style or "") or "heading" in (style or "").lower()

        if is_heading or (len(text) < 30 and ("要求" in text or "需求" in text or "功能" in text)):
            # Save previous group
            if current_content:
                entries.append({
                    "bid": "\n".join(current_content),
                    "resp": "",
                    "deviation": "无偏离",
                })
            current_heading = text
            current_content = []
        else:
            current_content.append(text)

    # Don't forget the last group
    if current_content:
        entries.append({
            "bid": "\n".join(current_content),
            "resp": "",
            "deviation": "无偏离",
        })

    # If no entries from table or grouped paragraphs, split by individual paragraphs
    if not entries:
        for idx, style, text in paragraphs:
            if len(text) > 20:
                entries.append({"bid": text, "resp": "", "deviation": "无偏离"})

    return entries


# ── Simplified API (backward-compatible with existing bridge) ──


async def call_techtoexcel(
    tech_text: str,
    output_dir: str,
    project_name: str,
) -> dict:
    """Simplified call for text-only input (without original docx chapter extraction).

    Used when we only have extracted tech text (not the original document).
    Falls back to basic Excel generation.
    """
    from app.services.file_service import generate_tech_excel
    filepath = generate_tech_excel(tech_text, project_name)
    return {
        "filepath": filepath,
        "filename": os.path.basename(filepath),
        "success": True,
    }
