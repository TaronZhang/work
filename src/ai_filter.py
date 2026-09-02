"""AI 辅助分析模块 — 两阶段 AI 分析

阶段 1 (可选): 事前过滤招标文件中的格式要求等非实质内容
阶段 2 (核心): 事后分析比对结果，区分"合规应答"和"实际重复"

合规应答：投标文件中重复了招标文件的功能参数、技术规格等内容，
         这是投标人必须做的合规响应，不应算作重复。
实际重复：投标文件中大段照搬招标文件的背景描述、方案要求等内容，
         属于不必要的重复。
"""

import json
import re
from dataclasses import dataclass, field


@dataclass
class AnnotatedParagraph:
    """LLM 标注后的段落"""
    text: str
    category: str
    is_requirement: bool
    reason: str = ''


@dataclass
class FilteredTender:
    """过滤后的招标文件"""
    original_text: str
    paragraphs: list[AnnotatedParagraph] = field(default_factory=list)
    filtered_text: str = ''
    requirements_text: str = ''
    filter_summary: dict = field(default_factory=dict)


@dataclass
class SegmentAnalysis:
    """单个匹配段的 AI 分析结果"""
    segment_id: int
    tender_text: str
    bid_text: str
    similarity: float
    classification: str  # compliance_response | actual_duplication
    reason: str = ''
    adjusted_similarity: float = 0.0


@dataclass
class ComparisonAnalysis:
    """比对结果的 AI 分析"""
    pair_index: int
    label_a: str
    label_b: str
    original_percentage: float
    adjusted_percentage: float
    compliance_chars: int
    actual_duplication_chars: int
    segment_analyses: list[SegmentAnalysis] = field(default_factory=list)
    summary: str = ''


# ── 事前过滤提示词（保留原有功能）──
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


# ── 事后分析提示词（核心新增）──
AI_SEGMENT_ANALYSIS_PROMPT = """你是一位招投标领域的资深评审专家。你的任务是分析文档比对工具发现的重复段落，判断每一段重复属于"合规应答"还是"实际重复"。

背景：
在招标采购中，投标文件必须对招标文件的要求逐条响应。当招标文件规定了功能参数、技术规格、服务要求等内容时，投标文件中重复这些内容是合规应答的必要行为，不应算作抄袭或重复。

分类规则：

1. **合规应答** (compliance_response) — 满足以下任一条件：
   - 招标文件提出了具体的功能参数/技术指标，投标文件重复这些参数是响应要求
     例如：招标要求"支持100Gbps吞吐量"，投标文件写"支持100Gbps吞吐量"
   - 招标文件列出了服务范围/交付物清单，投标文件重复这些内容是确认承诺
     例如：招标要求"提供7×24小时运维"，投标文件写"提供7×24小时运维"
   - 招标文件规定了资质/认证要求，投标文件重复这些要求是声明满足
     例如：招标要求"具备ISO27001认证"，投标文件写"具备ISO27001认证"
   - 招标文件给出了验收标准/测试方法，投标文件重复这些标准是接受约束
   - 招标文件列出了具体的技术规格表/参数表，投标文件复制这些参数表是逐条响应
   - 本质：投标人在回应招标方的具体要求，重复是必要且合理的

2. **实际重复** (actual_duplication) — 满足以下任一条件：
   - 招标文件的项目背景/需求描述被大段照搬到投标文件中
     例如：招标文件描述"本项目旨在建设..."，投标文件原样复制这段背景描述
   - 招标文件的工作方案/实施方案要求被直接照搬
     例如：招标文件写了详细的实施步骤，投标文件直接复制不改
   - 招标文件的通用条款/模板文字被复制到投标文件中
   - 招标文件的技术方案描述被照搬（不是参数响应，而是方案描述）
   - 本质：投标人图省事直接照搬招标文件内容，这些内容本应自行撰写

判断要点：
- 关注内容的性质：是"参数指标/要求清单"（合规应答）还是"描述性文字/方案内容"（实际重复）
- 关注重复的方式：是"逐条对应响应"（合规应答）还是"大段照搬"（实际重复）
- 合规应答通常较短且结构化（参数表、指标列表、资质声明）
- 实际重复通常较长且为叙述性文字（背景描述、方案细节、实施步骤）

输出格式为严格JSON数组（不要有任何额外的解释文字）：
[
  {
    "segment_id": 0,
    "classification": "compliance_response",
    "reason": "招标文件提出技术参数要求，投标文件逐条响应，属于合规应答",
    "adjusted_similarity": 0.0
  }
]

adjusted_similarity 说明：
- compliance_response 类型：adjusted_similarity 设为 0.0（合规应答不算重复）
- actual_duplication 类型：adjusted_similarity 保留原始相似度值"""


