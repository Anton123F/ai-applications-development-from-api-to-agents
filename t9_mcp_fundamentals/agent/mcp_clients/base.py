from abc import abstractmethod, ABC
from typing import Optional, Any

from mcp import ClientSession
from mcp.types import CallToolResult, TextContent, GetPromptResult, ReadResourceResult, Resource, TextResourceContents, BlobResourceContents, Prompt
from pydantic import AnyUrl


class MCPClient(ABC):

    def __init__(self) -> None:
        self.session: ClientSession | None = None

    @abstractmethod
    async def __aenter__(self):
        ...

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        ...

    async def get_tools(self) -> list[dict[str, Any]]:
        """Get available tools from MCP server"""
        if not self.session:
            raise RuntimeError("MCP client not connected. Call connect() first.")
        #TODO:
        # 1. Call `await self.session.list_tools()` and assign to `tools`
        # 2. Return list with dicts with tool schemas. It should be provided according to OpenAI specification
        # https://developers.openai.com/api/docs/guides/function-calling
        tools = await self.session.list_tools()
        tool_schema = []
        for tool in tools.tools:
            tool_schema.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                }
            })
        return tool_schema

    async def call_tool(self, tool_name: str, tool_args: dict[str, Any]) -> Any:
        """Call a specific tool on the MCP server"""
        if not self.session:
            raise RuntimeError("MCP client not connected. Call connect() first.")

        #TODO:
        # 1. Call `await self.session.call_tool(tool_name, tool_args)` and assign to `tool_result: CallToolResult` variable
        # 2. Get `content` with index `0` from `tool_result` and assign to `content` variable
        # 3. print(f"    ⚙️: {content}\n")
        # 4. If `isinstance(content, TextContent)` -> return content.text
        #    else -> return content
        tool_result: CallToolResult = await self.session.call_tool(tool_name, tool_args)
        content = tool_result.content[0]
        print(f"    ⚙️: {content}\n")
        if isinstance(content, TextContent):
            return content.text
        else:
            return content

    async def get_resources(self) -> list[Resource]:
        """Get available resources from MCP server"""
        if not self.session:
            raise RuntimeError("MCP client not connected.")
        #TODO:
        # Wrap into try/except (not all MCP servers have resources), get `list_resources` (it is async) and resources
        # from it. In case of error print error and return an empty array
        try:
            result = await self.session.list_resources()
            return result.resources 
        except Exception as e:
            print(f"Error during get MCP resourses: {e}")
            return []

    async def get_resource(self, uri: AnyUrl) -> str:
        """Get specific resource content"""
        if not self.session:
            raise RuntimeError("MCP client not connected.")

        #TODO:
        # 1. Get resource by uri (uri is that we provided on the Server side "users-management://flow-diagram")
        # 2. Get contents of [0] resource
        # 3. ResourceContents has 2 types TextResourceContents and BlobResourceContents, in case if content is instance
        #    of TextResourceContents return it is `text`, in case of BlobResourceContents return it is `blob`
        # ---
        # Optional: Later on in app.py you can try to fetch resource and print it (in our case it is image/png provided
        # as bytes, but you can return on the server side some dict just to check how resources are looks like).
        uri_resurse = await self.session.read_resource(uri)
        content = uri_resurse.contents[0]
        if isinstance(content, TextResourceContents):
            return content.text
        else:
            return content.blob

    async def get_prompts(self) -> list[Prompt]:
        """Get available prompts from MCP server"""
        if not self.session:
            raise RuntimeError("MCP client not connected.")
        #TODO:
        # Wrap into try/except (not all MCP servers have prompts), get `list_prompts` (it is async) and prompts
        # from it. In case of error print error and return an empty array
        try:
            result = await self.session.list_prompts()
            return result.prompts
        except Exception as e:
            print(f"error during 'get promt' atempt: {e}")
            return []

    async def get_prompt(self, name: str) -> str:
        """Get specific prompt content"""
        if not self.session:
            raise RuntimeError("MCP client not connected.")
        #TODO:
        # 1. Get prompt by name
        # 2. Create variable `combined_content` with empty string
        # 3. Iterate through prompt result `messages` and:
        #       - if `message` has attribute 'content' and is instance of TextContent then concat `combined_content`
        #          with `message.content.text + "\n"`
        #       - if `message` has attribute 'content' and is instance of `str` then concat `combined_content` with
        #          with `message.content + "\n"`
        # 4. Return `combined_content`
        specific_promt = await self.session.get_prompt(name=name)
        combined_content = ''
        for message in specific_promt.messages:
            if hasattr(message, 'content') and isinstance(message.content, TextContent):
                combined_content += message.content.text + '\n'
            elif hasattr(message, 'content') and isinstance(message.content, str):
                combined_content += message.content + '\n'
        return combined_content


