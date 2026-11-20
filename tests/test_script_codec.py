#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests.test_script_codec - Comprehensive unit test suite for CSIF codec.
Validates AGENTS.md Rules 20 & 26 and Phase 2 PART A specifications.
"""
import unittest

from core.script_codec import (
    DialogueBlock,
    MetadataBlock,
    apply_to_document,
    parse,
    sanitize_speaker,
    serialize,
    sniff_format,
)
from core.story_ast import BoxSnapshot, Record, StoryDocument


class TestScriptCodec(unittest.TestCase):

    def setUp(self):
        # Create a sample StoryDocument with 3 boxes and metadata
        self.doc = StoryDocument([
            Record(cmd_id=0, cmd_name="fade", args=["Chapter Title"]),
            Record(cmd_id=1, cmd_name="log", args=["Chapter Synopsis"]),
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Good morning, my Lord."]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=35, cmd_name="tag", args=["She smiles warmly."]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Let's eat breakfast!"]),
        ])

    def test_sniff_format(self):
        self.assertEqual(sniff_format("@@Peco\nHello"), "csif")
        self.assertEqual(sniff_format("@@_\nNarration"), "csif")
        self.assertEqual(sniff_format("@@!title\nMy Title"), "csif")
        self.assertEqual(sniff_format("=== [BOX:0|Speaker:A] ===\nText"), "legacy_box")
        self.assertEqual(sniff_format("Block 1\n\n\nBlock 2"), "triple_enter")
        self.assertEqual(sniff_format("Para 1\n\nPara 2"), "paragraphs")
        self.assertEqual(sniff_format("Single line"), "plain")

    def test_speaker_sanitization(self):
        # Strip Cf (zero-width space \u200b) and Cc (control char \x07), map \u00a0 and \u3000
        dirty = "\u200b Kokkoro \u00a0\u3000\x07"
        self.assertEqual(sanitize_speaker(dirty), "Kokkoro")
        self.assertEqual(sanitize_speaker("_"), "")
        self.assertEqual(sanitize_speaker(""), "")

    def test_csif_roundtrip_lossless(self):
        text = (
            "@@!title\nChapter 1\n"
            "@@!summary\nSynopsis line 1\nSynopsis line 2\n"
            "@@Kokkoro\nHello, my Lord.\n"
            "@@_\nNarration line.\n"
            "@@Pecorine\nFood is ready!\n"
        )
        res = parse(text)
        self.assertEqual(res.metadata.title, "Chapter 1")
        self.assertEqual(res.metadata.summary, "Synopsis line 1\nSynopsis line 2")
        self.assertEqual(len(res.blocks), 3)
        self.assertEqual(res.blocks[0].speaker, "Kokkoro")
        self.assertEqual(res.blocks[0].text, "Hello, my Lord.")
        self.assertTrue(res.blocks[1].is_narration)
        self.assertEqual(res.blocks[1].text, "Narration line.")
        self.assertEqual(res.blocks[2].speaker, "Pecorine")
        self.assertEqual(res.blocks[2].text, "Food is ready!")

    def test_eof_without_trailing_newline(self):
        text = "@@Kokkoro\nLine 1\nLine 2"
        res = parse(text)
        self.assertEqual(len(res.blocks), 1)
        self.assertEqual(res.blocks[0].speaker, "Kokkoro")
        self.assertEqual(res.blocks[0].text, "Line 1\nLine 2")

    def test_blank_lines_inside_bodies(self):
        text = "@@Kokkoro\nLine 1\n\nLine 2\n\nLine 3\n@@Pecorine\nDone."
        res = parse(text)
        self.assertEqual(len(res.blocks), 2)
        self.assertEqual(res.blocks[0].text, "Line 1\n\nLine 2\n\nLine 3")
        self.assertEqual(res.blocks[1].text, "Done.")

    def test_escaped_at_at(self):
        text = "@@Kokkoro\nNormal line\n\\@@escaped tag\nAnother line"
        res = parse(text)
        self.assertEqual(len(res.blocks), 1)
        self.assertEqual(res.blocks[0].text, "Normal line\n@@escaped tag\nAnother line")

        # Serializing back must escape the @@ line
        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Normal line\n@@escaped tag\nAnother line"])
        ])
        s = serialize(doc, include_metadata=False)
        self.assertIn("\\@@escaped tag", s)

    def test_crlf_and_bom_normalization(self):
        text = "\ufeff@@Kokkoro\r\nHello\r\nworld!\r\n@@_\r\nNarration\r\n"
        res = parse(text)
        self.assertEqual(len(res.blocks), 2)
        self.assertEqual(res.blocks[0].text, "Hello\nworld!")
        self.assertEqual(res.blocks[1].text, "Narration")

    def test_code_fence_stripping(self):
        fenced = "```markdown\n@@Kokkoro\nHello\n```"
        res = parse(fenced)
        self.assertEqual(len(res.blocks), 1)
        self.assertEqual(res.blocks[0].text, "Hello")
        self.assertTrue(any("code fence stripped" in w.lower() for w in res.warnings))

        # Inner code fence must not be stripped
        inner_fence = "@@Kokkoro\nHere is code:\n```python\nprint(1)\n```\nDone."
        res2 = parse(inner_fence)
        self.assertEqual(len(res2.blocks), 1)
        self.assertIn("```python", res2.blocks[0].text)

    def test_metadata_rejected_after_dialogue(self):
        bad_text = "@@Kokkoro\nHello\n@@!title\nToo Late Title"
        with self.assertRaises(ValueError):
            parse(bad_text)

    def test_sparse_addressing_and_rejections(self):
        sparse_text = "@@#1|Kokkoro\nText 1\n@@#3|Pecorine\nText 3\n"
        res = parse(sparse_text)
        self.assertTrue(res.is_sparse)
        self.assertEqual(len(res.blocks), 2)
        self.assertEqual(res.blocks[0].index, 1)
        self.assertEqual(res.blocks[1].index, 3)

        # Reject mixed sparse and non-sparse
        mixed_text = "@@#1|Kokkoro\nText 1\n@@Pecorine\nText 2\n"
        with self.assertRaises(ValueError):
            parse(mixed_text)

        # Reject duplicate sparse index
        duplicate_text = "@@#1|Kokkoro\nText 1\n@@#1|Pecorine\nText 2\n"
        with self.assertRaises(ValueError):
            parse(duplicate_text)

        # Reject invalid sparse index (index 0)
        invalid_text = "@@#0|Kokkoro\nText\n"
        with self.assertRaises(ValueError):
            parse(invalid_text)

    def test_serialize_contiguous_vs_sparse(self):
        # Contiguous selection: numberless
        s_contig = serialize(self.doc, box_indices=[0, 1], include_metadata=False)
        self.assertIn("@@Kokkoro\n", s_contig)
        self.assertIn("@@_\n", s_contig)
        self.assertNotIn("@@#", s_contig)

        # Non-contiguous selection: sparse 1-based
        s_sparse = serialize(self.doc, box_indices=[0, 2], include_metadata=False)
        self.assertIn("@@#1|Kokkoro\n", s_sparse)
        self.assertIn("@@#3|Pecorine\n", s_sparse)

    def test_apply_to_document_insert(self):
        csif = "@@Karyl\nWhat are you doing?\n@@_\nShe sighs.\n"
        res = parse(csif)
        init_count = len(self.doc.boxes)
        # Insert after box 0 (at index 1)
        applied = apply_to_document(self.doc, res, mode="insert", start_box_index=1)
        self.assertEqual(applied, 2)
        self.assertEqual(len(self.doc.boxes), init_count + 2)
        self.assertEqual(self.doc.boxes[1].speaker, "Karyl")
        self.assertEqual(self.doc.boxes[1].clean_text, "What are you doing?")
        self.assertEqual(self.doc.boxes[2].kind, "tag")
        self.assertEqual(self.doc.boxes[2].clean_text, "She sighs.")

    def test_apply_to_document_replace_no_op(self):
        # Serializing doc and replacing back is a content no-op
        orig_speakers = [b.speaker for b in self.doc.boxes]
        orig_texts = [b.clean_text for b in self.doc.boxes]

        csif = serialize(self.doc, include_metadata=True)
        res = parse(csif)
        applied = apply_to_document(self.doc, res, mode="replace", start_box_index=0)
        self.assertEqual(applied, len(self.doc.boxes))

        new_speakers = [b.speaker for b in self.doc.boxes]
        new_texts = [b.clean_text for b in self.doc.boxes]
        self.assertEqual(orig_speakers, new_speakers)
        self.assertEqual(orig_texts, new_texts)

    def test_apply_sparse_rejects_out_of_range(self):
        bad_sparse = "@@#99|Kokkoro\nHello\n"
        res = parse(bad_sparse)
        with self.assertRaises(IndexError):
            apply_to_document(self.doc, res)


if __name__ == "__main__":
    unittest.main()
