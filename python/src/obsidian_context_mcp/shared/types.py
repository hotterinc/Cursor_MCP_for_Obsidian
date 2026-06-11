from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class IndexStatus(str, Enum):
    NOT_CONFIGURED = "not_configured"
    READY = "ready"
    INDEXING = "indexing"
    STALE = "stale"
    ERROR = "error"


class IndexMode(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


class SearchMode(str, Enum):
    HYBRID = "hybrid"
    SEMANTIC = "semantic"
    LEXICAL = "lexical"


class PatchMode(str, Enum):
    REPLACE_EXACT = "replace_exact"
    UNIFIED_DIFF = "unified_diff"
    APPEND_SECTION = "append_section"
    UPSERT_SECTION = "upsert_section"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DiagnosticStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


class VaultConfig(BaseModel):
    version: int = 1
    vault_id: str
    vault_path: str
    vault_real_path: str
    include: list[str] = Field(default_factory=lambda: ["**/*.md"])
    exclude: list[str] = Field(
        default_factory=lambda: [
            ".obsidian/**",
            ".git/**",
            "node_modules/**",
            ".trash/**",
            "templates/**",
        ]
    )
    embedding_provider: str = "sentence-transformers"
    embedding_model: str = "intfloat/multilingual-e5-small"
    watcher_enabled: bool = True
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class AccessScope(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    include: list[str] = Field(default_factory=lambda: ["**/*.md"])
    exclude: list[str] = Field(default_factory=list)
    write_access: bool = Field(default=False, alias="writeAccess")
    write_include: list[str] = Field(default_factory=list, alias="writeInclude")
    can_reindex: bool = Field(default=False, alias="canReindex")
    token: str = ""


class ScopesFile(BaseModel):
    scopes: list[AccessScope] = Field(default_factory=list)


class VaultRuntimeInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    port: int
    pid: int
    host: str = "127.0.0.1"
    status: str = "running"
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z", alias="startedAt")
    vault_id: str = Field(default="", alias="vaultId")


class ProjectConfig(BaseModel):
    version: int = 1
    project_root: str
    project_real_path: str
    project_name: str
    vault_path: str | None = None
    vault_real_path: str | None = None
    docs_subfolder: str | None = None
    include: list[str] = Field(default_factory=lambda: ["**/*.md"])
    exclude: list[str] = Field(
        default_factory=lambda: [
            ".obsidian/**",
            ".git/**",
            "node_modules/**",
            ".trash/**",
            "templates/**",
        ]
    )
    write_access: bool = False
    backup_before_edit: bool = True
    embedding_provider: str = "sentence-transformers"
    embedding_model: str = "intfloat/multilingual-e5-small"
    watcher_enabled: bool = True
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    @property
    def configured(self) -> bool:
        return bool(self.vault_path and self.vault_real_path)


class ResolvedPath(BaseModel):
    relative_path: str
    absolute_path: str
    real_path: str


class HeadingInfo(BaseModel):
    level: int
    text: str
    line: int


class ParsedNote(BaseModel):
    relative_path: str
    title: str
    content: str
    frontmatter: dict[str, Any] = Field(default_factory=dict)
    headings: list[HeadingInfo] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    wikilinks: list[str] = Field(default_factory=list)
    md_links: list[str] = Field(default_factory=list)
    eol: str = "\n"
    sha256: str = ""


class ChunkRecord(BaseModel):
    id: str
    file_id: str
    chunk_index: int
    chunk_hash: str
    heading_path: list[str] = Field(default_factory=list)
    heading_level: int = 0
    text: str
    token_count: int
    start_line: int
    end_line: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    chunk_id: str
    relative_path: str
    title: str
    heading_path: list[str] = Field(default_factory=list)
    start_line: int
    end_line: int
    score: float
    text: str
    tags: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)


class ContextSource(BaseModel):
    relative_path: str
    title: str
    heading_path: list[str] = Field(default_factory=list)
    start_line: int
    end_line: int
    score: float


class ContextPack(BaseModel):
    project_id: str  # vault_id or legacy project_id
    task: str
    index_freshness: IndexStatus
    context: str
    sources: list[ContextSource] = Field(default_factory=list)


class IndexProgress(BaseModel):
    job_id: str
    status: JobStatus
    total_files: int = 0
    files_scanned: int = 0
    files_indexed: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    chunks_created: int = 0
    chunks_embedded: int = 0
    current_file: str | None = None
    queue_size: int = 0
    error: str | None = None


class DiagnosticCheck(BaseModel):
    name: str
    status: DiagnosticStatus
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
