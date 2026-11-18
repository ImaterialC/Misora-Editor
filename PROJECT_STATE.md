# MISORA — PROJECT STATE
*Last updated: 2026-11-19 — Unified Bug Mapping & Execution Roadmap (Turn 12)*

---

## SESSION HANDOFF / MERGED BUG AUDIT

### Merged Known Issues & Architectural Status (Turn 12 Unified Review)

| ID | Issue / Feature Area | Category | Status | Technical Root Cause & Implementation Plan |
|---|---|---|---|---|
| **B1** | **Open Folder Flow (`File -> Open Folder...` & DnD)** | Workflow | **RESOLVED** | Unified in `_process_opened_folder()`: handles *Yes (Open All) / No (Scope Only) / Cancel*, auto-opens single files, sets Current File(s) scope, and enforces batch safety. Verified by user. |
| **B2** | **Core Search Engine Failure Across Segments** | Core / Engine | **ACTIVE (CRITICAL)** | `ProjectSearchEngine` in scope "Current File(s)" re-reads raw disk bundles rather than active in-memory document boxes, and whitespace/placeholder normalization failed to match concatenated multi-segment boxes. Fix: Search directly across in-memory `Box.clean_text` and `box.speaker` with span tracking. |
| **B3** | **Checkbox Visual Contrast (Empty vs Checked Confusion)** | GUI / Theme | **ACTIVE** | `selectcolor=t["bg_dark"]` on Tkinter `Checkbutton` renders checked state as a solid dark block without a clear tick mark (✓). Fix: Implement high-contrast checked indicator with clear tick mark styling across all theme palettes. |
| **B4** | **DnD Silent Scope Corruption on Invalid/Empty Drops** | Workflow / Safety | **ACTIVE** | Dropping non-story files or empty folders silently altered `selected_search_folder` and triggered `folder_path_var.trace`, corrupting `project_folder` without user notice. Fix: Strict validation gate; if no `.unity3d`, `.asset`, or `.txt` exist, abort with toast/notice and keep scopes completely untouched. |
| **B5** | **Speaker Display Name Disappearance** | GUI / Binding | **ACTIVE (CRITICAL)** | `self.var_continuous_view.set()` at startup desynced view state without invoking `_on_toggle_continuous_view()`. `_update_views()` rendered into hidden continuous view, leaving Page View `Speaker:` entry blank. Also, empty speaker strings in `inject_box()` wiped underlying record speakers. Fix: Proper toggle synchronization and robust speaker population in all views. |
| **B6** | **Continuous View Desync / Inoperability** | GUI / View | **ACTIVE (CRITICAL)** | Setting `var_continuous_view` programmatically never swapped widget rows (`clean_editor_row` vs `continuous_wrap`). Fix: Explicitly invoke `_on_toggle_continuous_view()` upon restoration and ensure bidirectional view switching preserves layout and text. |
| **B7** | **Undo/Redo Insertion Cursor Teleportation** | UX / Editor | **ACTIVE** | `_apply_delta()` wipes and re-inserts text via `delete("1.0", tk.END)` and `insert("1.0", target_tx)`, resetting Tkinter `INSERT` caret to document end. Fix: Save cursor position (`txt_dialogue.index(tk.INSERT)`) before delta, restore and clamp caret after text insertion. |
| **B8** | **Startup Freeze Without Splash Animation** | Lifecycle / Perf | **ACTIVE** | `MisoraSplashScreen` closed in `main()` *before* `_restore_session()` ran. Inside `after(100)`, loading up to 25 UnityPy bundles synchronously froze the main GUI thread while window was blank/white. Fix: Incorporate session restoration into the splash screen progress loop with real-time file counters, or restore in a non-blocking background queue. |
| **B9** | **Intermittent Folder Opening Crash** | Stability / Win32 | **ACTIVE** | Win32 `WM_DROPFILES` ctypes WndProc subclass encountered message re-entrancy / memory collision when modal dialogs (`askyesnocancel`) pumped Windows events inside the callback. Fix: Defer modal dialogs via `after(50, ...)` so Win32 WndProc returns cleanly (`return 0`) before modal UI spawns; wrap bundle directory scan in safe try/except. |
| **B10**| **Story Header / Metadata Box 0 (Title & Summary Editing)** | Feature / AST | **APPROVED (Option 1)** | Cutscene Title (record 0 `fade`), Summary/Synopsis (record 1 `log`), and Subtitle (record 5/32) were unparsed in `Box` list and uneditable. Per user approval of Option 1: Implement dedicated **Box 0 (Story Metadata Box)** with multi-line word-wrapping for in-game synopsis, and lossless binary repacking. |
| **B11**| **View Menu: Line Numbers & Ruler Toggles** | GUI / View | **ACTIVE** | `selectcolor` on native Windows `tk.Menu` checkbuttons conflicted with checkmark rendering; canvas scroll bounds required immediate refresh. Fix: Clean toggle handlers with canvas scroll synchronization. |
| **B12**| **Custom Themes in Side Drawer** | GUI / Theme | **ACTIVE** | Preset combobox missing `"Custom"` in values; preset `[Apply]` overwrote custom colors. Fix: Seamless two-way binding between color swatches, hex inputs, and theme dictionary. |
| **B13**| **Ribbon Button Dimensions & Undo/Redo Buttons** | GUI / Layout | **RESOLVED** | Compact `tk.Button` widgets implemented per Image 2 spec (~45px primary, ~21px mini, green `↶` and `↷` buttons). Ribbon width reduced from 969px to 421px. Verified. |
| **B14**| **Pink Highlight Artifact on Multi-Segment Boxes** | AST / Editor | **RESOLVED** | `inject_box()` fill argument changed from `" "` to `""`; intrusive pink `#ffd6d6` rectangle removed. Verified by user. |
| **B15**| **Crisp 1px Editor Border** | GUI / Styling | **RESOLVED** | Text widgets set to `highlightthickness=0, bd=1, relief="solid"` eliminating thick 2px focus border. |
| **B16**| **Plain `.txt` Save Verification & Automated Backups** | File I/O | **PENDING (Phase 2)** | Verify and unit test plain `.txt` translation dictionaries with dirty-tracking and timestamped backups. |

