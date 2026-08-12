import os
import json
from pathlib import Path
from datetime import datetime

AGENT_VERSION = "v1"

# --- Directories ---
CONFIG_DIR   = Path(__file__).resolve().parent / "test_cases"
REPO_ROOT    = Path(__file__).resolve().parent.parent
LOGS_DIR     = REPO_ROOT / "data/logs"
WORKSPACES_DIR = REPO_ROOT / "workspaces"
MODELS_YAML  = CONFIG_DIR / "models.yaml"
PROMPTS_YAML = CONFIG_DIR / "prompts.yaml"

# --- Logging utilities ---
def log_event(log_file: str, event_type: str, data: dict | str):
    """Appends a JSON-formatted event to the session-specific log file."""
    entry = {"timestamp": datetime.now().isoformat(), "event": event_type, "data": data}
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def is_run_complete(log_file_path: str) -> bool:
    """Returns True if the log file exists and its last event is 'Run complete'."""
    if not os.path.exists(log_file_path):
        return False
    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            lines = [line for line in f if line.strip()]
        if not lines:
            return False
        return json.loads(lines[-1]).get("event") == "Run complete"
    except (json.JSONDecodeError, OSError):
        return False