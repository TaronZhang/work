"""文本比对模块 — jieba 分词 + 字符级 LCS 混合 + 分片并发比对"""

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable


@dataclass
class MatchedSegment:
    """匹配段落"""
    segment_id: int
    tender_text: str
    bid_text: str
    similarity: float
    tender_start: int   # 招标文件中起始字符位置
    tender_end: int
    bid_start: int      # 投标文件中起始字符位置
    bid_end: int
    length: int         # 匹配字符数


@dataclass
class ComparisonResult:
    """单份投标文件的比对结果"""
    bid_index: int
    bid_filename: str
    total_tender_chars: int
    total_bid_chars: int
    matched_chars: int
    duplicate_percentage: float
    matched_segments: list[MatchedSegment] = field(default_factory=list)
    metric: str = 'bid_vs_tender'


@dataclass
class ComparisonConfig:
    """比对配置"""
    chunk_size: int = 200
    chunk_overlap: int = 50
    min_match_length: int = 15
    similarity_threshold: float = 0.75
    use_jieba: bool = True
    max_workers: int = 4           # 并发线程数


def compare_documents(
    tender_text: str,
    bid_text: str,
    bid_index: int,
    bid_filename: str,
    config: ComparisonConfig = None,
    progress_callback: Callable = None,
) -> ComparisonResult:
    """对比招标文件和一份投标文件"""
    if config is None:
        config = ComparisonConfig()

    # 分块
    tender_chunks = segment_text(tender_text, config)
    bid_chunks = segment_text(bid_text, config)

    # 查找匹配段落
    matches = find_matches(
        bid_chunks, tender_chunks, bid_text, tender_text, config,
        progress_callback=progress_callback,
    )

    # 计算重复字符数
    matched_chars = sum(m.length for m in matches)
    dup_pct = (matched_chars / max(len(tender_text), 1)) * 100
    dup_pct = round(dup_pct, 1)

    return ComparisonResult(
        bid_index=bid_index,
        bid_filename=bid_filename,
        total_tender_chars=len(tender_text),
        total_bid_chars=len(bid_text),
        matched_chars=matched_chars,
        duplicate_percentage=dup_pct,
        matched_segments=matches,
        metric='bid_matched_vs_tender_total',
    )


def compare_documents_chunked(
    tender_chunks: list,
    bid_chunks: list,
    tender_text: str,
    bid_text: str,
    bid_index: int,
    bid_filename: str,
    config: ComparisonConfig = None,
    progress_callback: Callable = None,
) -> ComparisonResult:
    """分片级比对 — 将招标和投标均拆分为分片，分别比对后合并

    tender_chunks: list[ChunkDoc]
    bid_chunks: list[ChunkDoc]
    """
    if config is None:
        config = ComparisonConfig()

    total_pairs = len(tender_chunks) * len(bid_chunks)
    completed_pairs = 0
    all_segments = []

    # 使用线程池并发比对分片对
    with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        futures = {}
        for tc in tender_chunks:
            for bc in bid_chunks:
                future = executor.submit(
                    _process_chunk_pair, tc, bc, config
                )
                futures[future] = (tc.chunk_id, bc.chunk_id)

        for future in as_completed(futures):
            tc_id, bc_id = futures[future]
            try:
                pair_segments = future.result(timeout=300)
                if pair_segments:
                    all_segments.extend(pair_segments)
            except Exception:
                pass
            completed_pairs += 1
            if progress_callback:
                progress_callback(completed_pairs, total_pairs)

    # 合并去重
    all_segments.sort(key=lambda s: s.similarity, reverse=True)
    deduped = _deduplicate_segments(all_segments)

    matched_chars = sum(s.length for s in deduped)
    dup_pct = (matched_chars / max(len(tender_text), 1)) * 100
    dup_pct = round(dup_pct, 1)

    return ComparisonResult(
        bid_index=bid_index,
        bid_filename=bid_filename,
        total_tender_chars=len(tender_text),
        total_bid_chars=len(bid_text),
        matched_chars=matched_chars,
        duplicate_percentage=dup_pct,
        matched_segments=deduped[:50],  # top 50
        metric='bid_matched_vs_tender_total',
    )


def _process_chunk_pair(tender_chunk, bid_chunk, config: ComparisonConfig) -> list[MatchedSegment]:
    """处理单个分片对"""
    tender_parts = segment_text(tender_chunk.text, config)
    bid_parts = segment_text(bid_chunk.text, config)
    return find_matches(
        bid_parts, tender_parts,
        bid_chunk.text, tender_chunk.text,
        config,
        offset_bid=bid_chunk.char_start,
        offset_tender=tender_chunk.char_start,
    )


def _deduplicate_segments(segments: list[MatchedSegment]) -> list[MatchedSegment]:
    """去重重叠的匹配段"""
    if not segments:
        return []
    sorted_segs = sorted(segments, key=lambda s: (s.bid_start, -s.similarity))
    result = []
    for seg in sorted_segs:
        is_dup = False
        for existing in result:
            overlap_start = max(seg.bid_start, existing.bid_start)
            overlap_end = min(seg.bid_end, existing.bid_end)
            if overlap_end > overlap_start:
                overlap_len = overlap_end - overlap_start
                seg_len = seg.bid_end - seg.bid_start
                if overlap_len > seg_len * 0.5:
                    is_dup = True
                    break
        if not is_dup:
            result.append(seg)
    return result


