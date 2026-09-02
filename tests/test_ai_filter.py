"""Edge case tests for AI filter module — adjusted rate calculation and parsing."""

import pytest
from unittest.mock import patch, MagicMock
from src.ai_filter import (
    _parse_segment_analysis, SegmentAnalysis, ComparisonAnalysis,
    analyze_comparison_segments,
)

# OpenAI is imported inside functions, so patch at the openai package level
OPENAI_PATCH = 'openai.OpenAI'


class TestParseSegmentAnalysis:
    """Test _parse_segment_analysis with various edge cases."""

    def test_parse_empty_response(self):
        """JSON parse failure returns empty list."""
        batch = [{'id': 0, 'tender_text': 'text A', 'bid_text': 'text B', 'similarity': 0.8}]
        result = _parse_segment_analysis('not json at all', batch)
        assert result == []

    def test_parse_empty_json_array(self):
        """Empty JSON array returns empty list."""
        batch = [{'id': 0, 'tender_text': 'text A', 'bid_text': 'text B', 'similarity': 0.8}]
        result = _parse_segment_analysis('[]', batch)
        assert result == []

    def test_parse_missing_items(self):
        """LLM returns fewer items than batch — missing ones filled as actual_duplication."""
        batch = [
            {'id': 0, 'tender_text': 'text A', 'bid_text': 'text B', 'similarity': 0.8},
            {'id': 1, 'tender_text': 'text C', 'bid_text': 'text D', 'similarity': 0.9},
        ]
        response = '[{"segment_id": 0, "classification": "compliance_response", "reason": "test", "adjusted_similarity": 0.0}]'
        result = _parse_segment_analysis(response, batch)

        assert len(result) == 2
        assert result[0].classification == 'compliance_response'
        assert result[1].classification == 'actual_duplication'
        assert '保守标记' in result[1].reason

    def test_parse_invalid_classification(self):
        """Invalid classification value corrected to actual_duplication."""
        batch = [{'id': 0, 'tender_text': 'text', 'bid_text': 'text', 'similarity': 0.5}]
        response = '[{"segment_id": 0, "classification": "invalid_type", "reason": "", "adjusted_similarity": 0.5}]'
        result = _parse_segment_analysis(response, batch)

        assert len(result) == 1
        assert result[0].classification == 'actual_duplication'

    def test_parse_segment_id_mismatch(self):
        """When segment_id doesn't match, fall back to index position."""
        batch = [{'id': 5, 'tender_text': 'text', 'bid_text': 'text', 'similarity': 0.7}]
        response = '[{"segment_id": 99, "classification": "compliance_response", "reason": "ok", "adjusted_similarity": 0.0}]'
        result = _parse_segment_analysis(response, batch)

        assert len(result) == 1
        assert result[0].classification == 'compliance_response'

    def test_parse_full_text_preserved(self):
        """Segment text is preserved from original batch, not truncated."""
        long_text = 'A' * 1000
        batch = [{'id': 0, 'tender_text': long_text, 'bid_text': 'B', 'similarity': 0.9}]
        response = '[{"segment_id": 0, "classification": "actual_duplication", "reason": "dup", "adjusted_similarity": 0.9}]'
        result = _parse_segment_analysis(response, batch)

        assert len(result[0].tender_text) == 1000
        assert result[0].tender_text == long_text


class TestAnalyzeComparisonSegments:
    """Test analyze_comparison_segments with mocked LLM calls."""

    def test_empty_segments_no_llm_call(self):
        """When segments is empty, LLM is not called, adjusted = original."""
        results = [{
            'label_a': 'A', 'label_b': 'B',
            'segments': [],
            'duplicate_percentage': 50.0,
            'matched_chars': 0,
            'total_tender_chars': 100,
        }]

        with patch(OPENAI_PATCH):
            analyses = analyze_comparison_segments(results, 'fake_key')

        assert len(analyses) == 1
        assert analyses[0].original_percentage == 50.0
        assert analyses[0].adjusted_percentage == 50.0
        assert '无匹配段落' in analyses[0].summary

    def test_json_parse_failure_fallback(self):
        """When LLM returns non-JSON, segments fallback to actual_duplication."""
        seg_text = 'A' * 80  # 80 chars
        results = [{
            'label_a': 'A', 'label_b': 'B',
            'segments': [{'id': 0, 'tender_text': seg_text, 'bid_text': 'text B', 'similarity': 0.8}],
            'duplicate_percentage': 40.0,
            'matched_chars': 80,
            'total_tender_chars': 200,
        }]

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = 'this is not json'
        mock_client.chat.completions.create.return_value = mock_response

        with patch(OPENAI_PATCH, return_value=mock_client):
            analyses = analyze_comparison_segments(results, 'fake_key')

        assert len(analyses) == 1
        # All segments fallback to actual_duplication
        assert all(
            sa.classification == 'actual_duplication'
            for sa in analyses[0].segment_analyses
        )
        # adjusted = (80/200)*100 = 40.0 = original (all marked as dup)
        assert analyses[0].adjusted_percentage == 40.0

    def test_adjusted_rate_calculation(self):
        """Adjusted rate = (actual_dup_chars / total_tender) * 100."""
        results = [{
            'label_a': 'A', 'label_b': 'B',
            'segments': [
                {'id': 0, 'tender_text': 'A' * 100, 'bid_text': 'B', 'similarity': 0.9},
                {'id': 1, 'tender_text': 'C' * 50, 'bid_text': 'D', 'similarity': 0.8},
            ],
            'duplicate_percentage': 75.0,
            'matched_chars': 150,
            'total_tender_chars': 200,
        }]

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '[{"segment_id": 0, "classification": "compliance_response", "reason": "param response", "adjusted_similarity": 0.0},'
            '{"segment_id": 1, "classification": "actual_duplication", "reason": "copy", "adjusted_similarity": 0.8}]'
        )
        mock_client.chat.completions.create.return_value = mock_response

        with patch(OPENAI_PATCH, return_value=mock_client):
            analyses = analyze_comparison_segments(results, 'fake_key')

        assert len(analyses) == 1
        a = analyses[0]
        assert a.original_percentage == 75.0
        assert a.compliance_chars == 100
        assert a.actual_duplication_chars == 50
        assert a.adjusted_percentage == 25.0  # 50/200 * 100

    def test_llm_exception_fallback(self):
        """When LLM call throws, segments fallback to actual_duplication."""
        seg_text = 'T' * 60  # 60 chars
        results = [{
            'label_a': 'A', 'label_b': 'B',
            'segments': [{'id': 0, 'tender_text': seg_text, 'bid_text': 'text', 'similarity': 0.9}],
            'duplicate_percentage': 60.0,
            'matched_chars': 60,
            'total_tender_chars': 100,
        }]

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception('network error')

        with patch(OPENAI_PATCH, return_value=mock_client):
            analyses = analyze_comparison_segments(results, 'fake_key')

        assert len(analyses) == 1
        # adjusted = (60/100)*100 = 60.0 = original (all marked as dup)
        assert analyses[0].adjusted_percentage == 60.0
        assert all(
            sa.classification == 'actual_duplication'
            for sa in analyses[0].segment_analyses
        )
        assert 'AI 分析失败' in analyses[0].segment_analyses[0].reason
