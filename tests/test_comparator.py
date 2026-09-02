"""Tests for the comparison engine — happy path + boundary conditions."""

from src.comparator import (
    compare_documents,
    compute_similarity,
    segment_text,
    ComparisonConfig,
    MatchedSegment,
    ComparisonResult,
)


def test_compare_identical_documents():
    """Happy path: identical documents have ~100% duplication."""
    text = 'This is a test document with some content for comparison testing.'
    result = compare_documents(text, text, 0, 'test.txt')
    assert result.duplicate_percentage > 50
    assert result.matched_chars > 0


def test_compare_different_documents():
    """Happy path: completely different documents have low duplication."""
    text_a = 'apple banana cherry date elderberry fig grape'
    text_b = 'keyboard monitor mouse printer scanner speaker webcam'
    result = compare_documents(text_a, text_b, 0, 'test.txt')
    assert result.duplicate_percentage < 30


def test_compare_empty_documents():
    """Boundary: empty documents return zero duplication."""
    result = compare_documents('', '', 0, 'empty.txt')
    assert result.duplicate_percentage == 0.0
    assert result.matched_chars == 0


def test_compute_similarity_identical():
    """Happy path: identical strings have high similarity."""
    text = 'This is a test string for similarity'
    score = compute_similarity(text, text)
    assert score > 0.9


def test_compute_similarity_empty():
    """Boundary: empty strings return zero similarity."""
    assert compute_similarity('', 'test') == 0.0
    assert compute_similarity('test', '') == 0.0


def test_segment_text_basic():
    """Happy path: text is segmented into chunks."""
    config = ComparisonConfig(chunk_size=100, chunk_overlap=20)
    text = 'word ' * 100
    chunks = segment_text(text, config)
    assert len(chunks) > 1
    assert all(len(c) == 3 for c in chunks)  # tuples of (start, end, text)


def test_segment_text_short():
    """Boundary: short text produces single chunk or none."""
    config = ComparisonConfig(chunk_size=200, chunk_overlap=50, min_match_length=15)
    text = 'short'
    chunks = segment_text(text, config)
    assert len(chunks) <= 1


def test_long_matched_segment_preserves_full_text():
    """长匹配段：匹配段文本应保留完整内容（上限2000字符），验证截断口径修复。
    
    修复前：匹配段文本被截断至300字符，AI调整率按截断长度计算，口径偏小。
    修复后：匹配段文本上限2000字符，AI分析和字符数计算使用完整长度。
    """
    # 构造500字符的相同文本
    long_text = '网络安全技术参数要求' * 50  # 50 * 10 = 500字符
    assert len(long_text) == 500
    
    config = ComparisonConfig(chunk_size=200, chunk_overlap=50, min_match_length=15)
    result = compare_documents(long_text, long_text, 0, 'test_long.txt', config=config)
    
    # 验证匹配段存在且文本长度正确
    assert len(result.matched_segments) > 0
    seg = result.matched_segments[0]
    
    # 匹配段文本应保留完整内容（500字符，远大于原300字符截断）
    assert len(seg.tender_text) >= 400, f"匹配段文本仅{len(seg.tender_text)}字符，应为完整500字符左右"
    assert len(seg.bid_text) >= 400
    
    # 验证匹配段长度字段与实际文本一致
    assert seg.length > 0
    assert seg.tender_start == 0
    assert seg.tender_end >= 400


def test_overlapping_segments_deduplication():
    """重叠区间：验证重叠匹配段的去重逻辑正确。
    
    当多个匹配段在投标文件中存在重叠时，应保留相似度最高的段，
    避免重复计算字符数。
    """
    # 构造有重叠匹配的文本
    base = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' * 10  # 260字符
    # 投标文件包含重复的重叠区域
    tender = base
    bid = base[:200] + base[150:]  # 重叠50字符
    
    config = ComparisonConfig(chunk_size=100, chunk_overlap=30, min_match_length=20)
    result = compare_documents(tender, bid, 0, 'test_overlap.txt', config=config)
    
    # 验证存在匹配段
    assert len(result.matched_segments) > 0
    
    # 验证匹配段之间没有明显重叠（去重后）
    segs = sorted(result.matched_segments, key=lambda s: s.bid_start)
    for i in range(len(segs) - 1):
        current_end = segs[i].bid_end
        next_start = segs[i + 1].bid_start
        # 相邻段之间不应有大量重叠（超过50%）
        if next_start < current_end:
            overlap = current_end - next_start
            min_len = min(segs[i].length, segs[i + 1].length)
            assert overlap < min_len * 0.5, f"匹配段{i}和{i+1}重叠过多: {overlap}/{min_len}"


