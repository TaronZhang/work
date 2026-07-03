"""文档拆分引擎 — 大文件按章节/页码/等长策略自动切分"""

import re
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class SplitConfig:
    """拆分配置"""
    max_chars_per_chunk: int = 50000      # 每片最大字符数
    overlap_chars: int = 5000             # 片间重叠字符数
    min_chunk_chars: int = 500            # 最小片字符数（小于此值合并到相邻片）
    max_workers: int = 4                  # 并发比对线程数


@dataclass
class ChunkDoc:
    """文档分片"""
    chunk_id: int
    text: str
    char_start: int         # 原文中起始字符位置
    char_end: int           # 原文中结束字符位置
    page_start: int = 1     # 起始页码
    page_end: int = 1       # 结束页码
    heading: str = ''       # 所属章节标题（如有）
    metadata: dict = field(default_factory=dict)


def split_document(
    text: str,
    paragraphs: list = None,
    config: SplitConfig = None,
    page_count: int = 1,
) -> list[ChunkDoc]:
    """将文档文本拆分为多个分片

    拆分策略（按优先级）：
    1. 如果提供了 paragraphs 且有 Heading 信息 → 章节拆分
    2. 如果 page_count > 1 → 页码拆分
    3. 其他情况 → 等长拆分
    """
    if config is None:
        config = SplitConfig()

    if not text or len(text) < config.max_chars_per_chunk:
        # 文本小于一个分片，不分
        return [
            ChunkDoc(
                chunk_id=0,
                text=text,
                char_start=0,
                char_end=len(text),
                page_start=1,
                page_end=page_count,
            )
        ]

    # 尝试章节拆分
    if paragraphs:
        chunks = _split_by_headings(paragraphs, text, config, page_count)
        if len(chunks) > 1:
            return chunks

    # 尝试页码拆分
    if page_count > 1:
        chunks = _split_by_pages(text, page_count, config)
        if len(chunks) > 1:
            return chunks

    # 等长拆分
    return _split_by_length(text, config)


def _split_by_headings(paragraphs: list, full_text: str, config: SplitConfig, page_count: int) -> list[ChunkDoc]:
    """沿章节标题边界拆分"""
    heading_indices = []
    for i, p in enumerate(paragraphs):
        style = getattr(p, 'style', '') or ''
        if 'Heading1' in style or 'heading 1' in style.lower() or '标题1' in style or '标题 1' in style:
            heading_indices.append(i)

    if len(heading_indices) <= 1:
        return []  # 不够拆

    chunks = []
    for hi, heading_idx in enumerate(heading_indices):
        start_idx = heading_idx
        end_idx = heading_indices[hi + 1] if hi + 1 < len(heading_indices) else len(paragraphs)

        # 收集段落文本
        section_paras = paragraphs[start_idx:end_idx]
        section_text = '\n'.join(p.text for p in section_paras)

        # 如果此节太大，递归等长拆分
        if len(section_text) > config.max_chars_per_chunk:
            sub_chunks = _split_by_length(section_text, config, chunk_id_offset=len(chunks))
            for sc in sub_chunks:
                if paragraphs[start_idx].page:
                    sc.page_start = paragraphs[start_idx].page or 1
            chunks.extend(sub_chunks)
        else:
            # 找到原文中的位置
            heading_text = paragraphs[start_idx].text if start_idx < len(paragraphs) else ''
            char_start = full_text.find(section_text) if full_text else 0
            if char_start == -1:
                char_start = 0

            chunks.append(ChunkDoc(
                chunk_id=len(chunks),
                text=section_text,
                char_start=char_start,
                char_end=char_start + len(section_text),
                page_start=paragraphs[start_idx].page or 1 if paragraphs[start_idx].page else 1,
                page_end=paragraphs[end_idx - 1].page or page_count if end_idx > 0 else page_count,
                heading=heading_text[:100],
            ))

    # 添加重叠：每个 chunk 的末尾 overlap_chars 复制到下一个 chunk 的开头
    return _add_overlap(chunks, config)


