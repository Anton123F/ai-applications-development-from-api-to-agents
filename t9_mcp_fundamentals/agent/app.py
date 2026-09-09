import os
import sys
import asyncio
import json
from pathlib import Path

from mcp import Resource
from mcp.types import Prompt

from commons.constants import OPENAI_API_KEY
from commons.models.message import Message
from commons.models.role import Role
from t9_mcp_fundamentals.agent.agent import AgentMCPFundamentals
from t9_mcp_fundamentals.agent.mcp_clients.http import HttpMCPClient
from t9_mcp_fundamentals.agent.mcp_clients.stdio import StdioMCPClient
from t9_mcp_fundamentals.agent.prompts import SYSTEM_PROMPT


async def main():
    #TODO:
    # 1. Create `HttpMCPClient(mcp_server_url="http://localhost:8005/mcp")` as an async context manager
    #    (`async with ... as mcp_client:`) — all steps below happen inside this block
    # 2. Print Available Resources
    # 3. Print Available Tools
    # 4. Create `AgentMCPFundamentals`
    # 5. Create `messages` list with a single system prompt
    # 6. Print Available Prompts
    # 7. Run an infinite loop:
    #    - get user input with `input("\n> ").strip()`
    #    - if user_input.lower() == 'exit': break
    #    - append Message(role=Role.USER, content=user_input) to `messages`
    #    - call `await agent.get_response(messages)` and append the returned `ai_message` to `messages`

#======================> HTTP MCP Client <=====================
    async with HttpMCPClient(mcp_server_url="http://localhost:8005/mcp") as http_mcp_client:
        resourses = await http_mcp_client.get_resources()
        print(f"List of available resourses: =>>>>>>>>>>> \n{resourses}")
        tools = await http_mcp_client.get_tools() 
        print(f"List of available tools: =>>>>>>>>>>> \n {tools}")
        agent_mcp = AgentMCPFundamentals(
            model="gpt-5.2-2025-12-11", 
            tools=tools, 
            api_key=OPENAI_API_KEY, 
            mcp_client=http_mcp_client
        )
        messages = [Message(role=Role.SYSTEM, content=SYSTEM_PROMPT)]
        print(await http_mcp_client.get_prompts())
        while True:
            user_input = input('=> please enter agent question => ').strip()
            if user_input.lower() == 'exit':
                break
            if user_input == '':
                continue
            user_message = Message(role=Role.USER, content=user_input)
            messages.append(user_message)
            ai_response = await agent_mcp.get_response(messages=messages)
            messages.append(ai_response)



#======================> STDIO MCP Client <=====================
    # PROJECT_ROOT = Path(__file__).resolve().parents[2]
    # STDIO_SERVER_PATH = PROJECT_ROOT / "t9_mcp_fundamentals" / "mcp_server" / "stdio_server.py"

    # async with StdioMCPClient(
    #     command=sys.executable,
    #     args=[str(STDIO_SERVER_PATH)],
    #     env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    # ) as mcp_client:
    #     resourses = await mcp_client.get_resources()
    #     print(f"List of available resourses: =>>>>>>>>>>> \n{resourses}")
    #     tools = await mcp_client.get_tools() 
    #     print(f"List of available tools: =>>>>>>>>>>> \n {tools}")
    #     agent_mcp = AgentMCPFundamentals(
    #         model="gpt-5.2-2025-12-11", 
    #         tools=tools, 
    #         api_key=OPENAI_API_KEY, 
    #         mcp_client=mcp_client
    #     )
    #     messages = [Message(role=Role.SYSTEM, content=SYSTEM_PROMPT)]
    #     print(await mcp_client.get_prompts())
    #     while True:
    #         user_input = input('=> please enter agent question => ').strip()
    #         if user_input.lower() == 'exit':
    #             break
    #         if user_input == '':
    #             continue
    #         user_message = Message(role=Role.USER, content=user_input)
    #         messages.append(user_message)
    #         ai_response = await agent_mcp.get_response(messages=messages)
    #         messages.append(ai_response)


#======================> Docker MCP Client <=====================
    # async with StdioMCPClient(docker_image="mcp/duckduckgo:latest") as mcp_client:
    #     resourses = await mcp_client.get_resources()
    #     print(f"List of available resourses: =>>>>>>>>>>> \n{resourses}")
    #     tools = await mcp_client.get_tools() 
    #     print(f"List of available tools: =>>>>>>>>>>> \n {tools}")
    #     agent_mcp = AgentMCPFundamentals(
    #         model="gpt-5.2-2025-12-11", 
    #         tools=tools, 
    #         api_key=OPENAI_API_KEY, 
    #         mcp_client=mcp_client
    #     )
    #     messages = [Message(role=Role.SYSTEM, content=SYSTEM_PROMPT)]
    #     print(await mcp_client.get_prompts())
    #     while True:
    #         user_input = input('=> please enter agent question => ').strip()
    #         if user_input.lower() == 'exit':
    #             break
    #         if user_input == '':
    #             continue
    #         user_message = Message(role=Role.USER, content=user_input)
    #         messages.append(user_message)
    #         ai_response = await agent_mcp.get_response(messages=messages)
    #         messages.append(ai_response)

if __name__ == "__main__":
    asyncio.run(main())
