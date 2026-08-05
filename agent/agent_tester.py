import os
import yaml
import json
import agent
import docker
import shutil

from pathlib import Path
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv
from docker import DockerClient
from system_prompt import SYSTEM_PROMPT


def main():

    BASE_DIR = Path(__file__).resolve().parent
    LOGS_DIR = BASE_DIR.parent / "logs"

    with open("test-data/models.yaml") as f:
        models = yaml.safe_load(f)["models"]

    with open("test-data/prompts.yaml") as f:
        prompts = yaml.safe_load(f)["prompts"]

    load_dotenv()
    api_key = os.environ.get("API_KEY")
    if api_key is None:
        raise RuntimeError("API key not found.")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        )

    docker_client, docker_warning = get_docker_client()
    if docker_warning:
        print(f"⚠️ {docker_warning} Running without sandboxing for run_python_file.")

    for model in models:
        os.makedirs(f"../logs/{model['model_slug']}", exist_ok=True)
        for prompt in prompts:
            log_file_path = f"{LOGS_DIR}/{model['model_slug']}/{prompt['prompt_id']}.jsonl"

            if is_run_complete(log_file_path):
                print(f"Skipping {log_file_path} (already complete).")
                continue

            if os.path.exists(log_file_path):
                os.remove(log_file_path)  # partial/corrupted run from a previous crash — start clean

            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.append({"role": "user", "content": prompt["text"]})
            log_event(log_file_path, "User input", prompt)
            workspace_dir = f"workspaces/{model['model_slug']}/{prompt['prompt_id']}"
            prepare_workspace(workspace_dir, prompt.get("fixture_dir"))

            try:
                agent.generate_response(client, model["model_id"], messages, workspace_dir, docker_client, log_file_path)
            except Exception as e:
                print(f"Error during response generation: {e}")



def get_docker_client() -> tuple[DockerClient | None, str]:
    if shutil.which("docker") is None:
        return None, "Docker is not installed."
    try:
        client = docker.from_env()
        client.ping()
        return client, None
    except Exception:
        return None, "Docker is installed but the daemon isn't running (start Docker Desktop / the docker service)."


def prepare_workspace(workspace_dir: str, fixture_dir: str | None):
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir)
    os.makedirs(workspace_dir, exist_ok=True)
    if fixture_dir and os.path.isdir(fixture_dir):
        shutil.copytree(fixture_dir, workspace_dir, dirs_exist_ok=True)


# -------------- Logging helpers --------------
def log_event(log_file: str, event_type: str, data: dict | str):
    """Appends a JSON-formatted event to the session-specific log file."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        "data": data
    }
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
        last_entry = json.loads(lines[-1])
        return last_entry.get("event") == "Run complete"
    except (json.JSONDecodeError, OSError):
        # corrupted or unreadable file — treat as incomplete, will be overwritten below
        return False
        

if __name__ == "__main__":
    main()
