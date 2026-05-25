"""Heading-aware document chunking."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from obsidian_context_mcp.core.project import compute_chunk_id, compute_file_id
from obsidian_context_mcp.shared.constants import (
    CHUNK_MAX_TOKENS,
    CHUNK_OVERLAP_TOKENS,
    CHUNK_TARGET_TOKENS,
)
from obsidian_context_mcp.shared.types import ChunkRecord, ParsedNote

CODE_FENCE_RE = re.compile(r"^```")


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def normalize_chunk_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def compute_chunk_hash(text: str, metadata: dict) -> str:
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


def _split_large_section(section: Section, target: int = CHUNK_TARGET_TOKENS) -> list[Section]:
    if estimate_tokens(section.text) <= CHUNK_MAX_TOKENS:
        return [section]

    lines = section.text.splitlines()
    chunks: list[Section] = []
    current_lines: list[str] = []
    current_start = section.start_line
    in_fence = False

    for i, line in enumerate(lines):
        if CODE_FENCE_RE.match(line.strip()):
            in_fence = not in_fence
        current_lines.append(line)
        current_text = "\n".join(current_lines)
        if not in_fence and estimate_tokens(current_text) >= target:
            chunks.append(
                Section(
                    heading_path=section.heading_path,
                    heading_level=section.heading_level,
                    start_line=current_start,
                    end_line=current_start + len(current_lines) - 1,
                    text=current_text,
                )
            )
            overlap_lines = max(1, CHUNK_OVERLAP_TOKENS // 16)
            current_lines = current_lines[-overlap_lines:]
            current_start = section.start_line + i - len(current_lines) + 1

    if current_lines:
        chunks.append(
            Section(
                heading_path=section.heading_path,
                heading_level=section.heading_level,
                start_line=current_start,
                end_line=section.end_line,
                text="\n".join(current_lines),
            )
        )
    return chunks if chunks else [section]


def chunk_note(
    note: ParsedNote,
    *,
    project_id: str,
    vault_real_path: str,
) -> list[ChunkRecord]:
    file_id = compute_file_id(project_id, vault_real_path, note.relative_path)
    sections: list[Section] = []
    for section in _split_into_sections(note):
        sections.extend(_split_large_section(section))

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
                token_count=estimate_tokens(section.text),
                start_line=section.start_line,
                end_line=section.end_line,
                metadata=metadata,
            )
        )
    return chunks
