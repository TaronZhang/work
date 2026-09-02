"""Service layer — file management, comparison execution, result formatting."""

import os

from src.config import config
from src.parser import parse_file
from src.comparator import (
    compare_documents,
    compare_documents_chunked,
    ComparisonConfig,
    ComparisonResult,
)
from src.splitter import split_document, SplitConfig
from src.ai_filter import filter_tender_requirements
from src.utils import severity_label

# In-memory stores
file_store: dict[str, dict] = {}
parsed_cache: dict[str, str] = {}


def ensure_upload_folder() -> None:
    """Create upload folder if it does not exist."""
    os.makedirs(config.upload_folder, exist_ok=True)


def get_text(file_id: str) -> str:
    """Retrieve file text content (lazy-load from disk if needed)."""
    entry = file_store.get(file_id, {})
    if entry.get('content'):
        return entry['content']
    if file_id in parsed_cache:
        return parsed_cache[file_id]
    path = entry.get('path', '')
    if path and os.path.exists(path):
        parsed = parse_file(path, entry.get('filename', ''))
        text = parsed.full_text
        parsed_cache[file_id] = text
        return text
    return ''


def should_split(file_size: int, chars: int) -> bool:
    """Determine if a file needs chunked splitting."""
    return (
        file_size > config.auto_split_threshold
        or chars > config.auto_split_max_chars
    )


def store_file(
    file_id: str, filename: str, doc_type: str, label: str,
    filepath: str, file_size: int, chars: int,
    content: str, parse_status: str, needs_split: bool,
) -> dict:
    """Store file metadata and return the entry."""
    entry = {
        'id': file_id,
        'filename': filename,
        'doc_type': doc_type,
        'label': label,
        'path': filepath,
        'content': content,
        'chars': chars,
        'size_bytes': file_size,
        'status': parse_status,
        'needs_split': needs_split,
    }
    file_store[file_id] = entry
    return entry


def parse_uploaded_file(filepath: str, filename: str) -> tuple[str, int, str]:
    """Parse an uploaded file and return (content, chars, status).

    Returns ('', 0, 'error') on failure.
    """
    try:
        parsed = parse_file(filepath, filename)
        return parsed.full_text, len(parsed.full_text), 'parsed'
    except Exception as e:
        print(f'Parse error for {filename}: {e}')
        return '', 0, 'error'


def resolve_comparison_pairs(data: dict) -> list[tuple]:
    """Resolve comparison pairs from request data.

    Supports three formats:
    1. Pair: {"doc_a_id": "...", "doc_b_id": "..."}
    2. Multi-doc: {"doc_ids": ["id1", "id2", ...]}
    3. One-to-many: {"tender_id": "...", "bid_ids": ["..."]}
    """
    # Format 1: pair
    if data.get('doc_a_id') and data.get('doc_b_id'):
        a_entry = file_store.get(data['doc_a_id'], {})
        b_entry = file_store.get(data['doc_b_id'], {})
        return [(
            data['doc_a_id'], data['doc_b_id'],
            a_entry.get('label', 'Doc A'),
            b_entry.get('label', 'Doc B'),
        )]

    # Format 2: multi-doc pairwise
    doc_ids = data.get('doc_ids', [])
    if doc_ids and len(doc_ids) >= 2:
        pairs = []
        for i in range(len(doc_ids)):
            for j in range(i + 1, len(doc_ids)):
                a_entry = file_store.get(doc_ids[i], {})
                b_entry = file_store.get(doc_ids[j], {})
                if a_entry and b_entry:
                    pairs.append((
                        doc_ids[i], doc_ids[j],
                        a_entry.get('label', f'Doc {i + 1}'),
                        b_entry.get('label', f'Doc {j + 1}'),
                    ))
        return pairs

    # Format 3: one-to-many (legacy)
    tender_id = data.get('tender_id', '')
    bid_ids = data.get('bid_ids', [])
    if tender_id and bid_ids:
        tender_entry = file_store.get(tender_id, {})
        pairs = []
        for bid_id in bid_ids:
            bid_entry = file_store.get(bid_id, {})
            if bid_entry:
                pairs.append((
                    tender_id, bid_id,
                    tender_entry.get('label', 'Tender'),
                    bid_entry.get('label', 'Bid'),
                ))
        return pairs

    return []


def run_chunked_comparison(
    tender_id: str, bid_id: str, bid_index: int,
    bid_filename: str, cfg: ComparisonConfig,
) -> ComparisonResult:
    """Execute chunked comparison for large files."""
    tender_text = get_text(tender_id)
    bid_text = get_text(bid_id)
    split_cfg = SplitConfig(max_chars_per_chunk=50000, overlap_chars=5000)

    tender_chunks = split_document(tender_text, config=split_cfg)
    bid_chunks = split_document(bid_text, config=split_cfg)

    if len(tender_chunks) == 1 and len(bid_chunks) == 1:
        return compare_documents(tender_text, bid_text, bid_index, bid_filename, cfg)

    return compare_documents_chunked(
        tender_chunks=tender_chunks,
        bid_chunks=bid_chunks,
        tender_text=tender_text,
        bid_text=bid_text,
        bid_index=bid_index,
        bid_filename=bid_filename,
        config=cfg,
    )


def run_chunked_comparison_ai(
    filtered_text: str, bid_id: str, bid_index: int,
    bid_filename: str, cfg: ComparisonConfig,
) -> ComparisonResult:
    """Execute chunked comparison with AI-filtered text."""
    bid_text = get_text(bid_id)
    split_cfg = SplitConfig(max_chars_per_chunk=50000, overlap_chars=5000)
    tender_chunks = split_document(filtered_text, config=split_cfg)
    bid_chunks = split_document(bid_text, config=split_cfg)
    if len(tender_chunks) == 1 and len(bid_chunks) == 1:
        return compare_documents(filtered_text, bid_text, bid_index, bid_filename, cfg)
    return compare_documents_chunked(
        tender_chunks, bid_chunks, filtered_text, bid_text,
        bid_index, bid_filename, cfg,
    )


def format_pair_result(
    result: ComparisonResult, doc_a_id: str, doc_b_id: str,
    label_a: str, label_b: str, severity: dict,
) -> dict:
    """Format comparison result for API response."""
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


def run_ai_filter(
    tender_text: str, api_key: str, base_url: str, model: str,
):
    """Run AI filter on tender text and return FilteredTender."""
    return filter_tender_requirements(
        tender_text=tender_text,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )


def delete_file(file_id: str) -> None:
    """Remove a file from store and disk."""
    if file_id in file_store:
        entry = file_store.pop(file_id)
        parsed_cache.pop(file_id, None)
        try:
            os.remove(entry['path'])
        except OSError:
            pass


def clear_all_files() -> None:
    """Remove all files from store and disk."""
    for entry in file_store.values():
        try:
            os.remove(entry['path'])
        except OSError:
            pass
    file_store.clear()
    parsed_cache.clear()
