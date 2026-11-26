#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S07 (v1.4.7) Verification Suite — Transactional XUAT Cleanup, Mandatory Archival & Debug > Safety:
- Probe 1: Per-file cleanup preserves BOM, CRLF/LF, comments, escaped '=', whitespace values, short JP keys & EOF newlines.
- Probe 2: Stale SHA-256 source fingerprint aborts before modifying source or archive on disk (StaleSourceError).
- Probe 3: Mandatory archive encoding contracts (per_source_file raw byte-for-byte + no mid-file BOM on append;
           combined UTF-8/LF + original metadata headers), source-overwrite guard, .txt/Text/ warning & opt-out confirm.
- Probe 4: Archive-first execution and granular partial-batch failure CleanupReport.
- Probe 5: Duplicate scope (selected_only vs all_duplicates, UI hidden when 0 duplicates) & conservative 3-tier
           classification (already_translated_unique vs uncertain short/ambiguous/shared-speaker unchecked by default).
- Probe 6: Meaningfully-empty XUAT detection without auto-delete, 2-step backup-path confirmation & Debug > Safety toggle.
- Probe 7: Pure-core boundary (core.xuat_cleanup imports 0 tkinter/misora) and injected backup_path_fn callback.
- Guard 1: Cancelling ImportFromXUATDialog never opens cleanup dialog or modifies XUAT files.
- Guard 2: Strict decode rejects corrupt binary bytes without errors='replace' rewriting.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora  # noqa: E402
from core.story_ast import Record, StoryDocument  # noqa: E402
from core.text_encoding import BOM_UTF8, BOM_UTF16_LE, detect_encoding_and_decode, read_text_file_strictly  # noqa: E402
from core.xuat_index import build_xuat_index  # noqa: E402


class S07TestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_v15_s07_"))
        self.config_path = self.tmp_dir / "misora_config.json"
        self.config_path.write_text("{}", encoding="utf-8")

        self.patch_cfg = patch.object(misora, "CONFIG_PATH", self.config_path)
        self.patch_info = patch.object(misora.messagebox, "showinfo", return_value=None)
        self.patch_warn = patch.object(misora.messagebox, "showwarning", return_value=None)
        self.patch_err = patch.object(misora.messagebox, "showerror", return_value=None)

        self.patch_cfg.start()
        self.patch_info.start()
        self.patch_warn.start()
        self.patch_err.start()

        self.app = misora.MisoraApp(restore_session=False, show_splash=False)
        self.app._test_bypass_dialogs = True
        self.app.withdraw()
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.xuat_archive_dir = self.tmp_dir / "backups" / "xuat_archive"

    def _wait_for_cleanup_scan(self, dlg, timeout: float = 5.0) -> None:
        """Pump Tk mainloop until async XuatCleanupDialog scan & batched Treeview insert finish."""
        import time
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.app.update()
            if (not getattr(dlg, "_is_scanning", False)) and (getattr(dlg, "_batch_insert_job", None) is None):
                return
            time.sleep(0.01)
        self.fail("Timed out waiting for async XuatCleanupDialog scan/batch insert")

    def tearDown(self) -> None:
        try:
            if self.app is not None:
                self.app.destroy()
        except Exception:
            pass
        self.app = None
        import gc
        gc.collect()
        self.patch_err.stop()
        self.patch_warn.stop()
        self.patch_info.stop()
        self.patch_cfg.stop()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)


