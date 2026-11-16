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

DEFAULT_EMBEDDING_PROVIDER = "onnx"
DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

PROJECT_CONFIG_VERSION = 1

BLOCKED_WRITE_PREFIXES = (
    ".obsidian/",
    ".git/",
    "node_modules/",
    ".trash/",
)

# Measured in embedding-model tokens. multilingual-e5-small reads 512 tokens and
# silently drops the rest, so a chunk must fit the window with some margin.
CHUNK_TARGET_TOKENS = 380
CHUNK_OVERLAP_TOKENS = 48
CHUNK_MAX_TOKENS = 480
CHUNK_WINDOW_MARGIN_TOKENS = 16
# Bump when chunk boundaries change so existing indexes are rebuilt.
CHUNKER_VERSION = 2

WATCHER_DEBOUNCE_MS_MIN = 500
WATCHER_DEBOUNCE_MS_MAX = 1500
WATCHER_DEBOUNCE_MS_DEFAULT = 800

INDEX_CONCURRENCY_DEFAULT = 2

ENV_PROJECT_ROOT = "OBSIDIAN_CONTEXT_PROJECT_ROOT"
ENV_DATA_DIR = "OBSIDIAN_CONTEXT_DATA_DIR"
ENV_VAULT_PATH = "OBSIDIAN_CONTEXT_VAULT_PATH"
ENV_VAULT_DATA_DIR = "OBSIDIAN_CONTEXT_VAULT_DATA_DIR"

DEEP_LINK_SCHEME = "obsidian-context-mcp"

VAULT_CONFIG_VERSION = 1
PLUGIN_ID = "obsidian-context-mcp"
SCOPE_TOKEN_PREFIX = "ocm_"

DEFAULT_VAULT_SERVER_HOST = "127.0.0.1"
DEFAULT_VAULT_SERVER_PORT = 18432
