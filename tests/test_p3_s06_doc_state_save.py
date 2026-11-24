"""
Unit and regression test suite for Phase 2.5 S06:
Per-Document State/Stable Locks, Plain-Text Preview Save, Windows LF Writes & 0-Box Save
(BUG-11, BUG-12, BUG-18, BUG-19).

Defect Probes (failing-first):
- Probe 1 (BUG-11): Plain-text on_save() preserves NGUI markup while var_preview_compiled is True.
- Probe 2 (BUG-12): Per-document state (locks, cursor, modified boxes, original JP snapshot) preserved
  across tab switches; non-switching _save_document_entry() saves inactive dirty docs during close_file;
  stable lock identity helpers (box_ordinal, sha256(jp)) round-trip and return unresolved locks.
- Probe 3 (BUG-18): write_atomic_encoded() with newline='\n' writes raw LF (zero CRLF) on Windows;
  on_export_script() writes LF atomically without Windows newline translation.
- Probe 4 (BUG-19): Saving 0-box metadata-only story succeeds across Page, Continuous, and Preview modes
  with zero IndexError.

Regression Guard:
- Guard 1: Direct lightweight sanity check for S1/S2/S3/S8b3 contracts.
"""

import hashlib
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import misora
from core.story_ast import Record, StoryDocument
from core.text_encoding import encode_with_metadata, write_atomic_encoded


