from __future__ import annotations

"""LLM-based metadata extraction from bid documents."""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from openai import AsyncOpenAI

METADATA_PROMPT = """你是一个标书信息提取专家。你的任务是从招标文件中提取三项关键信息。

请严格按以下要求提取：

1. 项目名称（项目名称）：
   - 通常在文件开头、标题或"项目名称"字段附近
   - 格式如："XXX项目"、"XXX采购"、"XXX服务"
   - 提取完整的项目全称

2. 招标人名称（招标人名称）：
   - 通常是"招标人"、"采购人"、"业主"后面的单位名称
   - 也可能是"XXX公司"、"XXX局"、"XXX中心"等
   - 提取完整的单位全称，不含"招标人："前缀

3. 投标截止日期（投标截止日期）：
   - 格式如：2025年6月30日 09:30 或 2025-06-30 09:30
   - 通常出现在"投标截止时间"、"递交截止时间"、"开标时间"附近
   - 如果只有日期没有时间，默认时间为 09:00
   - 如果完全找不到，设为 null

输出格式 (JSON):
{
  "project_name": "提取的项目全称",
  "bidder_name": "提取的招标人全称",
  "submission_deadline": "YYYY-MM-DD HH:MM",
  "deadline_found": true,
  "confidence": "high|medium|low"
}

注意：
- 如果某项信息不确定，设置 confidence 为 medium 或 low
- 尽量从原文中精确提取，不要编造或修改
- deadline 字段如果是null，deadline_found 为 false"""


@dataclass
class MetadataResult:
    project_name: str = ""
    bidder_name: str = ""
    submission_deadline: Optional[datetime] = None
    deadline_found: bool = False
    confidence: str = "low"
    raw_response: dict = field(default_factory=dict)


async def extract_metadata(
    doc_text: str,
    base_url: str,
    api_key: str,
    model: str,
) -> MetadataResult:
    """Call LLM to extract project name, bidder name, and deadline from document text.

    Only sends the first ~15000 characters since key metadata is usually at the top.
    """
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    # Truncate to avoid token limits — metadata is typically in the first section
    snippet = doc_text[:15000]

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": METADATA_PROMPT},
                {"role": "user", "content": f"请从以下招标文件中提取信息：\n\n{snippet}"},
            ],
            temperature=0.05,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        data = json.loads(raw) if raw else {}

    except Exception as e:
        return MetadataResult(
            confidence="low",
            raw_response={"error": str(e)},
        )

    deadline = None
    deadline_str = data.get("submission_deadline", "")
    if deadline_str and deadline_str != "null":
        deadline = _parse_deadline(deadline_str)

    return MetadataResult(
        project_name=data.get("project_name", ""),
        bidder_name=data.get("bidder_name", ""),
        submission_deadline=deadline,
        deadline_found=data.get("deadline_found", bool(deadline)),
        confidence=data.get("confidence", "low"),
        raw_response=data,
    )


def _parse_deadline(date_str: str) -> Optional[datetime]:
    """Parse various Chinese date formats into datetime."""
    if not date_str or date_str == "null":
        return None

    date_str = date_str.strip()

    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y年%m月%d日 %H:%M",
        "%Y年%m月%d日%H:%M",
        "%Y年%m月%d日 %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y年%m月%d日",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    # Try regex fallback: extract YYYY-MM-DD
    match = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})[日]?", date_str)
    if match:
        y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
        # Try to extract time
        time_match = re.search(r"(\d{1,2}):(\d{2})", date_str)
        hour, minute = (int(time_match.group(1)), int(time_match.group(2))) if time_match else (9, 0)
        try:
            return datetime(y, m, d, hour, minute)
        except ValueError:
            pass

    return None
