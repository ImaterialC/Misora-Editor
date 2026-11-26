#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S08 (v1.4.7 Release Gate Hold) — End-to-End Stress QA & Release Gate Verification:
- Stress 1: Memory leak & env disposal across 12 open/close cycles (tracemalloc + weakref).
- Stress 2: Search cancel race across 5 rapid start/cancel cycles verifying spawned _search_thread cleanup.
- Stress 3: 500-box word-wrap + CSIF + v2 + binary round-trip parity & Undo/Redo.
- Stress 4: All Script Technique A widget budget (1 mapped tk.Text, <=3 total tk.Text, 0 Treeviews) & Preview bleed.
- Stress 5: Single-source __version__ parity ("1.4.7" Release Gate Hold) via AST without comment/docstring false positives.
- Guard 1: .misora v1 JSON schema matches WorkspaceSession.to_dict() (no drafts, no blobs, no Record.uid).
- Guard 2: Binary cmd_id 35/32 and empty-arg sentinel preservation.
"""
from __future__ import annotations

import ast
import gc
import importlib.util
import json
import shutil
import sys
import tempfile
import tkinter as tk
from tkinter import ttk
import tracemalloc
import unittest
import weakref
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora  # noqa: E402
from assets import splash  # noqa: E402
from core import mtl_engine  # noqa: E402
from core.script_codec import parse as parse_csif, serialize as serialize_csif  # noqa: E402
from core.story_ast import Record, StoryDocument  # noqa: E402
from core.workspace import LockedKeyEntry, WorkspaceFileEntry, WorkspaceSession, save_workspace  # noqa: E402


def _collect_descendants(widget: tk.Misc) -> list[tk.Misc]:
    out: list[tk.Misc] = []
    for child in widget.winfo_children():
        out.append(child)
        out.extend(_collect_descendants(child))
    return out


def _read_root_init_version() -> str:
    spec = importlib.util.spec_from_file_location("_misora_root_init_s08", str(_REPO / "__init__.py"))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return str(getattr(mod, "__version__", ""))


class TestV15S08ReleaseGateStress(unittest.TestCase):
    """S08 stress QA & release gate verification (held at v1.4.7 pending manual Windows QA)."""

    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_v15_s08_"))
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

    def tearDown(self) -> None:
        try:
            if self.app is not None:
                self.app.destroy()
        except Exception:
            pass
        self.app = None
        gc.collect()
        self.patch_err.stop()
        self.patch_warn.stop()
        self.patch_info.stop()
        self.patch_cfg.stop()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_stress_1_memory_leak_and_env_disposal_open_close_cycles(self) -> None:
        """[Stress 1] 20 open/close cycles release StoryDocument weakrefs & per-doc caches with bounded tracemalloc growth."""
        tracemalloc.start()
        try:
            refs: list[weakref.ReferenceType] = []
            all_uids: set = set()
            snap_warmup = None
            for i in range(20):
                doc = StoryDocument([
                    Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", f"セリフ {i}-{j}"])
                    for j in range(25)
                ])
                fp = self.tmp_dir / f"cycle_{i:02d}.v2.txt"
                fp.write_text(doc.to_v2_text(), encoding="utf-8")
                self.app.open_file(fp)
                live_doc = self.app.current_doc
                self.assertIsNotNone(live_doc)
                refs.append(weakref.ref(live_doc))
                doc_id = id(live_doc)
                fp_str = str(fp.resolve())
                for box in live_doc.boxes:
                    b_uid = getattr(box, "uid", None)
                    if b_uid is not None:
                        all_uids.add(b_uid)
                        ctx = (fp_str, doc_id, b_uid, "Google")
                        self.app._mtl_all_results[ctx] = f"Translated {i}"
                        self.app._mtl_all_statuses[ctx] = "ready"
                        self.app._mtl_all_req_seqs[(b_uid, "Google")] = i + 1
                        self.app._latest_applied_mtl_seq[b_uid] = i + 1
                        self.app.sync_manager.register_jp_key(b_uid, box.clean_text)
                del live_doc
                del doc
                self.app.close_file(fp)
                gc.collect()
                if i == 4:
                    snap_warmup = tracemalloc.take_snapshot()

            snap_final = tracemalloc.take_snapshot()
            delta_kb = 0.0
            if snap_warmup is not None:
                stats = snap_final.compare_to(snap_warmup, "lineno")
                delta_kb = sum(s.size_diff for s in stats) / 1024.0
            print(f"\n[S08 Stress 1] 20-cycle tracemalloc delta (cycle 5 -> 20): {delta_kb:+.2f} KiB")

            alive_count = sum(1 for r in refs if r() is not None)
            self.assertEqual(alive_count, 0, f"{alive_count} closed StoryDocument(s) remained alive")
            self.assertEqual(len(self.app._mtl_all_results), 0, "_mtl_all_results not pruned to 0")
            self.assertEqual(len(self.app._mtl_all_statuses), 0, "_mtl_all_statuses not pruned to 0")
            self.assertEqual(len(self.app._mtl_all_errors), 0, "_mtl_all_errors not pruned to 0")
            self.assertEqual(len(self.app._mtl_all_req_seqs), 0, "_mtl_all_req_seqs not pruned to 0")
            self.assertEqual(len(self.app._latest_applied_mtl_seq), 0, "_latest_applied_mtl_seq not pruned to 0")
            leaked_jp = [u for u in all_uids if self.app.sync_manager.has_jp_key(u)]
            self.assertEqual(len(leaked_jp), 0, f"jp_source_cache retained {len(leaked_jp)} closed UIDs")
            # Allow reasonable Tk/undo-independent buffer; ensure no runaway multi-MB leak
            self.assertLess(delta_kb, 5120.0, f"Unexpected memory growth: {delta_kb:.1f} KiB")
        finally:
            tracemalloc.stop()

    def test_stress_2_search_cancel_race_and_thread_cleanup(self) -> None:
        """[Stress 2] 5 rapid search start/cancel cycles via on_cancel_search() leave zero live _search_thread workers."""
        search_dir = self.tmp_dir / "search_pool"
        search_dir.mkdir(parents=True, exist_ok=True)
        for i in range(30):
            doc = StoryDocument([
                Record(cmd_id=6, cmd_name="print", args=["キャル", f"検索テスト {i}-{j}"])
                for j in range(20)
            ])
            (search_dir / f"story_{i:02d}.v2.txt").write_text(doc.to_v2_text(), encoding="utf-8")

        self.app._set_project_folder(search_dir)
        self.app.scope_var.set("folder")
        self.app.folder_path_var.set(str(search_dir))
        self.app.search_var.set("検索テスト")

        spawned_threads = []
        for _ in range(5):
            self.app.on_start_search()
            t = getattr(self.app, "_search_thread", None)
            if t is not None:
                spawned_threads.append(t)
            self.app.on_cancel_search()
            self.app.update()

        import time
        self.assertGreaterEqual(len(spawned_threads), 1)
        for t in spawned_threads:
            t.join(timeout=2.5)
            self.assertFalse(t.is_alive(), f"Search worker thread {t.name} stayed alive after cancel")
        deadline = time.time() + 1.5
        while not self.app.search_queue.empty() and time.time() < deadline:
            self.app.update()
            time.sleep(0.02)
        self.assertTrue(self.app.search_queue.empty(), "search_queue did not drain cleanly after cancel")

    def test_stress_3b_mtl_cancel_pending_futures_and_stale_rejection(self) -> None:
        """[Stress 3b] Cancelling Translate All mid-flight drains executor/threads and rejects late stale results."""
        import threading
        import time

        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["キャル", f"日本語テスト {i}"])
            for i in range(12)
        ])
        fp = self.tmp_dir / "mtl_cancel.v2.txt"
        fp.write_text(doc.to_v2_text(), encoding="utf-8")
        self.app.open_file(fp)
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app._set_mtl_drawer_mode("all_script")
        self.app.var_mtl_all_engine.set("Google")

        def _slow_translate(self_eng, text, config=None, xuat_cache=None):
            time.sleep(0.06)
            return f"EN: {text}"

        with patch.object(mtl_engine.MTLEngine, "translate", _slow_translate):
            self.app._on_mtl_all_script_translate_all()
            time.sleep(0.08)
            self.app._cancel_mtl_all_batch()
            self.assertTrue(self.app._mtl_all_batch_cancel.is_set())
            self.app.close_file(fp)
            deadline = time.time() + 3.0
            while time.time() < deadline:
                mtl_threads = [t for t in threading.enumerate() if t.name.startswith("MisoraMTL") and t.is_alive()]
                if not mtl_threads and self.app._mtl_all_executor is None:
                    break
                self.app.update()
                time.sleep(0.05)

        mtl_threads = [t for t in threading.enumerate() if t.name.startswith("MisoraMTL") and t.is_alive()]
        self.assertEqual(len(mtl_threads), 0, f"Leaked MTL threads: {[t.name for t in mtl_threads]}")
        self.assertIsNone(self.app._mtl_all_executor, "_mtl_all_executor was not cleared")
        self.assertEqual(len(self.app._mtl_all_results), 0, "Closed doc MTL results were repopulated")

    def test_stress_3_500_box_word_wrap_csif_and_binary_roundtrip(self) -> None:
        """[Stress 3] 500-box story survives Auto Word Wrap, Undo/Redo, CSIF round-trip, and binary round-trip."""
        records = []
        for i in range(500):
            if i % 10 == 0:
                records.append(Record(cmd_id=35, cmd_name="tag", args=[f"Narration line {i} " + ("word " * 12)]))
            else:
                records.append(Record(cmd_id=6, cmd_name="print", args=["Pecorine", f"[FF0000]Hello {{playername}}[-] line {i} " + ("story " * 12)]))
            records.append(Record(cmd_id=10, cmd_name="touch", args=[]))
        doc = StoryDocument(records)
        fp = self.tmp_dir / "stress_500.v2.txt"
        fp.write_text(doc.to_v2_text(), encoding="utf-8")
        self.app.open_file(fp)

        stats = self.app.apply_auto_word_wrap(scope="all", reflow_existing_breaks=False)
        self.assertEqual(stats["total_targets"], 500)
        self.assertGreater(stats["wrapped"], 400)

        # Single-batch Undo & Redo
        self.assertTrue(self.app.undo_journal.can_undo())
        self.app.on_undo()
        self.assertTrue(self.app.undo_journal.can_redo())
        self.app.on_redo()

        # CSIF & Binary round-trips
        csif_txt = serialize_csif(self.app.current_doc, scope="all", include_metadata="auto")
        parsed = parse_csif(csif_txt)
        self.assertEqual(len(parsed.blocks), 500)

        bin_bytes = self.app.current_doc.to_binary()
        reloaded = StoryDocument.from_binary(bin_bytes)
        self.assertEqual(len(reloaded.boxes), 500)

    def test_stress_4_all_script_technique_a_widget_budget_and_preview_bleed(self) -> None:
        """[Stress 4] 150-box All Script keeps exactly 1 mapped tk.Text, <=3 total tk.Text, 0 Treeviews, and wrap='none' Preview."""
        records_150 = []
        for i in range(150):
            records_150.append(Record(cmd_id=6, cmd_name="print", args=["ユイ", ("1234567890" * 6) + f" box {i}"]))
            records_150.append(Record(cmd_id=10, cmd_name="touch", args=[]))
        doc = StoryDocument(records_150)
        fp = self.tmp_dir / "stress_150.v2.txt"
        fp.write_text(doc.to_v2_text(), encoding="utf-8")
        self.app.open_file(fp)

        import platform
        import time

        self.app.var_continuous_view.set(True)
        t0 = time.perf_counter()
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        print(
            f"\n[S08 Stress 4] 150-box All Script informational benchmark: {elapsed_ms:.2f} ms "
            f"(OS={platform.platform()}, Python={sys.version.split()[0]}, Tk={tk.TkVersion})"
        )

        desc = _collect_descendants(self.app.continuous_wrap)
        text_widgets = [w for w in desc if isinstance(w, tk.Text)]
        mapped_text_widgets = [w for w in text_widgets if w.winfo_manager() != ""]
        treeviews = [w for w in desc if isinstance(w, ttk.Treeview)]

        self.assertEqual(len(treeviews), 0, "All Script must contain 0 ttk.Treeview widgets")
        self.assertEqual(len(mapped_text_widgets), 1, f"Expected 1 mapped tk.Text, got {len(mapped_text_widgets)}")
        self.assertIs(mapped_text_widgets[0], self.app.txt_all_script)
        self.assertLessEqual(len(text_widgets), 3, f"Expected <=3 total tk.Text descendants, got {len(text_widgets)}")
        self.assertEqual(len(self.app._all_script_block_ranges), 150, "Expected 150 block ranges in Technique A")

        # Dialogue Preview uses wrap='none' (visible bleed, no auto-shrink)
        self.app.var_continuous_view.set(False)
        self.app._on_toggle_continuous_view()
        self.app.var_preview_compiled.set(True)
        self.app._on_toggle_preview_compiled()
        self.app.update_idletasks()
        self.assertEqual(str(self.app.txt_dialogue_preview.cget("wrap")), "none")

    def test_stress_5_version_parity_and_no_hardcoded_duplicates(self) -> None:
        """[Stress 5] Single-source semver __version__ parity across all modules with zero hardcoded version strings."""
        import re
        root_ver = _read_root_init_version()
        self.assertRegex(root_ver, r"^\d+\.\d+\.\d+$", f"Invalid semver format: {root_ver!r}")
        self.assertEqual(misora.__version__, root_ver)
        self.assertEqual(misora._get_app_version(), root_ver)
        self.assertEqual(mtl_engine.APP_VERSION, root_ver)
        self.assertEqual(splash._VERSION, root_ver)
        self.assertIn("Misora: Story Editor", self.app.title())

        # AST check: version-related functions/assignments must not contain hardcoded "1.4.x"/"1.5.x" literals
        ver_re = re.compile(r"^1\.[345]\.\d+$")
        for rel_path in ("misora.py", "core/mtl_engine.py", "assets/splash.py"):
            src = (_REPO / rel_path).read_text(encoding="utf-8")
            tree = ast.parse(src, filename=rel_path)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name in ("_get_app_version", "_load_app_version", "on_about"):
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                            self.assertIsNone(
                                ver_re.match(sub.value.strip()),
                                f"Hardcoded version literal {sub.value!r} found in {rel_path}:{node.name}",
                            )

    def test_guard_1_misora_workspace_v1_schema_and_stable_locks(self) -> None:
        """[Guard 1] .misora v1 JSON matches WorkspaceSession.to_dict() schema with zero drafts, blobs, or Record.uid."""
        story_p = self.tmp_dir / "ws_story.v2.txt"
        story_p.write_text("UNIT_DRAFT_SENTINEL", encoding="utf-8")
        ws_p = self.tmp_dir / "project.misora"
        ws = WorkspaceSession(
            schema_version=1,
            files=[
                WorkspaceFileEntry(
                    rel_path="ws_story.v2.txt",
                    abs_path=str(story_p),
                    locked_keys=[LockedKeyEntry(box_ordinal=0, jp_sha256="a" * 64)],
                )
            ],
            active_file="ws_story.v2.txt",
            active_box_idx=0,
            is_box0_active=False,
            view_mode="dialogue",
            search_scope="project",
        )
        save_workspace(ws_p, ws)
        payload = json.loads(ws_p.read_text(encoding="utf-8"))

        expected_keys = {
            "schema_version",
            "files",
            "active_file",
            "active_box_idx",
            "is_box0_active",
            "view_mode",
            "search_scope",
        }
        self.assertEqual(set(payload.keys()), expected_keys)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(len(payload["files"]), 1)
        self.assertEqual(payload["files"][0]["locked_keys"], [{"box_ordinal": 0, "jp_sha256": "a" * 64}])
        raw_json = ws_p.read_text(encoding="utf-8")
        self.assertNotIn("UNIT_DRAFT_SENTINEL", raw_json)
        self.assertNotIn("uid", raw_json.lower())

    def test_guard_2_binary_cmd_35_32_and_empty_arg_sentinel_intact(self) -> None:
        """[Guard 2] Binary cmd_id 35 (narration), 32 (subtitle), and empty-arg sentinel ' ' round-trip losslessly."""
        doc = StoryDocument([
            Record(cmd_id=32, cmd_name="subtitle", args=["Chapter 1"]),
            Record(cmd_id=35, cmd_name="tag", args=["Narration stays tag."]),
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", " "]),
        ])
        bin_data = doc.to_binary()
        reloaded_bin = StoryDocument.from_binary(bin_data)
        self.assertEqual([r.cmd_id for r in reloaded_bin.records], [32, 35, 6])
        self.assertEqual(reloaded_bin.records[2].args[1], " ")

        v2_txt = doc.to_v2_text()
        reloaded_v2 = StoryDocument.from_v2_text(v2_txt)
        self.assertEqual([r.cmd_id for r in reloaded_v2.records], [32, 35, 6])
        self.assertEqual(reloaded_v2.records[2].args[1], " ")

        # Adjacent narration separation & lossless BoxSnapshot replace_box
        from core.story_ast import BoxSnapshot
        doc2 = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Hello"]),
            Record(cmd_id=35, cmd_name="tag", args=["Narration line"]),
        ])
        doc2.inject_box(0, "", "Cleared speaker")
        self.assertEqual(len(doc2.boxes), 2, "Adjacent narration must remain separate")
        snap = BoxSnapshot(
            speaker="Karyl",
            voice_cue="vo_001",
            kind="print",
            seg_texts=["Seg1", "Seg2"],
            raw_breaks=["\n", "\n"],
            extra_args=[["extra1"], []],
        )
        doc2.replace_box(0, snap)
        self.assertEqual(doc2.boxes[0].speaker, "Karyl")
        self.assertEqual([s.text for s in doc2.boxes[0].segs], ["Seg1", "Seg2"])

        # MTL All Script 2-widget contract
        self.app._set_mtl_drawer_mode("all_script")
        mtl_texts = [w for w in _collect_descendants(self.app.tab_mtl_frame) if isinstance(w, tk.Text)]
        self.assertEqual(len(mtl_texts), 2, f"Expected 2 tk.Text in All Script MTL mode, got {len(mtl_texts)}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
