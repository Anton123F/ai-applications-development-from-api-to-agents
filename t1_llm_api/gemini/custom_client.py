import json
import aiohttp
import requests

from commons.models.message import Message
from commons.models.role import Role
from t1_llm_api.base_client import AIClient


class CustomGeminiAIClient(AIClient):
    """
    Custom HTTP client for Google Gemini API.

    This implementation uses raw HTTP requests (requests/aiohttp) instead of
    the official SDK, demonstrating how to interact with Gemini's API directly
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
            ValueError: If the API response contains no candidates.
            Exception: If the HTTP request fails (non-200 status code).

        Note:
            The URL is constructed by appending ':generateContent' to the model endpoint.
            Uses 'x-goog-api-key' header for authentication.
            Response candidates contain content parts that are concatenated.
        """
        #TODO:
        # https://ai.google.dev/gemini-api/docs/text-generation
        # - Prepare headers with api key and content type
        # - Add System prompt
        # - Execute post request to AI API (use `requests`)
        # - Parse response
        # - Print response to console
        # - Return ASSISTANT message
        headers = {
            "x-goog-api-key": self._api_key,
            "Content-Type": "application/json",
        }

        contents = []
        for msg in messages:
            if msg.role == Role.SYSTEM:
                continue
            role = "model" if msg.role in (Role.ASSISTANT, Role.MODEL) else "user"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

        body = {
            "contents": contents,
            "system_instruction": {"parts": [{"text": self._system_prompt}]},
            "generationConfig": {"maxOutputTokens": kwargs.get("max_tokens", 1024)},
        }

        url = f"{self._endpoint}/{self._model_name}:generateContent"
        resp = requests.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            raise Exception(f"HTTP {resp.status_code}: {resp.text}")

        data = resp.json()
        candidates = data.get("candidates")
        if not candidates:
            raise ValueError("No candidates in response")

        text = "".join(
            part["text"]
            for part in candidates[0]["content"]["parts"]
            if "text" in part
        )
        return Message(role=Role.ASSISTANT, content=text)


    async def stream_response(self, messages: list[Message], **kwargs) -> Message:
        """
        Get a streaming response using raw HTTP with Server-Sent Events (SSE).

        The response is streamed using Gemini's SSE format, with text chunks
        printed immediately as they arrive.

        Args:
            messages (list[Message]): The conversation history.
            **kwargs: Additional parameters like max_tokens (default: 1024).

        Returns:
            Message: The complete AI response message after all chunks are received.

        Note:
            The URL is constructed with ':streamGenerateContent?alt=sse' endpoint.
            Uses Server-Sent Events (SSE) format where each line starts with "data: ".
            Each SSE chunk contains candidates with content parts.
            Each text chunk is printed to stdout as it arrives.
        """
        #TODO:
        # https://ai.google.dev/gemini-api/docs/text-generation
        # - Prepare headers with api key and content type
        # - Add System prompt
        # - Execute post request to AI API (use `aiohttp`)
        # - Handle stream with chunks
        # - Parse response
        # - Print chunks to console
        # - Return ASSISTANT message
        headers = {
            "x-goog-api-key": self._api_key,
            "Content-Type": "application/json",
        }

        contents = []
        for msg in messages:
            if msg.role == Role.SYSTEM:
                continue
            role = "model" if msg.role in (Role.ASSISTANT, Role.MODEL) else "user"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

        body = {
            "contents": contents,
            "system_instruction": {"parts": [{"text": self._system_prompt}]},
            "generationConfig": {"maxOutputTokens": kwargs.get("max_tokens", 1024)},
        }

        url = f"{self._endpoint}/{self._model_name}:streamGenerateContent?alt=sse"

        chunks = []
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body) as resp:
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status}: {await resp.text()}")

                async for line in resp.content:
                    line = line.decode("utf-8").strip()
                    if not line.startswith("data: "):
                        continue

                    chunk_data = json.loads(line[6:])
                    candidates = chunk_data.get("candidates")
                    if not candidates:
                        continue

                    for part in candidates[0]["content"]["parts"]:
                        if "text" in part:
                            print(part["text"], end="", flush=True)
                            chunks.append(part["text"])

        print()
        return Message(role=Role.ASSISTANT, content="".join(chunks))