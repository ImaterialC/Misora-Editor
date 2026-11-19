# Misora Editor — Master Project State, Architecture & Roadmap (v1.4.0)

> **Repository:** `ImaterialC/Misora-Editor`  
> **Target Runtime:** Python 3.11+ (Recommended: Python 3.12 on Windows)  
> **Core Dependencies:** `UnityPy>=1.20.0`, `Pillow>=10.0.0`, `tkinter` (stdlib)  
> **Current Baseline:** `v1.1.0`–`v1.3.3` (Discrepancy unified to `v1.4.0` in Phase 1)

---

## 1. Project Overview & Repository Architecture

**Misora** is a dedicated, zero-pipeline revision editor and multi-scope search tool for *Princess Connect! Re:Dive* Unity3D story asset bundles (`.unity3d`) and XUnity Auto Translator (`XUAT`) dictionaries. It loads compiled `.unity3d` bundles into memory, exposes dialogue in dual synchronized views (**Game Display View** and **Raw AST Script View**), and repacks patched bundles in-place with byte-exact binary serialization.

### Directory Layout
```text
Misora-Editor/
├── assets/
│   ├── banner.jpg                  # Readme header banner
│   ├── misora_chibi.png            # Chibi mascot artwork
│   ├── icons/                      # Caravan buddy section header icons
│   ├── Splash_1.jpg .. Splash_9.jpg# Application splash art collection
│   ├── icon.py                     # Character theme palette & WCAG UI styling
│   └── splash.py                   # Splash boot window (to be decoupled out-of-process)
├── core/
│   ├── __init__.py                 # Core package exports
│   ├── bundle_io.py                # In-memory UnityPy bundle loader & repacker
│   ├── logger.py                   # Category-filtered UI logger
│   ├── mtl_engine.py               # Machine translation, TagMasker & AI prompt builder
│   ├── script_exchange.py          # [NEW - Phase 2] Universal {{meta}}/{{speaker}} codec & Import/Export
│   ├── search_engine.py            # Notepad++ multi-scope search with XUAT normalization
│   ├── story_ast.py                # AST parser, Box model & byte-exact codec
│   ├── undo_journal.py             # Multi-level transactional undo/redo journal
│   └── xunity_sync.py              # Bi-directional sync for XUAT translation dictionaries
├── tests/
│   ├── __init__.py
│   ├── test_misora_core.py         # Core engine, AST codec & exchange unit tests
│   └── test_misora_ui_integration.py # UI integration & folder DnD tests
├── __init__.py                     # Single source of truth for __version__ ("1.4.0")
├── misora.bat                      # Windows launcher with Python auto-detect
├── misora.py                       # Main Tkinter dual-view story editor GUI
├── PROJECT_STATE.md                # Single source of truth for state, audit & roadmap
├── README.md                       # Standalone project documentation
├── register_association.bat        # Register .unity3d Windows file association
├── requirements.txt                # Python dependencies
└── unregister_association.bat      # Remove .unity3d Windows file association
```

---

## 2. Architectural Invariants (NON-NEGOTIABLE RULES FOR AI AGENTS)

Any modification to this codebase MUST satisfy these five invariants:

1. **Byte-Exact Unity3D Serialization (`core/story_ast.py`, `core/bundle_io.py`):**
   - Binary command IDs use big-endian `>H` packing, and text payloads use base64-encoded bit-inverted UTF-8 strings.
   - Repacking an unmodified `.unity3d` bundle must remain byte-exact, and patched bundles must pass all round-trip tests in `py -3.12 -m unittest discover -s tests`.
2. **Single Source of Truth for Version (`__init__.py`):**
   - `__version__` in `__init__.py` is the sole authority for version labels across `misora.py` (window title, About dialog, popups), `assets/splash.py`, and logs. Never hardcode version numbers in UI widgets.
3. **Unified Transactional Undo/Redo (`core/undo_journal.py`):**
   - Every user-facing edit—single-box edits, Continuous View card edits, Box 0 metadata (`Title`, `Subtitle`, `Summary`), cross-box pastes, and MTL card replacements—MUST push a reversible delta (`BoxEditDelta`, `MetadataDelta`, or batched transaction) to `MasterUndoJournal`.
