"""TechToExcel 管线 — 招标文件 → 技术偏离表 Excel.

数据处理策略:
- 表格: 程序化直接解析 (每行 → 一条目, 表头行作字段名)
- 段落: LLM 智能拆条 (按规则合并/拆分)
- C列: 强制生成 "应答:完全满足且无偏离.我司按照招标要求提供服务.{清洗后原文}"
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from app.services.techtoexcel_utils import (
    clean_resp,
    extract_paragraphs,
    extract_tables,
    verify,
    write_excel,
)


# ── Entry format ─────────────────────────────────────────

# C 列应答模板
RESP_PREFIX = "应答:完全满足且无偏离.我司按照招标要求提供服务."


@dataclass
class TechToExcelResult:
    filepath: str = ""
    filename: str = ""
    entry_count: int = 0
    issues: list[str] = field(default_factory=list)
    success: bool = False
    error: str = ""


# ====================================================================
# 主入口
# ====================================================================


async def run_techtoexcel_pipeline(
    source_docx_path: str,
    chapter_name: str,
    output_dir: str,
    project_name: str,
    base_url: str = "",
    api_key: str = "",
    model: str = "",
) -> TechToExcelResult:
    """从招标文件提取技术章节，生成点对点技术偏离表。

    流程:
    1. 定位章节 → 提取段落 + 表格
    2. 表格直接解析为条目 (每行一条)
    3. 段落 LLM 拆条
    4. 合并 + C列清洗 + 验证
    5. 输出专业格式 Excel
    """
    # 1. 提取
    try:
        paragraphs = extract_paragraphs(source_docx_path)
        tables = extract_tables(source_docx_path)
    except Exception as e:
        return TechToExcelResult(success=False, error=f"文档读取失败: {e}")

    if not paragraphs:
        return TechToExcelResult(success=False, error="文档无内容")

    # 2. 定位章节
    ch_start, ch_end = _locate_chapter(paragraphs, chapter_name)
    if ch_start is None:
        return TechToExcelResult(success=False, error=f"未找到章节: {chapter_name}")

    ch_paragraphs = paragraphs[ch_start:ch_end]

    # 3. 表格 → 条目 (程序化解析，不依赖 LLM)
    table_entries = _parse_tables_to_entries(tables)

    # 4. 段落 → 条目 (LLM 或规则拆条)
    para_entries = []
    para_text = "\n".join(p[2] for p in ch_paragraphs)
    if api_key and base_url:
        para_entries = await _llm_split_paragraphs(para_text, base_url, api_key, model)
    if not para_entries:
        para_entries = _rule_split_paragraphs(ch_paragraphs)

    # 5. 合并所有条目
    all_entries = table_entries + para_entries

    if not all_entries:
        return TechToExcelResult(success=False, error="未能生成任何条目")

    # 6. 强制生成 C 列应答 + 清洗
    for entry in all_entries:
        bid_text = entry.get("bid", "")
        if not bid_text or not bid_text.strip():
            continue
        cleaned = clean_resp(bid_text)
        entry["resp"] = f"{RESP_PREFIX}{cleaned}"
        entry.setdefault("deviation", "无偏离")

    # 过滤无效条目
    all_entries = [
        e for e in all_entries
        if e.get("bid", "").strip()
        and not _is_chapter_title(e.get("bid", ""))
    ]

    if not all_entries:
        return TechToExcelResult(success=False, error="所有条目内容为空")

    # 7. 验证
    issues = verify(all_entries)

    # 8. 写 Excel
    from app.services.file_service import sanitize_filename

    name_safe = sanitize_filename(project_name) if project_name else "项目"
    filename = f"{name_safe}_技术偏离表.xlsx"
    filepath = os.path.join(output_dir, filename)
    os.makedirs(output_dir, exist_ok=True)

    count = write_excel(all_entries, filepath)

    return TechToExcelResult(
        filepath=filepath,
        filename=filename,
        entry_count=count,
        issues=issues,
        success=True,
    )


# ====================================================================
# 表格解析 (程序化，不依赖 LLM)
# ====================================================================


def _parse_tables_to_entries(tables: list[list[list[str]]]) -> list[dict]:
    """将 docx 表格直接解析为偏离表条目。

    规则:
    - 第一行作为表头 (字段名)
    - 后续每行 → 一条目
    - B列格式: "字段1：值1,字段2：值2,..."
    - 跳过空行和表头行
    """
    entries: list[dict] = []

    for table in tables:
        if not table or len(table) < 2:
            continue

        headers = table[0]  # 第一行 = 字段名

        for row in table[1:]:
            # 构建 "字段：值" 格式
            parts = []
            for i, cell in enumerate(row):
                val = (cell or "").strip()
                if not val:
                    continue
                # 使用对应表头作字段名
                field = headers[i].strip() if i < len(headers) and headers[i].strip() else f"字段{i+1}"
                parts.append(f"{field}：{val}")

            if not parts:
                continue

            bid_text = ", ".join(parts)
            entries.append({
                "bid": bid_text,
                "resp": "",    # 稍后统一填充
                "deviation": "无偏离",
            })

    return entries


# ====================================================================
# 段落拆条 (LLM)
# ====================================================================


PARA_SPLIT_PROMPT = """你是招标文件技术条款拆分专家。将以下段落内容拆分为逐条应答条目。