class TestP3S06DocStateSave(unittest.TestCase):
    """S06: Per-document state, stable locks, preview save, Windows LF & 0-box save."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s06_"))
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
            try:
                p.stop()
            except Exception:
                pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        misora.CONFIG_PATH = self._orig_config_path

    def _make_v2_script(self, filename: str, box_count: int = 5, meta: bool = True) -> Path:
        """Create a valid v2 story script with the requested number of boxes."""
        doc = StoryDocument()
        records = []
        if meta:
            records.append(Record(cmd_id=0, cmd_name="title", args=["Test Title"]))
            records.append(Record(cmd_id=1, cmd_name="outline", args=["Test Synopsis"]))
        for i in range(box_count):
            if i > 0:
                records.append(Record(cmd_id=10, cmd_name="touch", args=[]))
            records.append(Record(cmd_id=6, cmd_name="print", args=[f"Speaker_{i}", f"Japanese Text Box {i} [FF0000]Red[-] {{0}}"]))
        doc.records = records
        doc._rebuild_boxes()
        p = self.tmp_dir / filename
        p.write_text(doc.to_v2_text(), encoding="utf-8")
        return p

    def _make_plain_txt(self, filename: str, content: str) -> Path:
        """Create a plain text file."""
        p = self.tmp_dir / filename
        p.write_text(content, encoding="utf-8")
        return p

    # -------------------------------------------------------------------------
    # Defect Probes (MUST FAIL before patch, PASS after patch)
    # -------------------------------------------------------------------------
    def test_probe_1_bug11_plain_text_preview_save_preserves_tags(self):
        """[Probe 1 — BUG-11] Plain-text on_save() preserves NGUI markup under compiled preview.

        Pre-patch: on_save() reads from txt_dialogue or txt_continuous which contains stripped
        compiled text when var_preview_compiled is True, destroying all NGUI tags on disk.
        Post-patch: on_save() writes authoritative self._plain_text_content, preserving exact tags.
        """
        raw_content = "[FF0000]Red Text[-] and [00FF00]Green[-]"
        txt_path = self._make_plain_txt("tagged_plain.txt", raw_content)

        self.app.open_file(txt_path)
        self.assertEqual(self.app._plain_text_content, raw_content)

        # Toggle compiled preview ON
        self.app.var_preview_compiled.set(True)
        self.app._update_views()

        # The text widget display will show compiled (stripped) text
        widget_text = self.app.txt_dialogue.get("1.0", "end-1c")
        self.assertNotIn("[FF0000]", widget_text)
        self.assertIn("Red Text", widget_text)

        # Trigger Save while Preview is ON
        save_success = self.app.on_save()
        self.assertTrue(save_success)

        # Read back from disk — must retain original raw NGUI tags!
        saved_disk_content = txt_path.read_text(encoding="utf-8")
        self.assertIn("[FF0000]Red Text[-]", saved_disk_content,
                      "Disk file lost NGUI markup during preview save!")
        self.assertIn("[00FF00]Green[-]", saved_disk_content,
                      "Disk file lost NGUI markup during preview save!")
        self.assertEqual(saved_disk_content, raw_content)

    def test_probe_2_bug12_per_document_state_locks_and_inactive_save(self):
        """[Probe 2 — BUG-12] Per-document state, stable locks, and non-switching inactive save.

        Pre-patch:
        - open_file() clears _locked_boxes, resets current_box_idx to 0, and clobbers
          _original_box_texts with current clean_text on tab switch / cache hit.
        - close_file() switches active UI to inactive doc to save it, disrupting context.
        - No helpers for stable lock persistence (box_ordinal, sha256(jp)).
        Post-patch:
        - Box 2 remains locked, active box 4 persists, immutable JP snapshot is intact.
        - Inactive Doc A saves cleanly via _save_document_entry() without switching away Doc B.
        - Stable lock helpers compute and restore locks, returning (matched, unresolved).
        """
        doc_a_path = self._make_v2_script("doc_a.v2.txt", box_count=5)
        doc_b_path = self._make_v2_script("doc_b.v2.txt", box_count=2)

        # 1. Open Doc A, lock Box 2, navigate to Box 4, and mutate Box 4
        self.app.open_file(doc_a_path)
        self.assertEqual(len(self.app.current_doc.boxes), 5)
        self.app.current_box_idx = 2
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(2), "Box 2 should be locked")

        # Navigate to Box 4 and edit it
        self.app.current_box_idx = 4
        orig_jp_box4 = self.app.current_doc.boxes[4].clean_text
        self.app.txt_dialogue.delete("1.0", "end")
        self.app.txt_dialogue.insert("1.0", "Translated English Text Box 4")
        self.app._on_dialogue_edited()
        self.assertTrue(self.app.is_dirty)

        # 2. Open Doc B (switches away from Doc A)
        self.app.open_file(doc_b_path)
        self.assertEqual(self.app.current_file_path.resolve(), doc_b_path.resolve())

        # 3. Switch back to Doc A
        self.app.open_file(doc_a_path)
        self.assertEqual(self.app.current_file_path.resolve(), doc_a_path.resolve())

        # Assert per-document state was restored!
        self.assertTrue(self.app.is_box_locked(2),
                        "Box 2 lock status was lost after switching documents!")
        self.assertEqual(self.app.current_box_idx, 4,
                         "Active cursor box index 4 was reset to 0 on switch!")
        # Rule 10: Original JP snapshot must NOT be overwritten with English text!
        self.assertEqual(self.app._original_box_texts.get(4), orig_jp_box4,
                         "Original Japanese snapshot was overwritten with English text!")

        # 4. Switch back to Doc B; Doc A is now inactive and dirty
        self.app.open_file(doc_b_path)
        self.assertEqual(self.app.current_file_path.resolve(), doc_b_path.resolve())
        doc_a_entry = self.app.open_documents.get(doc_a_path.resolve())
        self.assertIsNotNone(doc_a_entry)
        self.assertTrue(doc_a_entry.get("dirty", False))

        # Close Doc A while Doc B is active, choosing Save (ans=True)
        with patch.object(misora.messagebox, "askyesnocancel", return_value=True):
            closed = self.app.close_file(doc_a_path)
            self.assertTrue(closed)

        # Assert Doc A is removed from open_documents and saved to disk
        self.assertNotIn(doc_a_path.resolve(), self.app.open_documents)
        saved_a_disk = doc_a_path.read_text(encoding="utf-8")
        self.assertIn("Translated English Text Box 4", saved_a_disk)

        # Crucial: Doc B must REMAIN active without UI churn
        self.assertEqual(self.app.current_file_path.resolve(), doc_b_path.resolve(),
                         "close_file() churned active UI document context!")

        # 5. Stable lock identity helper verification
        doc = StoryDocument.from_v2_text(doc_a_path.read_text(encoding="utf-8"))
        locked_uids = {doc.boxes[2].uid}
        orig_jp_map = {doc.boxes[2].uid: "Original JP Box 2"}

        stable_locks = misora.get_document_stable_locks(doc, locked_uids, orig_jp_map)
        self.assertEqual(len(stable_locks), 1)
        ordinal, sha_hash = stable_locks[0]
        self.assertEqual(ordinal, 2)
        expected_hash = hashlib.sha256("Original JP Box 2".encode("utf-8")).hexdigest()
        self.assertEqual(sha_hash, expected_hash)

        # Round-trip restore_stable_locks
        matched, unresolved = misora.restore_stable_locks(doc, stable_locks, orig_jp_map)
        self.assertEqual(matched, {doc.boxes[2].uid})
        self.assertEqual(unresolved, [])

        # Test unmatched / modified lock detection (never silently transferred)
        bad_locks = [(2, "deadbeef" * 8), (99, "cafebabe" * 8)]
        matched_bad, unresolved_bad = misora.restore_stable_locks(doc, bad_locks, orig_jp_map)
        self.assertEqual(matched_bad, set())
        self.assertEqual(len(unresolved_bad), 2)
        self.assertIn((2, "deadbeef" * 8), unresolved_bad)
        self.assertIn((99, "cafebabe" * 8), unresolved_bad)

    def test_probe_3_bug18_write_atomic_encoded_lf_and_export_script(self):
        """[Probe 3 — BUG-18] write_atomic_encoded preserves LF; on_export_script is atomic & LF.

        Pre-patch:
        - write_atomic_encoded() uses write_text(content) when newline in (None, '\n') and has_bom=False,
          which translates \n into \r\n on Windows.
        - on_export_script() uses target_path.write_text(), translating \n to \r\n and non-atomic.
        Post-patch:
        - write_atomic_encoded() always writes bytes via tmp_file.write_bytes(data).
        - on_export_script() calls write_atomic_encoded(..., newline='\n').
        """
        # Part A: Direct write_atomic_encoded LF test on Windows
        test_file = self.tmp_dir / "lf_test.txt"
        content_lf = "alpha\nbeta\ngamma\n"
        write_atomic_encoded(test_file, content_lf, encoding="utf-8", newline="\n")

        raw_bytes = test_file.read_bytes()
        self.assertNotIn(b"\r\n", raw_bytes,
                         "write_atomic_encoded mangled LF into CRLF on Windows!")
        self.assertEqual(raw_bytes, b"alpha\nbeta\ngamma\n")

        # Part B: on_export_script atomic & LF test
        story_file = self._make_v2_script("export_source.v2.txt", box_count=2)
        self.app.open_file(story_file)

        export_target = self.tmp_dir / "exported_script.csif.txt"
        exported_path = self.app.on_export_script(file_path=export_target)
        self.assertIsNotNone(exported_path)
        self.assertTrue(export_target.is_file())

        export_raw = export_target.read_bytes()
        self.assertNotIn(b"\r\n", export_raw,
                         "on_export_script wrote Windows CRLF instead of atomic LF!")
        self.assertIn(b"@@Speaker_0", export_raw)

    def test_probe_4_bug19_zero_box_story_saves_cleanly(self):
        """[Probe 4 — BUG-19] Saving 0-box metadata-only story succeeds without IndexError.

        Pre-patch: on_save() accesses current_doc.boxes[current_box_idx] or calls inject_box()
        in preview, continuous, and page branches, raising IndexError when boxes list is empty.
        Post-patch: All three branches guard not current_doc.boxes cleanly.
        """
        # Create a metadata-only story with 0 dialogue boxes
        zero_v2 = (
            "#!priconne-story\n"
            "format: v2\n"
            "\n"
            "meta: title\n"
            "  Zero Box Story\n"
            "meta: synopsis\n"
            "  Synopsis Only\n"
        )
        zero_path = self.tmp_dir / "zero_box.v2.txt"
        zero_path.write_text(zero_v2, encoding="utf-8")

        self.app.open_file(zero_path)
        self.assertEqual(len(self.app.current_doc.boxes), 0)

        # 1. Page View Save (var_continuous_view = False, var_preview_compiled = False)
        self.app.var_continuous_view.set(False)
        self.app.var_preview_compiled.set(False)
        self.app.is_box0_active = False  # explicitly test non-box0 active path
        try:
            ok_page = self.app.on_save()
            self.assertTrue(ok_page, "Page view save on 0-box story failed!")
        except IndexError as e:
            self.fail(f"on_save() raised IndexError in Page View for 0-box story: {e}")

        # 2. Continuous View Save (var_continuous_view = True)
        self.app.var_continuous_view.set(True)
        self.app.var_preview_compiled.set(False)
        self.app.is_box0_active = False
        try:
            ok_cont = self.app.on_save()
            self.assertTrue(ok_cont, "Continuous view save on 0-box story failed!")
        except IndexError as e:
            self.fail(f"on_save() raised IndexError in Continuous View for 0-box story: {e}")

        # 3. Compiled Preview Save (var_preview_compiled = True)
        self.app.var_continuous_view.set(False)
        self.app.var_preview_compiled.set(True)
        self.app.is_box0_active = False
        try:
            ok_prev = self.app.on_save()
            self.assertTrue(ok_prev, "Preview save on 0-box story failed!")
        except IndexError as e:
            self.fail(f"on_save() raised IndexError in Preview Mode for 0-box story: {e}")

        # Verify disk contents retain metadata
        disk_content = zero_path.read_text(encoding="utf-8")
        self.assertIn("Zero Box Story", disk_content)
        self.assertIn("Synopsis Only", disk_content)

    # -------------------------------------------------------------------------
    # Regression Guards (MUST PASS both before AND after patch)
    # -------------------------------------------------------------------------
    def test_guard_1_s1_s2_s3_s8b3_core_contracts(self):
        """[Guard 1] Lightweight regression guard for S1/S2/S3/S8b3 core contracts."""
        # S8b-3: encode_with_metadata BOM + CRLF
        data = encode_with_metadata("test\ntext", encoding="utf-8", has_bom=True, newline="\r\n")
        self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
        self.assertIn(b"\r\n", data)

        # S3: close clean file removes from open_documents without prompt
        clean_p = self._make_plain_txt("guard_clean.txt", "clean")
        self.app.open_file(clean_p)
        self.assertIn(clean_p.resolve(), self.app.open_documents)
        res = self.app.close_file(clean_p)
        self.assertTrue(res)
        self.assertNotIn(clean_p.resolve(), self.app.open_documents)


if __name__ == "__main__":
    unittest.main()
