#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_s9a_search_unicode.py
================================
Verification test suite for Slice S9a:
- SPAN-NFKC-PER-CHAR: Japanese combining characters (dakuten \u3099, handakuten \u309a)
  and half-width katakana voiced marks (\uff9e, \uff9f) matching and span fidelity.
- Unicode NFKC normalization equivalence between whole-string norm_search() and
  normalize_with_spans().
- Source text highlight span accuracy with combining characters.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.search_engine import ProjectSearchEngine
from core.story_ast import norm_search


class TestS9aSearchUnicode(unittest.TestCase):
    """Test suite for Japanese Unicode normalization and combining character span fidelity."""

    def test_01_halfwidth_katakana_voiced_sound_marks(self):
        """Half-width katakana with voiced mark ('ｶﾞ' \uff76\uff9e) must normalize to 'ガ' and match query."""
        source_text = "こんにちは、ｶﾞｰﾃﾞﾝへようこそ！"
        norm_txt, spans = ProjectSearchEngine._norm_search_with_spans(source_text)

        # Query normalized with standard norm_search
        query = "ガーデン"
        norm_q = norm_search(query)

        self.assertIn("ガーデン", norm_txt)
        idx = norm_txt.find(norm_q)
        self.assertNotEqual(idx, -1, f"Normalized text '{norm_txt}' should contain query '{norm_q}'")

        # Check source span of 'ガ'
        src_start, src_end = spans[idx]
        matched_source = source_text[src_start:src_end]
        self.assertEqual(matched_source, "ｶﾞ", f"Expected 'ｶﾞ' in source span, got {matched_source!r}")

    def test_02_halfwidth_katakana_semivoiced_sound_marks(self):
        """Half-width katakana with semi-voiced mark ('ﾊﾟ' \uff8a\uff9f) must normalize to 'パ'."""
        source_text = "特製ﾊﾟﾝｹｰｷはいかが？"
        norm_txt, spans = ProjectSearchEngine._norm_search_with_spans(source_text)

        query = "パンケーキ"
        norm_q = norm_search(query)

        self.assertIn("パンケーキ", norm_txt)
        idx = norm_txt.find(norm_q)
        self.assertNotEqual(idx, -1)

        src_start, src_end = spans[idx]
        self.assertEqual(source_text[src_start:src_end], "ﾊﾟ")

    def test_03_fullwidth_combining_voiced_sound_marks(self):
        """Full-width decomposed hiragana ('か' + \u3099) must match precomposed 'が'."""
        decomposed_ga = "か\u3099"
        source_text = f"これ{decomposed_ga}本物です。"
        norm_txt, spans = ProjectSearchEngine.normalize_with_spans(source_text)

        query = "これが本物"
        norm_q = norm_search(query)

        idx = norm_txt.find(norm_q)
        self.assertNotEqual(idx, -1, f"Expected '{norm_q}' in '{norm_txt}'")

        # The 'が' in norm_txt should map back to decomposed_ga in source_text
        ga_idx = norm_txt.find("が")
        ga_start, ga_end = spans[ga_idx]
        self.assertEqual(source_text[ga_start:ga_end], decomposed_ga)

    def test_04_fullwidth_combining_semivoiced_sound_marks(self):
        """Full-width decomposed hiragana ('は' + \u309a) must match precomposed 'ぱ'."""
        decomposed_pa = "は\u309a"
        source_text = f"リンゴ{decomposed_pa}イをお届け！"
        norm_txt, spans = ProjectSearchEngine.normalize_with_spans(source_text)

        query = "リンゴぱイ"
        norm_q = norm_search(query)

        idx = norm_txt.find(norm_q)
        self.assertNotEqual(idx, -1)

        pa_idx = norm_txt.find("ぱ")
        src_start, src_end = spans[pa_idx]
        self.assertEqual(source_text[src_start:src_end], decomposed_pa)

    def test_05_span_length_matches_normalized_text_length(self):
        """Every character in normalized text must have a corresponding (start, end) source span."""
        complex_samples = [
            "ｶﾞｷﾞｸﾞｹﾞｺﾞ ﾊﾟﾋﾟﾌﾟﾍﾟﾎﾟ",
            "テスト\u3099モジ\u309aレツ",
            "【称号】「{playername}の相棒」--登場！",
            "\\n改行を含む\r\nテキスト--2",
        ]
        for sample in complex_samples:
            norm_txt, spans = ProjectSearchEngine._norm_search_with_spans(sample)
            self.assertEqual(
                len(norm_txt),
                len(spans),
                f"Mismatch between norm_txt length ({len(norm_txt)}) and spans ({len(spans)}) for: {sample!r}",
            )
            # Verify each span is valid in source text
            for ch, (s, e) in zip(norm_txt, spans):
                self.assertGreaterEqual(s, 0)
                self.assertLessEqual(e, len(sample))
                self.assertLess(s, e)

    def test_06_norm_search_equivalence(self):
        """normalize_with_spans(s)[0] must be identical to norm_search(s)."""
        test_strings = [
            "ｶﾞｰﾃﾞﾝ ﾊﾟﾝｹｰｷ",
            "プレイヤー：{0}！\\n次のバトルへ",
            "全角　スペースと--ダッシュ---テスト",
            "きょうは　いい　てんき　ですね。",
        ]
        for s in test_strings:
            norm_from_spans, _ = ProjectSearchEngine._norm_search_with_spans(s)
            norm_direct = norm_search(s)
            self.assertEqual(
                norm_from_spans,
                norm_direct,
                f"_norm_search_with_spans and norm_search mismatch on {s!r}: '{norm_from_spans}' != '{norm_direct}'",
            )


if __name__ == "__main__":
    unittest.main()
