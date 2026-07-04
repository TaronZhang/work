from __future__ import annotations

"""Identify technical requirement sections in bid documents using LLM."""

import json
import re
from dataclasses import dataclass, field

from openai import AsyncOpenAI

TECH_SECTION_PROMPT = """你是一个招标文件的结构分析师。你的任务是从招标文件的完整文本中，识别出包含"技术要求"的章节。

这些章节通常包含：
- 项目需要达到的技术指标
- 系统需要实现的功能列表
- 服务需要满足的技术规范
- 产品或交付物需要符合的标准
- 具体的实施/开发要求

典型章节标题包括（但不限于）：
采购需求、采购要求、技术要求、技术规范、技术标准、项目需求、
服务内容及要求、服务需求、功能要求、技术参数、实施方案要求

必须排除以下章节/内容类型：
- 法人资格要求 — 例如"投标人应是在中华人民共和国境内注册的法人"
- 承诺书/声明书 — 格式化的承诺函模板
- 投标人资格要求 — 资质、证书、注册资金要求
- 商务条款 — 付款方式、合同期限、保证金
- 评分标准/评审细则 — 分值分配、打分规则
- 合同通用条款/法律条款 — 任何"法律法规"、"通用条款"段落

对于每个识别出的技术章节，请提供：
1. title: 章节原标题
2. content: 该章节的完整原文内容（不要总结或修改）

输出格式 (JSON):
{
  "tech_sections": [
    {
      "title": "章节原标题",
      "content": "章节的完整技术要求原文内容"
    }
  ],
  "total_tech_chars": 5678,
  "has_tech_content": true,
  "combined_tech_text": "所有章节内容的合并文本"
}

重要原则：
- 宁缺毋滥：如果不确定是否属于技术要求，宁可遗漏
- 保留原文：content字段应保留原文，不应概括或改写
- 完整提取：每个章节的content应该包含该章节的完整原文"""


@dataclass
class TechSection:
    title: str
    content: str


@dataclass
class TechSectionsResult:
    sections: list[TechSection] = field(default_factory=list)
    combined_text: str = ""
    total_chars: int = 0
    has_tech_content: bool = False
    raw_response: dict = field(default_factory=dict)


async def identify_tech_sections(
    doc_text: str,
    base_url: str,
    api_key: str,
    model: str,
) -> TechSectionsResult:
    """Use LLM to identify technical requirement sections, excluding business/legal content."""

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    # Send full doc text; LLM context windows are large enough for most bid docs
    # If extremely large, truncate intelligently
    snippet = doc_text if len(doc_text) < 120000 else doc_text[:120000]

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": TECH_SECTION_PROMPT},
                {"role": "user", "content": f"请识别以下招标文件中的技术要求章节：\n\n{snippet}"},
            ],
            temperature=0.05,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        data = json.loads(raw) if raw else {}

    except Exception as e:
        # Fallback: try keyword-based extraction
        return _keyword_fallback(doc_text, error=str(e))

    sections = [
        TechSection(title=s.get("title", ""), content=s.get("content", ""))
        for s in data.get("tech_sections", [])
    ]

    return TechSectionsResult(
        sections=sections,
        combined_text=data.get("combined_tech_text", ""),
        total_chars=data.get("total_tech_chars", 0),
        has_tech_content=data.get("has_tech_content", len(sections) > 0),
        raw_response=data,
    )


# ── Keyword-based fallback (no LLM required) ────────────

TECH_KEYWORDS = re.compile(
    r"(采购需求|采购要求|技术要求|技术规范|技术标准|项目需求|"
    r"服务内容及要求|服务需求|功能要求|技术参数|实施方案要求|"
    r"建设内容|建设要求|系统功能|性能要求|安全要求|接口要求)",
    re.IGNORECASE,
)

EXCLUDE_KEYWORDS = re.compile(
    r"(法人资格|承诺书|声明书|投标人资格|商务条款|付款方式|"
    r"合同期限|保证金|评分标准|评审细则|通用条款|法律法规|"
    r"投标人须知|投标文件格式|联合体|分包|转包)",
    re.IGNORECASE,
)


def _keyword_fallback(doc_text: str, error: str = "") -> TechSectionsResult:
    """Fallback: use keyword matching to find technical sections when LLM is unavailable."""
    sections = []
    # Split by common heading patterns
    heading_pattern = re.compile(
        r"^(.{0,50}(?:需求|要求|规范|标准|内容|参数|功能|性能).{0,30})$",
        re.MULTILINE,
    )

    matches = list(heading_pattern.finditer(doc_text))

    for i, match in enumerate(matches):
        title = match.group(1).strip()
        if EXCLUDE_KEYWORDS.search(title):
            continue
        if not TECH_KEYWORDS.search(title):
            continue

        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else min(len(doc_text), start + 5000)
        content = doc_text[start:end].strip()

        sections.append(TechSection(title=title, content=content[:3000]))

    combined = "\n\n".join(f"## {s.title}\n{s.content}" for s in sections)

    return TechSectionsResult(
        sections=sections,
        combined_text=combined,
        total_chars=len(combined),
        has_tech_content=len(sections) > 0,
        raw_response={"fallback": True, "error": error, "method": "keyword"},
    )
