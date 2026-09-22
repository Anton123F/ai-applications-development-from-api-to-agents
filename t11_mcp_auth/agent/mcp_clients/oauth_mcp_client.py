from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, TextContent

from t11_mcp_auth.agent.mcp_clients._base import T11MCPClient
from t11_mcp_auth.agent.mcp_clients._oauth_keycloak import OAuthTokenManager
import json

class OauthHttpMCPClient(T11MCPClient):
    """
    MCP client that authenticates via OAuth 2.0 + PKCE.

    On __aenter__:
      1. Runs the PKCE browser flow (opens Keycloak login once)
      2. Connects to the MCP server with the resulting Bearer token

    On tool calls:
      - Automatically retries with a refreshed token on 401 responses
    """

    def __init__(self, mcp_server_url: str) -> None:
        super().__init__()
        self.mcp_server_url = mcp_server_url
        self.token_manager = OAuthTokenManager()
        self._streams_context = None
        self._session_context = None
        self.session: ClientSession | None = None

    async def __aenter__(self):
        #TODO:
        # 1. Authenticate via browser PKCE flow using `self.token_manager`
        # 2. Get auth headers from the token manager and create an `httpx.AsyncClient` with them
        # 3. Set up `streamable_http_client`, enter it to get streams, create and enter a `ClientSession`,
        #    initialize the session, and print the result as indented JSON
        # 4. Return `self`
        await self.token_manager.authenticate()

        headers = await self.token_manager.auth_headers()
        self._client = httpx.AsyncClient(headers=headers, timeout=30.0)

        self._stream_context = streamable_http_client(http_client=self._client, url=self.mcp_server_url)
        read_stream, write_stream, _ = await self._stream_context.__aenter__()

        self._session_context = ClientSession(read_stream, write_stream)
        self.session = await self._session_context.__aenter__()
        init_result = await self.session.initialize()

        print(init_result.model_dump_json(indent=2))

        return self


    async def __aexit__(self, exc_type, exc_val, exc_tb):
        #TODO:
        # 1. If session context exists — exit it, passing through the exception info
        # 2. If streams context exists — exit it, passing through the exception info
        if self._session_context:
            await self._session_context.__aexit__(exc_type, exc_val, exc_tb)
        if self._stream_context:
            await self._stream_context.__aexit__(exc_type, exc_val, exc_tb)

    async def get_tools(self) -> list[dict[str, Any]]:
        """Get available tools from MCP server"""
        if not self.session:
            raise RuntimeError("MCP client not connected")

        #TODO:
        # 1. Fetch available tools from the session
        # 2. Return them as a list of dicts in the OpenAI function-calling format:
        #    {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
        tools = await self.session.list_tools()
        openai_tools = []
        for tool in tools.tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            })
        return openai_tools

    async def call_tool(self, tool_name: str, tool_args: dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server.
        Proactively refreshes the token before it expires to avoid broken streams.
        """
        if not self.session:
            raise RuntimeError("MCP client not connected")

        print(f"    🔧 Calling `{tool_name}` with {tool_args}")

        #TODO:
        # 1. Check if the token is expired via `self.token_manager.is_token_expired()`
        #    If so, print a refresh message and call `self._reconnect_with_fresh_token()`
        # 2. Return the result of `await self._do_call_tool(tool_name, tool_args)`
        if self.token_manager.is_token_expired():
            print(f"Token is expired , refreshing....")
            await self._reconnect_with_fresh_token()
        return await self._do_call_tool(tool_name, tool_args)

    async def _do_call_tool(self, tool_name: str, tool_args: dict[str, Any]) -> Any:
        #TODO:
        # 1. Call the tool on the session and assign the result to `tool_result: CallToolResult`
        # 2. If `tool_result.content` is empty — return `"No content returned from tool"`
        # 3. Get the first element, print it with prefix `"    ⚙️: "`, then return its `.text`
        #    if it's a `TextContent`, otherwise return `str(content)`
        tool_result: CallToolResult = await self.session.call_tool(tool_name, tool_args)
        if not tool_result.content:
            return "No content returned from tool"
        content = tool_result.content[0]
        # print(f"    ⚙️: {content}")
        if isinstance(content, TextContent):
            return content.text
        else:
            return str(content)


    async def _reconnect_with_fresh_token(self) -> None:
        """Refresh OAuth token and re-establish the MCP session with the new token"""
        #TODO:
        # 1. Refresh the token via `self.token_manager.refresh()`
        # 2. Tear down the existing session and streams contexts (exit both if they exist)
        # 3. Get new auth headers, create a new `httpx.AsyncClient`, set up a new
        #    `streamable_http_client`, enter it, create and enter a new `ClientSession`,
        #    initialize it, then print "    ✅ Reconnected with fresh token"
        await self.token_manager.refresh()
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._stream_context:
            await self._stream_context.__aexit__(None, None, None)

        headers = await self.token_manager.auth_headers()
        self._client = httpx.AsyncClient(headers=headers, timeout=30.0)
        
        self._stream_context = streamable_http_client(http_client=self._client, url=self.mcp_server_url)
        read_stream, write_stream, _ = await self._stream_context.__aenter__()

        self._session_context = ClientSession(read_stream, write_stream)
        self.session = await self._session_context.__aenter__()

        await self.session.initialize()

        print(f"    ✅ Reconnected with fresh token")