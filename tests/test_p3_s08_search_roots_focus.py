#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_p3_s08_search_roots_focus.py
=======================================
Verification test suite for Phase 2.5 Slice S08:
- BUG-21: Case-sensitive whitespace-insensitive search in story_ast.norm_search()
  and ProjectSearchEngine._norm_search_with_spans() preserving S9a Unicode equivalence.
- BUG-22: Search decode/error reporting in UI (never silently 0), Grok-E02 snapshot failure
  isolation (never pass live orig_doc), monotonic self._search_seq message guard,
  and accurate raw-text fallback spans (QW-E06, never fabricate 0..len(box)).
- BUG-23: Replace (never append indefinitely) project roots when project_folder changes,
  clean bounded (Text, RedirectedResources) directories (never plugins/ or config/),
  no auto-injection of unrelated input/output (GEM-N01).
- BUG-30: Retain card text widget focus on search jump in Continuous View (never steal to
  txt_continuous), update gutter_clean in _on_dialogue_edited(), and return bool from
  _on_card_text_edited() & _on_box0_metadata_edited() to guard _dirty_state_changed() on arrow keys.

Defect Probes (MUST FAIL before patch, PASS after patch):
- Probe 1 (BUG-21): Match Case ON + Ignore Whitespace ON matches 'Hero'/'Ｈｅｒｏ' and rejects 'hero'/'ｈｅｒｏ'.
- Probe 2 (BUG-22): Corrupt/unreadable file recorded in skipped list; failed snapshot skips file instead of
  passing live orig_doc; stale search_seq messages discarded; raw-text fallback maps spans accurately.
- Probe 3 (BUG-23): Switching project_folder removes old project; BepInEx root resolves strictly to
  existing Text / RedirectedResources (OR condition, never plugins/ or config/); no input/output auto-injection.
- Probe 4 (BUG-30): Search jump in Continuous View focuses card text widget (not txt_continuous);
  Page View dialogue edit updates gutter_clean; arrow keys in card & Box 0 trigger 0 file list refreshes.

Regression Guards:
- Guard 1: Direct lightweight assertion verifying S9a combining character normalization equivalence.
- Guard 2: Direct lightweight assertion verifying _run_background_search always posts finished in finally.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import misora
from core.search_engine import ProjectSearchEngine, SearchOptions, SearchResult
from core.story_ast import Record, StoryDocument, norm_search


