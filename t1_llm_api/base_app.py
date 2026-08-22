from commons.models.conversation import Conversation
from commons.models.message import Message
from commons.models.role import Role
from t1_llm_api.base_client import AIClient


async def start(stream: bool, client: AIClient) -> None:
    """
    Start an interactive chat session with an AI client.

    This function runs a continuous loop that:
    1. Prompts the user for input
    2. Sends the conversation history to the AI
    3. Displays the AI's response
    4. Maintains conversation context

    The loop continues until the user types 'exit'.

    Args:
        stream (bool): If True, use streaming responses (real-time token display).
                      If False, use synchronous responses (complete response at once).
        client (AIClient): The AI client instance to use for generating responses.
    """

    user_conversation = Conversation()

    while True:
        user_input = input("Hello! Print something that you want to ask.\nType 'exit' to quit:\n")
        if user_input.lower() == 'exit':
            print("Exiting the chat session.")
            break
        user_message = Message(role=Role.USER, content=user_input)
        user_conversation.add_message(user_message)

        if stream:
            client_response: Message = await client.stream_response(user_conversation.get_messages())
        else:
            client_response: Message = client.response(user_conversation.get_messages())
            print(f"AI: {client_response.content}")

        user_conversation.add_message(client_response)
