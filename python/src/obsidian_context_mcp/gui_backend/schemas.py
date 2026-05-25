"""Pydantic schemas for GUI backend RPC."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from obsidian_context_mcp.shared.types import SearchMode


class RpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: dict = Field(default_factory=dict)


class RpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    result: dict | None = None
    error: dict | None = None


class RpcEvent(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: dict = Field(default_factory=dict)


class _CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class VaultValidateParams(_CamelModel):
    vault_path: str = Field(alias="vaultPath")


class VaultSaveParams(_CamelModel):
    project_root: str = Field(alias="projectRoot")
    vault_path: str = Field(alias="vaultPath")
    write_access: bool = False
    backup_before_edit: bool = True
    include: list[str] | None = None
    exclude: list[str] | None = None


class SearchParams(BaseModel):
    project_root: str | None = None
    query: str
    mode: SearchMode = SearchMode.HYBRID
    top_k: int = 10


class ReadNoteParams(BaseModel):
    project_root: str | None = None
    relative_path: str


class ListNotesParams(BaseModel):
    project_root: str | None = None
    query: str | None = None
    tag: str | None = None
    limit: int = 50


class IndexStartParams(BaseModel):
    project_root: str | None = None
    mode: str = "incremental"


class SettingsUpdateParams(BaseModel):
    project_root: str | None = None
    write_access: bool | None = None
    backup_before_edit: bool | None = None
    watcher_enabled: bool | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None
    include: list[str] | None = None
    exclude: list[str] | None = None
