# MISORA — PROJECT STATE
*Last updated: 2026-11-19 — Single-Root Tkinter Architecture, Speaker & Continuous Fix, and Smart Cross-Box Paste*

**Repository Location**: `D:\Misora-Editor`  
**Git Remote**: `https://github.com/ImaterialC/Misora-Editor.git` (Branch: `main`)  
**Test Suite**: 35/35 Unit & Integration Tests Passing (0 Failures, 0 Errors, 0 Skipped)

---

## SESSION HANDOFF / MERGED BUG AUDIT

### Merged Known Issues & Architectural Status

| ID | Issue / Feature Area | Category | Status | Technical Root Cause & Implementation Summary |
|---|---|---|---|---|
| **B1** | **Open Folder Flow (`File -> Open Folder...` & DnD)** | Workflow | **RESOLVED** | Unified in `_process_opened_folder()`: handles *Yes (Open All) / No (Scope Only) / Cancel*, auto-opens single files, sets Current File(s) scope, and enforces batch safety. |
| **B2** | **Core Search Engine Failure Across Segments** | Core / Engine | **RESOLVED** | `ProjectSearchEngine` now searches directly across in-memory `open_documents` buffers (`Box.clean_text` and `box.speaker`) with independent speaker checking and span tracking. Also searches cutscene Story Metadata (Title, Subtitle, Summary). |
| **B3** | **Checkbox Visual Contrast (Empty vs Checked Confusion)** | GUI / Theme | **RESOLVED** | Converted all search, scope, continuous view, and XUAT sync checkbuttons to native `ttk.Checkbutton` styled with `Panel.TCheckbutton` and `Accent.TCheckbutton`, rendering crisp Windows checkmarks (✓) inside clear square boxes across all themes. |
| **B4** | **DnD Silent Scope Corruption on Invalid/Empty Drops** | Workflow / Safety | **RESOLVED** | Added 0-byte file detection and unsupported file filtering in `_handle_dropped_paths()`. Dropping empty folders or non-story files triggers a warning notice without altering `selected_search_folder`, `folder_path_var`, or `project_folder`. |
| **B5** | **Speaker Display Name Disappearance (Root Cause)** | GUI / Architecture | **RESOLVED** | Root cause: `MisoraSplashScreen` created a secondary `tk.Tk()` root; `speaker_var` was created without `master=self`, binding to splash. Destroying splash orphaned the variable, leaving `entry_speaker.get() == ''`. Resolved via **Single-Root Toplevel Splash** and explicit `master=self` binding across all Tkinter variables. |
| **B6** | **Continuous View Desync / Inoperability (Root Cause)** | GUI / Architecture | **RESOLVED** | Root cause: `var_continuous_view` was orphaned by the secondary splash root. Resolved by binding `var_continuous_view` to `self` in single-root architecture and syncing view repacking cleanly between Page View and Continuous View. |
| **B7** | **Undo/Redo Insertion Cursor Teleportation** | UX / Editor | **RESOLVED** | In `_apply_delta()`, insertion caret index (`tk.INSERT`) is recorded prior to delta application and restored immediately after updating views, preventing cursor jumps to the end of the text. |
| **B8** | **Startup Freeze Without Splash Animation** | Lifecycle / Perf | **RESOLVED** | Single-root Toplevel splash eliminates dual-root Win32 event queue contention. Session restoration is synchronized with splash progress bar. |
| **B9** | **Intermittent Folder Opening Crash** | Stability / Win32 | **RESOLVED** | Increased deferral delay in `WM_DROPFILES` ctypes callback to 50ms so `DragFinish` and the OS drop loop unwind cleanly before modal dialogs spawn. Wrapped batch loading in robust exception handlers. |
| **B10**| **Story Header / Metadata Box 0 (Title & Summary Editing)** | Feature / AST | **RESOLVED (Option 1)** | Implemented dedicated **Box 0 (Story Metadata Box)** accessible via `< Prev` from Box 1 or at top of Continuous View (`◆ [BOX #000]`). Includes Episode Title, Chapter Subtitle, and a multi-line word-wrapping editor for Summary with live character counting, reversible via `MetadataDelta` undo/redo. |
| **B11**| **View Menu: Line Numbers & Ruler Toggles** | GUI / View | **RESOLVED** | Added `selectcolor=t["misora_pink"]` to View menu checkbuttons to render visible tick marks on Windows native menus, with immediate canvas scroll bounds synchronization. |
| **B12**| **Custom Themes in Side Drawer** | GUI / Theme | **RESOLVED** | Added `"Custom"` preset support to combobox and updated `_apply_theme_preset()` to commit active Entry hex values live when "Custom" is selected, eliminating no-op behavior. |
| **B13**| **Ribbon Button Dimensions & Undo/Redo Buttons** | GUI / Layout | **RESOLVED** | Compact ribbon buttons implemented (~45px primary, ~21px mini, green `↶` and `↷` buttons). Ribbon width reduced to <= 425px. |
| **B14**| **Pink Highlight Artifact on Multi-Segment Boxes** | AST / Editor | **RESOLVED** | `inject_box()` fill argument changed from `" "` to `""`; intrusive pink `#ffd6d6` rectangle removed. |
| **B15**| **Crisp 1px Editor Border** | GUI / Styling | **RESOLVED** | Text editors configured with `highlightthickness=0, bd=1, relief="solid"` eliminating thick 2px focus border. |
| **B16**| **Plain `.txt` Save Verification & Automated Backups** | File I/O | **RESOLVED (Phase 2)** | Supported plain text file editing and dirty tracking across both Page View and Continuous View, saving with timestamped `.bak` backups. |
| **B17**| **Smart Cross-Box Script Paste (`Ctrl+Shift+V`)** | Workflow / Editor | **RESOLVED** | Implemented `on_paste_cross_box()`: parses delimited scripts (`=== [BOX:x|Speaker:y] ===`) or smart plain text (splits by paragraphs or lines), preserving existing actor/speaker names in game binary, with preview confirmation and batch undo/redo. |

