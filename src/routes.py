"""Route handlers — API endpoints for file upload, comparison, and management."""

from flask import Blueprint, request, jsonify, render_template
from pydantic import ValidationError
from datetime import datetime

from src.config import config
from src.models import ComparisonRequest, AIComparisonRequest
from src.services import (
    ensure_upload_folder, get_text, should_split, store_file,
    parse_uploaded_file, resolve_comparison_pairs,
    run_chunked_comparison, run_chunked_comparison_ai,
    format_pair_result, run_ai_filter, delete_file, clear_all_files,
    file_store, parsed_cache,
)
from src.comparator import compare_documents, ComparisonConfig
from src.utils import allowed_file, generate_file_id, severity_label
from src.exporter import generate_docx, generate_pdf
from src.ai_filter import analyze_comparison_segments, filter_tender_requirements
from flask import send_file
import io

bp = Blueprint('api', __name__)


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/healthz')
def healthz():
    """Health check endpoint for deployment verification."""
    return jsonify({'status': 'ok', 'service': 'docdiff'}), 200


@bp.route('/api/upload', methods=['POST'])
def upload():
    """Upload a file for comparison."""
    ensure_upload_folder()

    if 'file' not in request.files:
        return jsonify({'error': True, 'code': 'NO_FILE', 'message': 'No file provided'}), 400

    file = request.files['file']
    doc_type = request.form.get('doc_type', 'document')
    label = request.form.get('label', '')

    if not file.filename:
        return jsonify({'error': True, 'code': 'EMPTY_FILENAME', 'message': 'Empty filename'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': True, 'code': 'INVALID_FORMAT', 'message': 'Supported: .doc, .docx, .pdf, .txt'}), 400

    file_id = generate_file_id(file.filename)
    filepath = f'{config.upload_folder}/{file_id}'
    file.save(filepath)

    file_size = _safe_file_size(filepath)
    if file_size > config.max_content_length:
        _safe_remove(filepath)
        return jsonify({'error': True, 'code': 'FILE_TOO_LARGE', 'message': 'File exceeds size limit'}), 413

    content, chars, parse_status = parse_uploaded_file(filepath, file.filename)

    needs_split = should_split(file_size, chars)
    if needs_split and content:
        parsed_cache[file_id] = content
        content = ''
        parse_status = 'parsed_large'

    if not label:
        label = file.filename

    store_file(
        file_id, file.filename, doc_type, label,
        filepath, file_size, chars, content, parse_status, needs_split,
    )

    return jsonify({
        'file_id': file_id,
        'filename': file.filename,
        'doc_type': doc_type,
        'label': label,
        'size_bytes': file_size,
        'size_mb': round(file_size / (1024 * 1024), 2),
        'chars': chars,
        'status': parse_status,
        'needs_split': needs_split,
    }), 201


@bp.route('/api/comparison', methods=['POST'])
def run_comparison():
    """Fast-mode document comparison."""
    raw = request.get_json() or {}
    try:
        data = ComparisonRequest(**raw)
    except ValidationError as e:
        return jsonify({'error': True, 'code': 'VALIDATION_ERROR', 'message': e.message}), 400

    cfg = ComparisonConfig(
        chunk_size=data.chunk_size,
        similarity_threshold=data.threshold,
    )
    pairs = resolve_comparison_pairs(data.model_dump())
    if not pairs:
        return jsonify({'error': True, 'code': 'INVALID_REQUEST', 'message': 'Need at least 2 documents'}), 400

    results = []
    for doc_a_id, doc_b_id, label_a, label_b in pairs:
        if doc_a_id not in file_store or doc_b_id not in file_store:
            continue
        doc_a_text = get_text(doc_a_id)
        doc_b_text = get_text(doc_b_id)
        if not doc_a_text or not doc_b_text:
            continue

        doc_a_entry = file_store[doc_a_id]
        doc_b_entry = file_store[doc_b_id]
        use_chunked = doc_a_entry.get('needs_split') or doc_b_entry.get('needs_split')

        if use_chunked:
            result = run_chunked_comparison_ai(doc_a_text, doc_b_id, 0, doc_b_entry['label'], cfg)
        else:
            result = compare_documents(
                tender_text=doc_a_text, bid_text=doc_b_text,
                bid_index=0, bid_filename=doc_b_entry['label'], config=cfg,
            )

        severity = severity_label(result.duplicate_percentage)
        results.append(format_pair_result(result, doc_a_id, doc_b_id, label_a, label_b, severity))

        if doc_a_entry.get('needs_split'):
            parsed_cache.pop(doc_a_id, None)
        if doc_b_entry.get('needs_split'):
            parsed_cache.pop(doc_b_id, None)

    results.sort(key=lambda r: r['duplicate_percentage'], reverse=True)
    return jsonify({'mode': 'fast', 'results': results, 'pair_count': len(results)})


@bp.route('/api/comparison/ai', methods=['POST'])
def run_ai_comparison():
    """AI-assisted comparison mode — two-stage approach.

    Stage 1 (optional, pre_filter=True): AI filters tender paragraphs to remove
             format requirements, legal clauses, etc. before comparison.
             Entry point: filter_tender_requirements() in src/ai_filter.py
    Stage 2 (core): AI analyzes matched segments to classify them as:
             - compliance_response: bid legitimately echoes tender requirements
             - actual_duplication: real duplicate content
             Entry point: analyze_comparison_segments() in src/ai_filter.py
    Adjusts the duplication percentage by excluding compliance responses.

    API Key is read from server-side environment variables (config).
    """
    if not config.openai_api_key:
        return jsonify({
            'error': True, 'code': 'NO_API_KEY',
            'message': 'AI mode requires OPENAI_API_KEY in server .env',
        }), 503

    raw = request.get_json() or {}
    try:
        data = AIComparisonRequest(**raw)
    except ValidationError as e:
        return jsonify({'error': True, 'code': 'VALIDATION_ERROR', 'message': e.message}), 400

    pairs = resolve_comparison_pairs(data.model_dump())
    if not pairs:
        return jsonify({'error': True, 'code': 'INVALID_REQUEST', 'message': 'Need at least 2 documents'}), 400

    # ── Stage 1 (optional): AI pre-filter ──
    # 事前过滤：LLM 分类招标文件段落，移除格式要求等非实质性内容
    # 过滤后的文本用于后续比对，真正影响重复率计算
    # 源码位置：filter_tender_requirements() in src/ai_filter.py:162
    pre_filter_results = {}
    filtered_tender_texts = {}  # doc_a_id -> filtered text (or original if no filter)
    if data.pre_filter:
        tender_ids_seen = set()
        for doc_a_id, doc_b_id, label_a, label_b in pairs:
            if doc_a_id in tender_ids_seen:
                continue
            tender_ids_seen.add(doc_a_id)
            tender_text = get_text(doc_a_id)
            if not tender_text:
                continue
            try:
                filtered = filter_tender_requirements(
                    tender_text=tender_text,
                    api_key=config.openai_api_key,
                    base_url=config.openai_base_url,
                    model=config.openai_model,
                )
                pre_filter_results[doc_a_id] = {
                    'filter_summary': filtered.filter_summary,
                    'original_chars': len(filtered.original_text),
                    'filtered_chars': len(filtered.filtered_text),
                    'requirements_chars': len(filtered.requirements_text),
                }
                filtered_tender_texts[doc_a_id] = filtered.filtered_text
            except Exception as e:
                pre_filter_results[doc_a_id] = {'error': str(e)}
                filtered_tender_texts[doc_a_id] = tender_text  # fallback to original

    # ── Comparison using (optionally filtered) tender text ──
    cfg = ComparisonConfig(
        chunk_size=data.chunk_size,
        similarity_threshold=data.threshold,
    )
    results = []
    for doc_a_id, doc_b_id, label_a, label_b in pairs:
        if doc_a_id not in file_store or doc_b_id not in file_store:
            continue
        # Use filtered tender text if pre-filter was applied, otherwise original
        doc_a_text = filtered_tender_texts.get(doc_a_id) or get_text(doc_a_id)
        doc_b_text = get_text(doc_b_id)
        if not doc_a_text or not doc_b_text:
            continue

        doc_a_entry = file_store[doc_a_id]
        doc_b_entry = file_store[doc_b_id]
        use_chunked = doc_a_entry.get('needs_split') or doc_b_entry.get('needs_split')

        if use_chunked:
            result = run_chunked_comparison(doc_a_id, doc_b_id, 0, doc_b_entry['label'], cfg)
        else:
            result = compare_documents(
                tender_text=doc_a_text, bid_text=doc_b_text,
                bid_index=0, bid_filename=doc_b_entry['label'], config=cfg,
            )

        severity = severity_label(result.duplicate_percentage)
        results.append(format_pair_result(result, doc_a_id, doc_b_id, label_a, label_b, severity))

        if doc_a_entry.get('needs_split'):
            parsed_cache.pop(doc_a_id, None)
        if doc_b_entry.get('needs_split'):
            parsed_cache.pop(doc_b_id, None)

    if not results:
        return jsonify({'error': True, 'code': 'NO_RESULTS', 'message': 'No valid document pairs found'}), 400

    results.sort(key=lambda r: r['duplicate_percentage'], reverse=True)

    # Attach pre-filter info to results
    if pre_filter_results:
        for r in results:
            doc_a_id = r.get('doc_a_id', '')
            if doc_a_id in pre_filter_results:
                r['pre_filter_info'] = pre_filter_results[doc_a_id]

    # ── Stage 2: AI post-comparison analysis ──
    try:
        analyses = analyze_comparison_segments(
            results=results,
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
            model=config.openai_model,
        )
    except Exception as e:
        for r in results:
            r['ai_analysis'] = None
            r['ai_warning'] = f'AI analysis failed: {str(e)}'
        return jsonify({
            'mode': 'ai',
            'ai_warning': f'AI analysis stage failed, showing fast-mode results: {str(e)}',
            'results': results,
            'pair_count': len(results),
        })

    # Merge AI analysis into results
    for i, r in enumerate(results):
        if i < len(analyses):
            analysis = analyses[i]
            r['ai_analysis'] = {
                'original_percentage': analysis.original_percentage,
                'adjusted_percentage': analysis.adjusted_percentage,
                'compliance_chars': analysis.compliance_chars,
                'actual_duplication_chars': analysis.actual_duplication_chars,
                'summary': analysis.summary,
                'segment_classifications': [
                    {
                        'segment_id': sa.segment_id,
                        'classification': sa.classification,
                        'reason': sa.reason,
                        'adjusted_similarity': sa.adjusted_similarity,
                    }
                    for sa in analysis.segment_analyses
                ],
            }
            r['adjusted_percentage'] = analysis.adjusted_percentage
            r['severity'] = severity_label(analysis.adjusted_percentage)
        else:
            r['ai_analysis'] = None

    return jsonify({
        'mode': 'ai',
        'results': results,
        'pair_count': len(results),
        'analyses': [
            {
                'pair_index': a.pair_index,
                'label_a': a.label_a,
                'label_b': a.label_b,
                'original_percentage': a.original_percentage,
                'adjusted_percentage': a.adjusted_percentage,
                'compliance_chars': a.compliance_chars,
                'actual_duplication_chars': a.actual_duplication_chars,
                'summary': a.summary,
            }
            for a in analyses
        ],
    })


@bp.route('/api/files/<file_id>', methods=['DELETE'])
def remove_file(file_id):
    """Delete a single uploaded file."""
    delete_file(file_id)
    return jsonify({'status': 'deleted'})


@bp.route('/api/clear', methods=['POST'])
def clear_all():
    """Clear all uploaded files."""
    clear_all_files()
    return jsonify({'status': 'cleared'})




@bp.route('/api/export/docx', methods=['POST'])
def export_docx():
    """Export comparison results as DOCX."""
    data = request.get_json() or {}
    results = data.get('results', [])
    mode = data.get('mode', 'fast')
    filter_info = data.get('filter_info')

    if not results:
        return jsonify({'error': True, 'code': 'NO_RESULTS', 'message': 'No results to export'}), 400

    try:
        docx_bytes = generate_docx(results, mode, filter_info)
        buf = io.BytesIO(docx_bytes)
        buf.seek(0)
        return send_file(
            buf,
            as_attachment=True,
            download_name=f'docdiff_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.docx',
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
    except Exception as e:
        return jsonify({'error': True, 'code': 'EXPORT_ERROR', 'message': str(e)}), 500


@bp.route('/api/export/pdf', methods=['POST'])
def export_pdf():
    """Export comparison results as PDF."""
    data = request.get_json() or {}
    results = data.get('results', [])
    mode = data.get('mode', 'fast')
    filter_info = data.get('filter_info')

    if not results:
        return jsonify({'error': True, 'code': 'NO_RESULTS', 'message': 'No results to export'}), 400

    try:
        pdf_bytes = generate_pdf(results, mode, filter_info)
        buf = io.BytesIO(pdf_bytes)
        buf.seek(0)
        return send_file(
            buf,
            as_attachment=True,
            download_name=f'docdiff_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
            mimetype='application/pdf',
        )
    except Exception as e:
        return jsonify({'error': True, 'code': 'EXPORT_ERROR', 'message': str(e)}), 500


def _build_filter_categories(filtered) -> list[dict]:
    """Build filter category summary for AI mode response."""
    if not filtered.paragraphs:
        return []
    categories: dict[str, dict] = {}
    for p in filtered.paragraphs:
        if p.category not in categories:
            categories[p.category] = {'count': 0, 'samples': []}
        categories[p.category]['count'] += 1
        if len(categories[p.category]['samples']) < 3:
            categories[p.category]['samples'].append(p.text[:200])

    category_labels = {
        'format_requirement': 'Format Requirements',
        'p2p_response': 'P2P Response Requirements',
        'legal_clause': 'Legal Clauses',
        'scoring_criteria': 'Scoring Criteria',
        'substantive': 'Substantive Content (kept for comparison)',
    }
    result = []
    for cat, info in categories.items():
        result.append({
            'category': cat,
            'label': category_labels.get(cat, cat),
            'count': info['count'],
            'samples': info['samples'],
        })
    return result


def _safe_file_size(filepath: str) -> int:
    """Get file size, return 0 on error."""
    import os
    try:
        return os.path.getsize(filepath)
    except OSError:
        return 0


def _safe_remove(filepath: str) -> None:
    """Remove a file, ignoring errors."""
    import os
    try:
        os.remove(filepath)
    except OSError:
        pass
