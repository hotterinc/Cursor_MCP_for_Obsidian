"""Context pack builder for Cursor agents."""

from __future__ import annotations

from obsidian_context_mcp.core.project import ProjectContext
from obsidian_context_mcp.core.retrieval import Retriever
from obsidian_context_mcp.shared.types import ContextPack, ContextSource, IndexStatus, SearchMode


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def build_context_pack(
    ctx: ProjectContext,
    task: str,
    *,
    token_budget: int = 6000,
    top_k: int = 12,
    include_linked: bool = True,
    include_frontmatter: bool = True,
) -> ContextPack:
    freshness = ctx.get_status()
    if not ctx.configured:
        return ContextPack(
            project_id=ctx.project_id,
            task=task,
            index_freshness=IndexStatus.NOT_CONFIGURED,
            context="Documentation is not configured. Use config_open_gui to set up Obsidian docs folder.",
            sources=[],
        )

    retriever = Retriever(ctx)
    results = retriever.search(task, top_k=top_k, mode=SearchMode.HYBRID)

    lines: list[str] = []
    sources: list[ContextSource] = []
    used_tokens = 0
    seen_files: set[str] = set()

    if freshness != IndexStatus.READY:
        lines.append(f"> Warning: index status is `{freshness.value}` — results may be stale.\n")

    lines.append(
        "Use this as local project documentation context. "
        "When editing documentation, cite relativePath and expectedSha256 from docs_read_note.\n"
    )

    by_file: dict[str, list] = {}
    for r in results:
        by_file.setdefault(r.relative_path, []).append(r)

    for rel_path, chunks in by_file.items():
        if rel_path in seen_files:
            continue
        header = f"## {chunks[0].title}\n**Path:** `{rel_path}`\n"
        section_lines = [header]
        for chunk in chunks:
            hp = " > ".join(chunk.heading_path) if chunk.heading_path else ""
            chunk_header = f"### {hp or 'Section'} (L{chunk.start_line}-{chunk.end_line})\n"
            chunk_text = chunk_header + chunk.text + "\n"
            tokens = estimate_tokens(chunk_text)
            if used_tokens + tokens > token_budget:
                break
            section_lines.append(chunk_text)
            used_tokens += tokens
            sources.append(
                ContextSource(
                    relative_path=rel_path,
                    title=chunk.title,
                    heading_path=chunk.heading_path,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    score=chunk.score,
                )
            )
        lines.extend(section_lines)
        seen_files.add(rel_path)

    return ContextPack(
        project_id=ctx.project_id,
        task=task,
        index_freshness=freshness,
        context="\n".join(lines),
        sources=sources,
    )
