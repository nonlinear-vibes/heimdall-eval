import time
import json

from openai import OpenAI
from docker import DockerClient
from datetime import datetime
from .agent_config import MAX_ITERS, REASONING_EFFORT
from .call_function import available_functions, call_function

# agentic loop
def generate_response(client: OpenAI, model_id: str, messages: list[dict[str, str]], workspace_dir: str, docker_client: DockerClient, log_file_name: str):
        LLM_run = []
        tool_called = False

        try:
            for it_num in range(MAX_ITERS):
                iteration_data = {}
                start = time.perf_counter()
                response = client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    tools=available_functions,
                    extra_body={
                        "reasoning": {
                            "effort": REASONING_EFFORT,
                            "summary": "auto"
                        }
                    }
                )
                duration_ms = (time.perf_counter() - start) * 1000

                message = response.choices[0].message
                usage = response.usage
                iteration_metadata = {
                    "duration": duration_ms,
                    "token_usage": {
                        "completion_tokens": usage.completion_tokens if usage else None,
                        "prompt_tokens": usage.prompt_tokens if usage else None,
                        "total_tokens": usage.total_tokens if usage else None,
                    },
                    "iteration_number": it_num,
                }
                
                assistant_msg = {"role": "assistant", "content": message.content}

                reasoning = getattr(message, "reasoning", None)
                if reasoning:
                    assistant_msg["reasoning"] = reasoning
                    iteration_data["reasoning"] = reasoning

                if message.tool_calls:
                    tool_called = True
                    assistant_msg["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ] # list of dicts
                    messages.append(assistant_msg)

                    iteration_data["function_calls"] = []
                    for tool_call in message.tool_calls:
                        function_name = tool_call.function.name
                        call_successful = True

                        try:
                            function_args = json.loads(tool_call.function.arguments)
                            result = call_function(function_name, function_args, workspace_dir, docker_client)
                        except json.JSONDecodeError as e:
                            function_args = None
                            result = {"error": f"Malformed tool arguments: {e}"}
                            call_successful = False
                        except Exception as e:
                            result = {"error": str(e)}
                            call_successful = False

                        iteration_data["function_calls"].append({
                            "name": function_name,
                            "args": function_args,
                            "result": result,
                            "successful": call_successful
                        })                 

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": json.dumps(result)
                        })

                    LLM_run.append({"iteration_metadata": iteration_metadata, "iteration_data": iteration_data})
                    continue

                messages.append(assistant_msg)
                iteration_data["ai_response"] = message.content or ""
                LLM_run.append({"iteration_metadata": iteration_metadata, "iteration_data": iteration_data})
                
                log_event(log_file_name, "LLM run", LLM_run)
                log_event(log_file_name, "Run complete", {"exit_reason": "Final answer", "total_iterations": it_num + 1, "tool_called": tool_called})
                return

            log_event(log_file_name, "LLM run", LLM_run)
            log_event(log_file_name, "Run complete", {"exit_reason": "Max iterations reached", "total_iterations": MAX_ITERS, "tool_called": tool_called})

        except Exception as e:
            log_event(log_file_name, "LLM run", LLM_run)
            log_event(log_file_name, "Error", {"message": str(e)})
            log_event(log_file_name, "Run complete", {"exit_reason": "Error", "total_iterations": len(LLM_run), "tool_called": tool_called})


# minor repetition, cleaner project structure
def log_event(log_file: str, event_type: str, data: dict | str):
    """Appends a JSON-formatted event to the session-specific log file."""
    entry = {"timestamp": datetime.now().isoformat(), "event": event_type, "data": data}
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")