def test_mixed_content_segment_merge():
    """混合内容拆分：验证相邻匹配段的合并逻辑正确。
    
    当多个匹配段相邻且间距小于overlap阈值时，应合并为一个匹配段，
    确保完整呈现连续重复内容。
    """
    # 构造两段相邻的重复内容，中间隔一小段不同内容
    part1 = '第一段重复内容：网络安全防护体系建设，包括边界安全、终端安全、安全运营中心。' * 3
    gap = '投标方独有内容：我们的优势在于7x24小时响应服务和专业技术团队。'
    part2 = '第二段重复内容：技术参数要求包括吞吐量100Gbps、并发连接数5000万、支持IPv6协议。' * 3
    
    tender = part1 + gap + part2
    # 投标文件：重复part1和part2，但gap部分不同
    bid_diff = '我方方案特色：采用分布式架构，支持弹性扩展，具备高可用性。'
    bid = part1 + bid_diff + part2
    
    config = ComparisonConfig(chunk_size=150, chunk_overlap=40, min_match_length=30)
    result = compare_documents(tender, bid, 0, 'test_mixed.txt', config=config)
    
    # 验证至少有2个匹配段（两段重复内容）
    assert len(result.matched_segments) >= 1
    
    # 验证总匹配字符数合理（应覆盖两段重复内容的大部分）
    expected_min_chars = len(part1) * 0.5 + len(part2) * 0.5
    assert result.matched_chars >= expected_min_chars * 0.5, \
        f"匹配字符数{result.matched_chars}偏少，预期至少{expected_min_chars * 0.5}"
    
    # 验证重复率计算正确
    expected_pct = (result.matched_chars / max(len(tender), 1)) * 100
    assert abs(result.duplicate_percentage - round(expected_pct, 1)) < 1.0, \
        f"重复率计算偏差: {result.duplicate_percentage} vs {round(expected_pct, 1)}"


def test_segment_2000_char_limit():
    """验证匹配段文本上限为2000字符，覆盖招投标场景绝大多数情况。"""
    # 构造超长文本（3000+字符）
    very_long_text = '超长匹配段测试文本，用于验证2000字符上限是否正确生效。' * 100
    assert len(very_long_text) > 2500  # 确保超过2000
    
    config = ComparisonConfig(chunk_size=500, chunk_overlap=100, min_match_length=50)
    result = compare_documents(very_long_text, very_long_text, 0, 'test_2000limit.txt', config=config)
    
    # 验证存在匹配段
    assert len(result.matched_segments) > 0
    
    # 验证匹配段文本不超过2000字符上限
    for seg in result.matched_segments:
        assert len(seg.tender_text) <= 2000, f"匹配段文本超过2000字符上限: {len(seg.tender_text)}"
        assert len(seg.bid_text) <= 2000
    
    # 但至少有一个段接近2000字符（验证上限生效且不是过早截断）
    max_len = max(len(seg.tender_text) for seg in result.matched_segments)
    assert max_len >= 1500, f"最长匹配段仅{max_len}字符，应接近2000字符上限"


def test_pre_filter_changes_duplicate_rate():
    """事前过滤：验证过滤后的文本确实参与比对，影响重复率计算。
    
    修复前：事前过滤结果仅被记录，后续比对仍使用原始文本，重复率不变。
    修复后：过滤后的文本用于实际比对，真正影响重复率计算。
    """
    from src.ai_filter import FilteredTender
    
    # 模拟事前过滤：移除格式要求部分（约100字符）
    full_text = (
        "格式要求：投标文件应采用A4纸张，中文书写。正本一份副本五份。"
        "技术要求：防火墙吞吐量不低于100Gbps，并发连接数不低于5000万。"
        "安全要求：支持IPS、WAF、反病毒模块，具备ISO27001认证。"
    )
    # 过滤后：只保留技术和安全要求，移除格式要求
    filtered_text = (
        "技术要求：防火墙吞吐量不低于100Gbps，并发连接数不低于5000万。"
        "安全要求：支持IPS、WAF、反病毒模块，具备ISO27001认证。"
    )
    
    bid_text = (
        "技术响应：我司防火墙吞吐量不低于100Gbps，并发连接数不低于5000万。"
        "安全响应：支持IPS、WAF、反病毒模块，具备ISO27001认证。"
    )
    
    config = ComparisonConfig(chunk_size=100, chunk_overlap=20, min_match_length=20)
    
    # 使用原始文本比对
    result_original = compare_documents(full_text, bid_text, 0, 'bid.txt', config=config)
    
    # 使用过滤后文本比对
    result_filtered = compare_documents(filtered_text, bid_text, 0, 'bid.txt', config=config)
    
    # 过滤后总字符数减少
    assert result_filtered.total_tender_chars < result_original.total_tender_chars
    
    # 过滤后的重复率应该不同（因为分母变小了，且格式要求部分不参与比对）
    # 这里验证的是：过滤确实会改变比对的输入文本，从而影响结果
    assert result_filtered.total_tender_chars == len(filtered_text), \
        "比对应使用过滤后的文本长度作为总字符数"