4. **NGUI Tag & Placeholder Integrity (`core/mtl_engine.py`, `core/story_ast.py`):**
   - Engine placeholder `{0}` maps to `{playername}` in community/UI views.
   - NGUI formatting tags (`[FF7DA7]`, `[-]`, `[rub:...]`, `\n`) must always be masked via `TagMasker` before machine translation and restored cleanly upon application.
5. **WCAG Contrast Safety (`assets/icon.py`):**
   - Dynamic theme surfaces and custom accent colors must compute foreground text contrast using `best_contrast_fg()`.

---

## 3. Historical Baseline & Technical Audit (v1.1.0 – v1.3.3)

### Completed & Verified Foundations
- **In-Memory Binary Repacker (`core/bundle_io.py`, `core/story_ast.py`):** Direct `.unity3d` loading, AST command record parsing, Box 0 metadata extraction, and `<100ms` in-place binary patching.
- **Dual-View Editor (`misora.py`):** Side-by-side Game Display View (Clean Dialogue) and Raw AST Script View, plus toggleable Continuous Scroll View and inline NGUI Color/Gradient/Ruby helpers.
- **Bi-Directional XUAT Sync (`core/xunity_sync.py`):** Automatic lookup and `.bak`-protected updates to `Translation\en\Text\*.txt` on `Ctrl+S`.
- **Notepad++ Multi-Scope Search (`core/search_engine.py`):** Active file, folder, and project-wide search with regex, case sensitivity, `IgnoreWhitespaceInDialogue`, and `{playername}` ↔ `{0}` equivalence.
- **Splash Art Expansion (`assets/splash.py`):** Splash artwork collection expanded to `Splash_1.jpg` through `Splash_9.jpg` (`commit bdde09d`).

### Root-Cause Audit of Known Bugs & Bottlenecks (Targeted in v1.4.0)
1. **Continuous View Edits Reverting on Mode Switch:**
   - `_on_card_text_edited()` calls `StoryDocument.inject_box(box_idx, None, new_tx)` which mutates `self.records`, but does not atomically update `Box.clean_text`. Toggling Continuous View off calls `_update_views()`, which reads stale `box.clean_text` and wipes out edits.
   - Card #0 (`b_idx == -1`, Box 0 summary) in `_render_continuous_view()` lacks `<KeyRelease>` binding and is skipped (`if b_idx == -1: continue`) inside `_flush_continuous_card_edits()`.
   - Conversely, `on_box_new()`, `on_box_cut()`, `on_box_paste()`, and `_on_card_paste_caret()` mutate `box.clean_text` without calling `inject_box()` back into `records`.
2. **Startup Latency Bottlenecks:**
   - `misora.bat` runs `py -%V -c "import UnityPy"` as a pre-check before launching `misora.py`, loading heavy `UnityPy` C-extensions twice on every launch.
   - `core/bundle_io.py` imports `UnityPy` synchronously at module import time before `MisoraApp` builds its window.
   - `assets/splash.py` blocks the main Tkinter startup thread instead of running as a detached subprocess.
3. **Fragile Cross-Box & AI Delimiters:**
   - Triple-newline (`\n\n\n`) delimiters lack speaker metadata, cannot target Box 0 metadata, and are frequently collapsed to double-newlines by LLMs and web translators.
4. **Modal MTL Workflow Friction:**
   - Current MTL interaction interrupts editing flow and lacks live box-navigation translation, side-by-side multi-engine comparison, and per-engine retry controls on network errors.
5. **Version Drift:**
   - `__init__.py` reports `1.1.0`, `assets/splash.py` reports `v1.3.1`, and `NguiColorPickerPopup` reports `v1.3.3`.

---

## 4. Master Development Roadmap (v1.4.0)