## 规则

### 条目划分
1. 每个独立需求点 = 一条目 (如一个功能点、一项技术指标)
2. 编号列表 (1. 2. 或 a) b) 或 (1) (2)) 按编号各自成条
3. "以下"/"如下"/"包括" 开头的段落 → 其后的子项合并为一条
4. 纯标题无内容 → 跳过
5. 备注/说明/注 → 跳过

### B列格式
完全复制原文，一字不改，不得截断。长段落完整保留。

### 输出 JSON
{
  "entries": [
    {"bid": "原文完整内容", "deviation": "无偏离"}
  ]
}"""


async def _llm_split_paragraphs(
    para_text: str,
    base_url: str,
    api_key: str,
    model: str,
) -> list[dict]:
    """LLM 将段落拆分为条目。"""
    if len(para_text) < 20:
        return _simple_split(para_text)

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    snippet = para_text[:80000]

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": PARA_SPLIT_PROMPT},
                {"role": "user", "content": f"请拆分以下技术条款:\n\n{snippet}"},
            ],
            temperature=0.05,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        data = json.loads(raw) if raw else {}
        entries = data.get("entries", [])
        # 确保每条都有 deviation
        for e in entries:
            e.setdefault("deviation", "无偏离")
        return entries
    except Exception:
        return _rule_split_paragraphs(
            [(i, "Normal", t) for i, t in enumerate(para_text.split("\n")) if t.strip()]
        )


def _simple_split(text: str) -> list[dict]:
    """极简拆分：短文本直接一条。"""
    return [{"bid": text.strip(), "deviation": "无偏离"}] if text.strip() else []


# ====================================================================
# 段落拆条 (规则回退)
# ====================================================================


def _rule_split_paragraphs(
    paragraphs: list[tuple[int, str, str]],
) -> list[dict]:
    """基于标题层级和编号规则的段落拆条 (无需 LLM)。"""
    entries: list[dict] = []
    current_bid: list[str] = []

    # 编号检测
    numbered = re.compile(
        r"^\s*(?:\d+[\.\)、]\s*|[\(（]\d+[\)）]\s*|[a-z][\)\.]\s*|[①②③④⑤⑥⑦⑧⑨⑩])"
    )

    for idx, style, text in paragraphs:
        text = text.strip()
        if not text:
            continue

        is_heading = bool(
            style and ("Heading" in style or "heading" in style.lower())
        ) or (len(text) < 40 and ("要求" in text or "需求" in text or "功能" in text or "内容" in text))

        is_numbered = bool(numbered.match(text))

        if is_heading and current_bid:
            entries.append({"bid": "\n".join(current_bid), "deviation": "无偏离"})
            current_bid = []
        elif is_numbered and current_bid:
            entries.append({"bid": "\n".join(current_bid), "deviation": "无偏离"})
            current_bid = [text]
        else:
            current_bid.append(text)

    if current_bid:
        entries.append({"bid": "\n".join(current_bid), "deviation": "无偏离"})

    # 如果拆得太少, 再按自然段拆
    if len(entries) <= 1 and len(paragraphs) > 3:
        entries = []
        buf: list[str] = []
        for idx, style, text in paragraphs:
            text = text.strip()
            if not text:
                continue
            if len(text) > 80:
                if buf:
                    entries.append({"bid": "\n".join(buf), "deviation": "无偏离"})
                    buf = []
                entries.append({"bid": text, "deviation": "无偏离"})
            else:
                buf.append(text)
        if buf:
            entries.append({"bid": "\n".join(buf), "deviation": "无偏离"})

    return entries


# ====================================================================
# 章节定位
# ====================================================================


def _locate_chapter(
    paragraphs: list[tuple[int, str, str]],
    chapter_name: str,
) -> tuple[int | None, int | None]:
    """在段落列表中定位章节的起止索引。"""
    ch_start = None
    ch_end = None

    ch_patterns = [
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
            for ch in ch_patterns:
                if ch != chapter_name and ch in text and ("第" in text or "、" in text[:3]):
                    ch_end = i
                    break

    if ch_end is None:
        ch_end = len(paragraphs)

    return ch_start, ch_end


def _is_chapter_title(text: str) -> bool:
    """判断是否为章节标题（无实质内容的纯标题行）。"""
    patterns = [
        r"^第[一二三四五六七八九十\d]+章",
        r"^第[一二三四五六七八九十\d]+节",
        r"^[一二三四五六七八九十]+[、，]",
        r"^（[一二三四五六七八九十\d]+）",
    ]
    text = text.strip()
    # 只有标题没有内容（长度 < 30 且匹配标题模式）
    if len(text) < 30:
        for pat in patterns:
            if re.match(pat, text):
                return True
    return False


# ====================================================================
# 简化接口 (文本模式回退)
# ====================================================================


async def call_techtoexcel(
    tech_text: str,
    output_dir: str,
    project_name: str,
) -> dict:
    """文本模式：无原始 docx 时的回退。"""
    from app.services.file_service import generate_tech_excel

    filepath = generate_tech_excel(tech_text, project_name)
    return {
        "filepath": filepath,
        "filename": os.path.basename(filepath),
        "success": True,
    }
