"""MCP prompts."""

USE_PROJECT_DOCS = """Before implementing code, call docs_get_context_pack with the current task.
Use returned local documentation as project context.
If docs are not configured, call config_open_gui or tell user to configure Obsidian docs folder."""

UPDATE_PROJECT_DOCS = """After code changes, identify relevant documentation notes,
read them with docs_read_note, and update them safely using docs_patch_note with expectedSha256."""

SUMMARIZE_PROJECT_DOCS = """Use docs_search and docs_get_context_pack to summarize selected documentation area.
Always include source relative paths."""
