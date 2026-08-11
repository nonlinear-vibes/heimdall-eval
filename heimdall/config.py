# evaluator/config.py
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
LOGS_DIR = DATA_DIR / "logs"
EVALS_DIR = DATA_DIR / "evals" / "AI-evals"
DB_PATH = DATA_DIR / "eval.db"

CONFIG_DIR = Path(__file__).resolve().parent / "config"
CRITERIA_YAML = CONFIG_DIR / "criteria.yaml"
JUDGES_YAML = CONFIG_DIR / "judges.yaml"