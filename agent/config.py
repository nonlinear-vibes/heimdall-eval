from pathlib import Path

# --- Constants & Settings ---
MAX_CHARS = 10000
MAX_ITERS = 10
REASONING_EFFORT = "low"

# --- Directories ---
BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR.parent / "data/logs"