from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, TextContent

from t11_mcp_auth.agent.mcp_clients._base import T11MCPClient

import json


class ApiKeyMCPClient(T11MCPClient):
    """Handles MCP server connection and tool execution via http"""

    def __init__(self, mcp_server_url: str, api_key: str) -> None:
        super().__init__()
        self.mcp_server_url = mcp_server_url
        self.api_key = api_key
        self._streams_context = None
        self._session_context = None

    async def __aenter__(self):
        #TODO:
        # 1. Create an `httpx.AsyncClient` that passes the API key in the `X-API-Key` request header
        # 2. Create a `streamable_http_client` using `self.mcp_server_url` and the http client above,
        #    assign to `self._streams_context`, then enter it to unpack `read_stream, write_stream, _`
        # 3. Create a `ClientSession(read_stream, write_stream)`, assign to `self._session_context`,
        #    then enter it and assign the result to `self.session`
        # 4. Initialize the session and print the result as indented JSON
        # 5. Return `self`
        client = httpx.AsyncClient(headers={
            "X-API-Key": self.api_key
        })
        self._streams_context = streamable_http_client(url=self.mcp_server_url, http_client=client)
        read_stream, write_stream, _ = await self._streams_context.__aenter__()
        self._session_context = ClientSession(read_stream=read_stream, write_stream=write_stream)
        self.session = await self._session_context.__aenter__()
        result = await self.session.initialize()
        print(result.model_dump_json(indent=2))
        return self


    async def __aexit__(self, exc_type, exc_val, exc_tb):
        #TODO:
        # 1. If session context exists — exit it, passing through the exception info
        # 2. If streams context exists — exit it, passing through the exception info
        if self._session_context:
            await self._session_context.__aexit__(exc_type, exc_val, exc_tb)
        if self._streams_context:
            await self._streams_context.__aexit__(exc_type, exc_val, exc_tb)


    async def get_tools(self) -> list[dict[str, Any]]:
        """Get available tools from MCP server"""
        if not self.session:
            raise RuntimeError("MCP client not connected. Call connect() first.")

        #TODO:
        # 1. Fetch available tools from the session
        # 2. Return them as a list of dicts in the OpenAI function-calling format, e.g.:
        #    {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
        tools = await self.session.list_tools()
        openai_tools = []
        for tool in tools.tools:
            openai_tools.append({
                "type": "function",
                'function': {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            })
        return openai_tools



    async def call_tool(self, tool_name: str, tool_args: dict[str, Any]) -> Any:
        """Call a specific tool on the MCP server"""
        if not self.session:
            raise RuntimeError("MCP client not connected. Call connect() first.")

        print(f"    🔧 Calling `{tool_name}` with {tool_args}")

        #TODO:
        # 1. Call the tool on the session and assign the result to `tool_result: CallToolResult`
        # 2. Get the first element from `tool_result.content` and print it with the prefix `"    ⚙️: "`
        # 3. If the content is a `TextContent` instance — return its `.text`, otherwise return `str(content)`
        tool_result: CallToolResult = await self.session.call_tool(name=tool_name, arguments=tool_args)
        content = tool_result.content[0]
        print(f"    ⚙️: {content}")
        if isinstance(content, TextContent):
            return content.text
        else:
            return str(content)