class TestV15S07XuatCleanupArchive(S07TestBase):
    """Failing-first probes (7) and regression guards (2) for v1.5 S07 (v1.4.7)."""

    def _make_xuat_tree(self):
        proj_dir = self.tmp_dir / "proj"
        text_dir = proj_dir / "BepInEx" / "Translation" / "en" / "Text"
        text_dir.mkdir(parents=True, exist_ok=True)
        return proj_dir, text_dir

    def test_probe_1_transactional_cleanup_preserves_bom_crlf_comments_and_linebreak_modes(self) -> None:
        """[Probe 1] Both keep_blank_line and remove_line_break preserve BOM, CRLF/LF, comments, regex, escaped '=', whitespace values, and short JP keys."""
        from core.xuat_cleanup import AppliedXuatRecord, classify_cleanup_candidates, execute_cleanup

        proj_dir, text_dir = self._make_xuat_tree()
        bom_crlf_file = text_dir / "bom_crlf.txt"
        bom_content = (
            "\ufeff"
            "# Header comment\r\n"
            "// Slash comment\r\n"
            "; Semi comment\r\n"
            "r:^regex$=KeepRegex\r\n"
            "sr:^sregex$=KeepSRegex\r\n"
            "  IndentedKey\\=WithEq  =EqualsVal\r\n"
            "WhitespaceOnly=   \r\n"
            "はい=Yes.\r\n"
            "こんにちは！=Hello!\r\n"
        )
        bom_crlf_file.write_bytes(bom_content.encode("utf-8"))

        lf_file = text_dir / "utf8_lf.txt"
        lf_content = (
            "# LF comment\n"
            "おはよう！=Good morning!\n"
            "さようなら=Goodbye!\n"
        )
        lf_file.write_bytes(lf_content.encode("utf-8"))

        idx = build_xuat_index([proj_dir])
        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "はい"]),
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "こんにちは！"]),
            Record(cmd_id=6, cmd_name="print", args=["キャル", "おはよう！"]),
        ])
        applied = [
            AppliedXuatRecord(file_path=bom_crlf_file, line_number=8, raw_key="はい", value="Yes.", box_index=0),
            AppliedXuatRecord(file_path=bom_crlf_file, line_number=9, raw_key="こんにちは！", value="Hello!", box_index=1),
        ]
        analysis = classify_cleanup_candidates(idx, doc, applied_records=applied, duplicate_scope="selected_only")
        archive_dir = self.tmp_dir / "archive_1"
        report1 = execute_cleanup(
            candidates=[c for c in analysis.candidates if c.file_path == bom_crlf_file],
            source_fingerprints=idx.file_fingerprints,
            archive_dir=archive_dir,
            archive_ext=".xuat.old",
            archive_strategy="combined",
            linebreak_policy="keep_blank_line",
            safety_backup_enabled=True,
            safety_backup_dir=self.tmp_dir / "safety_1",
        )
        self.assertEqual(report1.errors, [])
        raw_after_bom = bom_crlf_file.read_bytes()
        self.assertTrue(raw_after_bom.startswith(BOM_UTF8))
        decoded_bom = detect_encoding_and_decode(raw_after_bom)
        self.assertEqual(decoded_bom.newline, "\r\n")
        self.assertEqual(
            decoded_bom.text,
            "# Header comment\r\n"
            "// Slash comment\r\n"
            "; Semi comment\r\n"
            "r:^regex$=KeepRegex\r\n"
            "sr:^sregex$=KeepSRegex\r\n"
            "  IndentedKey\\=WithEq  =EqualsVal\r\n"
            "WhitespaceOnly=   \r\n"
            "\r\n"
            "\r\n",
        )

        # Second pass: remove_line_break on UTF-8 LF file
        applied_lf = [
            AppliedXuatRecord(file_path=lf_file, line_number=2, raw_key="おはよう！", value="Good morning!", box_index=2),
        ]
        idx2 = build_xuat_index([proj_dir])
        analysis2 = classify_cleanup_candidates(idx2, doc, applied_records=applied_lf, duplicate_scope="selected_only")
        report2 = execute_cleanup(
            candidates=[c for c in analysis2.candidates if c.file_path == lf_file],
            source_fingerprints=idx2.file_fingerprints,
            archive_dir=archive_dir,
            archive_ext=".xuat.old",
            archive_strategy="combined",
            linebreak_policy="remove_line_break",
            safety_backup_enabled=True,
            safety_backup_dir=self.tmp_dir / "safety_1",
        )
        self.assertEqual(report2.errors, [])
        raw_after_lf = lf_file.read_bytes()
        self.assertFalse(raw_after_lf.startswith(BOM_UTF8))
        self.assertNotIn(b"\r\n", raw_after_lf)
        self.assertEqual(raw_after_lf.decode("utf-8"), "# LF comment\nさようなら=Goodbye!\n")

    def test_probe_2_stale_source_sha256_aborts_before_modifying_disk(self) -> None:
        """[Probe 2] External modification to a targeted XUAT file raises StaleSourceError before archive or source writes."""
        from core.xuat_cleanup import AppliedXuatRecord, StaleSourceError, classify_cleanup_candidates, execute_cleanup

        proj_dir, text_dir = self._make_xuat_tree()
        target_file = text_dir / "Main.txt"
        target_file.write_text("おはよう！=Good morning!\nまた明日=See you tomorrow\n", encoding="utf-8")

        idx = build_xuat_index([proj_dir])
        captured_fps = dict(idx.file_fingerprints)
        doc = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "おはよう！"])])
        analysis = classify_cleanup_candidates(
            idx,
            doc,
            applied_records=[AppliedXuatRecord(file_path=target_file, line_number=1, raw_key="おはよう！", value="Good morning!", box_index=0)],
        )

        # Simulate external edit before cleanup execution
        modified_bytes = "おはよう！=Good morning!\n# Externally edited\nまた明日=See you tomorrow\n".encode("utf-8")
        target_file.write_bytes(modified_bytes)

        archive_dir = self.tmp_dir / "stale_archive"
        with self.assertRaises(StaleSourceError):
            execute_cleanup(
                candidates=analysis.candidates,
                source_fingerprints=captured_fps,
                archive_dir=archive_dir,
                archive_ext=".xuat.old",
                archive_strategy="combined",
            )

        self.assertEqual(target_file.read_bytes(), modified_bytes)
        self.assertFalse(archive_dir.exists() and any(archive_dir.iterdir()))

    def test_probe_3_mandatory_archive_encoding_contracts_and_irreversible_optout(self) -> None:
        """[Probe 3] Verify per_source_file raw encoding/BOM/EOL + append, combined UTF-8/LF metadata headers, target validation, and unarchived opt-out."""
        from core.xuat_cleanup import (
            AppliedXuatRecord,
            ArchiveTargetError,
            classify_cleanup_candidates,
            execute_cleanup,
            validate_archive_target,
        )

        proj_dir, text_dir = self._make_xuat_tree()
        cp932_file = text_dir / "Cp932Story.txt"
        cp932_file.write_bytes("おはよう！=Morning!\r\nありがとう=Thanks!\r\n".encode("cp932"))

        utf16_file = text_dir / "Utf16Story.txt"
        utf16_file.write_bytes(BOM_UTF16_LE + "さようなら=Bye now!\r\n".encode("utf-16-le"))

        idx = build_xuat_index([proj_dir])
        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "おはよう！"]),
            Record(cmd_id=6, cmd_name="print", args=["コッコロ", "さようなら"]),
        ])
        applied = [
            AppliedXuatRecord(file_path=cp932_file, line_number=1, raw_key="おはよう！", value="Morning!", box_index=0),
            AppliedXuatRecord(file_path=utf16_file, line_number=1, raw_key="さようなら", value="Bye now!", box_index=1),
        ]
        analysis = classify_cleanup_candidates(idx, doc, applied_records=applied)

        # 1. per_source_file creation + append preserves raw CP932 & UTF-16-LE BOM without mid-file duplicate BOM
        per_dir = self.tmp_dir / "per_file_archive"
        # Pre-seed an existing per-file archive without trailing newline to verify clean separator & no mid-file BOM
        per_dir.mkdir(parents=True, exist_ok=True)
        pre_utf16_arch = per_dir / "Utf16Story.xuat.old"
        pre_utf16_arch.write_bytes(BOM_UTF16_LE + "# Pre-existing".encode("utf-16-le"))

        report_per = execute_cleanup(
            candidates=analysis.candidates,
            source_fingerprints=idx.file_fingerprints,
            archive_dir=per_dir,
            archive_ext=".xuat.old",
            archive_strategy="per_source_file",
            safety_backup_enabled=False,
        )
        self.assertEqual(report_per.errors, [])
        cp_arch = per_dir / "Cp932Story.xuat.old"
        self.assertTrue(cp_arch.is_file())
        cp_bytes = cp_arch.read_bytes()
        self.assertFalse(cp_bytes.startswith(BOM_UTF8))
        self.assertIn(b"\r\n", cp_bytes)
        self.assertEqual(detect_encoding_and_decode(cp_bytes).encoding, "cp932")
        self.assertIn("おはよう！=Morning!", cp_bytes.decode("cp932"))

        u16_bytes = pre_utf16_arch.read_bytes()
        self.assertTrue(u16_bytes.startswith(BOM_UTF16_LE))
        self.assertEqual(u16_bytes.count(BOM_UTF16_LE), 1, "Appending must NOT emit duplicate BOM mid-file")
        u16_decoded = detect_encoding_and_decode(u16_bytes)
        self.assertEqual(u16_decoded.encoding, "utf-16-le")
        self.assertIn("# Pre-existing\r\n# [", u16_decoded.text)
        self.assertIn("さようなら=Bye now!", u16_decoded.text)

        # 2. combined archive uses canonical UTF-8/LF with structured encoding/bom/newline headers
        cp932_file.write_bytes("おはよう！=Morning!\r\nありがとう=Thanks!\r\n".encode("cp932"))
        utf16_file.write_bytes(BOM_UTF16_LE + "さようなら=Bye now!\r\n".encode("utf-16-le"))
        idx2 = build_xuat_index([proj_dir])
        analysis2 = classify_cleanup_candidates(idx2, doc, applied_records=applied)
        comb_dir = self.tmp_dir / "combined_archive"
        report_comb = execute_cleanup(
            candidates=analysis2.candidates,
            source_fingerprints=idx2.file_fingerprints,
            archive_dir=comb_dir,
            archive_ext=".xuat.old",
            archive_strategy="combined",
            story_name="story_test",
            reason="post_import",
        )
        self.assertEqual(report_comb.errors, [])
        comb_arch = comb_dir / "xuat_removed_archive.xuat.old"
        comb_bytes = comb_arch.read_bytes()
        self.assertFalse(comb_bytes.startswith(BOM_UTF8))
        self.assertNotIn(b"\r\n", comb_bytes)
        comb_text = comb_bytes.decode("utf-8")
        self.assertIn("encoding=cp932 | bom=false | newline=CRLF", comb_text)
        self.assertIn("encoding=utf-16-le | bom=true | newline=CRLF", comb_text)
        self.assertIn("おはよう！=Morning!", comb_text)
        self.assertIn("さようなら=Bye now!", comb_text)

        # 3. Target validation: refuse source overwrite; warn on .txt or Text/ dir
        v_same = validate_archive_target(text_dir, ".txt", "per_source_file", [cp932_file], xuat_roots=[text_dir])
        self.assertFalse(v_same.is_valid)
        self.assertTrue(v_same.warnings)
        with self.assertRaises(ArchiveTargetError):
            execute_cleanup(
                candidates=analysis2.candidates[:1],
                source_fingerprints=idx2.file_fingerprints,
                archive_dir=text_dir,
                archive_ext=".txt",
                archive_strategy="per_source_file",
                xuat_roots=[text_dir],
            )

        v_warn = validate_archive_target(text_dir / "sub", ".txt", "combined", [cp932_file], xuat_roots=[text_dir])
        self.assertTrue(v_warn.is_valid)
        self.assertGreaterEqual(len(v_warn.warnings), 2)

        # 4. UI unarchived opt-out requires separate irreversible confirmation
        cp932_file.write_bytes("おはよう！=Morning!\r\nありがとう=Thanks!\r\n".encode("cp932"))
        idx3 = build_xuat_index([proj_dir])
        self.app._set_project_folder(proj_dir)
        self.app.open_documents[self.tmp_dir / "s.v2.txt"] = {"doc": doc, "plain_text": "", "dirty": False}
        self.app.current_doc = doc
        self.app.current_file_path = self.tmp_dir / "s.v2.txt"
        dlg = misora.XuatCleanupDialog(
            self.app,
            xuat_index=idx3,
            doc=doc,
            applied_records=[AppliedXuatRecord(file_path=cp932_file, line_number=1, raw_key="おはよう！", value="Morning!", box_index=0)],
            source_fingerprints=idx3.file_fingerprints,
        )
        try:
            self._wait_for_cleanup_scan(dlg)
            dlg.var_allow_unarchived.set(True)
            # Declining irreversible confirmation leaves source intact
            with patch.object(misora.messagebox, "askyesno", return_value=False) as mock_yn:
                res_abort = dlg._on_execute_cleanup()
            self.assertFalse(res_abort)
            self.assertEqual(mock_yn.call_count, 1)
            self.assertIn("おはよう！=Morning!", cp932_file.read_bytes().decode("cp932"))

            # Confirming irreversible deletion executes without archive
            no_arch_dir = self.tmp_dir / "should_remain_empty"
            dlg.var_archive_dir.set(str(no_arch_dir))
            with patch.object(misora.messagebox, "askyesno", return_value=True) as mock_yn2:
                res_ok = dlg._on_execute_cleanup()
            self.assertTrue(res_ok)
            self.assertGreaterEqual(mock_yn2.call_count, 1)
            self.assertFalse(no_arch_dir.exists())
            self.assertNotIn("おはよう！=Morning!", cp932_file.read_bytes().decode("cp932"))
        finally:
            if dlg.winfo_exists():
                dlg._on_close()

    def test_probe_4_archive_first_and_partial_batch_failure_report(self) -> None:
        """[Probe 4] Archive writes first; failure on File #2 leaves File #1 modified, File #2 intact/rolled back, and returns granular CleanupReport."""
        from core.xuat_cleanup import AppliedXuatRecord, classify_cleanup_candidates, execute_cleanup

        proj_dir, text_dir = self._make_xuat_tree()
        f1 = text_dir / "A_First.txt"
        f2 = text_dir / "B_Second.txt"
        f1.write_text("一=One line\n残す1=Keep1\n", encoding="utf-8")
        f2_orig = "二=Two line\n残す2=Keep2\n".encode("utf-8")
        f2.write_bytes(f2_orig)

        idx = build_xuat_index([proj_dir])
        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "一"]),
            Record(cmd_id=6, cmd_name="print", args=["キャル", "二"]),
        ])
        applied = [
            AppliedXuatRecord(file_path=f1, line_number=1, raw_key="一", value="One line", box_index=0),
            AppliedXuatRecord(file_path=f2, line_number=1, raw_key="二", value="Two line", box_index=1),
        ]
        analysis = classify_cleanup_candidates(idx, doc, applied_records=applied)

        archive_dir = self.tmp_dir / "partial_arch"

        def fail_second(path: Path, _text: str) -> None:
            if path.name == "B_Second.txt":
                raise OSError("Simulated validation/write failure on File #2")

        report = execute_cleanup(
            candidates=analysis.candidates,
            source_fingerprints=idx.file_fingerprints,
            archive_dir=archive_dir,
            archive_ext=".xuat.old",
            archive_strategy="combined",
            safety_backup_enabled=True,
            safety_backup_dir=self.tmp_dir / "partial_safety",
            per_file_validator=fail_second,
        )

        # Archive was written first containing both entries
        self.assertEqual(len(report.archived_files), 1)
        arch_text = report.archived_files[0].read_text(encoding="utf-8")
        self.assertIn("一=One line", arch_text)
        self.assertIn("二=Two line", arch_text)

        # File #1 modified; File #2 preserved intact & reported in rolled_back/untouched + errors
        self.assertEqual(report.modified_files, [f1])
        self.assertEqual(f1.read_text(encoding="utf-8"), "残す1=Keep1\n")
        self.assertEqual(f2.read_bytes(), f2_orig)
        self.assertIn(f2, report.rolled_back_files + report.untouched_files)
        self.assertEqual(len(report.errors), 1)
        self.assertEqual(report.errors[0][0], f2)

    def test_probe_5_duplicate_scope_and_conservative_uncertain_classification(self) -> None:
        """[Probe 5] Duplicate scope (selected_only vs all_duplicates, UI hidden at 0 dups), no substring delete, unique vs uncertain classification & speaker guard."""
        from core.xuat_cleanup import AppliedXuatRecord, apply_duplicate_scope, classify_cleanup_candidates

        proj_dir, text_dir = self._make_xuat_tree()
        f_main = text_dir / "A_Main.txt"
        f_alt = text_dir / "B_Alt.txt"
        f_main.write_text(
            "おはよう！=Good morning!\n"
            "おはよう！元気？=Good morning! How are you?\n"
            "主さま、お帰りなさいませ。=Welcome home, my Lord.\n"
            "はい=Yes.\n"
            "了解です=Understood.\n"
            "ペコリーヌ=Pecorine\n",
            encoding="utf-8",
        )
        f_alt.write_text(
            "おはよう！=Morning everyone!\n"
            "分かりました=Understood.\n",
            encoding="utf-8",
        )

        idx = build_xuat_index([proj_dir])
        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "おはよう！"]),
            Record(cmd_id=6, cmd_name="print", args=["コッコロ", "Welcome home, my Lord."]),
            Record(cmd_id=6, cmd_name="print", args=["ユイ", "Yes."]),
            Record(cmd_id=6, cmd_name="print", args=["キャル", "Understood."]),
        ])
        applied = [
            AppliedXuatRecord(file_path=f_main, line_number=1, raw_key="おはよう！", value="Good morning!", box_index=0),
        ]

        # selected_only
        a_sel = classify_cleanup_candidates(idx, doc, applied_records=applied, duplicate_scope="selected_only")
        by_line = {(c.file_path.name, c.line_number): c for c in a_sel.candidates}

        self.assertEqual(by_line[("A_Main.txt", 1)].tier, "applied")
        self.assertTrue(by_line[("A_Main.txt", 1)].selected)

        self.assertEqual(by_line[("B_Alt.txt", 1)].tier, "duplicate")
        self.assertFalse(by_line[("B_Alt.txt", 1)].selected)

        # Prefix/substring non-match must NOT appear
        self.assertNotIn(("A_Main.txt", 2), by_line)

        # Unique long right-side match -> already_translated_unique (selected=True)
        self.assertEqual(by_line[("A_Main.txt", 3)].tier, "already_translated_unique")
        self.assertTrue(by_line[("A_Main.txt", 3)].selected)

        # Short right-side match ("Yes.") -> uncertain (selected=False)
        self.assertEqual(by_line[("A_Main.txt", 4)].tier, "uncertain")
        self.assertFalse(by_line[("A_Main.txt", 4)].selected)

        # Multi-key ambiguous match ("Understood.") -> uncertain (selected=False)
        self.assertEqual(by_line[("A_Main.txt", 5)].tier, "uncertain")
        self.assertFalse(by_line[("A_Main.txt", 5)].selected)
        self.assertEqual(by_line[("B_Alt.txt", 2)].tier, "uncertain")
        self.assertFalse(by_line[("B_Alt.txt", 2)].selected)

        # U-11: Global speaker dictionary entries are COMPLETELY EXCLUDED from candidates
        self.assertNotIn(("A_Main.txt", 6), by_line)

        # Switch duplicate scope to all_duplicates
        apply_duplicate_scope(a_sel.candidates, "all_duplicates")
        self.assertTrue(by_line[("B_Alt.txt", 1)].selected)

        # UI hides duplicate toggle when 0 duplicates exist
        f_nodup = self.tmp_dir / "nodup" / "BepInEx" / "Translation" / "en" / "Text"
        f_nodup.mkdir(parents=True, exist_ok=True)
        nd_file = f_nodup / "Single.txt"
        nd_file.write_text("一意=Unique dialogue translation\n", encoding="utf-8")
        idx_nd = build_xuat_index([f_nodup.parent.parent.parent.parent])
        doc_nd = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["A", "一意"])])
        dlg = misora.XuatCleanupDialog(
            self.app,
            xuat_index=idx_nd,
            doc=doc_nd,
            applied_records=[AppliedXuatRecord(file_path=nd_file, line_number=1, raw_key="一意", value="Unique dialogue translation", box_index=0)],
            source_fingerprints=idx_nd.file_fingerprints,
        )
        try:
            self._wait_for_cleanup_scan(dlg)
            self.assertFalse(bool(dlg._dup_scope_frame.winfo_manager()), "Duplicate scope toggle must be hidden when 0 duplicates exist")
        finally:
            if dlg.winfo_exists():
                dlg._on_close()

        # Verify manual Tools -> XUAT Translation Archiving... entry point works cleanly
        self.app._set_project_folder(f_nodup.parent.parent.parent.parent)
        self.app.open_documents[self.tmp_dir / "nd.v2.txt"] = {"doc": doc_nd, "plain_text": "", "dirty": False}
        self.app.current_doc = doc_nd
        self.app.current_file_path = self.tmp_dir / "nd.v2.txt"
        manual_dlg = self.app.on_clean_archive_xuat(xuat_index=idx_nd)
        self.assertIsNotNone(manual_dlg)
        try:
            self._wait_for_cleanup_scan(manual_dlg)
            self.assertIs(self.app._xuat_cleanup_dialog, manual_dlg)
            self.assertEqual(manual_dlg._analysis.counts_by_tier["applied"], 0)
        finally:
            if manual_dlg.winfo_exists():
                manual_dlg._on_close()

    def test_probe_6_empty_file_detection_and_debug_safety_toggle(self) -> None:
        """[Probe 6] Comments+whitespace-only file flagged empty without auto-delete, 2-step delete quotes exact backup path, and Debug > Safety persists."""
        from core.xuat_cleanup import (
            AppliedXuatRecord,
            classify_cleanup_candidates,
            execute_cleanup,
            is_xuat_file_meaningfully_empty,
        )

        proj_dir, text_dir = self._make_xuat_tree()
        f_only = text_dir / "OnlyOne.txt"
        f_only.write_text("# comment\n// another\n   \n消す行=Remove me\n", encoding="utf-8")

        idx = build_xuat_index([proj_dir])
        doc = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["A", "消す行"])])
        applied = [AppliedXuatRecord(file_path=f_only, line_number=4, raw_key="消す行", value="Remove me", box_index=0)]

        # Test engine non-auto-delete
        analysis = classify_cleanup_candidates(idx, doc, applied_records=applied)
        safety_dir = self.tmp_dir / "safety_6"
        report = execute_cleanup(
            candidates=analysis.candidates,
            source_fingerprints=idx.file_fingerprints,
            archive_dir=self.tmp_dir / "arch_6",
            safety_backup_enabled=True,
            safety_backup_dir=safety_dir,
        )
        self.assertTrue(f_only.is_file(), "Engine must NEVER auto-delete empty files")
        self.assertTrue(is_xuat_file_meaningfully_empty(f_only))
        self.assertEqual(len(report.empty_files), 1)
        self.assertIsNotNone(report.empty_files[0].safety_backup_path)
        self.assertTrue(report.empty_files[0].safety_backup_path.is_file())

        # Debug > Safety submenu toggle OFF requires confirmation and persists
        self.assertTrue(self.app.var_xuat_safety_backup.get())
        with patch.object(misora.messagebox, "askyesno", return_value=False) as mock_cancel:
            self.app.var_xuat_safety_backup.set(False)
            self.app._on_toggle_xuat_safety_backup()
        self.assertEqual(mock_cancel.call_count, 1)
        self.assertTrue(self.app.var_xuat_safety_backup.get())

        with patch.object(misora.messagebox, "askyesno", return_value=True) as mock_ok:
            self.app.var_xuat_safety_backup.set(False)
            self.app._on_toggle_xuat_safety_backup()
        self.assertEqual(mock_ok.call_count, 1)
        self.assertFalse(self.app.var_xuat_safety_backup.get())

        cfg_data = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertFalse(cfg_data["xuat_cleanup"]["safety_backup_enabled"])

        # Re-seed file and verify UI 2-step confirmation quotes no-backup warning when OFF, then exact backup when ON
        f_only.write_text("# comment\n消す行=Remove me\n", encoding="utf-8")
        idx2 = build_xuat_index([proj_dir])
        dlg = misora.XuatCleanupDialog(
            self.app,
            xuat_index=idx2,
            doc=doc,
            applied_records=[AppliedXuatRecord(file_path=f_only, line_number=2, raw_key="消す行", value="Remove me", box_index=0)],
            source_fingerprints=idx2.file_fingerprints,
        )
        try:
            self._wait_for_cleanup_scan(dlg)
            prompts = []
            def _capture_yesno(title, msg, **kwargs):
                prompts.append((title, msg))
                return False  # Do not delete on first check

            with patch.object(misora.messagebox, "askyesno", side_effect=_capture_yesno):
                dlg._on_execute_cleanup()
            self.assertTrue(f_only.is_file())
            self.assertTrue(any("NOT protected" in m for _, m in prompts))
        finally:
            if dlg.winfo_exists():
                dlg._on_close()

        # Re-enable safety backup and confirm deletion quotes exact safety backup path
        self.app._set_project_folder(proj_dir)
        self.app.var_xuat_safety_backup.set(True)
        self.app._on_toggle_xuat_safety_backup()
        f_only.write_text("# comment\n消す行=Remove me\n", encoding="utf-8")
        idx3 = build_xuat_index([proj_dir])
        dlg2 = misora.XuatCleanupDialog(
            self.app,
            xuat_index=idx3,
            doc=doc,
            applied_records=[AppliedXuatRecord(file_path=f_only, line_number=2, raw_key="消す行", value="Remove me", box_index=0)],
            source_fingerprints=idx3.file_fingerprints,
        )
        try:
            self._wait_for_cleanup_scan(dlg2)
            prompts2 = []
            def _confirm_del(title, msg, **kwargs):
                prompts2.append((title, msg))
                return True

            with patch.object(misora.messagebox, "askyesno", side_effect=_confirm_del):
                dlg2._on_execute_cleanup()
            self.assertFalse(f_only.is_file(), "Confirmed empty file should be deleted")
            self.assertTrue(any("OnlyOne" in m and "backups" in m for _, m in prompts2))
        finally:
            if dlg2.winfo_exists():
                dlg2._on_close()

        # Verify Debug > Safety > XUAT Cleanup & Archive Settings dialog & malformed config recovery
        s_dlg = self.app._on_xuat_cleanup_settings_dialog()
        self.assertIsNotNone(s_dlg)
        try:
            s_dlg.var_archive_ext.set(".txt")
            self.app.update_idletasks()
            self.assertIn(".txt", s_dlg.lbl_warning.cget("text"))
            s_dlg.var_archive_ext.set(".xuat.old")
            s_dlg.var_strategy.set("per_source_file")
            s_dlg._on_save()
        finally:
            if s_dlg.winfo_exists():
                s_dlg._on_close()

        # Corrupt xuat_cleanup sub-keys recover cleanly without losing other prefs
        # Destroy first Tk root and collect before creating a second MisoraApp (AGENTS.md §3: single tk.Tk())
        self.app.destroy()
        self.app = None
        import gc
        gc.collect()
        bad_cfg = self.tmp_dir / "malformed_xc_config.json"
        bad_cfg.write_text(
            json.dumps({
                "dialogue_font_size": 17,
                "xuat_cleanup": {
                    "safety_backup_enabled": "not-a-bool",
                    "archive_strategy": "invalid_strategy",
                    "archive_ext": 12345,
                },
            }),
            encoding="utf-8",
        )
        with patch.object(misora, "CONFIG_PATH", bad_cfg):
            app2 = misora.MisoraApp(restore_session=False, show_splash=False)
            app2.withdraw()
            app2.backup_folder = str(self.tmp_dir / "backups2")
            try:
                self.assertEqual(app2.dialogue_font_size, 17)
                self.assertTrue(app2.xuat_safety_backup_enabled)
                self.assertEqual(app2.xuat_archive_strategy, "combined")
                self.assertEqual(app2.xuat_archive_ext, ".xuat.old")
            finally:
                app2.destroy()

    def test_probe_7_pure_core_boundary_no_tkinter_or_misora_import(self) -> None:
        """[Probe 7] core.xuat_cleanup imports zero tkinter or misora modules and accepts injected backup_path_fn."""
        cmd = [
            sys.executable,
            "-c",
            (
                "import sys; import core.xuat_cleanup as xc; "
                "assert 'tkinter' not in sys.modules, 'tkinter imported'; "
                "assert 'misora' not in sys.modules, 'misora imported'; "
                "assert hasattr(xc, 'execute_cleanup')"
            ),
        ]
        res = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Pure-core boundary failed: {res.stderr}")

        from core.xuat_cleanup import AppliedXuatRecord, classify_cleanup_candidates, execute_cleanup

        proj_dir, text_dir = self._make_xuat_tree()
        tf = text_dir / "CbTest.txt"
        tf.write_text("あ=Alpha\nい=Beta\n", encoding="utf-8")
        idx = build_xuat_index([proj_dir])
        doc = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["A", "あ"])])
        analysis = classify_cleanup_candidates(
            idx,
            doc,
            applied_records=[AppliedXuatRecord(file_path=tf, line_number=1, raw_key="あ", value="Alpha", box_index=0)],
        )

        called_paths = []
        def custom_bak(src: Path, bak_dir: Path, tag: str) -> Path:
            bak_dir.mkdir(parents=True, exist_ok=True)
            out = bak_dir / f"custom_{tag}_{src.name}"
            called_paths.append(out)
            return out

        rep = execute_cleanup(
            candidates=analysis.candidates,
            source_fingerprints=idx.file_fingerprints,
            archive_dir=self.tmp_dir / "cb_arch",
            safety_backup_enabled=True,
            safety_backup_dir=self.tmp_dir / "cb_safety",
            backup_path_fn=custom_bak,
        )
        self.assertEqual(len(called_paths), 1)
        self.assertEqual(rep.safety_backups.get(tf), called_paths[0])
        self.assertTrue(called_paths[0].is_file())

    def test_guard_1_import_cancel_never_opens_cleanup_or_modifies_xuat(self) -> None:
        """[Guard 1] Cancelling ImportFromXUATDialog never opens cleanup dialog or modifies XUAT files."""
        proj_dir, text_dir = self._make_xuat_tree()
        tf = text_dir / "Main.txt"
        orig = "おはよう！=Good morning!\n".encode("utf-8")
        tf.write_bytes(orig)

        self.app._set_project_folder(proj_dir)
        doc = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "おはよう！"])])
        story_p = self.tmp_dir / "g1.v2.txt"
        story_p.write_text(doc.to_v2_text(), encoding="utf-8")
        self.app.open_file(story_p)

        dlg = self.app.on_import_from_xuat()
        self.assertIsNotNone(dlg)
        dlg._on_close()
        self.assertIsNone(getattr(self.app, "_xuat_cleanup_dialog", None))
        self.assertEqual(tf.read_bytes(), orig)

    def test_guard_2_strict_decode_rejects_corrupt_bytes_without_rewriting(self) -> None:
        """[Guard 2] Corrupt binary bytes in an XUAT file raise UnicodeDecodeError without errors='replace' corruption."""
        proj_dir, text_dir = self._make_xuat_tree()
        bad_file = text_dir / "Corrupt.txt"
        corrupt_bytes = b"\x80\x81\xfe\xff\x00\x01invalid"
        bad_file.write_bytes(corrupt_bytes)

        with self.assertRaises(UnicodeDecodeError):
            read_text_file_strictly(bad_file)

        idx = build_xuat_index([proj_dir])
        self.assertEqual(len(idx.skipped_files), 1)
        self.assertEqual(idx.skipped_files[0][0], bad_file)
        self.assertEqual(bad_file.read_bytes(), corrupt_bytes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
