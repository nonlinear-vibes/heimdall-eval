import os
from ..agent_config import MAX_CHARS


def get_file_content(working_directory: str, file_path: str, line_start: int=1, line_end: int | None=None) -> str:
    try:
        # guardrail
        abs_working_dir = os.path.realpath(working_directory)
        abs_file_path = os.path.realpath(os.path.join(abs_working_dir, file_path))
        if os.path.commonpath([abs_working_dir, abs_file_path]) != abs_working_dir:
            return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'
        if not os.path.isfile(abs_file_path):
            return f'Error: File not found or is not a regular file: "{file_path}"'
        
        # read all lines
        with open(abs_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        total_lines = len(lines)
        
        start_idx = max(0, line_start - 1)
        end_idx = total_lines if line_end is None else min(total_lines, line_end)

        if start_idx >= total_lines:
            return f"Error: line_start ({line_start}) exceeds total lines ({total_lines})"
        
        selected_lines = lines[start_idx:end_idx]
        content = "".join(selected_lines)

        if len(content) > MAX_CHARS:
            content = content[:MAX_CHARS] + f"\n[...Content truncated at {MAX_CHARS} characters]"

        header = f"--- File: {file_path} (Lines {start_idx + 1} to {end_idx} of {total_lines}) ---\n"
        return header + content

    except Exception as e:
        return f'Error reading file "{file_path}": {e}'


schema_get_file_content = {
    "type": "function",
    "function": {
        "name": "get_file_content",
        "description": f"Retrieves a specific line range (with a maximum of {MAX_CHARS} characters) from a file within the working directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file relative to working directory"
                },
                "line_start": {
                    "type": "integer",
                    "description": "The first line to read (1-indexed). Defaults to 1."
                },
                "line_end": {
                    "type": "integer",
                    "description": "The last line to read (inclusive). Defaults to the end of the file."
                }
            },
            "required": ["file_path"] 
        }
    }
}
