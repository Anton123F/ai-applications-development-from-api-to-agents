# T12 Skills System — Architecture

## How the LLM Knows About Skills (Startup)

```
_skills/
├── calculator/SKILL.md        ← YAML frontmatter: name, description, allowed_tools
├── unit-converter/SKILL.md
└── .../SKILL.md

load_skills(SKILLS_DIR)
  └─ reads each SKILL.md, parses YAML frontmatter
  └─ validates name, description
  └─ returns list[SkillMetadata]

build_system_prompt(skills)
  └─ converts skills list → XML block <available_skills>
  └─ embeds XML + usage instructions into the SYSTEM message

# Result — LLM sees this in messages[0]:
SYSTEM: "You are an AI assistant with access to agent skills.
         <available_skills>
           <skill name="calculator"><description>...</description></skill>
           <skill name="unit-converter"><description>...</description></skill>
         </available_skills>
         ## How to use skills: ..."
```

The LLM knows skills exist because they are listed **in the system prompt**, not via a database or runtime discovery.

---

## How the LLM Decides to Use a Skill (Two-Step)

```
User: "convert 100km to miles"

Step 1 — LLM matches request to skill via system prompt XML
  └─ sees <skill name="unit-converter"> matches the request
  └─ decides to call tool: read_skill(path="/unit-converter/SKILL.md")

Step 2 — ReadSkillTool executes
  └─ strips leading "/"
  └─ resolves: SKILLS_DIR / "unit-converter/SKILL.md"
  └─ returns full SKILL.md content as string

Step 3 — LLM reads the SKILL.md instructions
  └─ may call execute_code(script_path="..", code="..") if skill needs Python
  └─ PythonCodeInterpreterTool sends code to MCP server → gets result
  └─ LLM uses result to form final answer
```

---

## Message Array — Low Level Flow

```
messages = [
  Message(role=SYSTEM, content=system_prompt)   ← built at startup, contains skill XML
]

─── LOOP ───────────────────────────────────────────────────────────────────

User types: "convert 5kg to lbs"

messages.append(Message(role=USER, content="convert 5kg to lbs"))

agent.chat_completion(messages)
  └─ builds API request:
       {
         model: "gpt-5.6...",
         messages: [SYSTEM, USER],
         tools: [read_skill.schema, execute_code.schema]   ← LLM knows WHAT it can call
       }
  └─ OpenAI returns: finish_reason="tool_calls"
       choice.message.tool_calls = [{id, function: {name:"read_skill", arguments:{path:...}}}]

  └─ assistant_msg = Message(role=ASSISTANT, tool_calls=[...])
     messages.append(assistant_msg)

  └─ _dispatch_tool_calls:
       tool = self._tools["read_skill"]          ← dict lookup by name
       result = await tool.execute(id, path=...) ← reads SKILL.md from disk
       messages.append(Message(role=TOOL, tool_call_id=id, content=skill_md_content))

  └─ RECURSE: _chat_completion(messages)
       messages now = [SYSTEM, USER, ASSISTANT(tool_calls), TOOL(skill content)]
       LLM reads SKILL.md content, decides next action
       → may call execute_code(...)  → another tool round trip
       → or returns final answer

messages.append(response)   ← assistant Message with final text

─── LOOP continues ─────────────────────────────────────────────────────────
```

---

## Component Map

```
custom_app.py
├── load_skills()          → models.py          reads _skills/*/SKILL.md YAML
├── build_system_prompt()  → custom_app.py      XML of skill names/descriptions → SYSTEM msg
├── ReadSkillTool          → tools/skills/      tool: reads any file from _skills/
├── PythonCodeInterpreterTool → tools/py_interpreter/
│     └── T12MCPClient     → mcp/mcp_client.py  HTTP calls to MCP server (execute_code)
├── T12Agent               → agent.py
│     ├── _tools: dict[str, BaseTool]            name → tool instance
│     ├── _tools_schemas: list[dict]             JSON schemas sent to OpenAI tools[]
│     ├── _chat_completion()                     main loop + recursion on tool_calls
│     └── _dispatch_tool_calls()                 routes tool_call → tool.execute()
└── BaseTool               → tools/base.py
      ├── .schema property                       builds {type,function,name,desc,params}
      └── .execute()                             wraps _execute(), returns Message(TOOL)
```

---

## Key Insight: Skills Are NOT Tools

| | Tools | Skills |
|---|---|---|
| What | `read_skill`, `execute_code` | `calculator`, `unit-converter` |
| How LLM knows | JSON schema in `tools[]` array | XML in system prompt |
| How invoked | OpenAI tool_calls mechanism | LLM calls `read_skill` to load instructions |
| Lives in | Python classes (BaseTool) | Markdown files on disk (SKILL.md) |

Skills are **documentation** the LLM fetches on demand. Tools are **functions** the LLM can call.
