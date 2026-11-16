"""Heading-aware document chunking."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from obsidian_context_mcp.core.project import compute_chunk_id, compute_file_id
from obsidian_context_mcp.shared.constants import (
    CHUNK_MAX_TOKENS,
    CHUNK_OVERLAP_TOKENS,
    CHUNK_TARGET_TOKENS,
    CHUNK_WINDOW_MARGIN_TOKENS,
)
from obsidian_context_mcp.shared.types import ChunkRecord, ParsedNote

CODE_FENCE_RE = re.compile(r"^```")


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def normalize_chunk_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def compute_chunk_hash(text: str, metadata: dict[str, Any]) -> str:
    key = normalize_chunk_text(text) + "|" + str(sorted(metadata.items()))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


@dataclass
class Section:
    heading_path: list[str]
    heading_level: int
    start_line: int
    end_line: int
    text: str


def _split_into_sections(note: ParsedNote) -> list[Section]:
    lines = note.content.splitlines()
    if not note.headings:
        return [
            Section(
                heading_path=[note.title],
                heading_level=1,
                start_line=1,
                end_line=max(1, len(lines)),
                text=note.content,
            )
        ]

    sections: list[Section] = []
    sorted_headings = sorted(note.headings, key=lambda h: h.line)
    for i, heading in enumerate(sorted_headings):
        start = heading.line
        end = sorted_headings[i + 1].line - 1 if i + 1 < len(sorted_headings) else len(lines)
        # Build heading path
        path: list[str] = []
        for h in sorted_headings[: i + 1]:
            if h.level <= heading.level:
                # trim path to parent level
                while path and len(path) >= h.level:
                    path.pop()
            if h.line <= heading.line:
                if h.level == heading.level and h.line == heading.line:
                    if len(path) >= heading.level:
                        path = path[: heading.level - 1]
                    path.append(h.text)
        section_text = "\n".join(lines[start - 1 : end])
        sections.append(
            Section(
                heading_path=path or [heading.text],
                heading_level=heading.level,
                start_line=start,
                end_line=end,
                text=section_text,
            )
        )
    return sections


TokenCounter = Callable[[str], int]


@dataclass
class _Unit:
    line: int
    text: str
    tokens: int
    continues_line: bool = False


def _split_long_line(line: str, raw: TokenCounter, max_raw: int) -> list[tuple[str, int]]:
    """Split one line that does not fit the window: by words, then by characters."""
    pieces: list[tuple[str, int]] = []
    words: list[str] = []
    words_tokens = 0

    def flush_words() -> None:
        nonlocal words, words_tokens
        # Summed word counts miss the separators; trim against the joined text.
        while words:
            take: list[str] = words
            rest: list[str] = []
            while len(take) > 1 and raw(" ".join(take)) > max_raw:
                cut = max(1, len(take) // 10)
                take, rest = take[:-cut], take[-cut:] + rest
            text = " ".join(take)
            pieces.append((text, raw(text)))
            words = rest
        words_tokens = 0

    for word in line.split(" "):
        tokens = raw(word)
        if tokens > max_raw:
            flush_words()
            step = max(1, len(word) * max_raw // max(tokens, 1))
            for i in range(0, len(word), step):
                part = word[i : i + step]
                pieces.append((part, raw(part)))
            continue
        if words and words_tokens + tokens > max_raw:
            flush_words()
        words.append(word)
        words_tokens += tokens
    flush_words()
    return pieces


def _split_large_section(
    section: Section,
    count: TokenCounter,
    *,
    target: int = CHUNK_TARGET_TOKENS,
    max_tokens: int = CHUNK_MAX_TOKENS,
    overlap: int = CHUNK_OVERLAP_TOKENS,
) -> list[Section]:
    if count(section.text) <= max_tokens:
        return [section]

    # count() includes the per-text overhead (prefix + special tokens); budget lines without it.
    # The character estimate reports 1 for "", which is a floor, not real overhead.
    empty = count("")
    overhead = empty if empty > 1 else 0

    def raw(text: str) -> int:
        return max(1, count(text) - overhead) if text else 0

    max_raw = max(1, max_tokens - overhead)
    target_raw = max(1, min(target, max_tokens) - overhead)
    overlap_raw = max(0, overlap)

    units: list[_Unit] = []
    for offset, line in enumerate(section.text.splitlines()):
        line_no = section.start_line + offset
        tokens = raw(line)
        if tokens <= max_raw:
            units.append(_Unit(line_no, line, tokens))
            continue
        for i, (piece, piece_tokens) in enumerate(_split_long_line(line, raw, max_raw)):
            units.append(_Unit(line_no, piece, piece_tokens, continues_line=i > 0))

    chunks: list[Section] = []
    current: list[_Unit] = []
    current_tokens = 0
    fresh = 0  # units in `current` that are not overlap carried from the previous chunk
    in_fence = False

    def join(items: list[_Unit]) -> str:
        out = ""
        for i, unit in enumerate(items):
            if i:
                out += " " if unit.continues_line else "\n"
            out += unit.text
        return out

    def flush() -> None:
        nonlocal current, current_tokens, fresh
        # Per-unit counts are an estimate of the joined text; check the real thing and
        # push trailing units into the next chunk if separators tipped it over.
        leftover: list[_Unit] = []
        while len(current) > 1 and count(join(current)) > max_tokens:
            leftover.insert(0, current.pop())
        chunks.append(
            Section(
                heading_path=section.heading_path,
                heading_level=section.heading_level,
                start_line=current[0].line,
                end_line=current[-1].line,
                text=join(current),
            )
        )
        if leftover:
            current, current_tokens, fresh = leftover, sum(u.tokens for u in leftover), len(leftover)
            return
        carried: list[_Unit] = []
        carried_tokens = 0
        for unit in reversed(current[1:]):
            if carried_tokens + unit.tokens > overlap_raw:
                break
            carried.insert(0, unit)
            carried_tokens += unit.tokens
        current, current_tokens, fresh = carried, carried_tokens, 0

    for unit in units:
        while current and current_tokens + unit.tokens > max_raw:
            if fresh:
                flush()
            else:
                # Only overlap from the previous chunk is left; drop it to make room.
                current, current_tokens = [], 0
        if not unit.continues_line and CODE_FENCE_RE.match(unit.text.strip()):
            in_fence = not in_fence
        current.append(unit)
        current_tokens += unit.tokens
        fresh += 1
        if not in_fence and current_tokens >= target_raw:
            flush()

    while fresh:
        flush()
    return chunks if chunks else [section]


def chunk_note(
    note: ParsedNote,
    *,
    project_id: str,
    vault_real_path: str,
    token_counter: TokenCounter | None = None,
    max_input_tokens: int | None = None,
) -> list[ChunkRecord]:
    """Split a note into chunks that fit the embedding model window.

    token_counter should return the tokens a text occupies in the model window
    (prefix and special tokens included); without it a character estimate is used.
    """
    count = token_counter or estimate_tokens
    max_tokens = CHUNK_MAX_TOKENS
    if max_input_tokens:
        max_tokens = min(max_tokens, max_input_tokens - CHUNK_WINDOW_MARGIN_TOKENS)
    file_id = compute_file_id(project_id, vault_real_path, note.relative_path)
    sections: list[Section] = []
    for section in _split_into_sections(note):
        sections.extend(_split_large_section(section, count, max_tokens=max_tokens))

    chunks: list[ChunkRecord] = []
    for idx, section in enumerate(sections):
        if estimate_tokens(section.text) < 1:
            continue
        metadata = {
            "title": note.title,
            "tags": note.tags,
            "links": note.wikilinks,
        }
        chunk_hash = compute_chunk_hash(section.text, metadata)
        chunk_id = compute_chunk_id(file_id, idx, chunk_hash)
        chunks.append(
            ChunkRecord(
                id=chunk_id,
                file_id=file_id,
                chunk_index=idx,
                chunk_hash=chunk_hash,
                heading_path=section.heading_path,
                heading_level=section.heading_level,
                text=section.text,
                token_count=count(section.text),
                start_line=section.start_line,
                end_line=section.end_line,
                metadata=metadata,
            )
        )
    return chunks
