<p align="center">
  <img src="assets/banner.jpg" alt="Misora Banner" width="100%">
</p>

# Misora: Unity3D Revision Tool & Story Editor

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-pink.svg" alt="License: MIT"></a>
  <a href="https://github.com/K0lb3/UnityPy"><img src="https://img.shields.io/badge/UnityPy-1.20+-green.svg" alt="UnityPy"></a>
  <img src="https://img.shields.io/badge/version-1.4.0-brightgreen.svg" alt="Version 1.4.0">
  <img src="https://img.shields.io/badge/tests-234%20passed-success.svg" alt="234 Tests Passed">
</p>

> *"A dedicated, zero-pipeline revision editor, multi-scope search engine, and interchange suite for Princess Connect! Re:Dive Unity3D story assets and XUAT translation dictionaries."*

---

## <img src="assets/icons/caravan_buddy_icon_118201.png" width="28" height="28" valign="middle"> Overview

In *Princess Connect! Re:Dive*, story data is distributed in compiled Unity3D asset bundles (`.unity3d`). When proofreading or correcting translations after assets have already been packed into `BepInEx\Translation\en\RedirectedResources\story\...`, making revisions traditionally required a tedious, multi-step pipeline:

1. Extract the `.unity3d` binary asset.
2. Locate the specific script file and dialogue segment.
3. Edit the text while carefully managing engine command tags.
4. Repack the asset using separate command-line utilities.

<img align="right" width="95" src="assets/misora_chibi.png" alt="Misora Chibi">

**Misora** completely eliminates this pipeline. It loads `.unity3d` bundles directly into memory, exposes dialogue in a clean **Dialogue View** side-by-side with a **Raw Commands** pane, and allows you to patch the bundle in-place in under **100 milliseconds** (`Ctrl+S`).

---

## <img src="assets/icons/caravan_buddy_icon_100101.png" width="28" height="28" valign="middle"> Key Features

### 1. Zero-Pipeline In-Place Repacking & Data Integrity
* **Instant Patching**: Open any `.unity3d` story asset directly. Edit the dialogue text or speaker name and hit **Ctrl+S**; Misora repacks the bundle in-memory with verified atomic same-directory `.tmp` staging, path ID verification, and byte-exact binary serialization (`>H` command IDs, base64 bit-inverted payloads).
* **Bi-directional XUAT Sync**: When saving a bundle correction, Misora automatically locates and updates the matching community translation dictionary (`.txt`) under `Translation\en\Text\`, escaping newlines, preserving BOM/CRLF formatting, and creating automated `.bak` backups.
* **Strict Text Encoding**: Multi-encoding engine with deterministic BOM detection (`UTF-8-SIG`, `UTF-16`) and strict CP932 / Windows-31J Japanese fallback without silent `errors="replace"` corruption.

### 2. Dual-View Story Editor & All Script Flow
* **Dialogue View (Clean Dialogue)**: Displays dialogue exactly as the player sees it in-game, uninterrupted by technical script cues for lip-sync (`lip_sync`), animations (`chara_anim`), camera pans, or voice cues (`voice`).
* **All Script View (`Ctrl+Alt+C`)**: Read and edit entire story chapters seamlessly in a modern scrollable card flow, with synchronized live carets, real-time speaker badges, and Box 0 chapter metadata synopsis editing.
* **Raw Commands View (Technical Records)**: Displays the full sequence of underlying engine command records with line markers and decoded arguments.
* **Placeholder Insertion**: Insert `{playername}` with a single click or shortcut (**Ctrl+P**). Misora automatically maps `{playername}` $\leftrightarrow$ `{0}` between community dictionaries and the game engine.

### 3. Clean Story Interchange Format (CSIF) & Paste Preview
* **Interchange Codec**: Export and import scripts via universal CSIF format (`Ctrl+Shift+E` / `Ctrl+Shift+I`) with explicit narration (`@@_`), speaker markers (`@@Speaker`), metadata blocks (`@@!title`), and sparse 1-based addressing (`@@#N|Speaker`).
* **Script Paste Preview**: Multi-line clipboard paste launches an interactive preview dialog displaying diffs, block counts, and speaker overrides before applying changes.
* **Translation Lock (`Ctrl+L`)**: Mark proofread boxes with a lock badge `🔒` to protect them from batch machine translation, script paste overwrites, and multi-file replace operations.