def filter_tender_requirements(
    tender_text: str,
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o",
) -> FilteredTender:
    """调用 LLM 分类招标文件段落，过滤格式要求等非实质性内容"""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)

    paragraphs = _split_tender_paragraphs(tender_text)

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
            for p in batch:
                all_annotations.append(AnnotatedParagraph(
                    text=p,
                    category='substantive',
                    is_requirement=False,
                    reason=f'LLM 调用失败: {str(e)}',
                ))

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


def analyze_comparison_segments(
    results: list,
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o",
) -> list[ComparisonAnalysis]:
    """对比对结果进行 AI 事后分析，区分合规应答和实际重复。

    Args:
        results: 比对结果列表，每个元素是 format_pair_result 返回的 dict
        api_key: OpenAI API Key
        base_url: API base URL
        model: 模型名称

    Returns:
        每对比对的 AnalysisResult
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    analyses = []

    for pair_idx, result in enumerate(results):
        segments = result.get('segments', [])
        if not segments:
            analyses.append(ComparisonAnalysis(
                pair_index=pair_idx,
                label_a=result.get('label_a', ''),
                label_b=result.get('label_b', ''),
                original_percentage=result.get('duplicate_percentage', 0),
                adjusted_percentage=result.get('duplicate_percentage', 0),
                compliance_chars=0,
                actual_duplication_chars=0,
                summary='无匹配段落，无需 AI 分析',
            ))
            continue

        # 分批处理匹配段（每批最多 10 个）
        all_segment_analyses = []
        batch_size = 10

        for i in range(0, len(segments), batch_size):
            batch = segments[i:i + batch_size]

            # 构建发送给 AI 的内容
            # 注意：发送给 LLM 时截断到 500 字以控制 token 用量，
            # 但计算调整后重复率时使用完整段落文本（见下方 seg_len 计算）
            segments_text = '\n\n'.join(
                f'--- 匹配段 #{seg.get("id", idx)} ---\n'
                f'相似度: {round(seg.get("similarity", 0) * 100)}%\n'
                f'招标文件内容: {seg.get("tender_text", "")[:500]}\n'
                f'投标文件内容: {seg.get("bid_text", "")[:500]}'
                for idx, seg in enumerate(batch, start=i)
            )

            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": AI_SEGMENT_ANALYSIS_PROMPT},
                        {"role": "user", "content": f"请分析以下文档比对中发现的重复段落：\n\n{segments_text}"},
                    ],
                    temperature=0.1,
                    max_tokens=4096,
                )
                content = response.choices[0].message.content
                batch_analyses = _parse_segment_analysis(content, batch)

                if not batch_analyses:
                    # JSON 解析失败或返回空数组时，保守标记为实际重复
                    for idx, seg in enumerate(batch, start=i):
                        all_segment_analyses.append(SegmentAnalysis(
                            segment_id=seg.get('id', idx),
                            tender_text=seg.get('tender_text', ''),
                            bid_text=seg.get('bid_text', ''),
                            similarity=seg.get('similarity', 0),
                            classification='actual_duplication',
                            reason='AI 返回解析失败，保守标记为实际重复',
                            adjusted_similarity=seg.get('similarity', 0),
                        ))
                else:
                    all_segment_analyses.extend(batch_analyses)
            except Exception as e:
                # 出错时保守标记为实际重复（不遗漏）
                for idx, seg in enumerate(batch, start=i):
                    all_segment_analyses.append(SegmentAnalysis(
                        segment_id=seg.get('id', idx),
                        tender_text=seg.get('tender_text', ''),
                        bid_text=seg.get('bid_text', ''),
                        similarity=seg.get('similarity', 0),
                        classification='actual_duplication',
                        reason=f'AI 分析失败: {str(e)}',
                        adjusted_similarity=seg.get('similarity', 0),
                    ))

        # 计算调整后的重复率
        # 口径说明：
        # - 使用完整段落文本长度计算（非发送给 LLM 的截断版本）
        # - 调整后重复率 = (实际重复字符数 / 招标文件总字符数) * 100
        # - 当 LLM 返回缺项或 JSON 解析失败时，对应段落保守标记为实际重复
        total_tender = result.get('total_tender_chars', 1) or 1
        compliance_chars = 0
        actual_dup_chars = 0

        for sa in all_segment_analyses:
            seg_len = len(sa.tender_text)
            if sa.classification == 'compliance_response':
                compliance_chars += seg_len
                sa.adjusted_similarity = 0.0
            else:
                actual_dup_chars += seg_len
                sa.adjusted_similarity = sa.similarity

        actual_dup_percentage = (actual_dup_chars / total_tender) * 100 if total_tender > 0 else 0
        original_pct = result.get('duplicate_percentage', 0)

        # 构建摘要
        compliance_count = sum(1 for sa in all_segment_analyses if sa.classification == 'compliance_response')
        dup_count = len(all_segment_analyses) - compliance_count

        summary = (
            f'共 {len(all_segment_analyses)} 段匹配：'
            f'合规应答 {compliance_count} 段（{compliance_chars} 字），'
            f'实际重复 {dup_count} 段（{actual_dup_chars} 字）。'
            f'原始重复率 {original_pct:.1f}%，调整后重复率 {actual_dup_percentage:.1f}%。'
        )

        analyses.append(ComparisonAnalysis(
            pair_index=pair_idx,
            label_a=result.get('label_a', ''),
            label_b=result.get('label_b', ''),
            original_percentage=original_pct,
            adjusted_percentage=round(actual_dup_percentage, 1),
            compliance_chars=compliance_chars,
            actual_duplication_chars=actual_dup_chars,
            segment_analyses=all_segment_analyses,
            summary=summary,
        ))

    return analyses


def _split_tender_paragraphs(text: str) -> list[str]:
    """将招标文本按自然段落切分"""
    parts = re.split(r'\n\s*\n', text)
    result = []
    for p in parts:
        p = p.strip()
        if len(p) >= 10:
            result.append(p)
    return result


def _parse_filter_response(response: str) -> list[AnnotatedParagraph]:
    """解析 LLM 返回的事前过滤 JSON 响应"""
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


def _parse_segment_analysis(response: str, batch: list) -> list[SegmentAnalysis]:
    """解析 LLM 返回的事后分析 JSON 响应

    边界处理：
    - JSON 解析失败 → 返回空列表（调用方负责兜底）
    - LLM 返回缺项 → 按原始段顺序补全为 actual_duplication
    - segment_id 不匹配 → 按索引位置匹配
    """
    json_match = re.search(r'\[[\s\S]*\]', response)
    if not json_match:
        return []

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list) or not data:
        return []

    result = []
    parsed_map: dict[int, dict] = {}
    for item in data:
        if isinstance(item, dict):
            seg_id = item.get('segment_id', -1)
            parsed_map[seg_id] = item

    for idx, seg in enumerate(batch):
        seg_id = seg.get('id', idx)
        item = parsed_map.get(seg_id) or parsed_map.get(idx) or (data[idx] if idx < len(data) and isinstance(data[idx], dict) else None)

        if item:
            classification = item.get('classification', 'actual_duplication')
            if classification not in ('compliance_response', 'actual_duplication'):
                classification = 'actual_duplication'
            result.append(SegmentAnalysis(
                segment_id=seg_id,
                tender_text=seg.get('tender_text', ''),
                bid_text=seg.get('bid_text', ''),
                similarity=seg.get('similarity', 0),
                classification=classification,
                reason=item.get('reason', ''),
                adjusted_similarity=item.get('adjusted_similarity', 0),
            ))
        else:
            result.append(SegmentAnalysis(
                segment_id=seg_id,
                tender_text=seg.get('tender_text', ''),
                bid_text=seg.get('bid_text', ''),
                similarity=seg.get('similarity', 0),
                classification='actual_duplication',
                reason='LLM 未返回该段分析，保守标记为实际重复',
                adjusted_similarity=seg.get('similarity', 0),
            ))
    return result
