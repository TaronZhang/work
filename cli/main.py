#!/usr/bin/env python3
"""bid-checker CLI — 文档比对命令行工具 (agent-compose 集成版)

用法:
  bid-checker compare <file_a> <file_b> [--ai] [--output-dir DIR] [--threshold 0.75] [--chunk-size 200]
  bid-checker compare-all <dir_or_files...> [--ai] [--output-dir DIR] [--threshold 0.75] [--chunk-size 200]
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.parser import parse_file
from src.comparator import compare_documents, compare_documents_chunked, ComparisonConfig
from src.splitter import split_document, SplitConfig
from src.ai_filter import analyze_comparison_segments, filter_tender_requirements
from src.exporter import generate_pdf
from src.utils import severity_label
from cli.html_reporter import generate_html_report

SPLIT_THRESHOLD = 100000


def _parse_file_safe(filepath):
    try:
        return parse_file(filepath)
    except Exception as e:
        print(f'ERROR: 解析文件失败 {filepath}: {e}', file=sys.stderr)
        return None


def _needs_split(text_a, text_b):
    return len(text_a) > SPLIT_THRESHOLD or len(text_b) > SPLIT_THRESHOLD


def _run_comparison_pair(text_a, text_b, label_a, label_b, cfg, bid_index=0):
    if _needs_split(text_a, text_b):
        split_cfg = SplitConfig(max_chars_per_chunk=50000, overlap_chars=5000)
        chunks_a = split_document(text_a, config=split_cfg)
        chunks_b = split_document(text_b, config=split_cfg)
        result = compare_documents_chunked(
            tender_chunks=chunks_a, bid_chunks=chunks_b,
            tender_text=text_a, bid_text=text_b,
            bid_index=bid_index, bid_filename=label_b, config=cfg,
        )
    else:
        result = compare_documents(
            tender_text=text_a, bid_text=text_b,
            bid_index=bid_index, bid_filename=label_b, config=cfg,
        )
    return result


def _format_result(result, label_a, label_b):
    severity = severity_label(result.duplicate_percentage)
    return {
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


def _run_ai_analysis(results):
    """Run AI analysis on comparison results (Stage 2: post-comparison segment analysis).
    
    Stage 1 pre-filter is handled before comparison in cmd_compare().
    """
    api_key = os.environ.get('OPENAI_API_KEY', '')
    base_url = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

    if not api_key:
        for r in results:
            r['ai_warning'] = 'OPENAI_API_KEY 未配置，跳过 AI 分析'
        return

    # ── Stage 2: Post-analysis (core) ──
    # 事后分析：LLM 分析匹配段，区分合规应答与实际重复
    # 入口：analyze_comparison_segments() in src/ai_filter.py
    try:
        analyses = analyze_comparison_segments(
            results=results, api_key=api_key, base_url=base_url, model=model,
        )
        for i, r in enumerate(results):
            if i < len(analyses):
                a = analyses[i]
                r['ai_analysis'] = {
                    'original_percentage': a.original_percentage,
                    'adjusted_percentage': a.adjusted_percentage,
                    'compliance_chars': a.compliance_chars,
                    'actual_duplication_chars': a.actual_duplication_chars,
                    'summary': a.summary,
                    'segment_classifications': [
                        {
                            'segment_id': sa.segment_id,
                            'classification': sa.classification,
                            'reason': sa.reason,
                            'adjusted_similarity': sa.adjusted_similarity,
                        }
                        for sa in a.segment_analyses
                    ],
                }
                r['adjusted_percentage'] = a.adjusted_percentage
                r['severity'] = severity_label(a.adjusted_percentage)
    except Exception as e:
        for r in results:
            r['ai_warning'] = f'AI 分析失败: {e}'


def _generate_reports(results, mode, output_dir, label_a, label_b):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_a = Path(label_a).stem[:20] if label_a else 'docA'
    safe_b = Path(label_b).stem[:20] if label_b else 'docB'
    report_name = f'{safe_a}_vs_{safe_b}_{timestamp}'

    os.makedirs(output_dir, exist_ok=True)

    html_path = os.path.join(output_dir, f'{report_name}.html')
    generate_html_report(results, mode, html_path)

    pdf_path = os.path.join(output_dir, f'{report_name}.pdf')
    pdf_bytes = generate_pdf(results, mode)
    with open(pdf_path, 'wb') as f:
        f.write(pdf_bytes)

    return html_path, pdf_path


def _print_summary(results, mode, html_path, pdf_path):
    mode_label = 'AI 辅助' if mode == 'ai' else '快速'
    print(f'\n比对完成 (模式: {mode_label})')
    print('=' * 60)

    for r in results:
        label_a = r.get('label_a', '')
        label_b = r.get('label_b', '')
        pct = r.get('duplicate_percentage', 0)
        sev = r.get('severity', {})
        seg_count = len(r.get('segments', []))

        print(f'\n  文件 A: {label_a}')
        print(f'  文件 B: {label_b}')
        print(f'  重复率: {pct:.1f}%')
        print(f'  匹配段数: {seg_count}')
        print(f'  严重程度: {sev.get("label", "")}')

        if 'ai_analysis' in r:
            ai = r['ai_analysis']
            print(f'  AI 分析: {ai["summary"]}')
            print(f'  调整后重复率: {ai["adjusted_percentage"]:.1f}%')
        elif 'ai_warning' in r:
            print(f'  AI 警告: {r["ai_warning"]}')

        if 'pre_filter_info' in r:
            pf = r['pre_filter_info']
            print(f'  事前过滤: 原始 {pf["original_chars"]} 字 → 过滤后 {pf["filtered_chars"]} 字')
        elif 'pre_filter_warning' in r:
            print(f'  事前过滤警告: {r["pre_filter_warning"]}')

    print(f'\n{"=" * 60}')
    print(f'HTML 报告: {html_path}')
    print(f'PDF 报告: {pdf_path}')


def cmd_compare(args):
    if not os.path.exists(args.file_a):
        print(f'ERROR: 文件不存在: {args.file_a}', file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.file_b):
        print(f'ERROR: 文件不存在: {args.file_b}', file=sys.stderr)
        sys.exit(1)

    doc_a = _parse_file_safe(args.file_a)
    doc_b = _parse_file_safe(args.file_b)
    if not doc_a or not doc_b:
        sys.exit(1)

    label_a = os.path.basename(args.file_a)
    label_b = os.path.basename(args.file_b)

    cfg = ComparisonConfig(
        chunk_size=args.chunk_size,
        similarity_threshold=args.threshold,
    )

    # ── Stage 1 (optional): AI pre-filter ──
    # 事前过滤：LLM 分类招标文件段落，移除格式要求等非实质性内容
    # 过滤后的文本用于后续比对，真正影响重复率计算
    use_pre_filter = getattr(args, 'pre_filter', False) and args.ai
    pre_filter_info = None
    tender_text_for_compare = doc_a.full_text

    if use_pre_filter:
        api_key = os.environ.get('OPENAI_API_KEY', '')
        base_url = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
        if api_key:
            try:
                filtered = filter_tender_requirements(
                    tender_text=doc_a.full_text,
                    api_key=api_key, base_url=base_url, model=model,
                )
                tender_text_for_compare = filtered.filtered_text
                pre_filter_info = {
                    'filter_summary': filtered.filter_summary,
                    'original_chars': len(filtered.original_text),
                    'filtered_chars': len(filtered.filtered_text),
                    'requirements_chars': len(filtered.requirements_text),
                }
            except Exception as e:
                print(f'  事前过滤失败（使用原始文本继续）: {e}', file=sys.stderr)

    result = _run_comparison_pair(
        tender_text_for_compare, doc_b.full_text, label_a, label_b, cfg,
    )
    result_dict = _format_result(result, label_a, label_b)

    if pre_filter_info:
        result_dict['pre_filter_info'] = pre_filter_info

    mode = 'ai' if args.ai else 'fast'
    if args.ai:
        _run_ai_analysis([result_dict])

    html_path, pdf_path = _generate_reports(
        [result_dict], mode, args.output_dir, label_a, label_b,
    )

    _print_summary([result_dict], mode, html_path, pdf_path)


def cmd_compare_all(args):
    files = _collect_files(args.files)
    if len(files) < 2:
        print('ERROR: 至少需要 2 个文件进行比对', file=sys.stderr)
        sys.exit(1)

    docs = {}
    for f in files:
        parsed = _parse_file_safe(str(f))
        if parsed:
            docs[str(f)] = parsed

    if len(docs) < 2:
        print('ERROR: 有效文件不足 2 个', file=sys.stderr)
        sys.exit(1)

    cfg = ComparisonConfig(
        chunk_size=args.chunk_size,
        similarity_threshold=args.threshold,
    )

    # ── Stage 1 (optional): AI pre-filter ──
    # 事前过滤：LLM 分类招标文件段落，移除格式要求等非实质性内容
    # 过滤后的文本用于后续比对，真正影响重复率计算
    use_pre_filter = getattr(args, 'pre_filter', False) and args.ai
    pre_filter_cache = {}  # file_path -> pre_filter_info or None
    tender_texts_cache = {}  # file_path -> filtered text or original

    if use_pre_filter:
        api_key = os.environ.get('OPENAI_API_KEY', '')
        base_url = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
        if api_key:
            for fpath, doc in docs.items():
                try:
                    filtered = filter_tender_requirements(
                        tender_text=doc.full_text,
                        api_key=api_key, base_url=base_url, model=model,
                    )
                    tender_texts_cache[fpath] = filtered.filtered_text
                    pre_filter_cache[fpath] = {
                        'filter_summary': filtered.filter_summary,
                        'original_chars': len(filtered.original_text),
                        'filtered_chars': len(filtered.filtered_text),
                        'requirements_chars': len(filtered.requirements_text),
                    }
                except Exception as e:
                    print(f'  事前过滤失败（使用原始文本继续） {os.path.basename(fpath)}: {e}', file=sys.stderr)
                    tender_texts_cache[fpath] = doc.full_text
                    pre_filter_cache[fpath] = None

    file_list = list(docs.keys())
    results = []
    for i in range(len(file_list)):
        for j in range(i + 1, len(file_list)):
            fa, fb = file_list[i], file_list[j]
            la, lb = os.path.basename(fa), os.path.basename(fb)
            text_a = tender_texts_cache.get(fa, docs[fa].full_text)
            text_b = docs[fb].full_text
            result = _run_comparison_pair(
                text_a, text_b, la, lb, cfg, bid_index=j,
            )
            result_dict = _format_result(result, la, lb)
            if fa in pre_filter_cache and pre_filter_cache[fa] is not None:
                result_dict['pre_filter_info'] = pre_filter_cache[fa]
            results.append(result_dict)

    results.sort(key=lambda r: r['duplicate_percentage'], reverse=True)

    mode = 'ai' if args.ai else 'fast'
    if args.ai:
        _run_ai_analysis(results)

    label_a = os.path.basename(file_list[0])
    label_b = f'{len(file_list)}files'
    html_path, pdf_path = _generate_reports(
        results, mode, args.output_dir, label_a, label_b,
    )

    _print_summary(results, mode, html_path, pdf_path)


def _collect_files(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            for ext in ('*.doc', '*.docx', '*.pdf', '*.txt', '*.DOC', '*.DOCX', '*.PDF', '*.TXT'):
                files.extend(Path(p).glob(ext))
        elif os.path.isfile(p):
            files.append(Path(p))
        else:
            print(f'WARNING: 路径不存在: {p}', file=sys.stderr)
    return sorted(set(files))


def build_parser():
    parser = argparse.ArgumentParser(
        prog='bid-checker',
        description='文档重复度比对工具 — agent-compose 集成版',
    )
    sub = parser.add_subparsers(dest='command')

    cp = sub.add_parser('compare', help='单对比对')
    cp.add_argument('file_a', help='文件 A 路径')
    cp.add_argument('file_b', help='文件 B 路径')
    cp.add_argument('--ai', action='store_true', help='启用 AI 辅助分析（事后段分析）')
    cp.add_argument('--pre-filter', action='store_true', help='启用事前 AI 过滤（需配合 --ai 使用，分类招标文件段落移除格式要求）')
    cp.add_argument('--output-dir', default='/workspace/reports', help='报告输出目录 (默认: /workspace/reports)')
    cp.add_argument('--threshold', type=float, default=0.75, help='相似度阈值 (默认: 0.75)')
    cp.add_argument('--chunk-size', type=int, default=200, help='分块大小 (默认: 200)')

    cap = sub.add_parser('compare-all', help='两两互比')
    cap.add_argument('files', nargs='+', help='文件路径或目录 (可多个)')
    cap.add_argument('--ai', action='store_true', help='启用 AI 辅助分析（事后段分析）')
    cap.add_argument('--pre-filter', action='store_true', help='启用事前 AI 过滤（需配合 --ai 使用）')
    cap.add_argument('--output-dir', default='/workspace/reports', help='报告输出目录 (默认: /workspace/reports)')
    cap.add_argument('--threshold', type=float, default=0.75, help='相似度阈值 (默认: 0.75)')
    cap.add_argument('--chunk-size', type=int, default=200, help='分块大小 (默认: 200)')

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == 'compare':
        cmd_compare(args)
    elif args.command == 'compare-all':
        cmd_compare_all(args)


if __name__ == '__main__':
    main()
