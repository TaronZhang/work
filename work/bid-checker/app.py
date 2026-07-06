"""文档重复度比对工具 — Flask 主应用 (v3 — 灵活文档比对)"""

import os
import json
import threading
import time
from flask import Flask, render_template, request, jsonify

from src.utils import (
    allowed_file,
    generate_file_id,
    validate_file_size,
    format_percentage,
    severity_label,
)
from src.parser import parse_file
from src.comparator import (
    compare_documents,
    compare_documents_chunked,
    ComparisonConfig,
    ComparisonResult,
    MatchedSegment,
)
from src.splitter import split_document, SplitConfig, ChunkDoc, merge_chunk_results
from src.ai_filter import filter_tender_requirements


app = Flask(__name__)

# 配置
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

AUTO_SPLIT_THRESHOLD = 10 * 1024 * 1024  # 10MB 自动触发拆分

# 内存存储 — v3: content 仅在小文件存储，大文件从磁盘懒加载
_file_store: dict[str, dict] = {}
_parsed_cache: dict[str, str] = {}     # file_id -> text (parsed content on disk)
_job_store: dict[str, dict] = {}       # job_id -> progress info


def _ensure_upload_folder():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def _get_text(file_id: str) -> str:
    """获取文件文本内容（懒加载/缓存读取）"""
    entry = _file_store.get(file_id, {})
    if entry.get('content'):
        return entry['content']
    if file_id in _parsed_cache:
        return _parsed_cache[file_id]
    # 从磁盘重新解析
    path = entry.get('path', '')
    if path and os.path.exists(path):
        parsed = parse_file(path, entry.get('filename', ''))
        text = parsed.full_text
        _parsed_cache[file_id] = text
        return text
    return ''


def _should_split(file_id: str) -> bool:
    """判断文件是否需要拆分"""
    entry = _file_store.get(file_id, {})
    size = entry.get('size_bytes', 0)
    chars = entry.get('chars', 0)
    return size > AUTO_SPLIT_THRESHOLD or chars > 100000


def _should_split_from_size(file_size: int, chars: int) -> bool:
    return file_size > AUTO_SPLIT_THRESHOLD or chars > 100000


