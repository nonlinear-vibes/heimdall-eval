import os
import sys
import subprocess
from docker import DockerClient


def run_python_file(working_directory: str, file_path: str, args: list[dict[str, str]]=None, docker_client: DockerClient | None=None) -> str:
    try:
        # guardrail
        abs_working_dir = os.path.realpath(working_directory)
        abs_file_path = os.path.realpath(os.path.join(abs_working_dir, file_path))
        if os.path.commonpath([abs_working_dir, abs_file_path]) != abs_working_dir:
            return f'Error: Cannot execute "{file_path}" as it is outside the permitted working directory'
        if not os.path.isfile(abs_file_path):
            return f'Error: "{file_path}" does not exist or is not a regular file'
        if not abs_file_path.endswith(".py"):
            return f'Error: "{file_path}" is not a Python file'

        if docker_client:
            container = docker_client.containers.run(
                image="python:3.12-slim",
                command=["python", file_path, *(args or [])],
                volumes={abs_working_dir: {"bind": "/workspace", "mode": "rw"}},
                working_dir="/workspace",
                network_disabled=True,
                mem_limit="256m",
                pids_limit=64,
                user="nobody",
                tmpfs={"/tmp": ""},
                read_only=True,
                detach=True,
            )
            try:
                exit_status = container.wait(timeout=30)["StatusCode"]
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            except:
                container.remove(force=True)
                raise
            container.remove(force=True)

            output = []
            if exit_status != 0:
                output.append(f"Process exited with code {exit_status}")
            if not stdout and not stderr:
                output.append("No output produced")
            if stdout:
                output.append(f"STDOUT:\n{stdout}")
            if stderr:
                output.append(f"STDERR:\n{stderr}")
            return "\n".join(output)
        else:
            command = [sys.executable, abs_file_path]
            if args:
                command.extend(args)

            result = subprocess.run(
                command,
                cwd=abs_working_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )

        # process the output
        output = []
        if result.returncode != 0:
            output.append(f"Process exited with code {result.returncode}")
        if not result.stdout and not result.stderr:
            output.append("No output produced")
        if result.stdout:
            output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output.append(f"STDERR:\n{result.stderr}")
        return "\n".join(output)
    
    except Exception as e:
        return f"Error: executing Python file: {e}"



schema_run_python_file = {
    "type": "function",
    "function": {
        "name": "run_python_file",
        "description": "Executes a specified Python file within the working directory and returns its output",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the Python file to run, relative to the working directory"
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of arguments to pass to the Python script"
                }
            },
            "required": ["file_path"] 
        }
    }
}