def segment_text(text: str, config: ComparisonConfig) -> list[tuple[int, int, str]]:
    """将文本切分为滑动窗口块"""
    chunks = []
    step = config.chunk_size - config.chunk_overlap
    if step <= 0:
        step = config.chunk_size

    pos = 0
    while pos < len(text):
        end = min(pos + config.chunk_size, len(text))
        chunk = text[pos:end]
        if len(chunk.strip()) >= config.min_match_length:
            chunks.append((pos, end, chunk))
        pos += step

    return chunks


def compute_similarity(a: str, b: str, config: ComparisonConfig = None) -> float:
    """计算两段文本的相似度 (0-1)"""
    if config is None:
        config = ComparisonConfig()

    if not a or not b:
        return 0.0

    la, lb = len(a), len(b)
    if abs(la - lb) / max(la, lb) > 0.5 and (la < 30 or lb < 30):
        return 0.0

    word_ratio = 0.0
    char_ratio = 0.0

    if config.use_jieba:
        try:
            import jieba
            words_a = jieba.lcut(a)
            words_b = jieba.lcut(b)
            if words_a and words_b:
                sm = SequenceMatcher(None, words_a, words_b)
                word_ratio = sm.ratio()
        except Exception:
            word_ratio = 0.0

    sm = SequenceMatcher(None, a, b)
    char_ratio = sm.ratio()

    if config.use_jieba:
        return word_ratio * 0.6 + char_ratio * 0.4
    else:
        return char_ratio


def find_matches(
    bid_chunks: list[tuple[int, int, str]],
    tender_chunks: list[tuple[int, int, str]],
    bid_text: str = '',
    tender_text: str = '',
    config: ComparisonConfig = None,
    offset_bid: int = 0,
    offset_tender: int = 0,
    progress_callback: Callable = None,
) -> list[MatchedSegment]:
    """查找投标文件中与招标文件匹配的段落"""
    if config is None:
        config = ComparisonConfig()

    raw_matches = []
    total_comparisons = len(bid_chunks) * len(tender_chunks)
    done = 0

    for b_start, b_end, b_chunk in bid_chunks:
        best_score = 0.0
        best_t_start, best_t_end = 0, 0
        best_t_chunk = ''

        for t_start, t_end, t_chunk in tender_chunks:
            la, lb = len(b_chunk), len(t_chunk)
            if abs(la - lb) / max(la, lb) > 0.5:
                continue

            score = compute_similarity(b_chunk, t_chunk, config)
            if score > best_score:
                best_score = score
                best_t_start, best_t_end = t_start, t_end
                best_t_chunk = t_chunk

            done += 1

        if best_score >= config.similarity_threshold:
            raw_matches.append({
                'bid_start': b_start + offset_bid,
                'bid_end': b_end + offset_bid,
                'tender_start': best_t_start + offset_tender,
                'tender_end': best_t_end + offset_tender,
                'score': best_score,
                'bid_text': b_chunk,
                'tender_text': best_t_chunk,
            })

    merged = _merge_segments(raw_matches, config)

    result = []
    for i, m in enumerate(merged):
        # 存储完整匹配段文本，上限 2000 字符（覆盖绝大多数招投标场景）
        # AI 分析和字符数计算均使用完整文本长度，确保口径一致
        seg = MatchedSegment(
            segment_id=i,
            tender_text=m['tender_text'][:2000],
            bid_text=m['bid_text'][:2000],
            similarity=round(m['score'], 2),
            tender_start=m['tender_start'],
            tender_end=m['tender_end'],
            bid_start=m['bid_start'],
            bid_end=m['bid_end'],
            length=m['bid_end'] - m['bid_start'],
        )
        result.append(seg)

    result.sort(key=lambda s: s.similarity, reverse=True)
    return result[:50]


def _merge_segments(raw_matches: list[dict], config: ComparisonConfig) -> list[dict]:
    """合并相邻且重叠的匹配段"""
    if not raw_matches:
        return []

    sorted_matches = sorted(raw_matches, key=lambda m: m['bid_start'])
    merged = []
    current = dict(sorted_matches[0])

    for next_m in sorted_matches[1:]:
        gap = next_m['bid_start'] - current['bid_end']
        overlap_tolerance = config.chunk_overlap

        if gap <= overlap_tolerance:
            current['bid_end'] = max(current['bid_end'], next_m['bid_end'])
            current['tender_end'] = max(current['tender_end'], next_m['tender_end'])
            current['score'] = max(current['score'], next_m['score'])
            current['bid_text'] = current['bid_text'] + next_m['bid_text']
            current['tender_text'] = current['tender_text'] + next_m['tender_text']
        else:
            seg_len = current['bid_end'] - current['bid_start']
            if seg_len >= config.min_match_length:
                merged.append(current)
            current = dict(next_m)

    seg_len = current['bid_end'] - current['bid_start']
    if seg_len >= config.min_match_length:
        merged.append(current)

    return merged