class TestP3S08SearchRootsFocus(unittest.TestCase):
    """S08: Search Match-Case/Errors/Snapshots/Spans, Bounded Project Roots & Search Focus/Gutter/No-Op KeyRelease."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s08_"))
        self._patches = [
            patch.object(misora.messagebox, "askyesno", return_value=True),
            patch.object(misora.messagebox, "showinfo", return_value=None),
            patch.object(misora.messagebox, "showwarning", return_value=None),
            patch.object(misora.messagebox, "showerror", return_value=None),
            patch.object(misora.messagebox, "askokcancel", return_value=True),
            patch.object(misora.messagebox, "askyesnocancel", return_value=False),
        ]
        for p in self._patches:
            p.start()

        self._orig_config_path = misora.CONFIG_PATH
        misora.CONFIG_PATH = self.tmp_dir / "misora_config.json"
        misora.CONFIG_PATH.write_text("{}", encoding="utf-8")

        self.app = misora.MisoraApp(restore_session=False)
        self.app.withdraw()
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.var_preview_compiled.set(False)
        self.app.var_continuous_view.set(False)

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass
        for p in self._patches:
            p.stop()
        misora.CONFIG_PATH = self._orig_config_path
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Defect Probe 1: BUG-21 (Case-Sensitive Whitespace-Insensitive Search)
    # -------------------------------------------------------------------------
    def test_probe_1_bug_21_case_sensitive_whitespace_search(self):
        """[Probe 1 — BUG-21] Match Case ON + Ignore Whitespace ON matches 'Hero'/'Ｈｅｒｏ' and rejects 'hero'/'ｈｅｒｏ'."""
        # 1. Direct function tests for norm_search(s, match_case=True)
        # Pre-patch: norm_search does not accept match_case or unconditionally calls casefold()
        norm_case_on = norm_search("Hero", match_case=True)
        self.assertEqual(norm_case_on, "Hero", f"norm_search('Hero', match_case=True) must preserve case, got {norm_case_on!r}")

        norm_case_off = norm_search("Hero", match_case=False)
        self.assertEqual(norm_case_off, "hero", f"norm_search('Hero', match_case=False) must casefold, got {norm_case_off!r}")

        # Full-width Unicode (Guard 4 requirement)
        norm_fw_on = norm_search("Ｈｅｒｏ", match_case=True)
        self.assertEqual(norm_fw_on, "Hero", f"norm_search('Ｈｅｒｏ', match_case=True) must NFKC normalize to 'Hero', got {norm_fw_on!r}")

        norm_fw_off = norm_search("Ｈｅｒｏ", match_case=False)
        self.assertEqual(norm_fw_off, "hero", f"norm_search('Ｈｅｒｏ', match_case=False) must casefold to 'hero', got {norm_fw_off!r}")

        # 2. Direct tests for _norm_search_with_spans(s, match_case=True)
        spans_txt_on, spans_on = ProjectSearchEngine._norm_search_with_spans("Our Hero arrives", match_case=True)
        self.assertEqual(spans_txt_on, "OurHeroarrives")
        self.assertEqual(spans_txt_on, norm_search("Our Hero arrives", match_case=True))

        spans_txt_off, spans_off = ProjectSearchEngine._norm_search_with_spans("Our Hero arrives", match_case=False)
        self.assertEqual(spans_txt_off, "ourheroarrives")
        self.assertEqual(spans_txt_off, norm_search("Our Hero arrives", match_case=False))

        # 3. Matcher compiled with match_case=True, ignore_whitespace=True
        opts_case_on = SearchOptions(query="Hero", match_case=True, ignore_whitespace=True)
        matcher_on = ProjectSearchEngine._compile_matcher(opts_case_on)

        # Must match 'Hero' (with spaces)
        hits_hero = matcher_on("A true Hero emerges!")
        self.assertEqual(len(hits_hero), 1)
        start, end, m_text = hits_hero[0]
        self.assertEqual(m_text, "Hero")
        self.assertEqual("A true Hero emerges!"[start:end], "Hero")

        # Must match full-width 'Ｈ ｅ ｒ ｏ'
        hits_fw = matcher_on("伝説の Ｈ ｅ ｒ ｏ 参上")
        self.assertEqual(len(hits_fw), 1)

        # MUST REJECT lowercase 'hero'
        hits_lower = matcher_on("A true hero emerges!")
        self.assertEqual(len(hits_lower), 0, "Match Case ON must reject 'hero' when querying 'Hero'")

        # MUST REJECT full-width lowercase 'ｈｅｒｏ'
        hits_fw_lower = matcher_on("伝説の ｈｅｒｏ 参上")
        self.assertEqual(len(hits_fw_lower), 0, "Match Case ON must reject 'ｈｅｒｏ' when querying 'Hero'")

    # -------------------------------------------------------------------------
    # Defect Probe 2: BUG-22 (Search Errors, Safe Snapshots, Sequences & Raw Spans)
    # -------------------------------------------------------------------------
    def test_probe_2_bug_22_errors_snapshots_sequences_spans(self):
        """[Probe 2 — BUG-22] Corrupt file appears in skipped list; failed snapshot skips file (never live doc);
        stale search_seq messages discarded; raw-text fallback maps spans accurately (never fabricates 0..len)."""
        engine = ProjectSearchEngine()

        # Part A: Corrupt / unreadable file reported in skipped list (never silently 0)
        search_dir = self.tmp_dir / "probe2_search"
        search_dir.mkdir(parents=True, exist_ok=True)
        valid_file = search_dir / "valid.txt"
        valid_file.write_text("Hello valid search target", encoding="utf-8")

        corrupt_file = search_dir / "corrupt.txt"
        corrupt_file.write_bytes(b"Invalid non-utf8 \x80\x81 byte sequence")

        skipped_reported = []
        def on_err(fp, reason):
            skipped_reported.append((Path(fp), reason))

        opts = SearchOptions(query="target")
        res = engine.search_directory(search_dir, opts, on_error=on_err)

        self.assertEqual(len(res), 1, "Should find match in valid.txt")
        self.assertGreaterEqual(len(skipped_reported), 1, "Corrupt file must be reported via on_error (never silently 0)")
        skipped_paths = [Path(p).resolve() for p, _ in skipped_reported]
        self.assertIn(corrupt_file.resolve(), skipped_paths, "corrupt.txt must appear in skipped entries")

        # Part B: Grok-E02 snapshot failure isolation & open plain-text snapshot
        open_bundle_path = (self.tmp_dir / "open_story.unity3d").resolve()
        mock_doc = MagicMock()
        type(mock_doc).records = PropertyMock(side_effect=RuntimeError("Simulated snapshot clone failure"))

        self.app.open_documents[open_bundle_path] = {"doc": mock_doc, "dirty": False}

        # Also open plain-text buffer with unsaved edit
        open_text_path = (self.tmp_dir / "open_script.txt").resolve()
        open_text_path.write_text("Saved disk content", encoding="utf-8")
        self.app.open_documents[open_text_path] = {
            "plain_text": "Unsaved in-memory plain text with SecretKeyword target",
            "dirty": True
        }

        self.app.search_var.set("SecretKeyword")
        self.app.scope_var.set("current")

        captured_mem_docs = {}
        captured_skip_paths = set()

        def spy_background_search(paths, options, mem_docs=None, search_seq=1, skip_paths=None, initial_skipped=None, *args, **kwargs):
            if mem_docs:
                captured_mem_docs.update(mem_docs)
            if skip_paths:
                captured_skip_paths.update(skip_paths)
            self.app.search_queue.put(("finished", 0, [], search_seq))

        with patch.object(self.app, "_run_background_search", side_effect=spy_background_search):
            self.app.on_start_search()
            if getattr(self.app, "_search_thread", None):
                self.app._search_thread.join(timeout=2.0)

        # Grok-E02: mock_doc must NEVER be passed as live orig_doc on snapshot failure
        self.assertNotIn(open_bundle_path, captured_mem_docs.values(), "Grok-E02: live mutable orig_doc must NEVER be passed on snapshot failure")
        self.assertIn(open_bundle_path, captured_skip_paths, "Grok-E02: failed snapshot path must be added to skip_paths")

        # Open plain text buffer must be snapshotted
        self.assertIn(open_text_path, captured_mem_docs, "Open plain-text document must be snapshotted with normalized Path key")
        self.assertIn("SecretKeyword", captured_mem_docs[open_text_path])

        # Part C: Monotonic search sequence guard
        initial_seq = getattr(self.app, "_search_seq", 0)
        self.assertGreater(initial_seq, 0, "self._search_seq must be initialized and incremented")

        # Post a message with stale search sequence
        stale_seq = initial_seq - 1
        stale_result = SearchResult(
            file_path=Path("stale.txt"), file_type="text", line_number=1, box_index=None,
            speaker="", full_text="stale", match_snippet="stale", start_pos=0, end_pos=5
        )
        self.app.search_queue.put(("batch", [stale_result], stale_seq))
        self.app._process_search_queue()

        self.assertEqual(len(self.app.active_search_results), 0, "Stale search_seq messages must be discarded")

        # Part D: QW-E06 raw-text fallback span accuracy (never fabricate 0..len(box.clean_text))
        recs = [
            Record(cmd_id=6, cmd_name="print", args=["Speaker", "Hello {0} World!"])
        ]
        doc = StoryDocument(recs)
        raw_opts = SearchOptions(query="{0}", ignore_whitespace=False)
        box_res = engine.search_file(Path("fake.unity3d"), raw_opts, doc=doc)

        self.assertEqual(len(box_res), 1)
        r = box_res[0]
        # In clean_text: "Hello {playername} World!"
        # '{playername}' span is (6, 18). Total length is 25.
        clean_len = len(doc.boxes[0].clean_text)
        self.assertNotEqual((r.start_pos, r.end_pos), (0, clean_len),
                            "QW-E06: raw match span must NOT fabricate full-box (0, len(clean_text))")
        self.assertEqual((r.start_pos, r.end_pos), (6, 18),
                         "Raw {0} match must map to {playername} span in clean_text")

    # -------------------------------------------------------------------------
    # Defect Probe 3: BUG-23 (Bounded Project Roots & Replacement)
    # -------------------------------------------------------------------------
    def test_probe_3_bug_23_bounded_project_roots_and_replacement(self):
        """[Probe 3 — BUG-23] Switching project_folder removes old project completely;
        BepInEx root resolves strictly to Text & RedirectedResources (OR condition, never plugins/ or config/)."""
        proj_a = self.tmp_dir / "ProjA"
        proj_a.mkdir(parents=True, exist_ok=True)
        (proj_a / "Text").mkdir(parents=True, exist_ok=True)

        proj_b = self.tmp_dir / "ProjB"
        proj_b.mkdir(parents=True, exist_ok=True)
        (proj_b / "Text").mkdir(parents=True, exist_ok=True)

        # 1. Set ProjA
        self.app.scope_var.set("project")
        self.app.folder_path_var.set(str(proj_a))
        self.app._on_folder_path_var_trace()

        self.assertTrue(any(proj_a in p.parents or p == proj_a or p == proj_a / "Text" for p in self.app.xuat_search_roots))

        # 2. Set ProjB — ProjA must be completely removed
        self.app.folder_path_var.set(str(proj_b))
        self.app._on_folder_path_var_trace()

        for root in self.app.xuat_search_roots:
            self.assertFalse(proj_a in root.parents or root == proj_a or root == proj_a / "Text",
                             f"ProjA must be completely removed from xuat_search_roots when switching to ProjB, found: {root}")

        # 3. BepInEx root resolution with plugins and config directories present
        bepinex_root = self.tmp_dir / "Game" / "BepInEx"
        plugins_dir = bepinex_root / "plugins"
        config_dir = bepinex_root / "config"
        text_dir = bepinex_root / "Translation" / "en" / "Text"
        res_dir = bepinex_root / "Translation" / "en" / "RedirectedResources"

        plugins_dir.mkdir(parents=True, exist_ok=True)
        config_dir.mkdir(parents=True, exist_ok=True)
        text_dir.mkdir(parents=True, exist_ok=True)
        res_dir.mkdir(parents=True, exist_ok=True)

        # Put a marker file in plugins
        (plugins_dir / "PluginStory.unity3d").write_bytes(b"dummy")

        roots = self.app._resolve_project_search_roots(bepinex_root)
        resolved_roots = [p.resolve() for p in roots]

        self.assertIn(text_dir.resolve(), resolved_roots, "Text directory must be in resolved project roots")
        self.assertIn(res_dir.resolve(), resolved_roots, "RedirectedResources directory must be in resolved project roots")
        self.assertNotIn(plugins_dir.resolve(), resolved_roots, "plugins/ must NEVER be in resolved project roots")
        self.assertNotIn(config_dir.resolve(), resolved_roots, "config/ must NEVER be in resolved project roots")
        self.assertNotIn(bepinex_root.resolve(), resolved_roots, "Root containing plugins must not be scanned directly")

        # Guard 1 requirement: OR condition (if only Text exists, it must still resolve to [Text])
        shutil.rmtree(res_dir)
        roots_text_only = self.app._resolve_project_search_roots(bepinex_root)
        resolved_text_only = [p.resolve() for p in roots_text_only]
        self.assertIn(text_dir.resolve(), resolved_text_only)
        self.assertNotIn(plugins_dir.resolve(), resolved_text_only, "OR condition must not fall through to scanning plugins")

        # 4. No auto-injection of unrelated local input/output
        self.app.project_folder = bepinex_root
        target_search_paths = self.app._resolve_project_search_roots(bepinex_root)
        for p in target_search_paths:
            self.assertNotEqual(p.name.lower(), "input", "Unrelated input folder must not be auto-injected")
            self.assertNotEqual(p.name.lower(), "output", "Unrelated output folder must not be auto-injected")

    # -------------------------------------------------------------------------
    # Defect Probe 4: BUG-30 (Search Focus, Gutter Update & No-Op KeyRelease)
    # -------------------------------------------------------------------------
    def test_probe_4_bug_30_search_focus_gutter_and_noop_keyrelease(self):
        """[Probe 4 — BUG-30] Search jump in Continuous View focuses active card widget (not txt_continuous);
        Page View dialogue edit updates gutter_clean; arrow keys in card & Box 0 trigger 0 file list refreshes."""
        # 1. Focus retention in Continuous View
        recs = [
            Record(cmd_id=0, cmd_name="title", args=["Title"]),
            Record(cmd_id=6, cmd_name="print", args=["Yuuki", "First box dialogue."]),
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Second box target hit."]),
        ]
        doc = StoryDocument(recs)
        bundle_path = (self.tmp_dir / "story.unity3d").resolve()
        self.app.current_file_path = bundle_path
        self.app.current_doc = doc
        self.app.open_documents[bundle_path] = {"doc": doc, "dirty": False}

        self.app.var_continuous_view.set(True)
        self.app._render_continuous_view()

        hit = SearchResult(
            file_path=bundle_path, file_type="bundle", line_number=2, box_index=1,
            speaker="Kokkoro", full_text="Second box target hit.", match_snippet="target hit",
            start_pos=11, end_pos=21
        )
        self.app.active_search_results = [hit]
        self.app._result_idx_to_line = {0: 1}

        with patch.object(self.app, "_focus_continuous_box", wraps=self.app._focus_continuous_box) as spy_focus_box, \
             patch.object(self.app.txt_continuous, "focus_set") as spy_cont_focus:
            self.app._select_result_index(0, jump=True)
            # Continuous jump must focus continuous box with accurate offsets, and txt_continuous must NOT steal focus
            spy_focus_box.assert_called_with(1, move_cursor=True, char_offset=11, explicit_span=(11, 21))
            self.assertFalse(spy_cont_focus.called, "txt_continuous.focus_set() must NOT be called on bundle Continuous View")

        # 2. Gutter clean update in Page View on Enter/newline
        self.app.var_continuous_view.set(False)
        self.app._update_views()

        initial_gutter = self.app.gutter_clean.get("1.0", "end-1c")
        # Add 3 lines in txt_dialogue
        self.app.txt_dialogue.delete("1.0", "end")
        self.app.txt_dialogue.insert("1.0", "Line 1\nLine 2\nLine 3\nLine 4")
        self.app._on_dialogue_edited()

        updated_gutter = self.app.gutter_clean.get("1.0", "end-1c").strip().splitlines()
        self.assertEqual(len(updated_gutter), 4,
                         f"_on_dialogue_edited must call _update_gutter_clean(); expected 4 lines, got {len(updated_gutter)}")

        # 3. No-op KeyRelease in card and Box 0 triggers 0 _refresh_opened_files_list calls
        self.app.var_continuous_view.set(True)
        self.app._render_continuous_view()
        card_txt = self.app._card_widgets[1]["txt"]
        with patch.object(self.app, "_refresh_opened_files_list") as spy_refresh:
            # Simulate arrow key in card (text unchanged)
            ret_card = self.app._on_card_text_edited(1, card_txt, None)
            self.assertFalse(ret_card, "_on_card_text_edited must return False when text is unchanged")

            self.app._commit_widget_edit(card_txt)
            self.assertEqual(spy_refresh.call_count, 0,
                             "Arrow key in card text widget must not trigger _refresh_opened_files_list")

            # Simulate arrow key in Box 0 synopsis
            self.app.is_box0_active = True
            self.app.var_continuous_view.set(False)
            self.app._update_views()
            ret_box0 = self.app._on_box0_metadata_edited()
            self.assertFalse(ret_box0, "_on_box0_metadata_edited must return False when metadata is unchanged")

            self.app._commit_widget_edit(self.app.txt_box0_summary)
            self.assertEqual(spy_refresh.call_count, 0,
                             "Arrow key in Box 0 summary must not trigger _refresh_opened_files_list")

    # -------------------------------------------------------------------------
    # Regression Guards (Direct Lightweight Invariant Assertions)
    # -------------------------------------------------------------------------
    def test_guard_1_combining_character_normalization_retained(self):
        """[Guard 1] Half-width katakana voiced sound mark 'ｶﾞ' normalizes to 'ガ' with valid span."""
        norm_txt, spans = ProjectSearchEngine.normalize_with_spans("こんにちは、ｶﾞｰﾃﾞﾝへ！")
        self.assertIn("ガーデン", norm_txt)
        idx = norm_txt.find("ガーデン")
        src_start, src_end = spans[idx]
        self.assertEqual("こんにちは、ｶﾞｰﾃﾞﾝへ！"[src_start:src_end], "ｶﾞ")

    def test_guard_2_background_search_posts_finished_in_finally(self):
        """[Guard 2] _run_background_search() always posts ('finished', ...) to search_queue in finally."""
        opts = SearchOptions(query="dummy")
        non_existent = self.tmp_dir / "does_not_exist"

        while not self.app.search_queue.empty():
            self.app.search_queue.get_nowait()

        self.app._run_background_search([non_existent], opts, {})

        found_finished = False
        while not self.app.search_queue.empty():
            msg = self.app.search_queue.get_nowait()
            if msg[0] == "finished":
                found_finished = True
                break
        self.assertTrue(found_finished, "_run_background_search must always post ('finished', ...) to search_queue")


if __name__ == "__main__":
    unittest.main()
