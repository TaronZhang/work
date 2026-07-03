"""标书检查工具 - Flask 主应用 (v2 — 大文件拆分支持)"""

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

# 内存存储 — v2: content 仅在小文件存储，大文件从磁盘懒加载
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


# ── Routes ─────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload():
    """上传文件 (v2: 返回 needs_split 标记)"""
    _ensure_upload_folder()

    if 'file' not in request.files:
        return jsonify({'error': True, 'code': 'NO_FILE', 'message': '请选择文件'}), 400

    file = request.files['file']
    doc_type = request.form.get('doc_type', 'bid')
    bid_label = request.form.get('bid_label', '')

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

    entry = {
        'id': file_id,
        'filename': file.filename,
        'doc_type': doc_type,
        'label': bid_label or file.filename,
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


def _should_split_from_size(file_size: int, chars: int) -> bool:
    return file_size > AUTO_SPLIT_THRESHOLD or chars > 100000


@app.route('/api/comparison', methods=['POST'])
def run_comparison():
    """快速模式比对 (v2: 自动分片)"""
    data = request.get_json() or {}
    tender_id = data.get('tender_id', '')
    bid_ids = data.get('bid_ids', [])

    if tender_id not in _file_store:
        return jsonify({'error': True, 'code': 'NOT_FOUND', 'message': '招标文件未找到'}), 400
    if not bid_ids:
        return jsonify({'error': True, 'code': 'NO_BIDS', 'message': '请至少上传一份投标文件'}), 400

    tender_text = _get_text(tender_id)
    if not tender_text:
        return jsonify({'error': True, 'code': 'EMPTY_CONTENT', 'message': '招标文件内容为空'}), 400

    tender_entry = _file_store[tender_id]
    chunk_size = data.get('chunk_size', 200)
    threshold = data.get('threshold', 0.75)
    config = ComparisonConfig(chunk_size=chunk_size, similarity_threshold=threshold)

    use_chunked = (
        tender_entry.get('needs_split') or
        any(_file_store.get(bid_id, {}).get('needs_split') for bid_id in bid_ids)
    )

    results = []
    for i, bid_id in enumerate(bid_ids):
        if bid_id not in _file_store:
            continue
        bid_text = _get_text(bid_id)
        if not bid_text:
            continue

        bid_entry = _file_store[bid_id]

        if use_chunked:
            result = _run_chunked_comparison(tender_id, bid_id, i, bid_entry['label'], config)
        else:
            result = compare_documents(
                tender_text=tender_text,
                bid_text=bid_text,
                bid_index=i,
                bid_filename=bid_entry['label'],
                config=config,
            )

        severity = severity_label(result.duplicate_percentage)
        results.append(_format_result(result, bid_id, severity))

        # 释放大文件缓存
        if bid_entry.get('needs_split'):
            _parsed_cache.pop(bid_id, None)
    if tender_entry.get('needs_split'):
        _parsed_cache.pop(tender_id, None)

    results.sort(key=lambda r: r['duplicate_percentage'], reverse=True)
    return jsonify({'mode': 'fast', 'tender_filename': tender_entry['filename'], 'results': results, 'chunked': use_chunked})


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


def _format_result(result: ComparisonResult, bid_id: str, severity: dict) -> dict:
    return {
        'bid_index': result.bid_index,
        'bid_filename': result.bid_filename,
        'bid_id': bid_id,
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


@app.route('/api/comparison/ai', methods=['POST'])
def run_ai_comparison():
    """AI 辅助模式比对 (v2: 自动分片)"""
    data = request.get_json() or {}
    tender_id = data.get('tender_id', '')
    bid_ids = data.get('bid_ids', [])
    api_key = data.get('api_key', '')
    base_url = data.get('base_url', 'https://api.openai.com/v1')
    model = data.get('model', 'gpt-4o')

    if tender_id not in _file_store:
        return jsonify({'error': True, 'code': 'NOT_FOUND', 'message': '招标文件未找到'}), 400
    if not bid_ids:
        return jsonify({'error': True, 'code': 'NO_BIDS', 'message': '请至少上传一份投标文件'}), 400
    if not api_key:
        return jsonify({'error': True, 'code': 'NO_API_KEY', 'message': '请输入 API Key'}), 400

    tender_text = _get_text(tender_id)
    if not tender_text:
        return jsonify({'error': True, 'code': 'EMPTY_CONTENT', 'message': '招标文件内容为空'}), 400

    tender_entry = _file_store[tender_id]

    # AI 过滤
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

    use_chunked = (
        tender_entry.get('needs_split') or
        any(_file_store.get(bid_id, {}).get('needs_split') for bid_id in bid_ids)
    )

    config = ComparisonConfig(similarity_threshold=0.75)
    results = []

    for i, bid_id in enumerate(bid_ids):
        if bid_id not in _file_store:
            continue
        bid_text = _get_text(bid_id)
        if not bid_text:
            continue

        bid_entry = _file_store[bid_id]

        if use_chunked:
            tender_entry_tmp = dict(tender_entry)
            tender_entry_tmp['content'] = filtered_text if not tender_entry.get('needs_split') else ''
            result = _run_chunked_comparison_ai(filtered_text, bid_id, i, bid_entry['label'], config)
        else:
            result = compare_documents(
                tender_text=filtered_text,
                bid_text=bid_text,
                bid_index=i,
                bid_filename=bid_entry['label'],
                config=config,
            )

        severity = severity_label(result.duplicate_percentage)
        results.append(_format_result(result, bid_id, severity))

    results.sort(key=lambda r: r['duplicate_percentage'], reverse=True)

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
            filter_categories.append({'category': cat, 'label': category_labels.get(cat, cat), 'count': info['count'], 'samples': info['samples']})

    return jsonify({
        'mode': 'ai',
        'tender_filename': tender_entry['filename'],
        'filter_summary': filtered.filter_summary,
        'filter_categories': filter_categories,
        'filtered_chars_removed': len(tender_text) - len(filtered_text),
        'results': results,
        'chunked': use_chunked,
    })


def _run_chunked_comparison_ai(filtered_text: str, bid_id: str, bid_index: int, bid_filename: str, config: ComparisonConfig):
    bid_text = _get_text(bid_id)
    split_cfg = SplitConfig(max_chars_per_chunk=50000, overlap_chars=5000)
    tender_chunks = split_document(filtered_text, config=split_cfg)
    bid_chunks = split_document(bid_text, config=split_cfg)
    if len(tender_chunks) == 1 and len(bid_chunks) == 1:
        return compare_documents(filtered_text, bid_text, bid_index, bid_filename, config)
    return compare_documents_chunked(tender_chunks, bid_chunks, filtered_text, bid_text, bid_index, bid_filename, config)


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
    app.run(debug=True, host='127.0.0.1', port=5000)