### Phase 1: Critical Bugfixes & UI Polish (`Fast Mode`)
- [ ] **1.1 Fix Continuous View Persistence & Two-Way Model Sync (`core/story_ast.py`, `misora.py`):**
  - Update `StoryDocument.inject_box()` to atomically synchronize both `self.records` and `self.boxes[box_index].clean_text` (and speaker).
  - Bind `<KeyRelease>` to Card #0 (`txt_summary`, `b_idx == -1`) in `_render_continuous_view()` and handle `b_idx == -1` in `_flush_continuous_card_edits()` with `MetadataDelta` undo support.
  - Ensure `on_box_new()`, `on_box_cut()`, `on_box_paste()`, and `_on_card_paste_caret()` propagate edits back to `self.current_doc.records`.
- [ ] **1.2 Top Ribbon Cleanup (`misora.py`):**
  - Remove redundant `[-]` button (`btn_dash`) from the NGUI ribbon (`Color` and `Grad` already auto-wrap with `[-]`).
  - Remove `" {0}"` text suffix from `btn_player` so it renders as an icon-only button matching all other ribbon actions.
- [ ] **1.3 Comprehensive Hover Tooltips (`misora.py`):**
  - Add a `350ms` hover delay to `ToolTip` to prevent flickering across toolbars.
  - Attach descriptive function + keyboard shortcut tooltips via `create_tooltip()` to every button in the NGUI ribbon, speaker bar, box navigation header, left dock, MTL drawer, and bottom status bar.
- [ ] **1.4 Empty State Call-to-Action Overlay (`misora.py`):**
  - When `self.open_documents` is empty, display a centered empty-state overlay in the `Opened Files` dock tab and main editor viewport showing `"Drag & drop .unity3d files or folders here"` alongside `"Open File..."` and `"Open Folder..."` buttons. Auto-hide when a file opens and restore when all files close.
- [ ] **1.5 Version Unification (`__init__.py`, `misora.py`, `assets/splash.py`):**
  - Set `__version__ = "1.4.0"` in `__init__.py` and import it dynamically into all UI titles, dialogs, and the splash screen.

---

### Phase 2: Universal Two-Way Story Serialization & Smart Box 0 Paste (`Planning Mode`)
- [ ] **2.1 Create `core/script_exchange.py` (Universal `{{meta}}` & `{{speaker}}` Format):**
  - Replace `\n\n\n` delimiters with symmetric, AI-safe bracket headers:
    ```text
    {{meta}}
    title: <Episode Title>
    subtitle: <Chapter Subtitle>
    summary:
    <Multi-line summary text>

    {{yui}}
    <Dialogue line 1>
    {{player}}
    <Player choice or dialogue line>
    {{}}
    <Narration line without speaker>
    ```
  - **Normalization Rules:**
    - Serialize empty speaker as `{{}}`.
    - Serialize protagonist speaker as `{{player}}`; parser accepts `{{player}}`, `{{playername}}`, or legacy `{{{0}}}` tolerantly.
    - Retain fallback parser support for legacy `\n\n\n` separated blocks.
- [ ] **2.2 Smart Cross-Box Copy & Paste Routing (`misora.py`):**
  - Update cross-box copy (`Ctrl+Shift+C`, `Ctrl+Alt+C`) to serialize via `serialize_story_universal()`.
  - Update cross-box paste (`Ctrl+Shift+V`, `Ctrl+Alt+V`) with **Smart Paste Routing**:
    - If pasted text contains a `{{meta}}` block, route `title`, `subtitle`, and `summary` directly into **Box 0** regardless of the currently focused box, and flow subsequent `{{speaker}}` blocks starting at **Box #1** (index `0`).
    - If pasted text has no `{{meta}}` block, flow `{{speaker}}` blocks sequentially starting at the currently focused box index, updating both speaker and dialogue text inside a single batched `MasterUndoJournal` transaction.
- [ ] **2.3 Unify AI Prompt Generator & Clipboard Import (`core/mtl_engine.py`, `misora.py`):**
  - Update `on_copy_ai_prompt()` and clipboard translation import to emit and parse the exact same `{{meta}}` + `{{speaker}}` format.
- [ ] **2.4 Add `File -> Import` and `File -> Export` Submenus (`misora.py`, `core/script_exchange.py`):**
  - `File -> Import`:
    - `Import Universal Script (.txt)...`
    - `Import Legacy Triple-Enter Script (.txt)...`
    - `Import XUAT Dictionary (.txt)...`
    - `Import from Xuat2Raw...` (modular folder/file adapter)
  - `File -> Export`:
    - `Export Universal Script (.txt)...`
    - `Export Plain Dialogue Only (.txt)...`
    - `Export XUAT Translation Dictionary (.txt)...` (`Original=Translation`)
    - `Export Raw AST Script (.txt)...`

