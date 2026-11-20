# Cutscene Script Interchange Format (CSIF) Specification (v1.0)

CSIF is the plain-text interchange and clipboard format for Princess Connect! Re:Dive cutscenes in Misora Editor, governed by `AGENTS.md` Rules 20 and 26.

---

## 1. Syntax & Grammar

A CSIF document is encoded in UTF-8 (LF delimiters). It consists of optional Box 0 metadata blocks followed by sequential dialogue/narration blocks.

### Headers
Every block begins with a header occupying an entire line:

| Header | Meaning | Notes |
|---|---|---|
| `@@Speaker` | Spoken dialogue | Speaker character name. Whitespace sanitized (Cf/Cc stripped, NBSP mapped). |
| `@@_` | Narration | Explicit narration block (empty speaker, emitted as `tag` record). Bare `@@` also accepted on input. |
| `@@{playername}` | Spoken by Player | Literal player token, normalized to `{0}` in underlying game binary. |
| `@@#N\|Speaker` | Sparse addressing | 1-based box index `N`. Used **only** for non-contiguous export and targeted script application. |
| `@@!title` | Chapter Title | Box 0 metadata. Valid only before the first dialogue block. |
| `@@!subtitle` | Chapter Subtitle | Box 0 metadata. Valid only before the first dialogue block. |
| `@@!summary` | Chapter Synopsis | Box 0 metadata. Valid only before the first dialogue block. |

### Bodies & Escaping
- The body of each block consists of all lines following the header until the next header or EOF.
- **Escaping**: If any line in the dialogue text begins with `@@`, it must be escaped with a preceding backslash: `\@@`.
- **Delimiter**: Exactly one LF (`\n`) before the next header acts as the block delimiter. All other newlines (including blank lines inside the body) are preserved as literal dialogue content.
- **Code Fences**: Outer Markdown code fences (e.g. ```` ```csif ````) are stripped upon import with a warning. Inner code fences inside dialogue text are never altered.

---

## 2. Example Documents

### Standard Sequential Dialogue
```csif
@@!title
Main Story Chapter 1
@@!summary
Yuuki wakes up in Landsol with amnesia and meets Kokkoro.
@@Kokkoro
Good morning, my Lord.
Are you feeling well?
@@_
She gazes with gentle, devoted eyes.
@@Pecorine
Yummy! This onigiri is delicious!
\@@tags can be escaped if they start with two at signs.
```

### Sparse Non-Contiguous Export
When non-contiguous boxes (e.g. boxes #2 and #5) are copied in Select Box mode:
```csif
@@#2|Kokkoro
Are you feeling well?
@@#5|Pecorine
Yummy! This onigiri is delicious!
```

---

## 3. Application Modes

- **Insert Mode (`mode="insert"`)**:
  Inserts new dialogue boxes into the document after the active box. Narration blocks are converted to `tag` records; spoken blocks are converted to `print` records.
- **Replace Mode (`mode="replace"`)**:
  Overwrites existing dialogue boxes sequentially from the active box forward. If the clipboard has more blocks than available boxes and `overflow="create"`, new boxes are appended.
- **Sparse Addressing**:
  When sparse headers `@@#N|Speaker` are detected, the blocks are applied directly to the specified 1-based box indices `N`. Mixed sparse/non-sparse headers, duplicate indices, or out-of-range indices are strictly rejected. Positional fallback is never performed.

---

## 4. Legacy Input Compatibility

`core.script_codec.parse()` also automatically adapts:
1. Legacy `=== [BOX:n|Speaker:x] ===` delimiters.
2. Triple-enter blocks (`\n\n\n`).
3. Paragraph blocks (`\n\n`).
4. Plain line lists.
All exports from Misora Editor strictly emit CSIF.