# ── Routes ─────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload():
    """上传文件 (v3: 支持自定义 label 和 doc_type)"""
    _ensure_upload_folder()

    if 'file' not in request.files:
        return jsonify({'error': True, 'code': 'NO_FILE', 'message': '请选择文件'}), 400

    file = request.files['file']
    doc_type = request.form.get('doc_type', 'document')  # tender / bid / document
    label = request.form.get('label', '')                # 自定义标签

    if not file.filename:
        return jsonify({'error': True, 'code': 'EMPTY_FILENAME', 'message': '文件名为空'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': True, 'code': 'INVALID_FORMAT', 'message': '不支持的文件格式。支持的格式: .docx, .pdf, .txt'}), 400

    file_id = generate_file_id(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file_id)
    file.save(filepath)

    file_size = os.path.getsize(filepath)
    if file_size > app.config['MAX_CONTENT_LENGTH']:
        os.remove(filepath)
        return jsonify({'error': True, 'code': 'FILE_TOO_LARGE', 'message': '文件大小超过 500MB 限制'}), 413

    # 解析文档
    content = ''
    parse_status = 'parsed'
    chars = 0
    try:
        parsed = parse_file(filepath, file.filename)
        chars = len(parsed.full_text)
        if not _should_split_from_size(file_size, chars):
            content = parsed.full_text
        else:
            # 大文件：写入磁盘缓存，不存内存
            _parsed_cache[file_id] = parsed.full_text
            parse_status = 'parsed_large'
    except Exception as e:
        parse_status = 'error'
        app.logger.error(f'解析失败 {file.filename}: {e}')

    needs_split = _should_split_from_size(file_size, chars)

    # 自动生成标签
    if not label:
        label = file.filename

    entry = {
        'id': file_id,
        'filename': file.filename,
        'doc_type': doc_type,
        'label': label,
        'path': filepath,
        'content': content,
        'chars': chars,
        'size_bytes': file_size,
        'status': parse_status,
        'needs_split': needs_split,
    }
    _file_store[file_id] = entry

    return jsonify({
        'file_id': file_id,
        'filename': file.filename,
        'doc_type': doc_type,
        'label': entry['label'],
        'size_bytes': file_size,
        'size_mb': round(file_size / (1024 * 1024), 2),
        'chars': chars,
        'status': parse_status,
        'needs_split': needs_split,
    }), 201


@app.route('/api/comparison', methods=['POST'])
def run_comparison():
    """文档比对 (v3: 支持双向/多文档比对)

    支持三种请求格式：
    1. 双向比对: {"doc_a_id": "...", "doc_b_id": "..."}
    2. 多文档互比: {"doc_ids": ["id1", "id2", ...]}
    3. 一对多 (兼容): {"tender_id": "...", "bid_ids": ["..."]}
    """
    data = request.get_json() or {}
    chunk_size = data.get('chunk_size', 200)
    threshold = data.get('threshold', 0.75)
    config = ComparisonConfig(chunk_size=chunk_size, similarity_threshold=threshold)

    # 解析比对对
    pairs = _resolve_comparison_pairs(data)
    if not pairs:
        return jsonify({'error': True, 'code': 'INVALID_REQUEST', 'message': '请至少提供两个文档进行比对'}), 400

    results = []
    for doc_a_id, doc_b_id, label_a, label_b in pairs:
        if doc_a_id not in _file_store or doc_b_id not in _file_store:
            continue

        doc_a_text = _get_text(doc_a_id)
        doc_b_text = _get_text(doc_b_id)
        if not doc_a_text or not doc_b_text:
            continue

        doc_a_entry = _file_store[doc_a_id]
        doc_b_entry = _file_store[doc_b_id]

        use_chunked = (
            doc_a_entry.get('needs_split') or
            doc_b_entry.get('needs_split')
        )

        if use_chunked:
            result = _run_chunked_comparison(doc_a_id, doc_b_id, 0, doc_b_entry['label'], config)
        else:
            result = compare_documents(
                tender_text=doc_a_text,
                bid_text=doc_b_text,
                bid_index=0,
                bid_filename=doc_b_entry['label'],
                config=config,
            )

        severity = severity_label(result.duplicate_percentage)
        results.append(_format_pair_result(
            result, doc_a_id, doc_b_id, label_a, label_b, severity
        ))

        # 释放大文件缓存
        if doc_a_entry.get('needs_split'):
            _parsed_cache.pop(doc_a_id, None)
        if doc_b_entry.get('needs_split'):
            _parsed_cache.pop(doc_b_id, None)

    results.sort(key=lambda r: r['duplicate_percentage'], reverse=True)
    return jsonify({
        'mode': 'fast',
        'results': results,
        'pair_count': len(results),
    })


def _resolve_comparison_pairs(data: dict) -> list[tuple]:
    """解析请求数据，生成比对对列表

    返回: [(doc_a_id, doc_b_id, label_a, label_b), ...]
    """
    # 格式 1: 双向比对
    if data.get('doc_a_id') and data.get('doc_b_id'):
        a_entry = _file_store.get(data['doc_a_id'], {})
        b_entry = _file_store.get(data['doc_b_id'], {})
        return [(
            data['doc_a_id'],
            data['doc_b_id'],
            a_entry.get('label', '文档 A'),
            b_entry.get('label', '文档 B'),
        )]

    # 格式 2: 多文档互比 (所有 pair)
    doc_ids = data.get('doc_ids', [])
    if doc_ids and len(doc_ids) >= 2:
        pairs = []
        for i in range(len(doc_ids)):
            for j in range(i + 1, len(doc_ids)):
                a_entry = _file_store.get(doc_ids[i], {})
                b_entry = _file_store.get(doc_ids[j], {})
                if a_entry and b_entry:
                    pairs.append((
                        doc_ids[i],
                        doc_ids[j],
                        a_entry.get('label', f'文档 {i + 1}'),
                        b_entry.get('label', f'文档 {j + 1}'),
                    ))
        return pairs

    # 格式 3: 一对多 (兼容旧版)
    tender_id = data.get('tender_id', '')
    bid_ids = data.get('bid_ids', [])
    if tender_id and bid_ids:
        tender_entry = _file_store.get(tender_id, {})
        pairs = []
        for bid_id in bid_ids:
            bid_entry = _file_store.get(bid_id, {})
            if bid_entry:
                pairs.append((
                    tender_id,
                    bid_id,
                    tender_entry.get('label', '招标文件'),
                    bid_entry.get('label', '投标文件'),
                ))
        return pairs

    return []


@app.route('/api/comparison/ai', methods=['POST'])
def run_ai_comparison():
    """AI 辅助模式比对 (v3: 支持双向/多文档比对)"""
    data = request.get_json() or {}
    api_key = data.get('api_key', '')
    base_url = data.get('base_url', 'https://api.openai.com/v1')
    model = data.get('model', 'gpt-4o')

    if not api_key:
        return jsonify({'error': True, 'code': 'NO_API_KEY', 'message': '请输入 API Key'}), 400

    # 解析比对对
    pairs = _resolve_comparison_pairs(data)
    if not pairs:
        return jsonify({'error': True, 'code': 'INVALID_REQUEST', 'message': '请至少提供两个文档进行比对'}), 400

    # AI 过滤 — 对每对中的第一个文档 (参考文档) 进行过滤
    # 取第一个参考文档进行过滤
    ref_doc_id = pairs[0][0]
    tender_text = _get_text(ref_doc_id)
    if not tender_text:
        return jsonify({'error': True, 'code': 'EMPTY_CONTENT', 'message': '参考文档内容为空'}), 400

    try:
        filtered = filter_tender_requirements(
            tender_text=tender_text,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
    except Exception as e:
        return jsonify({'error': True, 'code': 'AI_API_ERROR', 'message': f'AI API 调用失败: {str(e)}'}), 502

    filtered_text = filtered.filtered_text or tender_text
    config = ComparisonConfig(similarity_threshold=0.75)
    results = []

    for doc_a_id, doc_b_id, label_a, label_b in pairs:
        if doc_a_id not in _file_store or doc_b_id not in _file_store:
            continue

        doc_b_text = _get_text(doc_b_id)
        if not doc_b_text:
            continue

        doc_a_entry = _file_store[doc_a_id]
        doc_b_entry = _file_store[doc_b_id]

        use_chunked = (
            doc_a_entry.get('needs_split') or
            doc_b_entry.get('needs_split')
        )

        # 如果参考文档变了，用原文
        compare_ref_text = filtered_text if doc_a_id == ref_doc_id else _get_text(doc_a_id)

        if use_chunked:
            result = _run_chunked_comparison_ai(compare_ref_text, doc_b_id, 0, doc_b_entry['label'], config)
        else:
            result = compare_documents(
                tender_text=compare_ref_text,
                bid_text=doc_b_text,
                bid_index=0,
                bid_filename=doc_b_entry['label'],
                config=config,
            )

        severity = severity_label(result.duplicate_percentage)
        results.append(_format_pair_result(
            result, doc_a_id, doc_b_id, label_a, label_b, severity
        ))

    results.sort(key=lambda r: r['duplicate_percentage'], reverse=True)

    # 构建过滤类别摘要
    filter_categories = []
    if filtered.paragraphs:
        categories = {}
        for p in filtered.paragraphs:
            if p.category not in categories:
                categories[p.category] = {'count': 0, 'samples': []}
            categories[p.category]['count'] += 1
            if len(categories[p.category]['samples']) < 3:
                categories[p.category]['samples'].append(p.text[:200])
        category_labels = {
            'format_requirement': '格式要求',
            'p2p_response': '点对点应答要求',
            'legal_clause': '法律条款/通用模板',
            'scoring_criteria': '评分标准',
            'substantive': '实质性内容（保留比对）',
        }
        for cat, info in categories.items():
            filter_categories.append({
                'category': cat,
                'label': category_labels.get(cat, cat),
                'count': info['count'],
                'samples': info['samples'],
            })

    ref_entry = _file_store.get(ref_doc_id, {})
    return jsonify({
        'mode': 'ai',
        'ref_filename': ref_entry.get('filename', ''),
        'filter_summary': filtered.filter_summary,
        'filter_categories': filter_categories,
        'filtered_chars_removed': len(tender_text) - len(filtered_text),
        'results': results,
        'pair_count': len(results),
    })


def _run_chunked_comparison(tender_id: str, bid_id: str, bid_index: int, bid_filename: str, config: ComparisonConfig):
    """执行分片级比对"""
    tender_text = _get_text(tender_id)
    bid_text = _get_text(bid_id)
    split_cfg = SplitConfig(max_chars_per_chunk=50000, overlap_chars=5000)

    tender_chunks = split_document(tender_text, config=split_cfg)
    bid_chunks = split_document(bid_text, config=split_cfg)

    if len(tender_chunks) == 1 and len(bid_chunks) == 1:
        return compare_documents(tender_text, bid_text, bid_index, bid_filename, config)

    return compare_documents_chunked(
        tender_chunks=tender_chunks,
        bid_chunks=bid_chunks,
        tender_text=tender_text,
        bid_text=bid_text,
        bid_index=bid_index,
        bid_filename=bid_filename,
        config=config,
    )


def _run_chunked_comparison_ai(filtered_text: str, bid_id: str, bid_index: int, bid_filename: str, config: ComparisonConfig):
    bid_text = _get_text(bid_id)
    split_cfg = SplitConfig(max_chars_per_chunk=50000, overlap_chars=5000)
    tender_chunks = split_document(filtered_text, config=split_cfg)
    bid_chunks = split_document(bid_text, config=split_cfg)
    if len(tender_chunks) == 1 and len(bid_chunks) == 1:
        return compare_documents(filtered_text, bid_text, bid_index, bid_filename, config)
    return compare_documents_chunked(tender_chunks, bid_chunks, filtered_text, bid_text, bid_index, bid_filename, config)


def _format_pair_result(result: ComparisonResult, doc_a_id: str, doc_b_id: str, label_a: str, label_b: str, severity: dict) -> dict:
    """格式化比对结果 (v3: 包含双方标签)"""
    return {
        'doc_a_id': doc_a_id,
        'doc_b_id': doc_b_id,
        'label_a': label_a,
        'label_b': label_b,
        'bid_index': result.bid_index,
        'bid_filename': result.bid_filename,
        'total_tender_chars': result.total_tender_chars,
        'total_bid_chars': result.total_bid_chars,
        'matched_chars': result.matched_chars,
        'duplicate_percentage': result.duplicate_percentage,
        'severity': severity,
        'segments': [
            {
                'id': s.segment_id,
                'tender_text': s.tender_text,
                'bid_text': s.bid_text,
                'similarity': s.similarity,
                'tender_span': (s.tender_start, s.tender_end),
                'bid_span': (s.bid_start, s.bid_end),
            }
            for s in result.matched_segments
        ],
    }


@app.route('/api/files/<file_id>', methods=['DELETE'])
def remove_file(file_id):
    if file_id in _file_store:
        entry = _file_store.pop(file_id)
        _parsed_cache.pop(file_id, None)
        try:
            os.remove(entry['path'])
        except OSError:
            pass
    return jsonify({'status': 'deleted'})


@app.route('/api/clear', methods=['POST'])
def clear_all():
    for entry in _file_store.values():
        try:
            os.remove(entry['path'])
        except OSError:
            pass
    _file_store.clear()
    _parsed_cache.clear()
    _job_store.clear()
    return jsonify({'status': 'cleared'})


@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': True, 'code': 'FILE_TOO_LARGE', 'message': '文件大小超过 500MB 限制'}), 413


if __name__ == '__main__':
    _ensure_upload_folder()
    app.run(debug=True, host='127.0.0.1', port=29661)
