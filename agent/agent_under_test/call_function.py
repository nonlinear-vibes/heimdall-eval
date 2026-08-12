import inspect
from docker import DockerClient
from .functions.get_file_content import get_file_content, schema_get_file_content
from .functions.get_files_info import get_files_info, schema_get_files_info
from .functions.run_python_file import run_python_file, schema_run_python_file
from .functions.write_file import schema_write_file, write_file

available_functions = [
        schema_get_files_info,
        schema_get_file_content,
        schema_run_python_file,
        schema_write_file,
    ]

# Map function names to actual implementations
function_map = {
    "get_files_info": get_files_info,
    "get_file_content": get_file_content,
    "run_python_file": run_python_file,
    "write_file": write_file,
}

def call_function(function_name: str, function_args: dict[str, str], working_dir: str, docker_client: DockerClient | None=None) -> str:
    if function_name not in function_map:
        return {"error": f"Unknown function: {function_name}"}
    
    func_args = dict(function_args) if function_args else {}
    func_args["working_directory"] = working_dir

    called_function = function_map[function_name]
    if "docker_client" in inspect.signature(called_function).parameters:
        func_args["docker_client"] = docker_client

    try:
        return called_function(**func_args)
    except Exception as e:
        return {"error": str(e)}