---

## DECISIONS LOG

| Decision | Detail |
|----------|--------|
| **Single-Root Tkinter Architecture** | Only ONE `tk.Tk()` root instance exists (`MisoraApp`). The splash screen runs as a borderless `tk.Toplevel(parent=self)`. All Tkinter variables explicitly pass `master=self`, preventing variable orphaning and event loop lockup. |
| **Smart Cross-Box Script Paste (`Ctrl+Shift+V`)** | Allows translators to paste full scripts across consecutive boxes. Plain text mode automatically preserves character/speaker names. Delimited mode updates both speaker and text. Entire multi-box paste is reversible with a single `Ctrl+Z`. |
| **Standalone Repository at `D:\Misora-Editor`** | All active development, tests, and version control are centered in `D:\Misora-Editor` linked to `https://github.com/ImaterialC/Misora-Editor.git`. |
| **Box 0 for Story Metadata (Option 1)** | Cutscene metadata (Title from record 0, Summary from record 1, and Subtitle from record 5/32) is accessed as **Box 0** (`Box: 0 / N`). Summary editing uses a dedicated multi-line editor with word-wrapping matching in-game display width. |
| **Seamless Cursor & View Sync** | Switching between Page View and Continuous View computes character offset and sets the caret at the matching position across both views. |
| **Opened Files Context Menu** | Right-clicking on Opened Files dock tab provides quick access to *Close File*, *Close Others*, *Close All Unmodified*, *Close All*, *Save File*, *Reveal in Explorer*, and *Copy Path/Name*. |
| **Strict DnD Scope Protection** | Dragging non-story files or empty folders will never alter `selected_search_folder`, `folder_path_var`, or `project_folder`. User is informed via toast/status without changing scope. |
| **Caret Preservation on Undo/Redo** | Tkinter `INSERT` caret position is recorded prior to delta application and restored immediately after widget re-population. |
| **High-Contrast Checkbox Styling** | Checkboxes use native `ttk.Checkbutton` with visible checkmarks (✓). |
| **In-Memory Search Target** | Search on "Current File(s)" queries active `open_documents` memory buffers, `Box.clean_text`, and cutscene metadata. |

---

## PHASED EXECUTION ROADMAP

### Phase 1: Critical Regressions & Stability Fixes (COMPLETED)
- [x] **1.1 Fix Core Search Across All Segments & Active Memory Documents (B2)**
- [x] **1.2 Fix Speaker Display & Continuous View Startup Desync (B5, B6)**
- [x] **1.3 Fix DnD Scope Protection & Re-entrancy Crash Prevention (B4, B9)**
- [x] **1.4 Fix Checkbox Visual States (B3)**
- [x] **1.5 Fix Undo/Redo Caret Jumping (B7)**
- [x] **1.6 Fix Startup Freeze & Splash Progress Loop (B8)**
- [x] **1.7 Fix View Menu Toggles & Custom Theme Side Drawer (B11, B12)**

### Phase 1.5: Story Metadata Box 0 Implementation (COMPLETED)
- [x] **1.5.1 Parse Title, Subtitle, and Summary into StoryDocument**
- [x] **1.5.2 Box 0 UI & In-Game Word-Wrap Display**
- [x] **1.5.3 Lossless Binary Repacking of Metadata & Search Integration**

### Phase 2: Workflow & Editor Usability (COMPLETED)
- [x] **2.1 Right-Click Context Menu for "Opened Files" Dock**
  - Context menu: *Close File*, *Close Others*, *Close All Unmodified*, *Close All*, *Save (Ctrl+S)*, *Reveal in File Explorer*, *Open With >*, *Copy Full Path*, *Copy File Name*.
- [x] **2.2 Seamless Cursor & Box Sync between Continuous View & Page View**
  - Instant caret and box alignment when switching between single-box Page View and Continuous View stream in both directions.
- [x] **2.3 Plain `.txt` Save Verification & Automated Backups (B16)**
  - Enhanced dirty-state detection, continuous-stream editing, and timestamped `.bak` backup verification when saving `.txt` files.

### Phase 3: Machine Translation (MTL) & AI Prompt Integration (READY FOR EXPLORATION)
- [ ] **3.1 DeepL, Google GTX & Local Sugoi MTL Connectivity & Verification**
- [ ] **3.2 Tag Masking & Entity Shielding (`{playername}`, NGUI tags, Ruby)**
- [ ] **3.3 AI / LLM Prompt Header Exporter & Customizer**
- [ ] **3.4 Dedicated Floating Translation Assistant Workspace**
- [ ] **3.5 Batch Story Translation Sweep with Cancellation**

---

## WORK STYLE & VERIFICATION PROTOCOL
1. Run syntax verification (`py -3.12 -m py_compile misora.py core/*.py`).
2. Run test suites (`py -3.12 -m unittest discover -s tests`).
3. Maintain zero code regressions across all 32 tests.