---

### Phase 3: Instant Startup & Decoupled Out-of-Process Splash (`Planning Mode`)
- [ ] **3.1 Eliminate Double `UnityPy` Import in `misora.bat`:**
  - Replace `py -%V -c "import UnityPy"` probe with lightweight interpreter check `py -%V -c ""`.
- [ ] **3.2 Lazy-Load `UnityPy` in `core/bundle_io.py`:**
  - Move `import UnityPy` and `UnityPy.config.FALLBACK_UNITY_VERSION = "2021.3.20f1"` into a thread-safe lazy loader `_get_unitypy()` invoked on demand or via background daemon prewarm after `MisoraApp` renders.
- [ ] **3.3 Out-of-Process Splash Launcher (`assets/splash.py`, `misora.py`):**
  - Spawn `assets/splash.py` as a detached lightweight subprocess at the very top of `misora.py` before importing `PIL`, `core`, or heavy GUI modules.
  - Have `assets/splash.py` watch a readiness signal / parent window visibility and self-terminate smoothly as soon as `MisoraApp.deiconify()` completes so main window startup is never blocked.

---

### Phase 4: Side-Docked Multi-MTL Live Panel & `Xuat2Raw` Ecosystem Hook (`Planning Mode`)
- [ ] **4.1 Right Side Drawer `MTL Live` Tab (`misora.py`, `core/mtl_engine.py`):**
  - Dock a third tab `"MTL Live"` in the right-hand `side_drawer` alongside `"Customize"` and `"NGUI Glossary"`, toggled by the top `"MTL"` button and `Ctrl+T`.
  - **Drawer Header Controls:**
    - `"Live Translate"` checkbox (`var_mtl_live`, persisted in `misora_config.json`) triggering asynchronous translation across all active engines `450ms` after box selection/navigation, cancelling stale requests on rapid navigation.
    - Source/Target language selectors (`ja -> en`, `ja -> id`, etc.), global `"Refresh All"` (`↻`), and `"Settings..."` button.
  - **Stacked Engine Result Cards:**
    - Render independent cards for all enabled engines (Google Translate, DeepL, Local/Sugoi MTL, LLM/Ollama) plus a `"XUAT Dictionary"` match card when a match exists in `self.xuat_search_roots`.
    - Protect NGUI tags and placeholders via `TagMasker`.
    - Per-card action controls:
      - **`←` (Apply/Replace):** Replaces active box text in the main editor, records `BoxEditDelta` / `MetadataDelta` in `MasterUndoJournal`, and refreshes both Clean and Continuous views.
      - **`↻` (Retry/Refresh):** Re-runs only that specific engine on connection/API error.
      - **`📋` (Copy):** Copies that engine's translated output to clipboard.
- [ ] **4.2 `Xuat2Raw` Integration Hook (`misora.py`, `core/script_exchange.py`):**
  - Add optional `xuat2raw_path` configuration key in `misora_config.json` and `Configure Paths & Backups...` dialog, wired to `File -> Import -> Import from Xuat2Raw...` as a clean adapter hook for upcoming `Xuat2Raw` tool outputs.

---

## 5. Verification & Testing Protocol

Every phase must pass automated and manual checks before moving to the next phase:

```bash
# Run full unit & UI integration test suite
py -3.12 -m unittest discover -s tests
```

### Mandatory Test Coverage Additions (`tests/test_misora_core.py`)
1. `test_continuous_edit_persists_across_view_toggle_and_save` (including Box 0 summary).
2. `test_universal_script_roundtrip_meta_and_speakers` (`{{meta}}`, `{{speaker}}`, `{{}}`, `{{player}}` ↔ `{0}`).
3. `test_smart_paste_routes_meta_to_box0_regardless_of_cursor`.
4. `test_mtl_card_apply_preserves_ngui_tags_and_pushes_undo`.