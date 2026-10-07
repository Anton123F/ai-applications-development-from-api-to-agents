import json
import logging
from collections import defaultdict
from typing import AsyncGenerator

from openai import AsyncOpenAI

from t13_final_task.task.agent.models import Message
from t13_final_task.task.agent.models import Role
from t13_final_task.task.agent.guardrail import UMSDataGuardrail
from t13_final_task.task.agent.tools.base import BaseTool

from openai import AzureOpenAI, AsyncAzureOpenAI
from commons.constants import OPENAI_CHAT_COMPLETIONS_ENDPOINT, OPENAI_API_KEY, DEFAULT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class UMSAgent:
    """Handles AI model interactions and integrates with MCP client"""

    def __init__(
            self,
            api_key: str,
            model: str,
            tools: list[BaseTool]
    ):
        #TODO:
        # - Store tools as dict `tool.name: tool`
        # - Store tools schemas list
        # - Store model
        # - Init AsyncOpenAI
        # - Init UMSDataGuardrail
        self.tools = {tool.name: tool for tool in tools}
        self.tools_schema  = [tool.schema for tool in tools]
        self.model = model

        self.async_openai = AsyncAzureOpenAI(
            # api_key=OPENAI_API_KEY, 
            api_key=api_key, 
            api_version="2025-04-01-preview", 
            azure_endpoint=OPENAI_CHAT_COMPLETIONS_ENDPOINT,
        )

        #uncomment later 
        self.ums_guardrail_client = UMSDataGuardrail()

    async def response(self, messages: list[Message]) -> Message:
        """Non-streaming completion with tool calling support"""
        #TODO:
        # 1. Build request_data: model, messages (each .to_dict()), tools schemas, stream=False
        # 2. Call async_openai chat completions with request_data
        # 3. Build ai_message (Role.ASSISTANT) from response content
        # 4. If response has tool_calls, assign them to ai_message.tool_calls
        # 5. If ai_message has tool_calls: append ai_message to messages, call _call_tools(),
        #    then make recursive call
        # 6. Return ai_message
        request_data = {
            "model": self.model,
            "messages": [ms.to_dict() for ms in messages],
            "tools": self.tools_schema,
            "stream": False
        }

        response = await self.async_openai.chat.completions.create(**request_data)
        choice_message = response.choices[0].message
        ai_mesasges = Message(role=Role.ASSISTANT, content=choice_message.content)

        if choice_message.tool_calls:
            ai_mesasges.tool_calls = choice_message.tool_calls
        if ai_mesasges.tool_calls:
            messages.append(ai_mesasges)
            await self._call_tools(ai_message=ai_mesasges, messages=messages)
            return await self.response(messages)
        return ai_mesasges


    async def stream_response(self, messages: list[Message]) -> AsyncGenerator[str, None]:
        """
        Streaming completion with tool calling support.
        Yields SSE-formatted chunks.
        """
        #TODO:
        # 1. Build request_data: model, messages (each .to_dict()), tools schemas, stream=True
        # 2. Stream via async_openai chat completions; buffer content and tool_deltas per chunk
        # 3. If tool_deltas after stream:
        #    - Collect tool_calls via _collect_tool_calls(), build ai_message, append to messages
        #    - Notify frontend about each tool call (type: "call") and result (type: "result") via SSE
        #    - Recursively yield from self.stream_response(messages), then return
        # 4. If no tool calls: append final assistant message
        # 5. Yield final SSE chunk with finish_reason="stop", then yield "data: [DONE]\n\n"
        stream_response = {
            "model": self.model,
            "messages": [ms.to_dict() for ms in messages],
            "tools": self.tools_schema,
            "stream": True
        }
        stream = await self.async_openai.chat.completions.create(**stream_response)
        full_content = []
        tool_deltas = []

        async for chunk in stream:
            delta = chunk.choices[0].delta

            if delta.content is not None:
                print(delta.content, end="", flush=True)

                yield f"data: {json.dumps({'type': 'content', 'delta': delta.content})}\n\n"

                full_content.append(delta.content)

            if delta.tool_calls:
                tool_deltas.extend(delta.tool_calls)
        
        tool_calls = self._collect_tool_calls(tool_deltas)

        if tool_calls:
            ai_messages = Message(role=Role.ASSISTANT, content=None)
            messages.append(ai_messages)
            ai_messages.tool_calls = tool_calls

            yield f"data: {json.dumps({'type': 'call'})}\n\n"
            await self._call_tools(ai_message=ai_messages, messages=messages)
            yield f"data: {json.dumps({'type': 'result'})}\n\n"


            async for chunk in self.stream_response(messages):
                yield chunk
            return
        else:
            ai_message = Message(role=Role.ASSISTANT, content="".join(full_content))
            messages.append(ai_message)

            yield f"data: {json.dumps({'type': 'done', 'finish_reason': 'stop'})}\n\n"
            yield "data: [DONE]\n\n"

    def _collect_tool_calls(self, tool_deltas):
        """Convert streaming tool call deltas to complete tool calls"""
        #TODO:
        # 1. Use defaultdict keyed by delta.index; each entry has shape:
        #    {"id": None, "function": {"arguments": "", "name": None}, "type": None}
        # 2. For each delta: accumulate id, function.name, function.arguments (concatenate), type
        # 3. Return list(tool_dict.values())
    
        tool_dict = defaultdict(lambda: {
            "id": None, 
            "function": {"arguments": "", "name": None}, 
            "type": None
        })
        
        for delta in tool_deltas:
            index = delta.index
            
            if delta.id:
                if tool_dict[index]["id"] is None:
                    tool_dict[index]["id"] = delta.id
                else:
                    tool_dict[index]["id"] += delta.id
                
            if delta.type:
                tool_dict[index]["type"] = delta.type
                
            if delta.function:
                if delta.function.name:
                    tool_dict[index]["function"]["name"] = delta.function.name
                if delta.function.arguments:
                    tool_dict[index]["function"]["arguments"] += delta.function.arguments

        return list(tool_dict.values())


    async def _call_tools(self, ai_message: Message, messages: list[Message], silent: bool = False):
        """Execute tool calls using MCP client"""
        #TODO:
        # Iterate through tool_calls:
        #   - Extract tool_name and arguments
        #   - If tool found in self.tools:
        #       - Execute tool call
        #       - Append tool message to messages
        #   - If tool not found: append a Tool Message error content and dont forget about tool_call_id
        for tool in ai_message.tool_calls:
            tool_call_id = tool["id"]
            tool_name = tool["function"]["name"]
            
            try:
                tool_arguments = json.loads(tool["function"]["arguments"])
            except Exception as e:
                tool_arguments = {}
                
            if tool_name in self.tools:
                try:
                    result_tool_message = await self.tools[tool_name].execute(tool_call_id=tool_call_id, arguments=tool_arguments)

                    if result_tool_message.content:
                        redact_result_context = self.ums_guardrail_client.redact(result_tool_message.content)
                        result_tool_message.content = redact_result_context

                    messages.append(result_tool_message)
                except Exception as e:
                    messages.append(Message(
                        role=Role.TOOL, 
                        content=f"Error executing tool {tool_name}: {str(e)}", 
                        tool_call_id=tool_call_id
                    ))
            else:
                messages.append(Message(
                    role=Role.TOOL, 
                    content=f"Error: Tool '{tool_name}' not found.", 
                    tool_call_id=tool_call_id
                ))

        #TODO 2:
        # Implement it ONLY after you started the app
        # Make PII filtering for tool call result