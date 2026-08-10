# agent_tester.py
import os
import yaml
import json
import agent
import docker
import shutil

from openai import OpenAI
from dotenv import load_dotenv
from docker import DockerClient
from system_prompt import SYSTEM_PROMPT
from log_utils import log_event, is_run_complete
from config import LOGS_DIR, AGENT_VERSION, MODELS_YAML, PROMPTS_YAML, WORKSPACES_DIR


def main():

    with open(MODELS_YAML) as f:
        models = yaml.safe_load(f)["models"]

    with open(PROMPTS_YAML) as f:
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
        model_tag = model['model_tag']
        os.makedirs(f"{LOGS_DIR}/{model_tag}/{AGENT_VERSION}", exist_ok=True)
        for prompt in prompts:
            prompt_id = prompt['prompt_id']
            run_id = f"{model_tag}_{AGENT_VERSION}_{prompt_id}"
            log_file_path = f"{LOGS_DIR}/{model_tag}/{AGENT_VERSION}/{prompt_id}.jsonl"

            if is_run_complete(log_file_path):
                print(f"Skipping {log_file_path} (already complete).")
                continue

            if os.path.exists(log_file_path):
                os.remove(log_file_path)  # partial/corrupted run from a previous crash — start clean

            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.append({"role": "user", "content": prompt.get("text")})
            log_event(log_file_path, "Start", {"run_id": run_id, "agent_version": AGENT_VERSION, "prompt_id": prompt.get("prompt_id"), "prompt_name": prompt.get("prompt_name"), "category": prompt.get("category"), "fixture_dir": prompt.get("fixture_dir")})
            log_event(log_file_path, "Task", prompt["text"])
            workspace_dir = WORKSPACES_DIR / model_tag / f"{AGENT_VERSION}" / prompt_id
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
        

if __name__ == "__main__":
    main()
