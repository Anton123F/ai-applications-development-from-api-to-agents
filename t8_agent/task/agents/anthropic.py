import json
from typing import Any

import requests

from commons.constants import ANTHROPIC_ENDPOINT
from commons.models.message import Message
from commons.models.role import Role
from t8_agent.task.agents._base import BaseAgent
from t8_agent.task.tools.base import BaseTool


class AnthropicBasedAgent(BaseAgent):

    def __init__(self, model: str, api_key: str, tools: list[BaseTool] | None = None, system_prompt: str | None = None):
        super().__init__(model, api_key, tools, system_prompt)
        #TODO:
        # 1. Set `self._endpoint` to `ANTHROPIC_ENDPOINT`
        # 2. Build `self._tools_schemas` using `tool.anthropic_schema` for each tool in `tools`
        #    Note: Anthropic uses a flat schema format — see `BaseTool.anthropic_schema`
        # 3. Print `self._endpoint` and `self._tools_schemas` (use json.dumps with indent=4)
        self._endpoint = ANTHROPIC_ENDPOINT

        self._tools_schemas = []
        if tools:
            for tool in tools:
                self._tools_schemas.append(tool.anthropic_schema)

        print(self._endpoint)
        print(json.dumps(self._tools_schemas, indent=4))

    def get_response(self, messages: list[Message], print_request: bool = True) -> Message:
        #TODO:
        # 1. Build headers: `x-api-key: self._api_key`, `anthropic-version: 2023-06-01`,
        #    `Content-Type: application/json`
        # 2. Convert messages to Anthropic format using `_to_anthropic_messages(messages)`
        # 3. Build request_data: model, max_tokens=8096, messages, tools
        # 4. If `self._system_prompt` is set — add `"system": self._system_prompt` to request_data
        # 5. If `print_request` — print `self._endpoint` and the REQUEST payload
        # 6. POST to `self._endpoint` with headers and json body
        # 7. On HTTP 200:
        #    a. Get `content` blocks and `stop_reason`, print RESPONSE
        #    b. Extract text: first block where type == "text" (use next() with default None)
        #    c. Extract tool_use blocks: filter blocks where type == "tool_use"
        #    d. Build `ai_response` as Message(role=Role.ASSISTANT, content=text,
        #       tool_calls=content_blocks if tool_use_blocks else None)
        #    e. If `stop_reason == "tool_use"`:
        #       - Append `ai_response` to `messages`
        #       - Call `_process_tool_calls(tool_use_blocks)` and extend `messages`
        #       - Recurse: return `self.get_response(messages, print_request)`
        #    f. Otherwise return `ai_response`
        # 8. On error — raise Exception with status code and response text
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        anthropic_messages = self._to_anthropic_messages(messages)

        request_data = {
            "model": self._model,
            "max_tokens": 8096,
            "messages": anthropic_messages,
            "tools": self._tools_schemas
        }

        if self._system_prompt:
            request_data["system"] = self._system_prompt

        if print_request:
            print(self._endpoint)
            print(json.dumps(request_data, indent=4))

        response = requests.post(self._endpoint, headers=headers, json=request_data)

        if response.status_code == 200:
            resp_json = response.json()
            content_blocks = resp_json.get("content", [])
            stop_reason = resp_json.get("stop_reason", None)

            print(json.dumps(resp_json, indent=4))

            text = next((block["text"] for block in content_blocks if block.get("type") == "text"), None)

            tool_use_blocks = [block for block in content_blocks if block.get("type") == "tool_use"]

            ai_response = Message(
                role=Role.ASSISTANT,
                content=text,
                tool_calls=content_blocks if tool_use_blocks else None
            )

            if stop_reason == "tool_use":
                messages.append(ai_response)
                tool_call_responses = self._process_tool_calls(tool_use_blocks)
                messages.extend(tool_call_responses)
                return self.get_response(messages, print_request)

            return ai_response
        else:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

    def _to_anthropic_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        #TODO: Convert internal Message list to Anthropic API format.
        # Walk the list with an index `i` (while loop):
        # - Role.TOOL: group consecutive TOOL messages into one user message:
        #   {"role": "user", "content": [{"type": "tool_result", "tool_use_id": ..., "content": ...}, ...]}
        # - Role.ASSISTANT: if msg.tool_calls is set use it as content (replays the full content blocks
        #   so Anthropic can correlate tool results), otherwise use msg.content as content
        # - Other roles: {"role": msg.role.value, "content": msg.content}
        # Return the resulting list
        result = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            if msg.role == Role.TOOL:
                tool_results = []
                while i < len(messages) and messages[i].role == Role.TOOL:
                    tool_msg = messages[i]
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_msg.tool_call_id,
                        "content": tool_msg.content
                    })
                    i += 1
                result.append({
                    "role": "user",
                    "content": tool_results
                })
                continue
            elif msg.role == Role.ASSISTANT:
                if msg.tool_calls:
                    result.append({
                        "role": "assistant",
                        "content": msg.tool_calls
                    })
                else:
                    result.append({
                        "role": "assistant",
                        "content": msg.content
                    })
            else:
                result.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
            i += 1
        return result

    def _process_tool_calls(self, tool_use_blocks: list[dict[str, Any]]) -> list[Message]:
        #TODO:
        # For each block in tool_use_blocks:
        # 1. Extract `tool_use_id` from block["id"]
        # 2. Extract `function_name` from block["name"]
        # 3. Get `arguments` from block["input"] — it is already a dict, no json.loads needed
        # 4. Call `_call_tool(function_name, arguments)` and store the result
        # 5. Append Message(role=Role.TOOL, name=function_name, tool_call_id=..., content=result)
        # 6. Print the function name and result
        # Return the list of tool messages
        tool_messages = []
        for block in tool_use_blocks:
            tool_use_id = block["id"]
            function_name = block["name"]
            arguments = block["input"]
            result = self._call_tool(function_name, arguments)
            tool_msg = Message(
                role=Role.TOOL,
                name=function_name,
                tool_call_id=tool_use_id,
                content=result
            )
            tool_messages.append(tool_msg)
            print(f"Tool call: {function_name}({arguments}) => {result}")
        return tool_messages

    def _call_tool(self, function_name: str, arguments: dict[str, Any]) -> str:
        #TODO:
        # 1. Look up the tool by `function_name` in `self._tools_dict`
        # 2. If found — call `tool.execute(arguments)` and return the result
        # 3. If not found — return `f"Unknown function: {function_name}"`
        tool = self._tools_dict.get(function_name)
        if tool:
            return tool.execute(arguments)
        return f"Unknown function: {function_name}"