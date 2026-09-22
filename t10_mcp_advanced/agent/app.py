import asyncio
import json
import os

from commons.constants import OPENAI_API_KEY

from commons.models.message import Message
from commons.models.role import Role
from t10_mcp_advanced.agent.agent import CustomAgentMCP
from t10_mcp_advanced.agent.clients.custom_mcp_client import CustomMCPClient
from t10_mcp_advanced.agent.clients.mcp_client import MCPClient
from commons.models.conversation import Conversation


async def main():
    #TODO:
    # 1. Take a look what applies CustomAgentMCP
    # 2. Create empty list where you save tools from MCP Servers later
    # 3. Create empty dict where where key is str (tool name) and value is instance of MCPClient or CustomMCPClient
    # 4. Create UMS MCPClient, url is `http://localhost:8006/mcp` (use static method create and don't forget that its async)
    # 5. Collect tools and dict [tool name, mcp client]
    # 6. Do steps 4 and 5 for `https://remote.mcpservers.org/fetch/mcp`
    # 7. Create CustomAgentMCP
    # 8. Create array with Messages and add there System message with simple instructions for LLM that it should help to handle user request
    # 9. Create simple console chat (as we done in previous tasks)
    tools = []
    my_dict: dict[str, MCPClient | CustomMCPClient] = {}
    # ums = await MCPClient.create(mcp_server_url="http://localhost:8006/mcp")
    ums = await CustomMCPClient.create(mcp_server_url="http://localhost:8006/mcp")
    tools = await ums.get_tools()

    for tool in tools:
        my_dict[tool['function']['name']] = ums

    ums = await MCPClient.create(mcp_server_url="https://remote.mcpservers.org/fetch/mcp")
    # ums = await MCPClient.create(mcp_server_url="https://fetch.mcp.so/mcp")
    fetch_tools = await ums.get_tools()
    tools.extend(fetch_tools)

    for tool in fetch_tools:
        my_dict[tool['function']['name']] = ums
    
    client = CustomAgentMCP(
        api_key=OPENAI_API_KEY,
        model="gpt-5.2-2025-12-11",
        tools=tools,
        tool_name_client_map=my_dict
    )

    user_conversation = Conversation()

    system_message = Message(role=Role.SYSTEM, content="you an agent that should help user handle it's request")
    user_conversation.add_message(system_message)
    
    try:
        while True:
            user_input = input("Hello! Print something that you want to ask.\nType 'exit' to quit:\n")
            if user_input.lower() == 'exit':
                print("Exiting the chat session.")
                
                break
            user_message = Message(role=Role.USER, content=user_input)
            user_conversation.add_message(user_message)

            client_response: Message = await client.get_completion(user_conversation.get_messages())
            print(f"AI: {client_response.content}")

            user_conversation.add_message(client_response)
    finally:
        await ums.disconnect()






if __name__ == "__main__":
    asyncio.run(main())


# Check if Arkadiy Dobkin present as a user, if not then search info about him in the web and add him