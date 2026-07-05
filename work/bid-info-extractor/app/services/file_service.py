"""File generation service — Markdown and artifact management."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings


def sanitize_filename(name: str) -> str:
    """Replace characters unsafe for filenames."""
    unsafe = r'[<>:"/\\|?*\n\r\t]'
    name = re.sub(unsafe, "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) > 200:
        name = name[:200]
    return name


def generate_markdown_summary(
    project_name: str,
    bidder_name: str,
    deadline,
    source_filename: str,
) -> str:
    """Generate a summary markdown file for the bid project."""
    name_safe = sanitize_filename(project_name) if project_name else "未命名项目"
    filename = f"{name_safe}信息V1.md"
    filepath = os.path.join(settings.export_dir, filename)

    deadline_str = ""
    if deadline:
        if hasattr(deadline, "strftime"):
            deadline_str = deadline.strftime("%Y-%m-%d %H:%M")
        else:
            deadline_str = str(deadline)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    content = f"""# {project_name or '未命名项目'} 信息摘要

## 基本信息

| 字段 | 内容 |
|---|---|
| **项目名称** | {project_name or '--'} |
| **招标人名称** | {bidder_name or '--'} |
| **投标截止日期** | {deadline_str or '--'} |
| **源文件** | {source_filename or '--'} |
| **提取时间** | {now} |

---

*本文件由 Bid Info Extractor 自动生成*
"""

    Path(os.path.dirname(filepath)).mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


def generate_tech_excel(
    tech_text: str,
    project_name: str,
) -> str:
    """Generate point-by-point technical response Excel.

    Uses the same 4-column format as the techtoexcel pipeline,
    with C column ALWAYS populated.
    """
    from app.services.techtoexcel_utils import clean_resp, write_excel

    name_safe = sanitize_filename(project_name) if project_name else "未命名项目"
    filename = f"{name_safe}_技术应答.xlsx"
    filepath = os.path.join(settings.export_dir, filename)

    # Parse items
    items = _parse_requirement_items(tech_text)

    # Build entries with mandatory C column
    entries = []
    for item in items:
        cleaned = clean_resp(item)
        entries.append({
            "bid": item,
            "resp": f"应答:完全满足且无偏离.我司按照招标要求提供服务.{cleaned}",
            "deviation": "无偏离",
        })

    Path(os.path.dirname(filepath)).mkdir(parents=True, exist_ok=True)
    write_excel(entries, filepath)
    return filepath


def _parse_requirement_items(text: str) -> list[str]:
    """Parse requirement text into individual items."""
    items = []

    pattern = re.compile(
        r"(?:^|\n)\s*(?:\d+[\.\)、]\s*|\(\d+\)\s*|[（(]\d+[）)]\s*)", re.MULTILINE
    )
    splits = pattern.split(text)

    for s in splits:
        s = s.strip()
        if s and len(s) > 10:
            items.append(s)

    if not items:
        items = [p.strip() for p in text.split("\n") if len(p.strip()) > 10]

    return items[:200]
