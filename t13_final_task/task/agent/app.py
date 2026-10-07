import logging
import os
import sys
import xml.etree.ElementTree as ET
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

from t13_final_task.task.agent.clients.http_mcp_client import HttpMcpClient
from t13_final_task.task.agent.clients.stdio_mcp_client import StdioMcpClient
from t13_final_task.task.agent.conversation_manager import ConversationManager
from t13_final_task.task.agent.tools.base import BaseTool
from t13_final_task.task.agent.tools.mcp_tool import McpTool
from t13_final_task.task.agent.tools.read_skill_tool import ReadSkillTool
from t13_final_task.task.agent.ums_agent import UMSAgent
from t13_final_task.task.agent.models import SkillMetadata, load_skills, Message

from commons.constants import OPENAI_API_KEY

SKILLS_DIR = Path(__file__).parent.parent / "_skills"


def _build_available_skills_xml(skills: list[SkillMetadata]) -> str:
    #TODO:
    # Build and return an XML string with root element <available_skills>.
    # For each skill add a <skill name="..."> element with child elements:
    #   - <description> (always)
    #   - <license> (if present)
    #   - <compatibility> (if present)
    #   - <metadata> with a dynamic child element per key/value pair (if present)
    #   - <allowed-tools> as a space-joined string (if present)
    root = ET.Element("available_skills")
    
    for skill in skills:
        skill_elem = ET.SubElement(root, "skill", name=str(skill.name))
        
        desc_elem = ET.SubElement(skill_elem, "description")
        desc_elem.text = str(skill.description)
        
        if getattr(skill, "license", None):
            license_elem = ET.SubElement(skill_elem, "license")
            license_elem.text = str(skill.license)
            
        if getattr(skill, "compatibility", None):
            compat_elem = ET.SubElement(skill_elem, "compatibility")
            compat_elem.text = str(skill.compatibility)
            
        metadata = getattr(skill, "metadata", None)

        if metadata:
            meta_elem = ET.SubElement(skill_elem, "metadata")

            if isinstance(metadata, dict):
                for k, v in metadata.items():
                    child_elem = ET.SubElement(meta_elem, str(k))
                    child_elem.text = str(v)
            elif isinstance(metadata, list):
                for item in metadata:
                    if len(item) == 2:
                        k, v = item
                        child_elem = ET.SubElement(meta_elem, str(k))
                        child_elem.text = str(v)

        allowed_tools = getattr(skill, "allowed_tools", None)

        if allowed_tools:
            tools_elem = ET.SubElement(skill_elem, "allowed-tools")

            if isinstance(allowed_tools, (list, tuple, set)):
                tools_elem.text = " ".join(str(t) for t in allowed_tools)
            else:
                tools_elem.text = str(allowed_tools)

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")


def build_system_prompt(skills: list[SkillMetadata]) -> str:
    #TODO:
    # Build and return the system prompt string that:
    #   - Describes the assistant as an AI with access to agent skills
    #   - Embeds the XML from _build_available_skills_xml(skills)
    #   - Explains how to use skills:
    #       1. Call `read_skill` with path="/<skill-name>/SKILL.md" to load instructions
    #       2. Follow the loaded SKILL.md precisely
    # Generate the XML string for the available skills
    skills_xml = _build_available_skills_xml(skills)

    system_prompt = f"""You are an advanced AI assistant equipped with specialized agent skills.
    ## Available Skills
    Below is the list of available skills you can utilize:

    {skills_xml}

    ## How to Use Skills
    When a task matches or requires a specific skill listed above:
    1. **Load Instructions:** Call the `read_skill` 
        tool with the path format `/<skill-name>/SKILL.md` 
        (e.g., `read_skill(path="/web-search-skill/SKILL.md")`) to fetch its detailed instruction set.
    2. **Execute:** Follow the guidelines, constraints, and operational steps specified in the loaded `SKILL.md` precisely.
    """

    return system_prompt.strip()


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

