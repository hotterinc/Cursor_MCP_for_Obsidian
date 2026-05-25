APP_NAME = "obsidian-context-mcp"
APP_VERSION = "0.1.0"

DEFAULT_INCLUDE = ["**/*.md"]
DEFAULT_EXCLUDE = [
    ".obsidian/**",
    ".git/**",
    "node_modules/**",
    ".trash/**",
    "templates/**",
]

DEFAULT_EMBEDDING_PROVIDER = "sentence-transformers"
DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

PROJECT_CONFIG_VERSION = 1

BLOCKED_WRITE_PREFIXES = (
    ".obsidian/",
    ".git/",
    "node_modules/",
    ".trash/",
)

CHUNK_TARGET_TOKENS = 1000
CHUNK_OVERLAP_TOKENS = 150
CHUNK_MIN_TOKENS = 800
CHUNK_MAX_TOKENS = 1200

WATCHER_DEBOUNCE_MS_MIN = 500
WATCHER_DEBOUNCE_MS_MAX = 1500
WATCHER_DEBOUNCE_MS_DEFAULT = 800

INDEX_CONCURRENCY_DEFAULT = 2

ENV_PROJECT_ROOT = "OBSIDIAN_CONTEXT_PROJECT_ROOT"

DEEP_LINK_SCHEME = "obsidian-context-mcp"
