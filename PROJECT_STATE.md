# MISORA — PROJECT STATE
*Last updated: 2026-11-19 — Box Card Stream Architecture, Triple-Enter Script Workflow, & Speaker Overhaul*

**Repository Location**: `D:\Misora-Editor`  
**Git Remote**: `https://github.com/ImaterialC/Misora-Editor.git` (Branch: `main`)  
**Test Suite**: 38/38 Unit & Integration Tests Passing (0 Failures, 0 Errors, 0 Skipped)

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
| **B17**| **Smart Cross-Box Script Paste (`Ctrl+Shift+V`)** | Workflow / Editor | **RESOLVED** | Implemented `on_paste_cross_box()`: parses delimited scripts (`=== [BOX:x|Speaker:y] ===`), triple-enter blocks (`\n\n\n`), or smart plain text, preserving existing actor/speaker names in game binary, with preview confirmation and batch undo/redo. |
| **B18**| **Continuous View Desync & Separator Vulnerability Overhaul** | GUI / Architecture | **RESOLVED** | Complete architectural overhaul from monolithic `tk.Text` to **Box Card Stream** (`tk.Canvas` + `tk.Frame`). Each box is rendered in an isolated card with native Tkinter UI frame separators and card headers. Text separators (`---`) and header string parsing inside dialogue buffers are completely eliminated, preventing any possibility of separator deletion, selection corruption, or header bleed into story text. |
| **B19**| **Triple-Enter (`\n\n\n`) Script Copy & Paste Workflow** | Workflow / Editor | **RESOLVED** | Implemented `on_copy_script_triple_enter()` (`Ctrl+Shift+C`) and enhanced `on_paste_cross_box()` (`Ctrl+Shift+V`): Uses clean triple-enter (`\n\n\n`) as natural delimiter between boxes without tag or header clutter. Automatically distributes text across boxes preserving character names. Retains `[📋 AI Prompt]` for LLM character-voice context. |
| **B20**| **Speaker Dropdown Simplification & Box 0 Invalidation** | GUI / Editor | **RESOLVED** | Removed redundant "Speaker Attributes / Variants" submenu cascade; story actors are listed directly at the top level of the popup menu. On Box 0 (Story Metadata), speaker entry and dropdown button are emptied and disabled (`state="disabled"`), and dropdown clicks do nothing, strictly preventing accidental dialogue or speaker alteration on cutscene metadata. |

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
| **Box Card Stream Architecture** | Continuous View renders boxes as isolated UI cards within a scrollable canvas. Each card has its own native header, speaker badge, and independent `tk.Text` widget. `Ctrl+A` is scoped to the active card, eliminating accidental story-wide deletion. |
| **Triple-Enter Script Delimiter** | Triple line-breaks (`\n\n\n`) represent box boundaries for external text editors and AI translation pipelines, avoiding header formatting conflicts and allowing pure text editing. |
| **Box 0 Speaker Protection** | On Box 0 (Metadata), speaker fields are disabled (`state="disabled"`). Clicking dropdown or assigning speakers is an explicit no-op to protect metadata integrity. |
| **Seamless View & Caret Retention** | Switching between Single Box View and Continuous View preserves the active box index and character cursor offset without loss of uncommitted edits. |
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

### Phase 3: Box Card Stream Overhaul & Triple-Enter Script Workflow (COMPLETED)
- [x] **3.1 Overhaul Continuous View from monolithic text to Box Card Stream (`tk.Canvas` + `tk.Frame`)**
- [x] **3.2 Physical elimination of separator lines and header bleed inside dialogue buffers**
- [x] **3.3 Triple-Enter (`\n\n\n`) Script Copy (`Ctrl+Shift+C`) and Paste (`Ctrl+Shift+V`)**
- [x] **3.4 Card-Scoped `Ctrl+A` selection to prevent accidental story-wide deletion**
- [x] **3.5 Simplified Speaker Dropdown (direct actor list) and Box 0 invalidation/protection**
- [x] **3.6 Seamless View Switch and exact box/caret character offset retention**

### Phase 4: Continuous UX Refinements, Box-Level Tools & Caret Multi-Box Workflow (ACTIVE / PLANNED)
- [ ] **4.1 Fix Line Number Gutter in Continuous View**: Remove obsolete `gutter_cont`; add per-card line numbering without breaking canvas layout.
- [ ] **4.2 Global Mousewheel Canvas Scrolling**: Implement first-class `_on_cont_mousewheel` on `MisoraApp` returning `"break"` across all card widgets.
- [ ] **4.3 Remove Duplicate Scrollbar**: Eliminate unmanaged ghost scrollbar on right side of Game View.
- [ ] **4.4 Box 0 Distinct Background Tint**: Apply soft, slightly darker tint (`#dfd1f5` / `#2d1d29`) to Story Metadata Card.
- [ ] **4.5 Compact Card Spacing & Snug Headers**: Eliminate vertical separator frames, tighten padding (`pady=(1, 2)`), and reduce badge font size.
- [ ] **4.6 PanedWindow Resizing Lag Optimization**: Eliminate drag stutter via `opaqueresize=False` and debounced canvas configure handling.
- [ ] **4.7 Remove Individual Box Copy Button**: Remove redundant `[📋]` button from card headers.
- [ ] **4.8 Edit Menu & Shortcuts for Text and Box Actions**: Add menu commands and global shortcuts; integrate approved icon buttons.
- [ ] **4.9 'Select Box' Multi-Box Mode**: Add checkbox next to Continuous View for multi-box batch Cut, Copy, Paste, and Delete.
- [ ] **4.10 Caret-Aware Multi-Box Delimiter Paste (`\n\n\n+`)**: Split delimiter blocks from exact caret position across consecutive boxes on `Ctrl+V`.
- [ ] **4.11 Mid-Dialogue Font Size Tags & Toolbar**: Support `<size=...>` and `[size=...]` in syntax highlighting, add `[Size]` ribbon button, and render scaled font in Compiled Preview.

### Phase 5: Machine Translation (MTL) & AI Prompt Integration (PLANNED)
- [ ] **5.1 DeepL, Google GTX & Local Sugoi MTL Connectivity & Verification**
- [ ] **5.2 Tag Masking & Entity Shielding (`{playername}`, NGUI tags, Ruby)**
- [ ] **5.3 AI / LLM Prompt Header Exporter & Customizer**
- [ ] **5.4 Dedicated Floating Translation Assistant Workspace**
- [ ] **5.5 Batch Story Translation Sweep with Cancellation**

---

## WORK STYLE & VERIFICATION PROTOCOL
1. Run syntax verification (`py -3.12 -m py_compile misora.py core/*.py`).
2. Run test suites (`py -3.12 -m unittest discover -s tests`).
3. Maintain zero code regressions across all 38 tests.
