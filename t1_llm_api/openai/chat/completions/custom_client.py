import json
import aiohttp
import requests

from commons.models.message import Message
from commons.models.role import Role
from t1_llm_api.openai.base import BaseOpenAIClient


class CustomOpenAIClient(BaseOpenAIClient):
    """
    Custom HTTP client for OpenAI Chat Completions API.

    This implementation uses raw HTTP requests (requests/aiohttp) instead of
    the official SDK, providing more control over the HTTP layer and demonstrating
    how to interact with the API directly.
    """

    def response(self, messages: list[Message], **kwargs) -> Message:
        """
        Get a synchronous response using raw HTTP POST request.

        Args:
            messages (list[Message]): The conversation history.
            **kwargs: Additional parameters for the API (currently unused).

        Returns:
            Message: The AI's response message.

        Raises:
            ValueError: If the API response contains no choices.
            Exception: If the HTTP request fails (non-200 status code).

        Note:
            The system prompt is automatically prepended to the messages.
            The response is printed to stdout before being returned.
        """
        #TODO:
        # https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create
        # - Prepare headers with authorization and content type
        # - Prepare message history with System prompt
        # - Execute post request to AI API (use `requests`)
        # - Parse response
        # - Print response to console
        # - Return ASSISTANT message
        raw_end_point = f"{self._endpoint}/openai/deployments/{self._model_name}/chat/completions?api-version=2025-04-01-preview"
        custom_headers = {
            "Content-Type": "application/json",
            "api-key": self._api_key.replace("Bearer ", "")
        }
        all_messages = [{"role": "system", "content": self._system_prompt}] + [m.to_dict() for m in messages]
        data = {
            "model": self._model_name, 
            "messages": all_messages
        }

        raw_response = requests.post(url=raw_end_point, json=data, headers=custom_headers)

        if raw_response.status_code != 200:
            raise Exception(f"HTTP request failed with status code {raw_response.status_code} {raw_response.text}")

        response = raw_response.json()
        
        if not response.get('choices'):
            raise ValueError("API response contains no choices.")

        raw_message = response.get('choices')[0]["message"]["content"]
        return Message(role=Role.ASSISTANT, content=raw_message)

    async def stream_response(self, messages: list[Message], **kwargs) -> Message:
        """
        Get a streaming response using raw HTTP with Server-Sent Events (SSE).

        The response is streamed token-by-token using OpenAI's SSE format,
        with each chunk printed immediately as it arrives.

        Args:
            messages (list[Message]): The conversation history.
            **kwargs: Additional parameters for the API (currently unused).

        Returns:
            Message: The complete AI response message after all chunks are received.

        Note:
            The system prompt is automatically prepended to the messages.
            Each token is printed to stdout as it arrives.
            Uses Server-Sent Events (SSE) format where each line starts with "data: ".
        """
        #TODO:
        # https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create (Streaming tab)
        # - Prepare headers with authorization and content type
        # - Prepare message history with System prompt
        # - Execute post request to AI API (use `aihttp`)
        # - Handle stream with chunks
        # - Parse response
        # - Print chunks to console
        # - Return ASSISTANT message
        raw_end_point = f"{self._endpoint}/openai/deployments/{self._model_name}/chat/completions?api-version=2025-04-01-preview"
        custom_headers = {
            "Content-Type": "application/json",
            "api-key": self._api_key.replace("Bearer ", "")
        }
        all_messages = [{"role": "system", "content": self._system_prompt}] + [m.to_dict() for m in messages]
        data = {
            "model": self._model_name, 
            "messages": all_messages,
            "stream": True
        }

        assistant_content = ""
        async with aiohttp.ClientSession() as session:
            async with session.post(raw_end_point, json=data, headers=custom_headers) as response:
                if response.status != 200:
                    raise Exception(f"HTTP request failed with status {response.status}: {await response.text()}")
                async for line_bytes in response.content:
                    line = line_bytes.decode().strip()
                    if not line:
                        continue
                    if not line.startswith("data: "):
                        continue
                    line = line[len("data: "):]
                    if line == "[DONE]":
                        break
                    try:
                        chunk = json.loads(line)
                        content = chunk["choices"][0]["delta"].get("content", "") or ""
                        print(content, end="", flush=True)
                        assistant_content += content
                    except Exception as e:
                        print(f"\nError parsing line: {e}")
        return Message(role=Role.ASSISTANT, content=assistant_content)
