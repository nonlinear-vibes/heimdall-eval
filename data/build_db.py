import json
import yaml
import sqlite3
from pathlib import Path
from datetime import datetime

DATA_DIR  = Path(__file__).resolve().parent
REPO_ROOT = DATA_DIR.parent
LOGS_DIR  = DATA_DIR / "logs"
EVALS_DIR = DATA_DIR / "evals"
DB_PATH   = DATA_DIR / "eval.db"

MODELS_YAML   = REPO_ROOT / "agent" / "test_config" / "models.yaml"
PROMPTS_YAML  = REPO_ROOT / "agent" / "test_config" / "prompts.yaml"
CRITERIA_YAML = REPO_ROOT / "heimdall" / "judge_config" / "criteria.yaml"
JUDGES_YAML   = REPO_ROOT / "heimdall" / "judge_config" / "judges.yaml"

SCHEMA = """
CREATE TABLE models (
    model_tag       TEXT PRIMARY KEY,
    model_id        TEXT NOT NULL,
    display_name    TEXT
);

CREATE TABLE prompts (
    prompt_id       TEXT PRIMARY KEY,
    prompt_name     TEXT,
    category        TEXT,
    text            TEXT,
    fixture_dir     TEXT
);

CREATE TABLE criteria (
    criterion_id       TEXT PRIMARY KEY,
    criterion_name     TEXT,
    description        TEXT,
    scale_min          INTEGER,
    scale_max          INTEGER,
    base_criterion_id  TEXT REFERENCES criteria(criterion_id)   -- NULL for non-variant criteria
);

CREATE TABLE judges (
    judge_id        TEXT PRIMARY KEY,
    judge_tag       TEXT NOT NULL,
    display_name    TEXT NOT NULL
);

CREATE TABLE runs (
    run_id              TEXT PRIMARY KEY,
    model_tag           TEXT NOT NULL REFERENCES models(model_tag),
    agent_version       TEXT NOT NULL,
    prompt_id           TEXT NOT NULL REFERENCES prompts(prompt_id),
    exit_reason         TEXT,
    total_iterations    INTEGER,
    tool_called         INTEGER,
    error_message       TEXT,
    log_path            TEXT NOT NULL,
    started_at          TEXT,
    ended_at            TEXT,
    UNIQUE (model_tag, agent_version, prompt_id)
);

CREATE TABLE evaluations (
    run_id              TEXT NOT NULL REFERENCES runs(run_id),
    criterion_id        TEXT NOT NULL REFERENCES criteria(criterion_id),
    judge_id            TEXT NOT NULL REFERENCES judges(judge_id),
    agent_version       TEXT NOT NULL,
    score               INTEGER,
    rationale           TEXT,
    duration_ms         REAL,
    prompt_tokens       INTEGER,
    completion_tokens   INTEGER,
    total_tokens        INTEGER,
    langsmith_run_id    TEXT,
    error_message       TEXT,
    eval_path           TEXT NOT NULL,
    evaluated_at        TEXT,
    PRIMARY KEY (run_id, criterion_id, judge_id)
);

CREATE TABLE human_evals (
    run_id              TEXT NOT NULL REFERENCES runs(run_id),
    criterion_id        TEXT NOT NULL REFERENCES criteria(criterion_id),
    evaluator_id        TEXT NOT NULL DEFAULT 'human_001',
    score               INTEGER,
    rationale           TEXT,
    evaluated_at        TEXT,
    PRIMARY KEY (run_id, criterion_id, evaluator_id)
);

CREATE INDEX idx_evaluations_criterion ON evaluations(criterion_id);
CREATE INDEX idx_evaluations_judge ON evaluations(judge_id);
CREATE INDEX idx_runs_model ON runs(model_tag);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON") # enforce foreign key references
    conn.row_factory = sqlite3.Row # dict-style column access
    return conn

def parse_scale(scale: str) -> tuple[int, int]:
    lo, hi = scale.split("-")
    return int(lo), int(hi)

def now_isoformat() -> str:
    return datetime.now().isoformat()


# ---------------- reference tables ----------------

def load_reference_tables(conn: sqlite3.Connection):
    with open(MODELS_YAML) as f:
        for m in yaml.safe_load(f)["models"]:
            conn.execute(
                "INSERT OR REPLACE INTO models (model_tag, model_id, display_name) VALUES (?, ?, ?)",
                (m["model_tag"], m["model_id"], m.get("display_name")),
            )

    with open(PROMPTS_YAML) as f:
        for p in yaml.safe_load(f)["prompts"]:
            conn.execute(
                "INSERT OR REPLACE INTO prompts (prompt_id, prompt_name, category, text, fixture_dir) "
                "VALUES (?, ?, ?, ?, ?)",
                (p["prompt_id"], p.get("prompt_name"), p.get("category"), p.get("text"), p.get("fixture_dir")),
            )

    with open(CRITERIA_YAML) as f:
        for c in yaml.safe_load(f)["criteria"]:
            scale_min, scale_max = parse_scale(c["scale"])
            conn.execute(
                "INSERT OR REPLACE INTO criteria (criterion_id, criterion_name, description, scale_min, scale_max) "
                "VALUES (?, ?, ?, ?, ?)",
                (c["criterion_id"], c.get("criterion_name"), c.get("description"), scale_min, scale_max),
            )

    with open(JUDGES_YAML) as f:
        for j in yaml.safe_load(f)["judges"]:
            conn.execute(
                "INSERT OR REPLACE INTO judges (judge_id, judge_tag, display_name) VALUES (?, ?, ?)",
                (j["judge_id"], j["judge_tag"], j["display_name"]),
            )


# ---------------- trajectory ingestion ----------------

def load_trajectory(log_path: Path) -> list[dict]:
    events = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def ingest_run(conn: sqlite3.Connection, model_tag: str, agent_version: str, prompt_id: str, log_path: Path):
    try:
        events = load_trajectory(log_path)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  Skipping {log_path}: {e}")
        return

    run_id, started_at, ended_at = None, None, None
    exit_reason, total_iterations, tool_called, error_message = None, None, None, None

    for event in events:
        etype, data = event.get("event"), event.get("data")
        if etype == "Start":
            run_id = data.get("run_id")
            started_at = event.get("timestamp")
        elif etype == "Run complete":
            exit_reason = data.get("exit_reason")
            total_iterations = data.get("total_iterations")
            tool_called = int(bool(data.get("tool_called")))
            ended_at = event.get("timestamp")
        elif etype == "Error":
            error_message = data.get("message")

    if run_id is None:
        print(f"  Skipping {log_path}: no run_id found (incomplete/corrupted trajectory)")
        return

    conn.execute(
        "INSERT OR REPLACE INTO runs "
        "(run_id, model_tag, agent_version, prompt_id, exit_reason, total_iterations, tool_called, "
        " error_message, log_path, started_at, ended_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (run_id, model_tag, agent_version, prompt_id, exit_reason, total_iterations, tool_called,
         error_message, str(log_path), started_at, ended_at),
    )


def ingest_all_runs(conn: sqlite3.Connection):
    if not LOGS_DIR.exists():
        print(f"No logs directory found at {LOGS_DIR}, skipping run ingestion.")
        return
    for model_dir in LOGS_DIR.iterdir():
        if not model_dir.is_dir():
            continue
        for agent_version_dir in model_dir.iterdir():
            if not agent_version_dir.is_dir():
                continue
            for log_path in agent_version_dir.glob("*.jsonl"):
                prompt_id = log_path.stem
                print(f"Ingesting run: {model_dir.name}/{agent_version_dir.name}/{prompt_id}")
                ingest_run(conn, model_dir.name, agent_version_dir.name, prompt_id, log_path)


# ---------------- evaluation ingestion ----------------

def ingest_all_evaluations(conn: sqlite3.Connection):
    if not EVALS_DIR.exists():
        print(f"No evals directory found at {EVALS_DIR}, skipping evaluation ingestion.")
        return

    known_run_ids = {row["run_id"] for row in conn.execute("SELECT run_id FROM runs")}
    known_criterion_ids = {row["criterion_id"] for row in conn.execute("SELECT criterion_id FROM criteria")}
    known_judge_ids = {row["judge_id"] for row in conn.execute("SELECT judge_id FROM judges")}

    ingested, skipped = 0, 0

    for eval_path in EVALS_DIR.rglob("*.json"):
        try:
            with open(eval_path, "r", encoding="utf-8") as f:
                d = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  Skipping {eval_path}: {e}")
            skipped += 1
            continue

        if not all(k in d for k in ("run_id", "criterion_id", "judge_id", "agent_version")):
            print(f"  Skipping {eval_path}: missing required keys")
            skipped += 1
            continue

        if d["run_id"] not in known_run_ids:
            print(f"  Skipping {eval_path}: run_id '{d['run_id']}' not found in runs")
            skipped += 1
            continue

        if d["criterion_id"] not in known_criterion_ids:
            print(f"  Skipping {eval_path}: criterion_id '{d['criterion_id']}' not found in criteria")
            skipped += 1
            continue

        if d["judge_id"] not in known_judge_ids:
            print(f"  Skipping {eval_path}: judge_id '{d['judge_id']}' not found in judges")
            skipped += 1
            continue

        usage = d.get("token_usage") or {}
        conn.execute(
            "INSERT OR REPLACE INTO evaluations "
            "(run_id, criterion_id, judge_id, agent_version, score, rationale, duration_ms, "
            " prompt_tokens, completion_tokens, total_tokens, langsmith_run_id, "
            " error_message, eval_path, evaluated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (d["run_id"], d["criterion_id"], d["judge_id"], d["agent_version"], d.get("score"), d.get("rationale"),
             d.get("duration_ms"), usage.get("prompt_tokens"), usage.get("completion_tokens"),
             usage.get("total_tokens"), d.get("langsmith_run_id"), d.get("error"),
             str(eval_path), d.get("evaluated_at")),
        )
        ingested += 1

    print(f"Ingested {ingested} evaluations, skipped {skipped}.")


def ingest_human_evals(conn: sqlite3.Connection):
    human_evals_dir = EVALS_DIR / "human-evals"
    if not human_evals_dir.exists():
        print(f"No human_evals directory found at {human_evals_dir}, skipping.")
        return

    # pre-load valid IDs once, so we can check membership without a query per row
    known_run_ids = {row["run_id"] for row in conn.execute("SELECT run_id FROM runs")}
    known_criterion_ids = {row["criterion_id"] for row in conn.execute("SELECT criterion_id FROM criteria")}

    for yaml_path in human_evals_dir.glob("*.yaml"):
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
        except (yaml.YAMLError, OSError) as e:
            print(f"  Skipping {yaml_path}: {e}")
            continue

        if not content or "evaluations" not in content:
            print(f"  Skipping {yaml_path}: no 'evaluations' key found")
            continue

        evaluator_id = content.get("evaluator_id", yaml_path.stem)
        entries = content["evaluations"]
        ingested = 0

        for i, entry in enumerate(entries):
            if not all(k in entry for k in ("run_id", "criterion_id")):
                print(f"  Skipping entry {i} in {yaml_path}: missing run_id or criterion_id")
                continue

            if entry["run_id"] not in known_run_ids:
                print(f"  Skipping entry {i} in {yaml_path}: run_id '{entry['run_id']}' not found in runs")
                continue

            if entry["criterion_id"] not in known_criterion_ids:
                print(f"  Skipping entry {i} in {yaml_path}: criterion_id '{entry['criterion_id']}' not found in criteria")
                continue

            conn.execute(
                "INSERT OR REPLACE INTO human_evals "
                "(run_id, criterion_id, evaluator_id, score, rationale, evaluated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    entry["run_id"],
                    entry["criterion_id"],
                    evaluator_id,
                    entry.get("score"),
                    entry.get("rationale"),
                    entry.get("evaluated_at", now_isoformat()),
                ),
            )
            ingested += 1

        print(f"Ingested {ingested}/{len(entries)} human evaluations from {yaml_path.name} (evaluator: {evaluator_id})")


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing database at {DB_PATH}")

    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        load_reference_tables(conn)
        ingest_all_runs(conn)
        ingest_all_evaluations(conn)
        ingest_human_evals(conn)
        conn.commit()
        print(f"\nDone. Database at {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()