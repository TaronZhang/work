"""TechToExcel 管线 — 纯 Python 解析 + LLM 仅辅助章节识别.

策略:
- 表格 → 程序化解析 (每行一条目, 表头=字段名)
- 段落 → 按标题/编号规则拆分
- C列 → 强制生成, 永不为空
- 不依赖 LLM 拆分条目 (避免格式混乱和空值)
"""

from __future__ import annotations

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

RESP_PREFIX = "应答:完全满足且无偏离.我司按照招标要求提供服务."

# 技术相关关键词 (用于段落筛选)
TECH_HEADING_KW = re.compile(
    r"(采购需求|采购要求|技术要求|技术规范|技术标准|项目需求|"
    r"服务内容|服务需求|功能要求|技术参数|实施方案|建设内容|"
    r"建设要求|系统功能|性能要求|安全要求|接口要求|"
    r"招标内容|项目概况|服务范围|工作内容)",
    re.IGNORECASE,
)

# Markdown / 格式符号清理
MD_CLEAN = re.compile(r"[*#_>`|~\-]{2,}")


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
    """从招标文件生成技术偏离表。

    纯 Python 解析，不依赖 LLM 拆分条目。
    LLM 仅在上游用于识别技术章节名称。
    """
    # 1. 提取
    try:
        paragraphs = extract_paragraphs(source_docx_path)
        tables = extract_tables(source_docx_path)
    except Exception as e:
        return TechToExcelResult(success=False, error=f"文档读取失败: {e}")

    if not paragraphs:
        return TechToExcelResult(success=False, error="文档无内容")

    # 2. 定位章节范围 (模糊匹配)
    ch_start, ch_end = _locate_chapter(paragraphs, chapter_name)

    # 3. 如果章节定位失败，用关键词筛选段落
    if ch_start is None:
        ch_paragraphs = _filter_tech_paragraphs(paragraphs)
    else:
        ch_paragraphs = paragraphs[ch_start:ch_end]

    if not ch_paragraphs:
        return TechToExcelResult(success=False, error="未找到技术相关段落")

    # 4. 表格 → 条目 (程序化)
    table_entries = _parse_tables_to_entries(tables)

    # 5. 段落 → 条目 (按标题/编号规则拆分)
    para_entries = _split_paragraphs_to_entries(ch_paragraphs)

    # 6. 合并
    all_entries = table_entries + para_entries

    if not all_entries:
        return TechToExcelResult(success=False, error="未能生成任何条目")

    # 7. 强制填充 C 列 + 清洗 Markdown
    for entry in all_entries:
        bid_text = _strip_markdown(entry.get("bid", ""))
        if not bid_text.strip():
            continue
        entry["bid"] = bid_text
        cleaned = clean_resp(bid_text)
        entry["resp"] = f"{RESP_PREFIX}{cleaned}"
        entry.setdefault("deviation", "无偏离")

    # 8. 过滤无效条目
    all_entries = [
        e for e in all_entries
        if e.get("bid", "").strip() and not _is_skip_line(e.get("bid", ""))
    ]

    if not all_entries:
        return TechToExcelResult(success=False, error="所有条目内容为空或仅含标题")

    # 9. 验证 + 写 Excel
    issues = verify(all_entries)

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
# 表格解析
# ====================================================================


def _parse_tables_to_entries(tables: list[list[list[str]]]) -> list[dict]:
    """表格行 → 条目。第一行=字段名, 后续每行=一条。"""
    entries: list[dict] = []

    for table in tables:
        if not table or len(table) < 2:
            continue

        headers = [_clean_cell(c) for c in table[0]]

        for row in table[1:]:
            parts = []
            for i, cell in enumerate(row):
                val = _clean_cell(cell)
                if not val:
                    continue
                field = headers[i] if i < len(headers) and headers[i] else f"字段{i + 1}"
                parts.append(f"{field}：{val}")

            if not parts:
                continue

            entries.append({
                "bid": "，".join(parts) + "。",
                "resp": "",
                "deviation": "无偏离",
            })

    return entries


def _clean_cell(text: str) -> str:
    """清洗单元格文本。"""
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ====================================================================
# 段落拆分 (纯规则，不需要 LLM)
# ====================================================================