conversation_manager: Optional[ConversationManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize MCP clients, Redis, and ConversationManager on startup"""
    global conversation_manager

    #TODO:
    # Startup:
    # 1. Load skills from SKILLS_DIR with load_skills(), build system_prompt with build_system_prompt()
    # 2. Create tools list starting with ReadSkillTool(skills_dir=SKILLS_DIR)
    # 3. Init HttpMcpClient via HttpMcpClient.create() using http://localhost:8005/mcp URL, get its tools and append each as McpTool
    # 4. Init StdioMcpClient with docker_image: "khshanovskyi/ddg-mcp-server:latest" get its tools and append each as McpTool
    # 5. Create UMSAgent
    # 6. Create redis.Redis client and ping it
    # 7. Create ConversationManager
    #    and assign to global conversation_manager
    skills = load_skills(SKILLS_DIR)
    system_promt = build_system_prompt(skills)
    tools = [ReadSkillTool(skills_dir=SKILLS_DIR)]

    httpMcpClient = await HttpMcpClient.create("http://localhost:8005/mcp")
    client_tools = await httpMcpClient.get_tools()
    tools.extend(McpTool(httpMcpClient, t) for t in client_tools)

    stdio_client  = await StdioMcpClient.create(docker_image="khshanovskyi/ddg-mcp-server:latest")
    stdio_tools = await stdio_client.get_tools()
    tools.extend(McpTool(stdio_client, t) for t in stdio_tools)

    ums_agent = UMSAgent(
        api_key=OPENAI_API_KEY,
         model="gpt-5.2-2025-12-11",
         tools=tools
    )

    redis_client = redis.Redis()
    await redis_client.ping()

    conversation_manager = ConversationManager(
        ums_agent=ums_agent, 
        redis_client=redis_client, 
        system_prompt=system_promt
    )

    yield

    #TODO: shutdown — close redis_client
    await redis_client.aclose()


app = FastAPI(
    #TODO: add `lifespan` param from above
    lifespan=lifespan
)

app.add_middleware(
    #TODO:
    # Since we will run it locally there will be some issues from FrontEnd side with CORS, and its okay for local setup to disable them:
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# Request/Response Models
class ChatRequest(BaseModel):
    message: Message
    stream: bool = True


class ChatResponse(BaseModel):
    content: str
    conversation_id: str


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class CreateConversationRequest(BaseModel):
    title: str = None


# Endpoints
@app.get("/health")
async def health():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "conversation_manager_initialized": conversation_manager is not None
    }

#TODO:
# Create such endpoints:
# 1. POST: "/conversations". Applies CreateConversationRequest and creates new conversation with ConversationManager.
# 2. GET: "/conversations" Extracts all conversation from storage. Returns list of ConversationSummary objects
# 3. GET: "/conversations/{conversation_id}". Applies conversation_id string and extracts from storage full conversation
# 4. DELETE: "/conversations/{conversation_id}". Applies conversation_id string and deletes conversation. Returns dict
#    with message with info if conversation has been deleted
# 5. POST: "/conversations/{conversation_id}/chat". Chat endpoint that processes messages and returns assistant response.
#    Supports both streaming and non-streaming modes.
#    Applies conversation_id and ChatRequest.
#    If `request.stream` then return `StreamingResponse(result, media_type="text/event-stream")`, otherwise return `ChatResponse(**result)`
@app.post("/conversations")
async def create_conversations(request: CreateConversationRequest):
    if conversation_manager is None:
        raise HTTPException(status_code=503, detail="Service unavailable")
    conversation = await conversation_manager.create_conversation(request.title)
    return conversation

@app.get("/conversations")
async def list_conversations():
    result = await conversation_manager.list_conversations()
    return result


@app.get("/conversations/{conversation_id}")
async def get_conversations_by_id(conversation_id: str):
    full_conversation = await conversation_manager.get_conversation(conversation_id=conversation_id)
    return full_conversation

@app.delete("/conversations/{conversation_id}")
async def delete_conversation_by_id(conversation_id: str):
    is_delete = await conversation_manager.delete_conversation(conversation_id=conversation_id)

    if is_delete:
        return {"message": "Successfully deleted"}
    else:
        return {"message": "hos not deleted"}

@app.post("/conversations/{conversation_id}/chat")
async def conversation_chat(conversation_id: str, request: ChatRequest):
    user_message = request.message
    response  = await conversation_manager.chat(
        conversation_id=conversation_id,
        user_message=user_message,
        stream=request.stream
    )
    if request.stream:
        return StreamingResponse(response, media_type="text/event-stream")
    else:
        return ChatResponse(**response)


if __name__ == "__main__":
    import uvicorn
    # import asyncio
    logger.info("Starting uvicorn server")
    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.run(
        #TODO:
         app,
         host="0.0.0.0",
         port=8011,
         log_level="debug"
    )