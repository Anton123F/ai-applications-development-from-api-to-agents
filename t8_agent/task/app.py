from commons.constants import OPENAI_API_KEY, ANTHROPIC_API_KEY
from commons.models.conversation import Conversation
from commons.models.message import Message
from commons.models.role import Role
from commons.user_service.client import UserServiceClient

from t8_agent.task.agents.anthropic import AnthropicBasedAgent
from t8_agent.task.agents.openai import OpenAIBasedAgent
from t8_agent.task.prompts import SYSTEM_PROMPT
from t8_agent.task.tools.users.create_user_tool import CreateUserTool
from t8_agent.task.tools.users.delete_user_tool import DeleteUserTool
from t8_agent.task.tools.users.get_user_by_id_tool import GetUserByIdTool
from t8_agent.task.tools.users.search_users_tool import SearchUsersTool
from t8_agent.task.tools.users.update_user_tool import UpdateUserTool
from t8_agent.task.tools.web_search import WebSearchTool


def main():
    #TODO:
    # 1. Create UserClient
    # 2. Create list with all tools (WebSearchTool, GetUserByIdTool, SearchUsersTool, CreateUserTool, UpdateUserTool, DeleteUserTool)
    # 3. Create OpenAIBasedAgent with all tools (or AnthropicBasedAgent)
    # 4. Create Conversation
    # 5. Run infinite loop and in loop and:
    #    - get user input from terminal (`input("> ").strip()`)
    #    - Add User message to Conversation
    #    - Call OpenAIClient with conversation history
    #    - Add Assistant message to Conversation and print its content
    user_client = UserServiceClient()
    tools = [
        CreateUserTool(user_client), 
        DeleteUserTool(user_client), 
        GetUserByIdTool(user_client), 
        SearchUsersTool(user_client), 
        UpdateUserTool(user_client),
        WebSearchTool(OPENAI_API_KEY)
    ]

    openai_agent = OpenAIBasedAgent(
        model="gpt-5.2-2025-12-11",
        tools=tools,
        api_key=OPENAI_API_KEY,
        system_prompt=SYSTEM_PROMPT,
    )
    conversation = Conversation()

    while True:
        user_input = input("> ").strip()
        if user_input.lower() == 'exit':
            print("Exiting the chat session.")
            break
        if not user_input:
            continue

        conversation.add_message(Message(role=Role.USER, content=user_input))

        try:
            response = openai_agent.get_response(conversation.get_messages())
            conversation.add_message(response)
            print(response.content)
        except Exception as e:
            print(f"Error: {e}")
            continue


main()
