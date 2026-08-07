import os
import yaml
import json
import time
import uuid
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from pydantic import BaseModel, Field



# --- per-criterion structured output schema ---
class JudgeVerdict(BaseModel):
    score: int = Field(description="Score from 1 (worst) to 5 (best) per the rubric", ge=1, le=5)
    rationale: str = Field(description="Brief justification for the score, 1-3 sentences")

""" In case we add different scales later:
from pydantic import create_model

def build_verdict_model(scale_min: int, scale_max: int):
    return create_model(
        "JudgeVerdict",
        score=(int, Field(description=f"Score from {scale_min} to {scale_max} per the rubric", ge=scale_min, le=scale_max)),
        rationale=(str, Field(description="Brief justification for the score, 1-3 sentences")),
    )

# per criterion:
verdict_model = build_verdict_model(*parse_scale(criterion["scale"]))  # e.g. "1-5" → (1, 5)
llm.with_structured_output(verdict_model)
"""

# --- single judge call, LangChain + LangSmith ---
def run_single_evaluation(run_id: str, langsmith_trace_id: str, criterion: dict, judge: dict, trajectory: dict, api_key: str) -> dict:
    with open(criterion["rubric_file"]) as f:
            system_prompt = f.read()

    trace_excerpt = json.dumps(trajectory) 
    user_prompt = f"Agent trajectory:\n{trace_excerpt}\n\nEvaluate per the rubric above."

    llm = ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        model=judge["judge_id"],
        api_key=api_key,
        ).with_structured_output(JudgeVerdict, include_raw=True)

    start = time.perf_counter()
    result = llm.invoke(
        [SystemMessage(system_prompt), HumanMessage(user_prompt)],
        config={
            "run_id": langsmith_trace_id, # what LangSmith indexes by
            "tags": ["evaluation", criterion["criterion_id"], judge["judge_slug"]],
            "metadata": {
                "run_id": run_id,
                "criterion_id": criterion["criterion_id"],
                "judge_id": judge["judge_id"],
            },
            "run_name": f"eval_{run_id}_{criterion['criterion_id']}_{judge['judge_id']}",
        }, # config for the LangSmith filters
    )
    duration_ms = (time.perf_counter() - start) * 1000
    verdict = result["parsed"]
    raw_message = result["raw"]

    return {
        "run_id": run_id,
        "criterion_id": criterion["criterion_id"],
        "judge_id": judge["judge_id"],
        "score": verdict.score,
        "rationale": verdict.rationale,
        "duration_ms": duration_ms,
        "token_usage": extract_usage(raw_message),   # from response_metadata / usage_metadata
        "langsmith_run_id": langsmith_trace_id,
        "evaluated_at": datetime.now().isoformat(),
    }

# --- resumability check, same pattern as the harness ---
def is_evaluated(eval_path: str) -> bool:
    if not os.path.exists(eval_path):
        return False
    if not is_valid_json(eval_path):
        os.remove(eval_path)   # partial write or a failed judge call — clear it so it gets retried cleanly
        return False
    return True


def is_valid_json(path: str) -> bool:
    """Returns True if the file contains a well-formed, complete evaluation result."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    if not isinstance(content, dict):
        return False

    # a successful evaluation must have an actual score — error entries don't, and should be retried
    if content.get("score") is None:
        return False

    return True


def extract_usage(raw_message) -> dict:
    usage = raw_message.usage_metadata
    if not usage:
        return {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}
    return {
        "prompt_tokens": usage.get("input_tokens"),
        "completion_tokens": usage.get("output_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }


def discover_runs(logs_dir: str = "logs") -> list[tuple[str, str, str]]:
    """Walk logs/<model_slug>/<prompt_id>.jsonl, returning (model_slug, prompt_id, log_path)."""
    runs = []
    for model_slug in os.listdir(logs_dir):
        model_dir = os.path.join(logs_dir, model_slug)
        if not os.path.isdir(model_dir):
            continue
        for fname in os.listdir(model_dir):
            if not fname.endswith(".jsonl"):
                continue
            prompt_id = fname[: -len(".jsonl")]
            runs.append((model_slug, prompt_id, os.path.join(model_dir, fname)))
    return runs


def load_trajectory(log_path: str) -> list[dict]:
    events = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def build_judge_trace(trajectory_events: list[dict]) -> dict:
    """Builds the judge-facing view: task + iteration_data only.
    Skips 'start' (run_id, prompt metadata — kept out to avoid judge
    self-preference bias) and iteration_metadata (duration, tokens —
    same reasoning: could let a judge infer model size/cost)."""

    judge_trace = {"task": None, "iterations": []}

    for event in trajectory_events:
        if event["event"] == "Task":
            judge_trace["task"] = event["data"]

        elif event["event"] == "LLM run":
            judge_trace["iterations"] = [it["iteration_data"] for it in event["data"]]

        elif event["event"] == "Run complete":
            judge_trace["exit_reason"] = event["data"]["exit_reason"]
            judge_trace["total_iterations"] = event["data"]["total_iterations"]

    return judge_trace


def extract_field(trajectory_events: list[dict], field: str):
    for event in trajectory_events:
        if field in event:
            return event[field]
        if isinstance(event.get("data"), dict) and field in event["data"]:
            return event["data"][field]
    raise ValueError(f"No '{field}' found in trajectory")


def write_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# --- main sweep ---
def main():
    with open("config/criteria.yaml") as f:
        criteria = yaml.safe_load(f)["criteria"]

    with open("config/judges.yaml") as f:
        judges = yaml.safe_load(f)["judges"]

    load_dotenv()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if api_key is None:
        raise RuntimeError("OpenRouter API key not found.")

    for model_slug, prompt_id, log_path in discover_runs("logs"):
        try:
            trajectory_events = load_trajectory(log_path)
            run_id = extract_field(trajectory_events, "run_id")
            prompt_name = extract_field(trajectory_events, "prompt_name")
        except Exception as e:
            print(f"Skipping {log_path}: failed to load/parse trajectory ({e})")
            continue

        eval_dir = os.path.join("evals", model_slug, prompt_id)
        os.makedirs(eval_dir, exist_ok=True)

        for criterion in criteria:
            for judge in judges:
                eval_path = os.path.join(eval_dir, f"{criterion['criterion_id']}_{judge['judge_slug']}.json")

                if is_evaluated(eval_path):
                    continue

                try:
                    langsmith_trace_id = str(uuid.uuid4()) # for LangSmith
                    judge_trace = build_judge_trace(trajectory_events)
                    result = run_single_evaluation(run_id, langsmith_trace_id, criterion, judge, judge_trace, api_key)
                    write_json(eval_path, result)
                except Exception as e:
                    write_json(eval_path, {
                        "run_id": run_id,
                        "criterion_id": criterion["criterion_id"],
                        "judge_id": judge["judge_id"],
                        "score": None,
                        "rationale": None,
                        "duration_ms": None,
                        "token_usage": None,
                        "langsmith_run_id": langsmith_trace_id,
                        "evaluated_at": datetime.now().isoformat(),
                        "error": str(e),
                    })


if __name__ == "__main__":
    main()