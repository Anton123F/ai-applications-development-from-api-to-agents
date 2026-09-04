import json
from typing import Any

import requests

from commons.constants import OPENAI_CHAT_COMPLETIONS_ENDPOINT, DIAL_API_VERSION
from commons.models.message import Message
from commons.models.role import Role
from t8_agent.task.agents._base import BaseAgent
from t8_agent.task.tools.base import BaseTool


class OpenAIBasedAgent(BaseAgent):

    def __init__(self, model: str, api_key: str, tools: list[BaseTool] | None = None, system_prompt: str | None = None):
        super().__init__(model, api_key, tools, system_prompt)
        #TODO:
        # 1. Format `self._api_key` as a Bearer token: `f"Bearer {api_key}"`
        # 2. Build `self._tools_schemas` using `tool.openai_schema` for each tool in `tools`
        # 3. Set `self._endpoint` to `OPENAI_CHAT_COMPLETIONS_ENDPOINT`
        # 4. Print `self._endpoint` and `self._tools_schemas` (use json.dumps with indent=4)
        self._api_key = api_key
        self._tools_schemas = []
        for tool in (tools or []):
            self._tools_schemas.append(tool.openai_schema)
        self._endpoint = f"{OPENAI_CHAT_COMPLETIONS_ENDPOINT}/openai/deployments/{model}/chat/completions?api-version={DIAL_API_VERSION}"
        # print(self._endpoint)
        # print(json.dumps(self._tools_schemas, indent=4))
        

    def get_response(self, messages: list[Message], print_request: bool = True) -> Message:
        # REQUEST body sent to the API:
        # {
        #   "model": "gpt-5.2-...",
        #   "tools": [ { "type": "function", "function": {...} }, ... ],
        #   "messages": [
        #     { "role": "system",    "content": "You are..." },   <- system prompt (prepended locally)
        #     { "role": "user",      "content": "Find user 5" },
        #     { "role": "assistant", "content": "", "tool_calls": [...] },
        #     { "role": "tool",      "tool_call_id": "call_abc", "content": "result..." }
        #   ]
        # }
        #
        # RESPONSE — final answer (finish_reason == "stop"):
        # { "choices": [ { "message": { "role": "assistant", "content": "Here is user 5..." },
        #                  "finish_reason": "stop" } ] }
        #
        # RESPONSE — tool call requested (finish_reason == "tool_calls"):
        # { "choices": [ { "message": { "role": "assistant", "content": "",
        #                               "tool_calls": [ { "id": "call_abc",
        #                                                 "function": { "name": "get_user_by_id",
        #                                                               "arguments": "{\"id\":5}" } } ] },
        #                  "finish_reason": "tool_calls" } ] }
        #
        #TODO:
        # 1. Build `request_messages`: if `self._system_prompt` is set, prepend a
        #    Message(role=Role.SYSTEM, content=self._system_prompt) to `messages` —
        #    do NOT store it in `messages` itself (local to this API call only)
        # 2. Build headers: `Authorization: self._api_key`, `Content-Type: application/json`
        # 3. Build request_data with `model`, serialized `request_messages` (.to_dict()), and `tools`
        # 4. If `print_request` — print `self._endpoint` and the REQUEST payload
        # 5. POST to `self._endpoint` with headers and json body
        # 6. On HTTP 200:
        #    a. Get `choices[0]`, print RESPONSE
        #    b. Extract `content` and `tool_calls` from `choices[0]["message"]`
        #    c. Build `ai_response` as Message(role=Role.ASSISTANT, content=..., tool_calls=...)
        #    d. If `finish_reason == "tool_calls"`:
        #       - Append `ai_response` to `messages`
        #       - Call `_process_tool_calls(tool_calls)` and extend `messages` with the result
        #       - Recurse: return `self.get_response(messages, print_request)`
        #    e. Otherwise return `ai_response`
        # 7. On error — raise Exception with status code and response text
        system_message = ''
        if self._system_prompt:
            system_message = Message(role=Role.SYSTEM, content=self._system_prompt)

        headers = {
            "Content-Type": "application/json",
            "api-key": self._api_key
        }
        data = {
            "model": self._model,
            "tools": self._tools_schemas,
            "messages": ([system_message.to_dict()] if system_message else []) + [m.to_dict() for m in messages]
        }

        if print_request:
            print(f"Endpoint = {self._endpoint}")
            try:
                print(json.dumps(json.loads(data), indent=2))
            except Exception:
                print(data)

        response = requests.post(self._endpoint, headers=headers, json=data)
            
        if response.status_code == 200:
            response_json = response.json()

            choices = response_json.get('choices')
            if not choices or len(choices) == 0:
                raise ValueError("API response contains no choices.")

            # print('=========================')
            # print(choices[0])
            # print('=========================')

            first_choice = choices[0]
            message = first_choice.get("message", {})
            content = message.get("content")
            tool_calls = message.get("tool_calls")
            finish_reason = first_choice.get("finish_reason")

            # print(content)
            # print(tool_calls)
            # print('=========================')

            ai_response = Message(role=Role.ASSISTANT, content=content, tool_calls=tool_calls)

            if finish_reason == 'tool_calls':
                messages.append(ai_response)
                tool_call_result = self._process_tool_calls(tool_calls)
                messages.extend(tool_call_result)
                return self.get_response(messages, print_request)
            return ai_response
        else:
            raise Exception(f"{response.status_code}: {response.text}")
        

    def _process_tool_calls(self, tool_calls: list[dict[str, Any]]) -> list[Message]:
        # INPUT — `tool_calls` is choices[0]["message"]["tool_calls"] from the API response:
        # [
        #   {
        #     "id": "call_abc123",                        <- tool_call["id"]
        #     "type": "function",
        #     "function": {
        #       "name": "get_user_by_id",                 <- tool_call["function"]["name"]
        #       "arguments": "{\"id\": 5}"                <- JSON string → json.loads → {"id": 5}
        #     }
        #   },
        #   { ... next tool call ... }
        # ]
        #
        # OUTPUT — list of TOOL messages sent back to the model next turn:
        # [
        #   Message(role=TOOL, name="get_user_by_id", tool_call_id="call_abc123", content="user info...")
        # ]
        #
        #TODO:
        # For each tool_call in tool_calls:
        # 1. Extract `tool_call_id` from tool_call["id"]
        # 2. Extract `function_name` from tool_call["function"]["name"]
        # 3. Parse `arguments` with `json.loads(tool_call["function"]["arguments"])`
        # 4. Call `_call_tool(function_name, arguments)` and store the result
        # 5. Append Message(role=Role.TOOL, name=function_name, tool_call_id=..., content=result)
        # 6. Print the function name and result
        # Return the list of tool messages
        messages = []
        for tool_call in tool_calls:
            id = tool_call["id"]
            function_name = tool_call["function"]["name"]
            argumnets = json.loads(tool_call["function"]["arguments"])
            result = self._call_tool(function_name, arguments=argumnets)
            messages.append(Message(role=Role.TOOL, name=function_name, tool_call_id=id, content=result))
            print(f"function name: {function_name}; function result:")
            print(json.dumps(result, indent=2))
        return messages
        

    def _call_tool(self, function_name: str, arguments: dict[str, Any]) -> str:
        # `function_name` and `arguments` come from the tool_call block in the API response:
        # {
        #   "id": "call_abc123",
        #   "function": {
        #     "name": "get_user_by_id",        <- function_name
        #     "arguments": "{\"id\": 5}"       <- parsed into arguments = {"id": 5}
        #   }
        # }
        # Returns a plain string — becomes `content` of the TOOL message sent back to model:
        # Message(role=Role.TOOL, name="get_user_by_id", tool_call_id="call_abc123", content="<result>")
        #
        #TODO:
        # 1. Look up the tool by `function_name` in `self._tools_dict`
        # 2. If found — call `tool.execute(arguments)` and return the result
        # 3. If not found — return `f"Unknown function: {function_name}"`
        tool = self._tools_dict.get(function_name)
        if tool:
            result = tool.execute(arguments)
            return result
        else:
            return f"Unknown function: {function_name}"