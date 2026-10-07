import json
import logging

from uuid import uuid5, uuid4
from datetime import datetime, UTC
from typing import Optional, AsyncGenerator

import redis.asyncio as redis

from t13_final_task.task.agent.models import Message
from t13_final_task.task.agent.models import Role
from t13_final_task.task.agent.ums_agent import UMSAgent

from typing import TypedDict, List, Any

logger = logging.getLogger(__name__)

_CONVERSATION_PREFIX = "conversation:"
_CONVERSATION_LIST_KEY = "conversations:list"

class Conversation(TypedDict):
    id: str
    title: str
    messages: List[Any]
    created_at: str
    updated_at: str


class ConversationManager:
    """Manages conversation lifecycle including AI interactions and persistence"""

    def __init__(self, ums_agent: UMSAgent, redis_client: redis.Redis, system_prompt: str):
        self.ums_agent = ums_agent
        self.redis = redis_client
        self._system_prompt = system_prompt
        logger.info("ConversationManager initialized")

    async def create_conversation(self, title: str) -> dict:
        """Create a new conversation"""
        #TODO:
        # - Build conversation dict: id (uuid4), title, messages=[], created_at, updated_at (UTC ISO)
        # - Persist to Redis: set by key, zadd to sorted list with timestamp score
        # - Return conversation dict
        now = datetime.now(UTC)
        timestamp = now.timestamp()

        conversation: Conversation = {
            "id": str(uuid4()),
            "title": title,
            "messages": [],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }

        await self.redis.set(f"{_CONVERSATION_PREFIX}{conversation['id']}", json.dumps(conversation))
        await self.redis.zadd(_CONVERSATION_LIST_KEY, {conversation["id"]: timestamp})

        return conversation


    async def list_conversations(self) -> list[dict]:
        """List all conversations sorted by last update time"""
        #TODO:
        # - Get all conversation ids via zrevrange on _CONVERSATION_LIST_KEY
        # - For each id fetch from Redis, parse, append summary dict (id, title, created_at, updated_at, message_count)
        # - Return list of summaries
        conversation_list = []
        ids = await self.redis.zrevrange(name=_CONVERSATION_LIST_KEY, start=0, end=-1)

        for id in ids:
            conversation_id = f"{_CONVERSATION_PREFIX}{id}"
            raw = await self.redis.get(conversation_id)
            
            if raw is None:
                continue

            converations_body: Conversation  = json.loads(raw)
            conversation_list.append({
                "id": converations_body["id"],
                "title": converations_body["title"],
                "created_at": converations_body["created_at"],
                "updated_at": converations_body["updated_at"],
                "message_count": len(converations_body["messages"])
            })

        return conversation_list

    async def get_conversation(self, conversation_id: str) -> Optional[dict]:
        """Get a specific conversation"""
        #TODO:
        # - Get from Redis by key, return None if missing
        # - Return parsed conversation dict
        conversation  = await self.redis.get(f"{_CONVERSATION_PREFIX}{conversation_id}")
        if conversation is None:
            return None
        return json.loads(conversation)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        #TODO:
        # - Delete from Redis by key; return False if not found (deleted == 0)
        # - Remove from sorted list via zrem
        # - Return True
        prefix_conversation_id = f"{_CONVERSATION_PREFIX}{conversation_id}"
        result = await self.redis.delete(prefix_conversation_id)

        if result == 0:
            return False

        await self.redis.zrem(_CONVERSATION_LIST_KEY, conversation_id)
        return True

    async def chat(
            self,
            user_message: Message,
            conversation_id: str,
            stream: bool = False
    ):
        """
        Process chat messages and return AI response.
        Automatically saves conversation state.
        """

        #TODO:
        # - Load conversation via get_conversation(); raise ValueError if not found
        # - Deserialize messages; if empty inject system prompt (Role.SYSTEM) first
        # - Append user_message
        # - If stream: return self._stream_chat(...), else return await self._non_stream_chat(...)
        conversation:Conversation = await self.get_conversation(conversation_id)

        if not conversation:
            raise ValueError(f"Conversation not found")

        messages = [
            Message(
                role=m["role"],
                content=m["content"],
                tool_call_id=m.get("tool_call_id"),
                name=m.get("name"),
                tool_calls=m.get("tool_calls")
            )
            for m in conversation["messages"]
        ]

        if not messages:
            messages.append(Message(role=Role.SYSTEM, content=self._system_prompt))
        messages.append(user_message)

        if stream:
            return self._stream_chat(conversation_id, messages)
        else:
            return await self._non_stream_chat(conversation_id, messages)

    async def _stream_chat(
            self,
            conversation_id: str,
            messages: list[Message],
    ) -> AsyncGenerator[str, None]:
        """Handle streaming chat with automatic saving"""
        #TODO:
        # - Yield conversation_id as first SSE event
        # - Yield each chunk from ums_agent.stream_response(messages)
        # - Save messages via _save_conversation_messages()
        yield conversation_id

        async for chunk in self.ums_agent.stream_response(messages):
            yield chunk

        await self._save_conversation_messages(conversation_id, messages)


    async def _non_stream_chat(
            self,
            conversation_id: str,
            messages: list[Message],
    ) -> dict:
        """Handle non-streaming chat"""
        #TODO:
        # - Get ai_message via ums_agent.response(messages)
        # - Save messages via _save_conversation_messages()
        # - Return dict with content and conversation_id
        ai_message = await self.ums_agent.response(messages)
        messages.append(ai_message)
        await self._save_conversation_messages(conversation_id, messages)

        return {"conversation_id": conversation_id, "content": ai_message.content}


    async def _save_conversation_messages(
            self,
            conversation_id: str,
            messages: list[Message]
    ):
        """Save or update conversation messages"""
        #TODO:
        # - Fetch existing conversation from Redis, update messages (to_dict) and updated_at
        # - Persist via _save_conversation()
        full_key = f"{_CONVERSATION_PREFIX}{conversation_id}"
        conversation:Conversation = json.loads(await self.redis.get(full_key))
        conversation["messages"] = [message.to_dict() for message in messages]
        conversation["updated_at"] = datetime.now(UTC).isoformat()
        await self._save_conversation(conversation)


    async def _save_conversation(self, conversation: dict):
        """Internal method to persist conversation to Redis"""
        #TODO:
        # - redis.set conversation by key (json.dumps)
        # - redis.zadd to sorted list with current timestamp score
        
        await self.redis.set(f"{_CONVERSATION_PREFIX}{conversation['id']}", json.dumps(conversation))

        now = datetime.now(UTC)
        timestamp = now.timestamp()

        await self.redis.zadd(_CONVERSATION_LIST_KEY, {conversation["id"]: timestamp})    