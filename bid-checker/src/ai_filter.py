"""AI 辅助过滤模块 — 用 LLM 识别并过滤招标文件中的格式要求"""

import json
import re
from dataclasses import dataclass, field


@dataclass
class AnnotatedParagraph:
    """LLM 标注后的段落"""
    text: str
    category: str  # format_requirement | p2p_response | legal_clause | scoring | substantive
    is_requirement: bool
    reason: str = ''


@dataclass
class FilteredTender:
    """过滤后的招标文件"""
    original_text: str
    paragraphs: list[AnnotatedParagraph] = field(default_factory=list)
    filtered_text: str = ''           # 仅实质性内容
    requirements_text: str = ''       # 格式要求内容（供展示）
    filter_summary: dict = field(default_factory=dict)  # 各类别统计


AI_FILTER_PROMPT = """你是一位经验丰富的招标文件分析专家。你的任务是分析招标文件内容，识别并分类每一段文本的性质。

请将每段内容归类到以下类型之一：

1. **格式要求** (format_requirement)
   - 字体、字号、行距、页边距、装订方式
   - 盖章要求、签字要求、份数要求
   - 封装、密封、标记要求
   - 文件格式、电子版要求

2. **点对点应答要求** (p2p_response)
   - "投标人应提供..." / "须附上..." / "需提交..."
   - "请逐条响应..." / "应包含以下内容..."
   - 具体证明材料的索要
   - 资格条件的逐条响应要求

3. **法律条款/通用模板** (legal_clause)
   - 通用的法律法规引用
   - 合同通用条款
   - 标准商务条款
   - 行业通用表述

4. **评分标准** (scoring_criteria)
   - 评分细则、分值分配
   - 评审标准、打分规则
   - 权重分配

5. **实质性内容** (substantive)
   - 项目背景、需求描述
   - 技术规格、功能要求
   - 服务范围、交付物描述
   - 验收标准、实施计划

输出格式为严格JSON数组（不要有任何额外的解释文字）：
[
  {
    "text": "原文段落...",
    "category": "format_requirement",
    "is_requirement": true,
    "reason": "简短分类理由"
  }
]

注意：
- "实质性内容"(substantive)是is_requirement=false的唯一类型
- 其他四种类型都是is_requirement=true
- 请尽量保持原文完整性，不要截断
- 如果文本太长，请合理分组合并相邻同类段落"""


def filter_tender_requirements(
    tender_text: str,
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o",
) -> FilteredTender:
    """调用 LLM 分类招标文件段落，过滤格式要求等非实质性内容"""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)

    # 将招标文本按段落切分（保留上下文）
    paragraphs = _split_tender_paragraphs(tender_text)

    # 如果文本太长，分批处理
    all_annotations = []
    batch_size = 15
    for i in range(0, len(paragraphs), batch_size):
        batch = paragraphs[i:i + batch_size]
        batch_text = '\n\n---\n\n'.join(
            f'[段{idx}] {p}' for idx, p in enumerate(batch, start=i)
        )

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": AI_FILTER_PROMPT},
                    {"role": "user", "content": f"请分析以下招标文件段落：\n\n{batch_text}"},
                ],
                temperature=0.1,
                max_tokens=4096,
            )
            content = response.choices[0].message.content
            annotations = _parse_filter_response(content)
            all_annotations.extend(annotations)
        except Exception as e:
            # 出错时将该批次全部标记为 substantive（保守策略）
            for p in batch:
                all_annotations.append(AnnotatedParagraph(
                    text=p,
                    category='substantive',
                    is_requirement=False,
                    reason=f'LLM 调用失败: {str(e)}',
                ))

    # 构建 FilteredTender
    substantive_parts = []
    requirement_parts = []
    summary = {'format_requirement': 0, 'p2p_response': 0, 'legal_clause': 0,
               'scoring_criteria': 0, 'substantive': 0}

    for ann in all_annotations:
        summary[ann.category] = summary.get(ann.category, 0) + 1
        if ann.is_requirement:
            requirement_parts.append(ann.text)
        else:
            substantive_parts.append(ann.text)

    return FilteredTender(
        original_text=tender_text,
        paragraphs=all_annotations,
        filtered_text='\n'.join(substantive_parts) if substantive_parts else tender_text,
        requirements_text='\n'.join(requirement_parts),
        filter_summary=summary,
    )


def _split_tender_paragraphs(text: str) -> list[str]:
    """将招标文本按自然段落切分"""
    # 按双换行或明显的段落标记切分
    parts = re.split(r'\n\s*\n', text)
    result = []
    for p in parts:
        p = p.strip()
        if len(p) >= 10:  # 忽略过短的行（可能是页码等）
            result.append(p)
    return result


def _parse_filter_response(response: str) -> list[AnnotatedParagraph]:
    """解析 LLM 返回的 JSON 响应"""
    # 尝试提取 JSON 数组
    json_match = re.search(r'\[[\s\S]*\]', response)
    if not json_match:
        return []

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError:
        return []

    result = []
    for item in data:
        result.append(AnnotatedParagraph(
            text=item.get('text', ''),
            category=item.get('category', 'substantive'),
            is_requirement=item.get('is_requirement', False),
            reason=item.get('reason', ''),
        ))
    return result
