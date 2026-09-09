import json
import aiohttp
import requests

from commons.models.message import Message
from commons.models.role import Role
from t1_llm_api.openai.base import BaseOpenAIClient


class CustomOpenAIResponsesClient(BaseOpenAIClient):
    """
    Custom HTTP client for OpenAI Responses API.

    This implementation uses raw HTTP requests (requests/aiohttp) instead of
    the official SDK, demonstrating how to interact with the Responses API directly
    and handle its unique event-based streaming format.
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
            ValueError: If the API response contains no output text.
            Exception: If the HTTP request fails (non-200 status code).

        Note:
            Uses the Responses API format with 'instructions' and 'input' parameters.
            The response is printed to stdout before being returned.
        """
        #TODO:
        # https://developers.openai.com/api/docs/guides/text?lang=curl
        # - Prepare headers with authorization and content type
        # - Prepare input messages
        # - Execute post request to AI API (use `requests`)
        # - Parse response
        # - Print response to console
        # - Return ASSISTANT message
        headers = {
            "api-key": self._api_key.replace("Bearer ", ""),
            "Content-Type": "application/json"
        }
        payload = {
            "model": self._model_name,
            "input": [{"role": msg.role, "content": msg.content} for msg in messages],
            "instructions": self._system_prompt
        }

        url = self._endpoint
        resp = requests.post(url, headers=headers, json=payload)

        if resp.status_code != 200:
            raise Exception(f"API request failed with status code {resp.status_code}: {resp.text}")
        output = resp.json()
        try:
            assistant_content = output["output"][0]["content"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ValueError("The API response contains no output text.") from e
        print(assistant_content)
        return Message(role=Role.ASSISTANT, content=assistant_content)
        

    async def stream_response(self, messages: list[Message], **kwargs) -> Message:
        """
        Get a streaming response using raw HTTP with event-based streaming.

        The Responses API uses a different SSE format than Chat Completions,
        with explicit event types and data fields.

        Args:
            messages (list[Message]): The conversation history.
            **kwargs: Additional parameters for the API (currently unused).

        Returns:
            Message: The complete AI response message after all deltas are received.

        Note:
            Uses event-based Server-Sent Events (SSE) format.
            Listens for 'response.output_text.delta' events to build the response.
            Each line with "event: " specifies the event type, followed by "data: " with the payload.
        """
        #TODO:
        # https://developers.openai.com/api/docs/guides/text?lang=curl
        # - Prepare headers with authorization and content type
        # - Prepare input messages
        # - Execute post request to AI API (use `aiohttp`)
        # - Handle stream with events
        # - Parse response
        # - Print chunks to console
        # - Return ASSISTANT message
        headers = {
            "api-key": self._api_key.replace("Bearer ", ""),
            "Content-Type": "application/json"
        }
        messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        payload = {
            "model": self._model_name,
            "input": messages,
            "instructions": self._system_prompt,
            "stream": True,
        }
        url = self._endpoint
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"HTTP request failed with status {response.status}: {await response.text()}")
                
                collected_content = []
                buffer = bytearray()
                current_event_type = ""

                async for chunk in response.content.iter_any():
                    if not chunk:
                        continue
                    buffer.extend(chunk)
                    
                    while b"\n" in buffer:
                        line_bytes, _, buffer = buffer.partition(b"\n")
                        line = line_bytes.decode("utf-8", errors="ignore").strip()

                        if not line or line.startswith(":"):
                            continue

                        if line.startswith("event: "):
                            current_event_type = line[7:].strip()
                            continue

                        if line.startswith("data: "):
                            data_str = line[6:].strip()

                            if data_str == "[DONE]":
                                break

                            try:
                                event_data = json.loads(data_str)
                                delta = ""

                                if current_event_type == "response.output_text.delta":
                                    delta = event_data.get("delta", "")

                                if delta:
                                    collected_content.append(delta)
                                    print(delta, end="", flush=True)

                            except json.JSONDecodeError:
                                continue

                full_content = "".join(collected_content)
                return Message(role=Role.ASSISTANT, content=full_content)