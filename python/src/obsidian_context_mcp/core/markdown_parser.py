"""Markdown parsing for Obsidian notes."""

from __future__ import annotations

import datetime
import hashlib
import re
from pathlib import Path
from typing import Any

import frontmatter
from markdown_it import MarkdownIt

from obsidian_context_mcp.shared.types import HeadingInfo, ParsedNote

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
INLINE_TAG_RE = re.compile(r"(?<![\w/])#([\w\-_/]+)")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _json_safe(value: Any) -> Any:
    """YAML turns `date: 2026-11-16` into date objects; keep frontmatter JSON-serializable."""
    if isinstance(value, (datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return value


def _frontmatter_dict(post: frontmatter.Post) -> dict[str, Any]:
    return _json_safe(dict(post.metadata)) if post.metadata else {}


def detect_eol(text: str) -> str:
    if "\r\n" in text:
        return "\r\n"
    return "\n"


def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_file_text(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "cp1251", "latin-1"):
        try:
            return raw.decode(enc), detect_eol(raw.decode(enc))
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "\n"


def extract_headings(content: str) -> list[HeadingInfo]:
    md = MarkdownIt()
    tokens = md.parse(content)
    headings: list[HeadingInfo] = []
    lines = content.splitlines()
    for token in tokens:
        if token.type == "heading_open":
            int(token.tag[1])
            # Find inline content in next tokens
            pass
    # Line-based heading extraction (more reliable for line numbers)
    for i, line in enumerate(lines, start=1):
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            headings.append(HeadingInfo(level=len(m.group(1)), text=m.group(2).strip(), line=i))
    return headings


def extract_title(content: str, frontmatter_data: dict[str, Any], filename: str) -> str:
    if frontmatter_data.get("title"):
        return str(frontmatter_data["title"])
    for h in extract_headings(content):
        if h.level == 1:
            return h.text
    return Path(filename).stem


def extract_tags(content: str, frontmatter_data: dict[str, Any]) -> list[str]:
    tags: set[str] = set()
    fm_tags = frontmatter_data.get("tags", [])
    if isinstance(fm_tags, str):
        tags.add(fm_tags)
    elif isinstance(fm_tags, list):
        tags.update(str(t) for t in fm_tags)
    for match in INLINE_TAG_RE.finditer(content):
        tags.add(match.group(1))
    return sorted(tags)


def extract_wikilinks(content: str) -> list[str]:
    return sorted(set(m.group(1).strip() for m in WIKILINK_RE.finditer(content)))


def extract_md_links(content: str) -> list[str]:
    links = []
    for m in MD_LINK_RE.finditer(content):
        href = m.group(1).strip()
        if not href.startswith(("http://", "https://", "#", "mailto:")):
            links.append(href)
    return sorted(set(links))


def parse_markdown_file(path: Path, relative_path: str) -> ParsedNote:
    text, eol = read_file_text(path)
    post = frontmatter.loads(text)
    content = post.content
    fm = _frontmatter_dict(post)
    title = extract_title(content, fm, path.name)
    headings = extract_headings(content)
    tags = extract_tags(content, fm)
    wikilinks = extract_wikilinks(content)
    md_links = extract_md_links(content)
    return ParsedNote(
        relative_path=relative_path,
        title=title,
        content=content,
        frontmatter=fm,
        headings=headings,
        tags=tags,
        wikilinks=wikilinks,
        md_links=md_links,
        eol=eol,
        sha256=compute_sha256(text),
    )


def parse_markdown_text(relative_path: str, text: str) -> ParsedNote:
    post = frontmatter.loads(text)
    content = post.content
    fm = _frontmatter_dict(post)
    title = extract_title(content, fm, Path(relative_path).name)
    return ParsedNote(
        relative_path=relative_path,
        title=title,
        content=content,
        frontmatter=fm,
        headings=extract_headings(content),
        tags=extract_tags(content, fm),
        wikilinks=extract_wikilinks(content),
        md_links=extract_md_links(content),
        eol=detect_eol(text),
        sha256=compute_sha256(text),
    )