---

## DECISIONS LOG

| Decision | Detail |
|----------|--------|
| **Box 0 for Story Metadata (Option 1)** | Cutscene metadata (Title from record 0, Summary from record 1, and Subtitle from record 5/32) is accessed as **Box 0** (`Box: 0 / N` or `Box: 1 / N+1` Metadata Header). Summary editing uses a dedicated multi-line editor with word-wrapping matching in-game display width, rather than cramming into the 1-line speaker entry. |
| **Strict DnD Scope Protection** | Dragging non-story files or empty folders will never alter `selected_search_folder`, `folder_path_var`, or `project_folder`. User is informed via toast/status without changing scope. |
| **Caret Preservation on Undo/Redo** | Tkinter `INSERT` caret position is recorded prior to delta application and restored immediately after widget re-population, preventing jarring cursor jumps to the end of the text. |
| **Non-Blocking Splash Restoration** | Session restoration (loading previous bundle tabs) is synchronized with splash progress bar or handled in a non-blocking queue so the editor never launches in a frozen state. |
| **High-Contrast Checkbox Styling** | Checkboxes use distinct, high-contrast states with visible checkmarks (✓) rather than solid dark filled rectangles. |
| **In-Memory Search Target** | Search on "Current File(s)" queries active `open_documents` memory buffers and `Box.clean_text` so unsaved edits and multi-segment boxes are instantly searchable. |

---

## PHASED EXECUTION ROADMAP

