from pathlib import Path

AGENT_VERSION = "v1"

# --- Constants & Settings ---
MAX_CHARS = 10000
MAX_ITERS = 10
REASONING_EFFORT = "low"

# --- Directories ---
CONFIG_DIR   = Path(__file__).resolve().parent / "config"
REPO_ROOT    = Path(__file__).resolve().parent.parent
LOGS_DIR     = REPO_ROOT / "data/logs"
WORKSPACES_DIR = REPO_ROOT / "agent" / "workspaces"
MODELS_YAML  = CONFIG_DIR / "models.yaml"
PROMPTS_YAML = CONFIG_DIR / "prompts.yaml"