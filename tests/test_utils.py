"""Tests for utility functions — happy path + boundary conditions."""

import os
import tempfile
import pytest

from src.utils import (
    allowed_file,
    generate_file_id,
    detect_encoding,
    normalize_text,
    format_percentage,
    severity_label,
    truncate_text,
)


def test_allowed_file_valid_extensions():
    """Happy path: valid file extensions are accepted."""
    assert allowed_file('document.docx') is True
    assert allowed_file('document.doc') is True
    assert allowed_file('document.pdf') is True
    assert allowed_file('document.txt') is True


def test_allowed_file_invalid_extensions():
    """Boundary: invalid extensions are rejected."""
    assert allowed_file('document.xlsx') is False
    assert allowed_file('document.jpg') is False
    assert allowed_file('document.rtf') is False
    assert allowed_file('document') is False


def test_allowed_file_case_insensitive():
    """Boundary: uppercase extensions are accepted."""
    assert allowed_file('document.DOCX') is True
    assert allowed_file('document.DOC') is True
    assert allowed_file('document.PDF') is True


def test_generate_file_id_unique():
    """Happy path: generates unique IDs for same filename."""
    id1 = generate_file_id('test.docx')
    id2 = generate_file_id('test.docx')
    assert id1 != id2
    assert len(id1) > 0


def test_generate_file_id_safe_name():
    """Boundary: special characters are sanitized."""
    fid = generate_file_id('test file (1).docx')
    assert '(' not in fid
    assert ')' not in fid
    assert ' ' not in fid or '_' in fid


def test_normalize_text_removes_extra_whitespace():
    """Happy path: normalizes whitespace."""
    text = 'line1\n\n\n\nline2\n   \nline3'
    result = normalize_text(text)
    assert '\n\n\n' not in result


def test_normalize_text_fullwidth_space():
    """Boundary: fullwidth spaces are converted."""
    text = 'hello\u3000world'
    result = normalize_text(text)
    assert '\u3000' not in result


def test_format_percentage():
    """Happy path: formats percentage correctly."""
    assert format_percentage(12.345) == '12.3%'


def test_severity_label_high():
    """Boundary: high severity for >= 30%."""
    result = severity_label(35.0)
    assert result['level'] == 'high'


def test_severity_label_medium():
    """Boundary: medium severity for >= 10%."""
    result = severity_label(15.0)
    assert result['level'] == 'medium'


def test_severity_label_low():
    """Boundary: low severity for < 10%."""
    result = severity_label(5.0)
    assert result['level'] == 'low'


def test_severity_label_boundary():
    """Boundary: exactly 30% and 10%."""
    assert severity_label(30.0)['level'] == 'high'
    assert severity_label(10.0)['level'] == 'medium'
    assert severity_label(9.9)['level'] == 'low'


def test_truncate_text_short():
    """Boundary: short text is not truncated."""
    assert truncate_text('short', 100) == 'short'


def test_truncate_text_long():
    """Happy path: long text is truncated with ellipsis."""
    text = 'a' * 300
    result = truncate_text(text, 200)
    assert len(result) == 201
    assert result.endswith('\u2026')


def test_detect_encoding_utf8():
    """Happy path: detects UTF-8 encoding."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write('hello world')
        path = f.name
    try:
        assert detect_encoding(path) == 'utf-8'
    finally:
        os.remove(path)