def _split_by_pages(text: str, page_count: int, config: SplitConfig) -> list[ChunkDoc]:
    """按页码均匀拆分"""
    chars_per_page = len(text) / max(page_count, 1)
    pages_per_chunk = max(1, config.max_chars_per_chunk / max(chars_per_page, 1))
    pages_per_chunk = int(pages_per_chunk)

    if pages_per_chunk >= page_count:
        return []  # 不够拆

    chunks = []
    pos = 0
    chunk_id = 0

    for page_group_start in range(1, page_count + 1, pages_per_chunk):
        page_group_end = min(page_group_start + pages_per_chunk - 1, page_count)
        # 估算该页组的字符范围
        start_pos = int((page_group_start - 1) * chars_per_page)
        end_pos = int(min(page_group_end * chars_per_page, len(text)))

        chunk_text = text[max(0, start_pos):min(end_pos, len(text))]
        if len(chunk_text.strip()) >= config.min_chunk_chars:
            chunks.append(ChunkDoc(
                chunk_id=chunk_id,
                text=chunk_text,
                char_start=start_pos,
                char_end=end_pos,
                page_start=page_group_start,
                page_end=page_group_end,
            ))
            chunk_id += 1

    return _add_overlap(chunks, config)


def _split_by_length(text: str, config: SplitConfig, chunk_id_offset: int = 0) -> list[ChunkDoc]:
    """等长切分，带重叠"""
    chunks = []
    step = config.max_chars_per_chunk - config.overlap_chars
    if step <= 0:
        step = config.max_chars_per_chunk

    pos = 0
    chunk_id = chunk_id_offset
    while pos < len(text):
        end = min(pos + config.max_chars_per_chunk, len(text))
        chunk_text = text[pos:end]

        # 尝试在段落边界切分（找最近的换行）
        if end < len(text):
            last_nl = chunk_text.rfind('\n', len(chunk_text) - 200)
            if last_nl > len(chunk_text) // 2:
                end = pos + last_nl
                chunk_text = text[pos:end]

        if len(chunk_text.strip()) >= config.min_chunk_chars:
            chunks.append(ChunkDoc(
                chunk_id=chunk_id,
                text=chunk_text,
                char_start=pos,
                char_end=end,
            ))
            chunk_id += 1

        pos += step

    return chunks


def _add_overlap(chunks: list[ChunkDoc], config: SplitConfig) -> list[ChunkDoc]:
    """为相邻分片添加重叠区域"""
    if len(chunks) <= 1:
        return chunks

    for i in range(1, len(chunks)):
        prev_tail = chunks[i - 1].text[-config.overlap_chars:]
        chunks[i].text = prev_tail + '\n' + chunks[i].text
        chunks[i].char_start = max(0, chunks[i].char_start - config.overlap_chars)

    return chunks


def merge_chunk_results(all_chunk_results: list[list]) -> list:
    """合并多个分片的比对结果，去重重叠区域的匹配"""
    if not all_chunk_results:
        return []

    # 展平所有分片的 segments
    all_segments = []
    for chunk_results in all_chunk_results:
        if isinstance(chunk_results, list):
            all_segments.extend(chunk_results)
        elif hasattr(chunk_results, 'matched_segments'):
            all_segments.extend(chunk_results.matched_segments)

    if not all_segments:
        return []

    # 按位置排序并去重
    sorted_segs = sorted(all_segments, key=lambda s: (
        getattr(s, 'bid_start', 0) if hasattr(s, 'bid_start') else 0
    ))

    deduped = []
    for seg in sorted_segs:
        if not deduped:
            deduped.append(seg)
            continue

        prev = deduped[-1]
        prev_start = getattr(prev, 'bid_start', 0) if hasattr(prev, 'bid_start') else 0
        prev_end = getattr(prev, 'bid_end', 0) if hasattr(prev, 'bid_end') else 0
        curr_start = getattr(seg, 'bid_start', 0) if hasattr(seg, 'bid_start') else 0
        curr_end = getattr(seg, 'bid_end', 0) if hasattr(seg, 'bid_end') else 0

        # 检查重叠
        overlap = max(0, prev_end - curr_start)
        if overlap > 0:
            sim_prev = getattr(prev, 'similarity', 0) if hasattr(prev, 'similarity') else 0
            sim_curr = getattr(seg, 'similarity', 0) if hasattr(seg, 'similarity') else 0
            if sim_curr > sim_prev:
                deduped[-1] = seg  # 保留相似度更高的
        else:
            deduped.append(seg)

    return deduped
