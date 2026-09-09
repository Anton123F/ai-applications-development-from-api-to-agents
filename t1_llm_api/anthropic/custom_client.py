import json
import aiohttp
import requests

from commons.models.message import Message
from commons.models.role import Role
from t1_llm_api.base_client import AIClient


class CustomAnthropicAIClient(AIClient):
    """
    Custom HTTP client for Anthropic's Claude API.

    This implementation uses raw HTTP requests (requests/aiohttp) instead of
    the official SDK, demonstrating how to interact with Claude's API directly
    and handle its Server-Sent Events (SSE) streaming format.
    """

    def response(self, messages: list[Message], **kwargs) -> Message:
        """
        Get a synchronous response using raw HTTP POST request.

        Args:
            messages (list[Message]): The conversation history.
            **kwargs: Additional parameters like max_tokens (default: 1024).

        Returns:
            Message: The AI's response message.

        Raises:
            ValueError: If the API response contains no content blocks.
            Exception: If the HTTP request fails (non-200 status code).

        Note:
            Requires 'x-api-key' header and 'anthropic-version' header.
            Claude's API returns content as an array of content blocks.
            The response is printed to stdout before being returned.
        """
        #TODO:
        # https://docs.anthropic.com/en/api/messages-examples
        # - Prepare headers with api key, anthropic version and content type
        # - Add System prompt
        # - Execute post request to AI API (use `requests`)
        # - Parse response
        # - Print response to console
        # - Return ASSISTANT message
        kwargs.setdefault("max_tokens", 1024)
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        all_messages = [{"role": m.role, "content": m.content} for m in messages]

        payload = {
            "model": self.model_name,
            "system": self.system_prompt,
            "messages": all_messages,
            **kwargs
        }
        response = requests.post(self.endpoint, headers=headers, json=payload)
        if response.status_code != 200:
            raise Exception(f"Anthropic API request failed with status code {response.status_code}: {response.text}")

        response_data = response.json()
        content_blocks = response_data.get("content", [])

        if not content_blocks:
            raise ValueError("The API response contains no content blocks.")

        assistant_text = "".join(
            block.get("text", "") for block in content_blocks if block.get("type") == "text"
        )

        if not assistant_text:
            assistant_text = "".join(block.get("text", "") for block in content_blocks)

        print(assistant_text)
        return Message(role="assistant", content=assistant_text)
        

    async def stream_response(self, messages: list[Message], **kwargs) -> Message:
        """
        Get a streaming response using raw HTTP with Server-Sent Events (SSE).

        The response is streamed using Anthropic's SSE format, with text deltas
        printed immediately as they arrive.

        Args:
            messages (list[Message]): The conversation history.
            **kwargs: Additional parameters like max_tokens (default: 1024).

        Returns:
            Message: The complete AI response message after all deltas are received.

        Note:
            Uses Server-Sent Events (SSE) format where each line starts with "data: ".
            Listens for 'content_block_delta' events with 'text_delta' type.
            Stops processing when 'message_stop' event is received.
            Each delta is printed to stdout as it arrives.
        """
        #TODO:
        # https://docs.anthropic.com/en/docs/build-with-claude/streaming
        # - Prepare headers with api key, anthropic version and content type
        # - Add System prompt
        # - Execute post request to AI API (use `aihttp`)
        # - Handle stream with chunks
        # - Parse response
        # - Print chunks to console
        # - Return ASSISTANT message
        kwargs.setdefault("max_tokens", 1024)
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "accept": "text/event-stream"
        }

        all_messages = [{"role": m.role, "content": m.content} for m in messages]

        payload = {
            "model": self.model_name,
            "system": self.system_prompt,
            "messages": all_messages,
            "stream": True,
            **kwargs
        }

        full_response_text = ""

        async with aiohttp.ClientSession() as session:
            async with session.post(self.endpoint, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Anthropic API streaming request failed with status code {response.status}: {error_text}")

                async for line_bytes in response.content:
                    line = line_bytes.decode("utf-8").strip()

                    if line.startswith("data: "):
                        data_str = line[len("data: "):].strip()
                        
                        try:
                            event_data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        event_type = event_data.get("type")

                        if event_type == "content_block_delta":
                            delta = event_data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text_chunk = delta.get("text", "")
                                print(text_chunk, end="", flush=True)
                                full_response_text += text_chunk

                        elif event_type == "message_stop":
                            break
        return Message(role="assistant", content=full_response_text)

