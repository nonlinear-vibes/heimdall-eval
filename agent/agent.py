import time
import json

from openai import OpenAI
from docker import DockerClient
from config import MAX_ITERS, REASONING_EFFORT
from call_function import available_functions, call_function
from agent_tester import log_event

# agentic loop
def generate_response(client: OpenAI, model_id: str, messages: list[dict[str, str]], workspace_dir: str, docker_client: DockerClient, log_file_name: str):
        LLM_run = []
        no_tool_called = True

        try:
            for it_num in range(MAX_ITERS):
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
                iteration_log = {
                    "Duration": duration_ms,
                    "Token usage": {
                        "Completion tokens": usage.completion_tokens if usage else None,
                        "Prompt tokens": usage.prompt_tokens if usage else None,
                        "Total tokens": usage.total_tokens if usage else None,
                    },
                    "Iteration number": it_num,
                }
                LLM_run.append(iteration_log)
                assistant_msg = {"role": "assistant", "content": message.content}

                reasoning = getattr(message, "reasoning", None)
                if reasoning:
                    assistant_msg["reasoning"] = reasoning
                    iteration_log["AI reasoning"] = reasoning

                if message.tool_calls:
                    no_tool_called = False
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

                    iteration_log["Function calls"] = []
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

                        iteration_log["Function calls"].append({
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

                    continue

                messages.append(assistant_msg)
                iteration_log["AI response"] = message.content or ""
                log_event(log_file_name, "LLM run", LLM_run)
                log_event(log_file_name, "Run complete", {"exit_reason": "Final answer", "total_iterations": it_num + 1, "no_tool_called": no_tool_called})
                return

            log_event(log_file_name, "LLM run", LLM_run)
            log_event(log_file_name, "Run complete", {"exit_reason": "Max iterations reached", "total_iterations": MAX_ITERS, "no_tool_called": no_tool_called})

        except Exception as e:
            log_event(log_file_name, "LLM run", LLM_run)
            log_event(log_file_name, "Error", {"message": str(e)})
            log_event(log_file_name, "Run complete", {"exit_reason": "error", "total_iterations": len(LLM_run), "no_tool_called": no_tool_called})