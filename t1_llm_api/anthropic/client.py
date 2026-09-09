from anthropic import Anthropic, AsyncAnthropic

from commons.models.message import Message
from commons.models.role import Role
from t1_llm_api.base_client import AIClient


class AnthropicAIClient(AIClient):
    """
    Client for Anthropic's Claude API using the official SDK.

    This implementation uses the official Anthropic Python library to interact
    with Claude models, providing both synchronous and streaming response capabilities.

    Attributes:
        _client (Anthropic): Synchronous Anthropic client instance.
        _async_client (AsyncAnthropic): Asynchronous Anthropic client instance.
        Inherits all other attributes from AIClient.
    """

    def __init__(self, endpoint: str, model_name: str, api_key: str, system_prompt: str):
        """
        Initialize the Anthropic client with SDK.

        Args:
            endpoint (str): The Anthropic API endpoint (for compatibility, not used by SDK).
            model_name (str): The Claude model to use (e.g., 'claude-3-opus', 'claude-sonnet-4-5').
            api_key (str): The Anthropic API key for authentication.
            system_prompt (str): The system instruction to guide Claude's behavior.
        """
        #TODO:
        # Call to __init__ of super class
        # Add Anthropic and AsyncAnthropic clients https://github.com/anthropics/anthropic-sdk-python?tab=readme-ov-file#usage
        # (In readme you can find samples with both of these clients)
        # Useful links with request/response samples:
        #   - https://docs.anthropic.com/en/api/overview
        #   - https://docs.anthropic.com/en/api/messages
        super().__init__(endpoint=endpoint, model_name=model_name, api_key=api_key, system_prompt=system_prompt)
    
        self.model_name = model_name
        self.system_prompt = system_prompt
        
        self.client = Anthropic(api_key=api_key)
        self.async_client = AsyncAnthropic(api_key=api_key)

    def response(self, messages: list[Message], **kwargs) -> Message:
        """
        Get a synchronous response from Anthropic's Claude API.

        Args:
            messages (list[Message]): The conversation history.
            **kwargs: Additional parameters like max_tokens (default: 1024).

        Returns:
            Message: The AI's response message.

        Note:
            Claude's API uses a separate 'system' parameter for system instructions.
            Response content blocks are concatenated into a single text response.
            The response is printed to stdout before being returned.
        """
        #TODO:
        # - Add System prompt
        # - Call client
        # - Print response to console
        # - Return ASSISTANT message
        kwargs.setdefault("max_tokens", 1024)


        all_messages = [{"role": m.role, "content": m.content} for m in messages]
        response = self.client.messages.create(
            model=self.model_name,
            system=self.system_prompt,
            messages=all_messages,
            **kwargs
        )

        assistant_text = "".join(
            block.text for block in response.content if hasattr(block, "text")
        )

        print(assistant_text)
        return Message(role="assistant", content=assistant_text)

    async def stream_response(self, messages: list[Message], **kwargs) -> Message:
        """
        Get a streaming response from Anthropic's Claude API.

        The response is streamed using event-based streaming, with text deltas
        printed immediately as they arrive.

        Args:
            messages (list[Message]): The conversation history.
            **kwargs: Additional parameters like max_tokens (default: 1024).

        Returns:
            Message: The complete AI response message after all deltas are received.

        Note:
            Listens for 'content_block_delta' events with text deltas.
            Each delta is printed to stdout as it arrives for real-time display.
        """
        #TODO:
        # - Add System prompt
        # - Call client with streaming mode
        # - Handle stream with chunks
        # - Print response to console
        # - Return ASSISTANT message
        kwargs.setdefault("max_tokens", 1024)

        full_response_text = ""

        all_messages = [{"role": m.role, "content": m.content} for m in messages]

        async with self.async_client.messages.stream(
            model=self.model_name,
            system=self.system_prompt,
            messages=all_messages,
            **kwargs
        ) as stream:
            async for text in stream.text_stream:
                print(text, end="", flush=True)
                full_response_text += text

        print()
        return Message(role="assistant", content=full_response_text)