def _split_paragraphs_to_entries(
    paragraphs: list[tuple[int, str, str]],
) -> list[dict]:
    """按标题层级和编号规则拆分段落为条目。"""
    entries: list[dict] = []
    current_title = ""
    current_lines: list[str] = []

    # 标题检测：Heading 样式 或 短文本+关键词
    def _is_title(text: str, style: str) -> bool:
        if style and ("Heading" in style or "heading" in style.lower()):
            return True
        if len(text) < 35 and ("要求" in text or "需求" in text or "内容" in text or "功能" in text):
            return True
        if re.match(r"^第[一二三四五六七八九十\d]+[章节]", text):
            return True
        if re.match(r"^[一二三四五六七八九十]+[、，]", text):
            return True
        return False

    for idx, style, text in paragraphs:
        text = text.strip()
        if not text:
            continue

        # 跳过纯格式/标记行
        if _is_skip_line(text):
            continue

        if _is_title(text, style):
            # 保存上一个分组
            if current_lines:
                entries.append(_make_entry(current_title, current_lines))
            current_title = text
            current_lines = []
        else:
            current_lines.append(text)

    # 保存最后一组
    if current_lines:
        entries.append(_make_entry(current_title, current_lines))

    # 如果条目太少，按自然段拆分
    if len(entries) <= 2 and len(paragraphs) > 5:
        entries = []
        buf: list[str] = []
        for idx, style, text in paragraphs:
            text = text.strip()
            if not text or _is_skip_line(text):
                continue
            # 编号行 → 新条目
            if re.match(r"^\s*(?:\d+[\.\)、]|[a-z][\)\.]|[\(（]\d+[\)）]|[①②③④⑤⑥⑦⑧⑨⑩])", text):
                if buf:
                    entries.append(_make_entry("", buf))
                    buf = []
            buf.append(text)
        if buf:
            entries.append(_make_entry("", buf))

    return entries


def _make_entry(title: str, lines: list[str]) -> dict:
    """构造条目。标题(如有)作为首行，后续为正文。"""
    if title and title not in lines:
        full = "\n".join([title] + lines)
    else:
        full = "\n".join(lines)
    return {"bid": full.strip(), "resp": "", "deviation": "无偏离"}


def _is_skip_line(text: str) -> bool:
    """跳过无意义的行。"""
    t = text.strip()
    if not t:
        return True
    if t in ("备注", "说明", "注", "注释", "提示"):
        return True
    if re.match(r"^备注[：:]", t):
        return True
    # 纯数字/页码
    if re.match(r"^\d{1,3}$", t):
        return True
    return False


# ====================================================================
# Markdown 清理
# ====================================================================


def _strip_markdown(text: str) -> str:
    """从文本中移除 Markdown 格式标记。"""
    # 去除 ## ### 等标题标记
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # 去除 ** 粗体
    text = text.replace("**", "")
    # 去除 __ 粗体
    text = text.replace("__", "")
    # 去除 ` 代码标记
    text = text.replace("`", "")
    # 去除 > 引用
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)
    # 去除水平线
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # 清理多余空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ====================================================================
# 章节定位
# ====================================================================


def _locate_chapter(
    paragraphs: list[tuple[int, str, str]],
    chapter_name: str,
) -> tuple[int | None, int | None]:
    """模糊匹配章节起止。"""
    if not chapter_name:
        return None, None

    ch_start = None
    ch_end = None

    ch_patterns = [
        "第一章", "第二章", "第三章", "第四章", "第五章",
        "第六章", "第七章", "第八章", "第九章", "第十章",
        "一、", "二、", "三、", "四、", "五、",
        "六、", "七、", "八、", "九、", "十、",
    ]

    # 提取搜索词
    keywords = _extract_keywords(chapter_name)

    for i, (idx, style, text) in enumerate(paragraphs):
        if ch_start is None and _fuzzy_match(text, keywords, chapter_name):
            ch_start = i
            continue
        if ch_start is not None and ch_end is None:
            for ch in ch_patterns:
                if ch not in chapter_name and ch in text and ("第" in text or "、" in text[:3]):
                    ch_end = i
                    break

    if ch_end is None and ch_start is not None:
        ch_end = len(paragraphs)

    return ch_start, ch_end


def _extract_keywords(name: str) -> list[str]:
    name = re.sub(r"第[一二三四五六七八九十\d]+章\s*", "", name)
    name = re.sub(r"第[一二三四五六七八九十\d]+节\s*", "", name)
    parts = re.split(r"[，,、\s]+", name.strip())
    return [p for p in parts if len(p) >= 2]


def _fuzzy_match(text: str, keywords: list[str], full_name: str) -> bool:
    if full_name in text:
        return True
    if full_name.replace(" ", "") in text.replace(" ", ""):
        return True
    for kw in keywords:
        if kw in text:
            return True
    return False


def _filter_tech_paragraphs(
    paragraphs: list[tuple[int, str, str]],
) -> list[tuple[int, str, str]]:
    """关键词筛选技术相关段落（章节定位失败时的回退）。"""
    result = []
    in_tech = False
    for idx, style, text in paragraphs:
        if TECH_HEADING_KW.search(text) and ("Heading" in str(style) or len(text) < 50):
            in_tech = True
        if in_tech:
            result.append((idx, style, text))
    return result if result else paragraphs


# ====================================================================
# 简化接口
# ====================================================================


async def call_techtoexcel(
    tech_text: str,
    output_dir: str,
    project_name: str,
) -> dict:
    """文本回退模式。"""
    from app.services.file_service import generate_tech_excel

    filepath = generate_tech_excel(tech_text, project_name)
    return {
        "filepath": filepath,
        "filename": os.path.basename(filepath),
        "success": True,
    }