### 4. Advanced Multi-Scope Search & Replace
* **Multi-Scope**: Search within active file, target folder, or across the whole project (`RedirectedResources` + `Text`).
* **Structured Bundle Replace-All**: Decodes compressed UnityFS/LZ4 story assets on-the-fly, counting and replacing matches directly in dialogue boxes with full atomic backup snapshotting and transactional undo/redo rollback.
* **Japanese Unicode Normalization**: Full NFKC grapheme cluster matching supporting half-width katakana (`ｶﾞ` $\leftrightarrow$ `ガ`), combining dakuten/handakuten (`か\u3099` $\leftrightarrow$ `が`), full-width punctuation, and whitespace insensitivity.
* **Regex & Live Highlight**: Real-time search query highlighting with interactive results tree.

### 5. Machine Translation, Security & Safety
* **DeepL & Local LLM Integration**: Fast single-box and batch translation with rate-limiting delay and non-blocking background workers.
* **DPAPI Credential Security**: API keys stored encrypted using Windows Data Protection API (`dpapi:...`); secrets automatically redacted from logs and diagnostic exports.
* **NGUI Tag Engine & Length Counter**: Single-source NGUI syntax highlighting, vertical hyphen gradient generation (`[c0-c1]`), ruby text (`[rub:...]`), and live rendered character length counter warning against in-game overflow (> 45 chars; native pixel-calibrated overflow ruler planned for v1.4.1 / S17).
* **Workspace & Geometry Safety**: Safe multi-folder drop notifications and virtual screen coordinate clamping to prevent off-screen window restoration.

---

## <img src="assets/icons/caravan_buddy_icon_126401.png" width="28" height="28" valign="middle"> Keyboard Shortcuts

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| **Ctrl + O** | Open File | Open a `.unity3d` bundle or `.txt` story script |
| **Ctrl + Shift + O** | Open Folder | Select a folder scope for multi-file search |
| **Ctrl + S** | Save & Patch | Byte-exact repack into `.unity3d` and sync to XUAT `.txt` |
| **Ctrl + Shift + S** | Save As | Save active story under a new filename |
| **Ctrl + W** | Close File | Close active document with Save/Discard/Cancel prompts |
| **Ctrl + Z** | Undo | Undo last operation with per-file revision tracking |
| **Ctrl + Y** / **Ctrl + Shift + Z** | Redo | Redo last reverted operation |
| **Ctrl + F** | Find | Open Find panel and focus search entry |
| **Ctrl + H** | Replace | Open Find & Replace panel |
| **Ctrl + Shift + F** | Project Search | Switch search scope to whole project |
| **Ctrl + P** | Insert Placeholder | Inserts `{playername}` at current cursor position |
| **Ctrl + L** | Translation Lock | Toggle translation lock on active dialogue box |
| **Ctrl + Shift + I** | Import Script | Import Clean Story Interchange Format (CSIF) script |
| **Ctrl + Shift + E** | Export Script | Export story to CSIF text file |
| **Ctrl + Alt + C** | All Script View | Switch to scrollable All Script flow view |
| **Ctrl + Alt + V** | Page View | Switch to single-box Dialogue view |
| **Alt + Left** | Previous Box | Navigate to previous dialogue box |
| **Alt + Right** | Next Box | Navigate to next dialogue box |
| **Ctrl + G** | Go to Box | Jump to specific dialogue box index |
| **F5** | Reload File | Revert changes and reload active document from disk |
| **Return (in Find)** | Search | Execute search across selected scope |
| **Escape** | Dismiss / Close | Close search panel, dialogs, or dropdowns |

---

## <img src="assets/icons/caravan_buddy_icon_100201.png" width="28" height="28" valign="middle"> Quickstart

### Prerequisites
* **Python 3.11+** installed (Python 3.12 recommended).
* **Dependencies**: Install required packages:
  ```bash
  pip install -r requirements.txt
  ```

### Launching Misora
Double-click `misora.bat` in Windows Explorer, or run:
```bash
py -3.12 misora.py
```

You can also pass a file or folder path directly on the command line, or drag and drop a `.unity3d` file directly onto `misora.bat`:
```bash
misora.bat "C:\Gacha\PriconneRe-TL\src\BepInEx\Translation\en\RedirectedResources\story\data\9080155.unity3d"
```

---

## <img src="assets/icons/caravan_buddy_icon_103601.png" width="28" height="28" valign="middle"> Project Structure

