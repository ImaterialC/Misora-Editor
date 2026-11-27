#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests.test_v15_s11b2_xuat_batch_sync — TDD test suite for Session S11b2 (v1.4.12):
Bounded Single-Pass Batched XUAT Sync & Strict Translation\\en\\Text Alignment (Q-02b).

Defect Probes (MUST FAIL pre-patch, PASS post-patch):
- test_probe_1_strict_en_text_boundary_and_case_insensitive_exclusions
- test_probe_2_single_pass_batched_sync_structural_counts_and_20box_benchmark
- test_probe_3_norm_search_parity_same_jp_conflict_freshness_and_partial_failure

Regression Guards (MUST PASS pre-patch AND post-patch):
- test_guard_1_pure_core_and_zero_circular_import_both_orders
- test_guard_2_s10_immutable_jp_conflict_gate_and_s2_secondary_failure_tolerance
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).resolve().parent
MISORA_DIR = TESTS_DIR.parent
if str(MISORA_DIR) not in sys.path:
    sys.path.insert(0, str(MISORA_DIR))

import misora
import core.xunity_sync as xunity_sync_mod
from core.story_ast import Record, StoryDocument
from core.xuat_index import _is_excluded_xuat_file
from core.xunity_sync import XUnitySyncManager


class TestV15S11b2XuatBatchSync(unittest.TestCase):
    def setUp(self):
        self.tmp_dir_obj = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp_dir_obj.name).resolve()

        self.orig_config_path = misora.CONFIG_PATH
        self.test_config = self.tmp_dir / "misora_config.json"
        misora.CONFIG_PATH = self.test_config

        self.backup_dir = self.tmp_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.app = None

    def tearDown(self):
        if self.app is not None:
            try:
                self.app.destroy()
            except Exception:
                pass
            self.app = None
        misora.CONFIG_PATH = self.orig_config_path
        self.tmp_dir_obj.cleanup()

    def _init_app(self) -> misora.MisoraApp:
        app = misora.MisoraApp(show_splash=False, restore_session=False)
        app.withdraw()
        app.backup_folder = str(self.backup_dir)
        app.var_preview_compiled.set(False)
        app.var_continuous_view.set(False)
        app.var_sync_xuat.set(True)
        self.app = app
        return app

    @staticmethod
    def _norm(p: Path) -> str:
        return os.path.normcase(os.path.normpath(str(p.resolve())))

    @staticmethod
    def _make_doc(jp_keys, speaker="Pecorine") -> StoryDocument:
        recs = []
        for i, jp in enumerate(jp_keys):
            if i > 0:
                recs.append(Record(cmd_id=10, cmd_name="touch", args=[]))
            recs.append(Record(cmd_id=6, cmd_name="print", args=[speaker, jp]))
        return StoryDocument(recs)

    # =========================================================================
    # Defect Probes (MUST FAIL pre-patch, PASS post-patch)
    # =========================================================================

    def test_probe_1_strict_en_text_boundary_and_case_insensitive_exclusions(self):
        """
        [Probe 1 — Q-01/Q-02b Alignment + Direct .txt Roots]
        Enforces strict Translation\\en\\Text boundary inside batch_sync(),
        single-source case-insensitive rule + legacy exclusions matching xuat_index,
        and direct .txt file roots handled before os.walk().
        """
        app = self._init_app()
        game_root = self.tmp_dir / "Game"
        en_text = game_root / "BepInEx" / "Translation" / "en" / "Text"
        en_text.mkdir(parents=True, exist_ok=True)

        jp_main = "わたし、お腹が空きました！"
        jp_direct = "直指定ファイル確認！"

        main_file = en_text / "Main.txt"
        main_file.write_bytes(f"\ufeff{jp_main}=Old Main\r\n".encode("utf-8"))

        direct_file = en_text / "DirectRoot.txt"
        direct_file.write_bytes(f"{jp_direct}=Old Direct\n".encode("utf-8"))

        # Official rule + legacy excluded files inside Translation\en\Text
        excluded_names = [
            "Noto.font.txt",
            "Dialog.resizer.txt",
            "MyPostprocessors.txt",
            "MyPreprocessors.txt",
            "CustomSubstitutions.txt",
            "_summary.txt",
            "_SUMMARY.txt",
            "foo.missing.txt",
            "bar.report.txt",
            "baz_warnings.txt",
            "Main.bak_20260101_000000.txt",
        ]
        excluded_paths = []
        excluded_orig_bytes = {}
        for name in excluded_names:
            p = en_text / name
            raw = f"{jp_main}=ShouldNotTouch\r\n{jp_direct}=ShouldNotTouchDirect\r\n".encode("utf-8")
            p.write_bytes(raw)
            excluded_paths.append(p)
            excluded_orig_bytes[p] = raw

        # Verify our synthetic exclusion set agrees 100% with core.xuat_index._is_excluded_xuat_file
        for p in excluded_paths:
            self.assertTrue(_is_excluded_xuat_file(p), f"xuat_index should exclude {p.name}")
        self.assertFalse(_is_excluded_xuat_file(main_file))
        self.assertFalse(_is_excluded_xuat_file(direct_file))

        # Forbidden directories + outside .txt
        forbidden_files = []
        for rel in [
            Path("BepInEx") / "Translation" / "en" / "Other" / "Other.txt",
            Path("BepInEx") / "Translation" / "en" / "RedirectedResources" / "assets" / "Redir.txt",
            Path("BepInEx") / "Translation" / "ja" / "Text" / "Ja.txt",
            Path("Outside.txt"),
        ]:
            fp = game_root / rel
            fp.parent.mkdir(parents=True, exist_ok=True)
            raw = f"{jp_main}=ForbiddenOld\r\n{jp_direct}=ForbiddenDirect\r\n".encode("utf-8")
            fp.write_bytes(raw)
            forbidden_files.append((fp, raw))

        story_file = self.tmp_dir / "probe1.v2.txt"
        doc = self._make_doc([jp_main, jp_direct], speaker="Pecorine")
        story_file.write_text(doc.to_v2_text(), encoding="utf-8")
        app.open_file(story_file)
        self.assertEqual(len(app.current_doc.boxes), 2)

        # Pass BOTH game_root (unvalidated root) and direct_file (overlapping direct .txt root)
        app.xuat_search_roots = [game_root, direct_file]

        # Edit both boxes
        for idx, new_en in [(0, "I am starving!"), (1, "Direct root synced!")]:
            app.current_doc.inject_box(idx, "Pecorine", new_en)
            app._modified_boxes.add(idx)
            b_uid = misora._get_box_uid(app.current_doc.boxes[idx])
            if b_uid is not None:
                app._modified_box_uids.add(b_uid)
        app.current_box_idx = 1
        app.txt_dialogue.delete("1.0", "end")
        app.txt_dialogue.insert("1.0", "Direct root synced!")

        scan_read_counts = {}
        backup_calls = []
        in_backup = False
        orig_read_bytes = Path.read_bytes
        orig_copy2 = shutil.copy2

        def _tracked_read_bytes(path_self: Path) -> bytes:
            if not in_backup and path_self.suffix.lower() == ".txt":
                k = self._norm(path_self)
                scan_read_counts[k] = scan_read_counts.get(k, 0) + 1
            return orig_read_bytes(path_self)

        def _tracked_copy2(src, dst, *args, **kwargs):
            nonlocal in_backup
            backup_calls.append((Path(src), Path(dst)))
            in_backup = True
            try:
                return orig_copy2(src, dst, *args, **kwargs)
            finally:
                in_backup = False

        with patch.object(Path, "read_bytes", _tracked_read_bytes), \
             patch.object(shutil, "copy2", side_effect=_tracked_copy2), \
             patch.object(misora.messagebox, "askyesno", return_value=True):
            self.assertTrue(app.on_save())

        # Forbidden and excluded files: 0 scan reads, 0 writes
        for p in excluded_paths:
            self.assertEqual(scan_read_counts.get(self._norm(p), 0), 0, f"Excluded file was scan-read: {p.name}")
            self.assertEqual(p.read_bytes(), excluded_orig_bytes[p], f"Excluded file was modified: {p.name}")
        for fp, orig_raw in forbidden_files:
            self.assertEqual(scan_read_counts.get(self._norm(fp), 0), 0, f"Forbidden file was scan-read: {fp}")
            self.assertEqual(fp.read_bytes(), orig_raw, f"Forbidden file was modified: {fp}")

        # Eligible files (including deduplicated direct_file): <= 1 scan read & updated
        self.assertEqual(scan_read_counts.get(self._norm(main_file), 0), 1)
        self.assertEqual(scan_read_counts.get(self._norm(direct_file), 0), 1)
        self.assertIn(f"{jp_main}=I am starving!", main_file.read_bytes().decode("utf-8-sig"))
        self.assertIn(f"{jp_direct}=Direct root synced!", direct_file.read_text(encoding="utf-8"))

        # Standalone direct .txt root only (no directory root, ensuring `if root.is_file():` handles it without os.walk)
        self.assertTrue(hasattr(app.sync_manager, "batch_sync"), "XUnitySyncManager.batch_sync missing")
        app.xuat_search_roots = [direct_file]
        app.current_box_idx = 1
        app.txt_dialogue.delete("1.0", "end")
        app.txt_dialogue.insert("1.0", "Direct file root only!")
        app.current_doc.inject_box(1, "Pecorine", "Direct file root only!")
        app._modified_boxes.add(1)
        b_uid_1 = misora._get_box_uid(app.current_doc.boxes[1])
        if b_uid_1 is not None:
            app._modified_box_uids.add(b_uid_1)
        with patch.object(misora.messagebox, "askyesno", return_value=True):
            self.assertTrue(app.on_save())
        self.assertIn(f"{jp_direct}=Direct file root only!", direct_file.read_text(encoding="utf-8"))

    def test_probe_2_single_pass_batched_sync_structural_counts_and_20box_benchmark(self):
        """
        [Probe 2 — Single-Pass O(E + B + M) Structural Counts + 100-File Benchmark Telemetry]
        20 modified boxes hitting 3 shared target files across 100 Translation\\en\\Text .txt files:
        - os.walk <= 1 per save
        - Each eligible file scan-decoded <= 1 time (separately instrumented from backup I/O)
        - Exactly 3 backups & 3 write_atomic_encoded calls for .txt targets (97 untouched)
        - Preserves BOM, CRLF/LF, single-line escaped \\n, exact raw key whitespace, EOF newline
        - Logs [XUAT Sync] elapsed duration
        """
        app = self._init_app()
        en_text = self.tmp_dir / "Translation" / "en" / "Text"
        en_text.mkdir(parents=True, exist_ok=True)

        jp_keys = [f"セリフキー_{i:02d}" for i in range(20)]
        target_files = [
            en_text / "Dict_003.txt",  # UTF-8 BOM + CRLF + trailing CRLF (keys 0..6)
            en_text / "Dict_042.txt",  # UTF-8 no BOM + LF + NO trailing newline (keys 7..13)
            en_text / "Dict_088.txt",  # UTF-8 no BOM + CRLF + extra raw key whitespace + multiline val (keys 14..19)
        ]

        # Build 100 .txt files (each ~40 filler lines)
        for i in range(100):
            fp = en_text / f"Dict_{i:03d}.txt"
            filler = [f"ダミーキー_{i:03d}_{j:02d}=Dummy_{i}_{j}" for j in range(40)]
            if i == 3:
                lines = [f"{jp_keys[k]}=Old_{k}" for k in range(0, 7)] + filler
                fp.write_bytes(("\ufeff" + "\r\n".join(lines) + "\r\n").encode("utf-8"))
            elif i == 42:
                lines = filler[:10] + [f"{jp_keys[k]}=Old_{k}" for k in range(7, 14)] + filler[10:]
                fp.write_bytes("\n".join(lines).encode("utf-8"))  # NO trailing EOF newline
            elif i == 88:
                lines = [f"  {jp_keys[k]}   =Old_{k}" for k in range(14, 20)] + ["# Comment preserved"] + filler
                fp.write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))
            else:
                fp.write_bytes(("\n".join(filler) + "\n").encode("utf-8"))

        story_file = self.tmp_dir / "probe2_20box.v2.txt"
        doc = self._make_doc(jp_keys, speaker="Pecorine")
        story_file.write_text(doc.to_v2_text(), encoding="utf-8")
        app.open_file(story_file)
        self.assertEqual(len(app.current_doc.boxes), 20)
        app.xuat_search_roots = [en_text]

        # Modify all 20 boxes (box 17..19 have multiline English)
        new_translations = []
        for idx in range(20):
            en_val = f"Translated line {idx}\nSecond line {idx}" if idx >= 17 else f"Translated box {idx}"
            new_translations.append(en_val)
            app.current_doc.inject_box(idx, "Pecorine", en_val)
            app._modified_boxes.add(idx)
            b_uid = misora._get_box_uid(app.current_doc.boxes[idx])
            if b_uid is not None:
                app._modified_box_uids.add(b_uid)
        app.current_box_idx = 19
        app.txt_dialogue.delete("1.0", "end")
        app.txt_dialogue.insert("1.0", new_translations[19])

        walk_calls = 0
        scan_reads = {}
        xuat_backups = []
        xuat_atomic_writes = []
        in_backup = False

        orig_walk = os.walk
        orig_read_bytes = Path.read_bytes
        orig_copy2 = shutil.copy2
        orig_write_atomic = xunity_sync_mod.write_atomic_encoded

        def _counted_walk(*args, **kwargs):
            nonlocal walk_calls
            walk_calls += 1
            return orig_walk(*args, **kwargs)

        def _counted_read_bytes(path_self: Path) -> bytes:
            if not in_backup and path_self.suffix.lower() == ".txt":
                k = self._norm(path_self)
                scan_reads[k] = scan_reads.get(k, 0) + 1
            return orig_read_bytes(path_self)

        def _counted_copy2(src, dst, *args, **kwargs):
            nonlocal in_backup
            src_p = Path(src)
            if src_p.suffix.lower() == ".txt" and self._norm(src_p).startswith(self._norm(en_text)):
                xuat_backups.append(src_p.name)
            in_backup = True
            try:
                return orig_copy2(src, dst, *args, **kwargs)
            finally:
                in_backup = False

        def _counted_write_atomic(path, content, *args, **kwargs):
            p = Path(path)
            if p.suffix.lower() == ".txt" and self._norm(p).startswith(self._norm(en_text)):
                xuat_atomic_writes.append(p.name)
            return orig_write_atomic(path, content, *args, **kwargs)

        log_records = []
        orig_info = app.logger.info

        def _capture_info(cat, msg):
            log_records.append((cat, msg))
            return orig_info(cat, msg)

        t0 = time.perf_counter()
        with patch("os.walk", side_effect=_counted_walk), \
             patch.object(Path, "read_bytes", _counted_read_bytes), \
             patch.object(shutil, "copy2", side_effect=_counted_copy2), \
             patch.object(xunity_sync_mod, "write_atomic_encoded", side_effect=_counted_write_atomic), \
             patch.object(app.logger, "info", side_effect=_capture_info), \
             patch.object(misora.messagebox, "askyesno", return_value=True):
            save_ok = app.on_save()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertTrue(save_ok)
        self.assertLessEqual(walk_calls, 1, f"Expected <= 1 os.walk, got {walk_calls}")
        self.assertEqual(len(scan_reads), 100, f"Expected all 100 .txt files scanned once, got {len(scan_reads)}")
        for k, cnt in scan_reads.items():
            self.assertEqual(cnt, 1, f"File {k} scanned {cnt} times instead of 1")
        self.assertEqual(len(xuat_backups), 3, f"Expected 3 XUAT backups, got {xuat_backups}")
        self.assertEqual(len(xuat_atomic_writes), 3, f"Expected 3 XUAT writes, got {xuat_atomic_writes}")
        self.assertEqual(set(xuat_atomic_writes), {"Dict_003.txt", "Dict_042.txt", "Dict_088.txt"})

        # Check exact format preservation
        raw_003 = target_files[0].read_bytes()
        self.assertTrue(raw_003.startswith(b"\xef\xbb\xbf"), "Dict_003 must retain UTF-8 BOM")
        self.assertNotIn(b"\r\r\n", raw_003, "No CR doubling")
        self.assertTrue(raw_003.endswith(b"\r\n"))
        dec_003 = raw_003.decode("utf-8-sig")
        for k in range(0, 7):
            self.assertIn(f"{jp_keys[k]}=Translated box {k}\r\n", dec_003)

        raw_042 = target_files[1].read_bytes()
        self.assertFalse(raw_042.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r", raw_042, "Dict_042 must retain LF line endings")
        self.assertFalse(raw_042.endswith(b"\n"), "Dict_042 must preserve absence of trailing EOF newline")
        dec_042 = raw_042.decode("utf-8")
        for k in range(7, 14):
            self.assertIn(f"{jp_keys[k]}=Translated box {k}", dec_042)

        raw_088 = target_files[2].read_bytes()
        dec_088 = raw_088.decode("utf-8")
        self.assertIn("# Comment preserved\r\n", dec_088)
        for k in range(14, 17):
            self.assertIn(f"  {jp_keys[k]}   =Translated box {k}\r\n", dec_088)
        for k in range(17, 20):
            self.assertIn(f"  {jp_keys[k]}   =Translated line {k}\\nSecond line {k}\r\n", dec_088)

        sync_logs = [m for c, m in log_records if c == "XUAT Sync" and "s (" in m]
        self.assertTrue(sync_logs, f"Expected [XUAT Sync] timing telemetry log, got {log_records}")
        print(f"\n[Probe 2 100-file structural telemetry] {elapsed_ms:.2f} ms; logs={sync_logs}")

    def test_probe_3_norm_search_parity_same_jp_conflict_freshness_and_partial_failure(self):
        """
        [Probe 3 — Parity, All 4 Conflict Edge Cases, Freshness Abort, Partial Failure & None-UID/Inactive Retention]
        """
        # -----------------------------------------------------------------
        # (a) Old preview_matches() vs New batch_sync() norm_search parity
        # -----------------------------------------------------------------
        parity_dir = self.tmp_dir / "parity" / "Translation" / "en" / "Text"
        parity_dir.mkdir(parents=True, exist_ok=True)
        parity_file = parity_dir / "Parity.txt"
        parity_file.write_bytes((
            "[ff0000]赤い[-]\u3000{playername}―World=OldA\n"
            "ＨＥＬＬＯ\t{0}  Test=OldB\n"
        ).encode("utf-8"))

        sm = XUnitySyncManager()
        query_keys = [
            "[FF0000]赤い[-] {0}―world",
            "hello {playername} test",
        ]
        legacy_set = set()
        for qk in query_keys:
            for m in sm.preview_matches(qk, [parity_dir]):
                legacy_set.add((self._norm(m.file_path), m.line_number))

        from core.story_ast import norm_search
        from core.xunity_sync import BatchSyncTarget
        targets = [
            BatchSyncTarget(target_token=f"t:{i}", box_uid=i, jp_key=qk, norm_key=norm_search(qk), new_english=f"New{i}", box_index=i)
            for i, qk in enumerate(query_keys)
        ]
        res_parity = sm.batch_sync(targets, [parity_dir], backup=False)
        self.assertEqual(legacy_set, {(self._norm(parity_file), 1), (self._norm(parity_file), 2)})
        self.assertEqual(res_parity.succeeded_tokens, {"t:0", "t:1"})
        updated_parity = parity_file.read_text(encoding="utf-8")
        self.assertIn("[ff0000]赤い[-]\u3000{playername}―World=New0", updated_parity)
        self.assertIn("ＨＥＬＬＯ\t{0}  Test=New1", updated_parity)

        # -----------------------------------------------------------------
        # (b) & (c) C1..C4 Conflicts, Single Batched Callback, Warnings, & Freshness Abort
        # -----------------------------------------------------------------
        app = self._init_app()
        en_text = self.tmp_dir / "main" / "Translation" / "en" / "Text"
        en_text.mkdir(parents=True, exist_ok=True)

        f1 = en_text / "One.txt"
        f2 = en_text / "Two.txt"
        f_fresh = en_text / "Fresh.txt"

        f1.write_bytes((
            "C1_CROSS=Val1\n"
            "C1_INTRA=DupA\n"
            "C1_INTRA=DupB\n"
            "C2_AGREE=OldAgree\n"
            "C3_DIFF=KeepOriginal\n"
            "CLEAN_KEY=OldClean\n"
        ).encode("utf-8"))
        f2.write_bytes("C1_CROSS=Val2\n".encode("utf-8"))
        f_fresh.write_bytes("FRESH_KEY=BeforeExternalEdit\n".encode("utf-8"))

        story_path = self.tmp_dir / "probe3_conflicts.v2.txt"
        doc = self._make_doc([
            "C1_CROSS",   # 0: C1 cross-file
            "C1_INTRA",   # 1: C1 intra-file dup
            "C2_AGREE",   # 2: C2 agree 1
            "C2_AGREE",   # 3: C2 agree 2
            "C3_DIFF",    # 4: C3 diff 1
            "C3_DIFF",    # 5: C3 diff 2
            "CLEAN_KEY",  # 6: clean
            "FRESH_KEY",  # 7: freshness abort
        ], speaker="A")
        story_path.write_text(doc.to_v2_text(), encoding="utf-8")
        app.open_file(story_path)
        self.assertEqual(len(app.current_doc.boxes), 8)
        app.xuat_search_roots = [en_text]

        edits = {
            0: "CrossNew",
            1: "IntraNew",
            2: "SameSharedEN",
            3: "SameSharedEN",
            4: "WinnerA",
            5: "WinnerB",
            6: "CleanNew",
            7: "FreshAttempt",
        }
        for idx, txt in edits.items():
            app.current_doc.inject_box(idx, "A", txt)
            app._modified_boxes.add(idx)
            b_uid = misora._get_box_uid(app.current_doc.boxes[idx])
            if b_uid is not None:
                app._modified_box_uids.add(b_uid)
        app.current_box_idx = 6
        app.txt_dialogue.delete("1.0", "end")
        app.txt_dialogue.insert("1.0", "CleanNew")

        warn_logs = []
        orig_warn = app.logger.warning

        def _cap_warn(cat, msg):
            warn_logs.append((cat, msg))
            return orig_warn(cat, msg)

        def _batched_askyesno(*args, **kwargs):
            # Simulate external edit to Fresh.txt between Stage 1+2 scan and Stage 5 write
            time.sleep(0.02)
            f_fresh.write_bytes("FRESH_KEY=ExternalHumanEdit\nEXTRA=1\n".encode("utf-8"))
            return False  # Decline C1 batched conflicts

        with patch.object(misora.messagebox, "askyesno", side_effect=_batched_askyesno) as mock_ask, \
             patch.object(app.logger, "warning", side_effect=_cap_warn):
            self.assertTrue(app.on_save())

        # Single batched dialog invoked ONCE for both C1 keys
        self.assertEqual(mock_ask.call_count, 1, f"Expected single batched C1 prompt, got {mock_ask.call_count}")

        # C2 + Clean succeeded; C1 + C3 + Fresh did NOT overwrite and stay retained
        f1_text = f1.read_text(encoding="utf-8")
        self.assertIn("C1_CROSS=Val1", f1_text)
        self.assertIn("C1_INTRA=DupA", f1_text)
        self.assertIn("C2_AGREE=SameSharedEN", f1_text)
        self.assertIn("C3_DIFF=KeepOriginal", f1_text)
        self.assertIn("CLEAN_KEY=CleanNew", f1_text)
        self.assertIn("FRESH_KEY=ExternalHumanEdit", f_fresh.read_text(encoding="utf-8"))

        # Retained indices: 0, 1 (C1), 4, 5 (C3), 7 (Freshness); Cleared: 2, 3 (C2), 6 (Clean)
        self.assertEqual(app._modified_boxes, {0, 1, 4, 5, 7})
        expected_retained_uids = {misora._get_box_uid(app.current_doc.boxes[i]) for i in (0, 1, 4, 5, 7)}
        self.assertEqual(app._modified_box_uids, expected_retained_uids)

        xuat_warns = "\n".join(m for c, m in warn_logs if c == "XUAT Sync")
        self.assertIn("C3_DIFF", xuat_warns, "Expected [XUAT Sync] warning for C3 conflict")
        self.assertIn("Fresh.txt", xuat_warns, "Expected [XUAT Sync] warning for Stage 4 freshness abort")

        # -----------------------------------------------------------------
        # (d) Partial multi-file write failure
        # -----------------------------------------------------------------
        p_en = self.tmp_dir / "partial" / "Translation" / "en" / "Text"
        p_en.mkdir(parents=True, exist_ok=True)
        fa = p_en / "FileA.txt"
        fb = p_en / "FileB.txt"
        fc = p_en / "FileC.txt"
        fa.write_bytes("KEY_A=OldA\nKEY_AB=OldAB_A\n".encode("utf-8"))
        fb.write_bytes("KEY_AB=OldAB_B\nKEY_B=OldB\n".encode("utf-8"))
        fc.write_bytes("KEY_C=OldC\n".encode("utf-8"))

        p_story = self.tmp_dir / "partial.v2.txt"
        p_doc = self._make_doc([
            "KEY_A",   # 0: only A -> succeed
            "KEY_AB",  # 1: A and B -> B fails -> io_failed!
            "KEY_B",   # 2: only B -> fails -> io_failed!
            "KEY_C",   # 3: only C -> succeed
        ], speaker="S")
        p_story.write_text(p_doc.to_v2_text(), encoding="utf-8")
        app.open_file(p_story)
        self.assertEqual(len(app.current_doc.boxes), 4)
        app.xuat_search_roots = [p_en]
        for i in range(4):
            app.current_doc.inject_box(i, "S", f"NewVal_{i}")
            app._modified_boxes.add(i)
            app._modified_box_uids.add(misora._get_box_uid(app.current_doc.boxes[i]))
        app.current_box_idx = 0
        app.txt_dialogue.delete("1.0", "end")
        app.txt_dialogue.insert("1.0", "NewVal_0")

        orig_write = xunity_sync_mod.write_atomic_encoded

        def _fail_file_b(path, content, *args, **kwargs):
            if Path(path).name == "FileB.txt":
                raise OSError("Simulated FileB write failure")
            return orig_write(path, content, *args, **kwargs)

        with patch.object(xunity_sync_mod, "write_atomic_encoded", side_effect=_fail_file_b), \
             patch.object(misora.messagebox, "askyesno", return_value=True):
            self.assertTrue(app.on_save())

        self.assertFalse(app.is_dirty)
        self.assertIn("KEY_A=NewVal_0", fa.read_text(encoding="utf-8"))
        self.assertIn("KEY_C=NewVal_3", fc.read_text(encoding="utf-8"))
        # Box 0 and 3 cleared; Box 1 (matched A & B) and Box 2 (matched B) MUST stay retained
        self.assertEqual(app._modified_boxes, {1, 2})

        # -----------------------------------------------------------------
        # (e) Inactive-doc retention + ineligible / None-UID clearing
        # -----------------------------------------------------------------
        # Doc B inactive save failure retains entry["modified_box_uids"]
        inactive_story = self.tmp_dir / "inactive.v2.txt"
        in_doc = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["I", "INACTIVE_JP"])])
        inactive_story.write_text(in_doc.to_v2_text(), encoding="utf-8")
        app.open_file(inactive_story)
        in_uid = misora._get_box_uid(app.current_doc.boxes[0])
        app.current_doc.inject_box(0, "I", "InactiveEdited")
        app._modified_boxes.add(0)
        app._modified_box_uids.add(in_uid)
        app.current_box_idx = 0
        app.txt_dialogue.delete("1.0", "end")
        app.txt_dialogue.insert("1.0", "InactiveEdited")
        app.is_dirty = True

        # Switch away to p_story so inactive_story becomes inactive
        app.open_file(p_story)
        app.xuat_search_roots = [p_en]
        with patch.object(app.sync_manager, "batch_sync", side_effect=RuntimeError("Boom")):
            ok_inactive = app._save_document_entry(inactive_story)
        self.assertTrue(ok_inactive)
        in_entry = app.open_documents[app._find_open_doc_key(inactive_story)]
        self.assertFalse(in_entry["dirty"])
        self.assertEqual(
            in_entry["modified_box_uids"],
            {in_uid},
            "Inactive document XUAT sync failure must preserve modified_box_uids for retry",
        )

        # Mixed eligible None-UID, ineligible None-UID, missing JP key, unmatched, matched, conflicted
        m_en = self.tmp_dir / "mixed" / "Translation" / "en" / "Text"
        m_en.mkdir(parents=True, exist_ok=True)
        m_file = m_en / "Mixed.txt"
        m_file.write_bytes((
            "MIX_NONE_ELIG=OldNone\n"
            "MIX_MATCHED=OldMatched\n"
            "MIX_CONF=Conf1\n"
            "MIX_CONF=Conf2\n"
        ).encode("utf-8"))
        m_story = self.tmp_dir / "mixed.v2.txt"
        m_doc = self._make_doc([
            "MIX_TEMP_KEY",  # 0: will have empty/missing JP key (ineligible)
            "MIX_MATCHED",   # 1: valid matched
            "MIX_UNMATCH",   # 2: valid unmatched
            "MIX_CONF",      # 3: C1 declined (retained)
        ], speaker="M")
        m_story.write_text(m_doc.to_v2_text(), encoding="utf-8")
        app.open_file(m_story)
        self.assertEqual(len(app.current_doc.boxes), 4)
        app.xuat_search_roots = [m_en]
        uid0 = misora._get_box_uid(app.current_doc.boxes[0])
        app._original_jp_by_uid[uid0] = ""
        app.sync_manager.unregister_jp_keys([uid0])
        app.current_doc.inject_box(1, "M", "NewMixedMatched")
        app.current_box_idx = 1
        app.txt_dialogue.delete("1.0", "end")
        app.txt_dialogue.insert("1.0", "NewMixedMatched")

        # Append two synthetic Box-like objects with b_uid=None (idx 4 eligible, idx 5 ineligible)
        class _DummyBox:
            def __init__(self, idx, text):
                self.index = idx
                self.speaker = "M"
                self.clean_text = text

        app.current_doc.boxes.append(_DummyBox(4, "NoneEligibleNew"))
        app.current_doc.boxes.append(_DummyBox(5, "NoneIneligibleNew"))
        app._original_box_texts[4] = "MIX_NONE_ELIG"
        # Intentionally NO _original_box_texts[5] -> ineligible None-UID!

        app._modified_boxes = {0, 1, 2, 3, 4, 5, 99}  # 99 is out-of-range ineligible
        app._modified_box_uids = {misora._get_box_uid(app.current_doc.boxes[i]) for i in (0, 1, 2, 3)}
        # Also force uid=None collision scenario: make box 1's uid == 4 in map if needed?
        # Already distinct because target_token uses "uid:<n>" vs "idx:<idx>"!
        with patch.object(misora.messagebox, "askyesno", return_value=False):
            self.assertTrue(app.on_save())

        self.assertIn("MIX_NONE_ELIG=NoneEligibleNew", m_file.read_text(encoding="utf-8"))
        self.assertIn("MIX_MATCHED=NewMixedMatched", m_file.read_text(encoding="utf-8"))
        # ONLY box 3 (declined conflict) remains retained; 0, 1, 2, 4, 5, 99 are ALL cleared!
        self.assertEqual(app._modified_boxes, {3})
        self.assertEqual(app._modified_box_uids, {misora._get_box_uid(app.current_doc.boxes[3])})

    # =========================================================================
    # Regression Guards (MUST PASS both pre-patch and post-patch)
    # =========================================================================

    def test_guard_1_pure_core_and_zero_circular_import_both_orders(self):
        """
        [Guard 1 — Pure-Core & Anti-Circular Import]
        Subprocess imports core.xunity_sync then core.xuat_index, and reverse,
        verifying 0 ImportError and 0 tkinter/misora imports inside core.xunity_sync.
        """
        for order_code in (
            "import sys; import core.xunity_sync; import core.xuat_index; "
            "assert 'tkinter' not in sys.modules and 'misora' not in sys.modules",
            "import sys; import core.xuat_index; import core.xunity_sync; "
            "assert 'tkinter' not in sys.modules and 'misora' not in sys.modules",
        ):
            proc = subprocess.run(
                [sys.executable, "-c", order_code],
                cwd=str(MISORA_DIR),
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 0, f"Import order failed: {proc.stderr}")

    def test_guard_2_s10_immutable_jp_conflict_gate_and_s2_secondary_failure_tolerance(self):
        """
        [Guard 2 — S10 Immutable JP Key & S02 Secondary Sync Failure Tolerance]
        """
        app = self._init_app()
        en_text = self.tmp_dir / "guard" / "Translation" / "en" / "Text"
        en_text.mkdir(parents=True, exist_ok=True)
        g_file = en_text / "Guard.txt"
        g_file.write_bytes("ガード日本語=OldGuard\r\n".encode("utf-8"))

        story_file = self.tmp_dir / "guard.v2.txt"
        doc = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["G", "ガード日本語"])])
        story_file.write_text(doc.to_v2_text(), encoding="utf-8")
        app.open_file(story_file)
        app.xuat_search_roots = [en_text]

        # Save 1 -> Save 2 preserves immutable JP key
        with patch.object(misora.messagebox, "askyesno", return_value=True):
            app.txt_dialogue.delete("1.0", "end")
            app.txt_dialogue.insert("1.0", "GuardFirst")
            self.assertTrue(app.on_save())
            app.txt_dialogue.delete("1.0", "end")
            app.txt_dialogue.insert("1.0", "GuardSecond")
            self.assertTrue(app.on_save())
        self.assertIn("ガード日本語=GuardSecond", g_file.read_text(encoding="utf-8"))

        # Secondary XUAT failure keeps primary save True, doc clean, retains _modified_boxes
        app.txt_dialogue.delete("1.0", "end")
        app.txt_dialogue.insert("1.0", "GuardFailRetry")
        with patch.object(xunity_sync_mod, "write_atomic_encoded", side_effect=OSError("Guard I/O error")):
            res = app.on_save()
        self.assertIs(res, True)
        self.assertFalse(app.is_dirty)
        self.assertIn(0, app._modified_boxes)


if __name__ == "__main__":
    unittest.main()
