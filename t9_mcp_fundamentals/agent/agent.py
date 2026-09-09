import json
from collections import defaultdict
from typing import Any

import aiohttp

from commons.constants import OPENAI_HOST, OPENAI_API_KEY, DIAL_API_VERSION
from commons.models.message import Message
from commons.models.role import Role
from t9_mcp_fundamentals.agent.mcp_clients.base import MCPClient


class AgentMCPFundamentals:
    """Handles AI model interactions and integrates with MCP client"""

    def __init__(self, api_key: str, model: str, tools: list[dict[str, Any]], mcp_client: MCPClient):
        self.model = model
        self.tools = tools
        self.mcp_client = mcp_client
        self._api_key = OPENAI_API_KEY
        self._endpoint = f"{OPENAI_HOST}/openai/deployments/{model}/chat/completions?api-version={DIAL_API_VERSION}"
        self._headers = {"api-key": self._api_key, "Content-Type": "application/json"}

    def _collect_tool_calls(self, tool_deltas):
        """Convert streaming tool call deltas to complete tool calls"""
        tool_dict = defaultdict(lambda: {"id": None, "function": {"arguments": "", "name": None}, "type": None})

        for delta in tool_deltas:
            idx = delta["index"]
            if delta.get("id"): tool_dict[idx]["id"] = delta["id"]
            if delta.get("function", {}).get("name"): tool_dict[idx]["function"]["name"] = delta["function"]["name"]
            if delta.get("function", {}).get("arguments"): tool_dict[idx]["function"]["arguments"] += delta["function"]["arguments"]
            if delta.get("type"): tool_dict[idx]["type"] = delta["type"]

        return list(tool_dict.values())

    async def _stream_response(self, messages: list[Message]) -> Message:
        """Stream response and handle tool calls"""
        data = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in messages],
            "tools": self.tools,
            "temperature": 0.0,
            "stream": True
        }

        content = ""
        tool_deltas = []

        print("🤖: ", end="", flush=True)

        async with aiohttp.ClientSession() as session:
            async with session.post(self._endpoint, json=data, headers=self._headers) as resp:
                async for line_bytes in resp.content:
                    line = line_bytes.decode().strip()
                    if not line.startswith("data: ") or line[6:] == "[DONE]":
                        continue
                    chunk = json.loads(line[6:])
                    delta = chunk["choices"][0]["delta"]

                    delta_content = delta.get("content") or ""
                    if delta_content:
                        print(delta_content, end="", flush=True)
                        content += delta_content

                    if delta.get("tool_calls"):
                        tool_deltas.extend(delta["tool_calls"])

        print()
        return Message(
            role=Role.ASSISTANT,
            content=content,
            tool_calls=self._collect_tool_calls(tool_deltas) if tool_deltas else []
        )

    async def get_response(self, messages: list[Message]) -> Message:
        """Process user query with streaming and tool calling"""
        ai_message: Message = await self._stream_response(messages)

        if ai_message.tool_calls:
            messages.append(ai_message)
            await self._call_tools(ai_message, messages)
            return await self.get_response(messages)

        return ai_message

    async def _call_tools(self, ai_message: Message, messages: list[Message]):
        """Execute tool calls using MCP client"""
        #TODO:
        # 1. Iterate through tool_calls
        # 2. Get tool name and tool arguments (arguments is a JSON, don't forget about that)
        # 3. Wrap into try/except block and call mcp_client tool call. If succeed then add tool message (don't forget
        #    about tool call id), otherwise add tool message with error message (it kind of fallback strategy).
        for tool_call in ai_message.tool_calls:
            t_name = tool_call["function"]["name"]
            t_arguments = json.loads(tool_call["function"]["arguments"])
            try:
                result = await self.mcp_client.call_tool(tool_name=t_name, tool_args=t_arguments)
                messages.append(Message(role=Role.TOOL, content=result, tool_call_id=tool_call["id"]))
            except Exception as e:
                print(f"Error during tool call attempt {e}")
                messages.append(Message(role=Role.TOOL, content=str(e), tool_call_id=tool_call["id"]))

        