```
Misora-Editor/
├── assets/
│   ├── banner.jpg                      # Readme header banner
│   ├── misora_chibi.png                # Chibi mascot artwork
│   ├── icons/                          # Section header icons & Twemoji assets
│   ├── Splash_1.jpg ... Splash_8.jpg   # Application splash art gallery
│   ├── icon.py                         # Character theme palette, icons & bounded caching
│   └── splash.py                       # Single-process splash boot window with version introspection
├── core/
│   ├── __init__.py                     # Package exports
│   ├── bundle_io.py                    # In-memory UnityPy bundle loader, atomic repacker & cycle cleanup
│   ├── logger.py                       # Category-filtered asynchronous queue logger
│   ├── mtl_engine.py                   # DeepL, Local LLM translation & DPAPI credentials
│   ├── ngui_tags.py                    # Central NGUI rich-text patterns, gradients, TagMasker & length metrics
│   ├── script_codec.py                 # Clean Story Interchange Format (CSIF v1) parser & serializer
│   ├── search_engine.py                # Multi-scope search engine with NFKC Japanese combining character normalization
│   ├── security.py                     # Windows DPAPI encryption & secret redaction
│   ├── story_ast.py                    # AST parser, Box projection model & byte-exact codec
│   ├── text_encoding.py                # Strict multi-encoding detection (UTF-8, UTF-16, CP932)
│   ├── undo_journal.py                 # Multi-level transactional undo/redo journal with per-file revision stacks
│   └── xunity_sync.py                  # Bi-directional sync for XUAT translation dictionaries
├── tests/                              # 23 automated test suites (234 unit tests; storydata_1001005.unity3d fixture & local docs/ excluded via .gitignore)
│   ├── test_misora_core.py             # Core AST, binary, search, and sync tests
│   ├── test_misora_ui_integration.py   # UI integration, Box 0, DnD, and editing tests
│   ├── test_phase1_manual_verification.py # Page and Continuous view verified workflows
│   ├── test_phase2_required.py         # GUI-level required tests
│   ├── test_phase3_performance_config.py # Startup, lazy-load, async logger, config tests
│   ├── test_phase4_import_export_preview.py # Import/export, paste preview, tooltip, version tests
│   ├── test_phase5_mtl_security_preview.py # NGUI tag, DPAPI, TLS verify, DeepL usage, lock tests
│   ├── test_script_codec.py            # CSIF codec unit tests
│   ├── test_s1_open_file_safety.py     # Staged open-file & multi-format tests
│   ├── test_s2_dirty_contract.py       # Per-document dirty contract tests
│   ├── test_s3_document_close.py       # Clean close & dirty lifecycle tests
│   ├── test_s4_view_model_sync.py      # Dynamic view & ribbon synchronization tests
│   ├── test_s5_bulk_replace_safety.py  # Atomic bulk replace & transaction rollback tests
│   ├── test_s6_threading_decoupling.py # Background search & worker thread queue tests
│   ├── test_s7_undo_speaker_safety.py  # Speaker commit & undo integrity tests
│   ├── test_s8a_dialog_grab_safety.py  # Modal dialog grab & lifecycle safety tests
│   ├── test_s8b1_notification_manager.py # Status bar & toast notification tests
│   ├── test_s8b2_memory_guards.py      # Asset disposal & memory leak tests
│   ├── test_s8b3_encoding_detection.py # Encoding detection, BOM & CP932 fallback tests
│   ├── test_s8b4_ui_polishing.py       # Dock collapse, DPI & tooltip tests
│   ├── test_s9a_search_unicode.py      # Japanese Unicode & combining character search tests
│   ├── test_s9b_replace_all_bundle_safety.py # Bundle replace-all extraction & undo tests
│   └── test_s9c_workspace_safety.py    # Workspace protection, geometry & undo isolation tests
├── .gitattributes                      # Git line ending and binary attributes
├── .gitignore                          # Git exclude rules
├── CHANGELOG.md                        # Project version changelog & release notes
├── LICENSE                             # MIT License
├── misora.bat                          # Windows launcher with Python auto-detect
├── misora.py                           # Main Tkinter dual-view story editor GUI
├── misora_config.default.json          # Default configuration template
├── PROJECT_STATE.md                    # Comprehensive project state, defect ledger & roadmap
├── README.md                           # Standalone project documentation
├── register_association.bat            # Register .unity3d file association
├── requirements.txt                    # Python dependencies (UnityPy>=1.20.0, Pillow>=10.0.0)
└── unregister_association.bat          # Remove .unity3d file association
```

---

## <img src="assets/icons/caravan_buddy_icon_132501.png" width="28" height="28" valign="middle"> Running Unit Tests

Run the full automated test suite:
```bash
py -3.12 -m unittest discover -s tests -v
```

---

## <img src="assets/icons/caravan_buddy_icon_133101.png" width="28" height="28" valign="middle"> License

This project is licensed under the MIT License. Princess Connect! Re:Dive and its character assets are trademarks and copyright of Cygames, Inc.
