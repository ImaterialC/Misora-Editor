"""
misora.core - Self-contained engine for Misora: Unity3D Revision Tool & Story Editor.
"""
from .story_ast import StoryDocument, Box, BoxSnapshot, Seg, Record, game_to_xuat, xuat_to_game, norm_search
from .bundle_io import load_bundle_story, save_bundle_story, BundleIOError, dispose_unity_env
from .search_engine import ProjectSearchEngine, SearchOptions, SearchResult
from .xunity_sync import XUnitySyncManager, SyncMatch
from .logger import MisoraLogger, LogEntry, LOG_CATEGORIES, LOG_LEVELS, ALWAYS_ON_CATEGORY
from .undo_journal import MasterUndoJournal, UndoOperation, BoxEditDelta, BoxStructuralDelta, BoxSnapshotReplaceDelta, PlainTextDelta, BulkFileDelta, MetadataDelta, DocumentRecordsDelta
from .mtl_engine import MTLConfig, MTLEngine, TagMasker, translate_async, MTL_ENGINES, DEFAULT_LLM_PROMPT
from .script_codec import serialize, parse, sniff_format, apply_to_document, sanitize_speaker, DialogueBlock, MetadataBlock, ParseResult
from .ngui_tags import (
    NGUI_TAG_RE, NGUI_TOKEN_RE, RUBY_RE, SIZE_RE, STYLE_RE, COLOR_HEX_RE, GRADIENT_RE,
    PLACEHOLDER_RE, normalize_gradient_syntax, strip_tags, get_rendered_length, measure_line_lengths,
)
from .security import protect_secret, unprotect_secret, redact_secret
from .text_encoding import (
    DecodedText, detect_encoding_and_decode, encode_with_metadata,
    read_text_file_strictly, write_atomic_encoded,
)
from .workspace import (
    WORKSPACE_SCHEMA_VERSION, MISORA_WORKSPACE_EXT, WorkspaceError,
    LockedKeyEntry, WorkspaceFileEntry, WorkspaceDiffEntry, WorkspaceSession,
    safe_relpath, resolve_workspace_file_path, match_active_file,
    compute_workspace_diff, save_workspace, load_workspace,
)
from .xuat_index import (
    XuatEntry, XuatLookupResult, XuatIndex,
    unescape_xuat_value, unescape_xuat_key, normalize_xuat_key,
    resolve_xuat_text_roots, build_xuat_index, build_xuat_index_async,
    analyze_story_matches,
)
from .font_manager import (
    FontManager, PRESET_GLOBAL, PRESET_JP, BUILTIN_FONT_PRESETS,
)
from .word_wrap import WrapResult, iter_graphemes, wrap_text

__all__ = [
    "StoryDocument", "Box", "BoxSnapshot", "Seg", "Record", "game_to_xuat", "xuat_to_game", "norm_search",
    "load_bundle_story", "save_bundle_story", "BundleIOError", "dispose_unity_env",
    "ProjectSearchEngine", "SearchOptions", "SearchResult",
    "XUnitySyncManager", "SyncMatch",
    "MisoraLogger", "LogEntry", "LOG_CATEGORIES", "LOG_LEVELS", "ALWAYS_ON_CATEGORY",
    "MasterUndoJournal", "UndoOperation", "BoxEditDelta", "BoxStructuralDelta", "BoxSnapshotReplaceDelta", "PlainTextDelta", "BulkFileDelta", "MetadataDelta", "DocumentRecordsDelta",
    "MTLConfig", "MTLEngine", "TagMasker", "translate_async", "MTL_ENGINES", "DEFAULT_LLM_PROMPT",
    "serialize", "parse", "sniff_format", "apply_to_document", "sanitize_speaker", "DialogueBlock", "MetadataBlock", "ParseResult",
    "NGUI_TAG_RE", "NGUI_TOKEN_RE", "RUBY_RE", "SIZE_RE", "STYLE_RE", "COLOR_HEX_RE", "GRADIENT_RE",
    "PLACEHOLDER_RE", "normalize_gradient_syntax", "strip_tags", "get_rendered_length", "measure_line_lengths",
    "protect_secret", "unprotect_secret", "redact_secret",
    "DecodedText", "detect_encoding_and_decode", "encode_with_metadata",
    "read_text_file_strictly", "write_atomic_encoded",
    "WORKSPACE_SCHEMA_VERSION", "MISORA_WORKSPACE_EXT", "WorkspaceError",
    "LockedKeyEntry", "WorkspaceFileEntry", "WorkspaceDiffEntry", "WorkspaceSession",
    "safe_relpath", "resolve_workspace_file_path", "match_active_file",
    "compute_workspace_diff", "save_workspace", "load_workspace",
    "XuatEntry", "XuatLookupResult", "XuatIndex",
    "unescape_xuat_value", "unescape_xuat_key", "normalize_xuat_key",
    "resolve_xuat_text_roots", "build_xuat_index", "build_xuat_index_async",
    "analyze_story_matches",
    "FontManager", "PRESET_GLOBAL", "PRESET_JP", "BUILTIN_FONT_PRESETS",
    "WrapResult", "iter_graphemes", "wrap_text",
]