### Phase 1: Critical Regressions & Stability Fixes (IMMEDIATE EXECUTION)
- [ ] **1.1 Fix Core Search Across All Segments & Active Memory Documents (B2)**
  - Update `ProjectSearchEngine` and `on_start_search()` to search directly over `self.open_documents` in-memory `StoryDocument` instances and `clean_text`.
  - Fix multi-segment boundary matching so concatenated dialogue lines match seamlessly.
- [ ] **1.2 Fix Speaker Display & Continuous View Startup Desync (B5, B6)**
  - Explicitly trigger `_on_toggle_continuous_view()` upon restoring config, ensuring widgets are properly packed.
  - Fix `_update_views()` and `_focus_continuous_box()` so `Speaker:` entry and dialogue text are always accurately populated.
  - Guard `inject_box()` so speaker names are never accidentally overwritten with empty strings.
- [ ] **1.3 Fix DnD Scope Protection & Re-entrancy Crash Prevention (B4, B9)**
  - Add strict validation to `_handle_dropped_paths()`: ignore irrelevant/empty files and leave folder/project scopes intact.
  - Defer modal dialogs out of Win32 WndProc callback via `self.after(50, ...)` to eliminate re-entrancy crashes.
- [ ] **1.4 Fix Checkbox Visual States (B3)**
  - Replace ambiguous solid-fill check indicators with high-contrast, clearly defined checkmark glyphs/styling across themes.
- [ ] **1.5 Fix Undo/Redo Caret Jumping (B7)**
  - Preserve and restore insertion caret (`tk.INSERT`) during undo and redo delta applications.
- [ ] **1.6 Fix Startup Freeze & Splash Progress Loop (B8)**
  - Integrate `_restore_session()` into the splash screen loop or background loader with visual progress feedback.
- [ ] **1.7 Fix View Menu Toggles & Custom Theme Side Drawer (B11, B12)**
  - Ensure Line Numbers & Column Ruler checkboxes toggle cleanly on Windows native menus.
  - Ensure Custom Theme presets, swatches, and hex entries sync bidirectionally without reverting.

### Phase 1.5: Story Metadata Box 0 Implementation (B10)
- [ ] **1.5.1 Parse Title, Subtitle, and Summary into StoryDocument**
  - Extract record 0 (`fade`/title), record 1 (`log`/summary), and record 5/32 (subtitle) into structured metadata fields on `StoryDocument`.
- [ ] **1.5.2 Box 0 UI & In-Game Word-Wrap Display**
  - When `current_box_idx == 0` (or Metadata mode), display Title, Subtitle, and a multi-line word-wrapped editor for Summary.
- [ ] **1.5.3 Lossless Binary Repacking of Metadata**
  - Inject edited Title, Subtitle, and Summary back into records 0, 1, and 5/32 without altering surrounding bytecode.

### Phase 2: Workflow & Editor Usability
- [ ] **2.1 Right-Click Context Menu for "Opened Files" Dock**
  - Context menu: *Close*, *Close Others*, *Close All*, *Save (Ctrl+S)*, *Reveal in Explorer*, *Copy Path*.
- [ ] **2.2 Seamless Cursor & Box Sync between Continuous View & Page View**
- [ ] **2.3 Plain `.txt` Save Verification & Automated Backups (B16)**

### Phase 3: Machine Translation (MTL) & AI Prompt Integration
- [ ] **3.1 DeepL & Sugoi MTL Connectivity & Verification**
- [ ] **3.2 Tag Masking & Entity Shielding (`{playername}`, NGUI tags, Ruby)**
- [ ] **3.3 AI / LLM Prompt Header Exporter & Customizer**
- [ ] **3.4 Dedicated Floating Translation Assistant Workspace**
- [ ] **3.5 Batch Story Translation Sweep with Cancellation**

---

## WORK STYLE & VERIFICATION PROTOCOL
1. Run syntax verification (`py -3.12 -m py_compile misora.py core/*.py`).
2. Run test suites (`py -3.12 -m unittest discover -s tests`).
3. Maintain zero code regressions on verified fixes (B1, B13, B14, B15).
