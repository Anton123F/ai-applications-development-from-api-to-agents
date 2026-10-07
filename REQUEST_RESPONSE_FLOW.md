# LLM Request / Response Flow

---

## 1. Simple Request — No Tools, No MCP

```
User
 │
 │  messages: [
 │    { role: "user", content: "What is the capital of France?" }
 │  ]
 ▼
LLM (OpenAI / Azure)
 │
 │  response:
 │    { role: "assistant", content: "The capital of France is Paris." }
 ▼
User sees: "The capital of France is Paris."
```

No tools involved. One round trip.

---

## 2. Request With Tool Call — No MCP (plain function)

Tool is a local Python function (e.g. ReadSkillTool).

```
User
 │
 │  messages: [
 │    { role: "user", content: "Load the UMS skill" }
 │  ]
 │  tools: [ { name: "read_skill", description: "...", parameters: {...} } ]
 ▼
LLM
 │
 │  response (tool call decision):
 │    { role: "assistant", content: null,
 │      tool_calls: [{ id: "x1", name: "read_skill", args: { path: "/ums-user-management/SKILL.md" } }] }
 ▼
Your Code (_call_tools)
 │
 │  1. Appends assistant message with tool_calls to messages
 │  2. Looks up tool by name → ReadSkillTool
 │  3. Calls ReadSkillTool._execute(args) → reads file from disk
 │  4. Appends tool result to messages:
 │     { role: "tool", tool_call_id: "x1", content: "# UMS User Management..." }
 ▼
LLM (recursive call with updated messages)
 │
 │  messages now:
 │    { role: "user",      content: "Load the UMS skill" }
 │    { role: "assistant", content: null, tool_calls: [{id: "x1", ...}] }
 │    { role: "tool",      tool_call_id: "x1", content: "# UMS User Management..." }
 │
 │  response (final):
 │    { role: "assistant", content: "Here is the UMS skill content: ..." }
 ▼
User sees final answer.
```

---

## 3. Request With Tool Call — Via MCP

Tool is remote (e.g. UMS MCP Server or DuckDuckGo MCP Server).
McpTool wraps the call — same flow as above but execution goes over HTTP.

```
User
 │
 │  messages: [
 │    { role: "user", content: "Find user John Smith" }
 │  ]
 │  tools: [ { name: "search_user", description: "...", parameters: {...} } ]
 ▼
LLM
 │
 │  response (tool call decision):
 │    { role: "assistant", content: null,
 │      tool_calls: [{ id: "x2", name: "search_user",
 │                     args: { search_user_request: { name: "John", surname: "Smith" } } }] }
 ▼
Your Code (_call_tools)
 │
 │  1. Appends assistant message with tool_calls to messages
 │  2. Looks up tool by name → McpTool (wraps HTTP MCP client)
 │  3. Calls McpTool._execute(args)
 │       └─→ HttpMcpClient.call_tool("search_user", args)
 │               └─→ HTTP POST http://localhost:8005/mcp
 │                     MCP Server executes DB query
 │                     Returns: [{ id: 1, name: "John", surname: "Smith", email: "..." }]
 │  4. Appends tool result to messages:
 │     { role: "tool", tool_call_id: "x2", content: "[{id:1, name: John...}]" }
 ▼
LLM (recursive call with updated messages)
 │
 │  messages now:
 │    { role: "user",      content: "Find user John Smith" }
 │    { role: "assistant", content: null, tool_calls: [{id: "x2", ...}] }
 │    { role: "tool",      tool_call_id: "x2", content: "[{id:1, name: John...}]" }
 │
 │  response (final):
 │    { role: "assistant", content: "Found user: John Smith, email: ..." }
 ▼
User sees final answer.
```

---

## 4. Multiple Tool Calls (chained)

LLM may call multiple tools before giving a final answer.

```
messages = [
  { role: "user",      content: "Add user Elon Musk, find his bio online" },

  { role: "assistant", content: null,
    tool_calls: [{ id: "x3", name: "search", args: { query: "Elon Musk bio" } }] },

  { role: "tool",      tool_call_id: "x3", content: "Elon Musk is CEO of Tesla..." },

  { role: "assistant", content: null,
    tool_calls: [{ id: "x4", name: "add_user", args: { name: "Elon", surname: "Musk", ... } }] },

  { role: "tool",      tool_call_id: "x4", content: "User created with id: 42" },

  { role: "assistant", content: "User Elon Musk has been added successfully." },
]
```

Each tool call adds two messages (assistant + tool), then LLM decides next step.

---

## 5. Raw JSON Previews

### Request payload sent to LLM (with tools)

```json
{
  "model": "gpt-4o",
  "stream": false,
  "messages": [
    {
      "role": "user",
      "content": "Find user John Smith"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "search_user",
        "description": "Search by name/surname/email/gender",
        "parameters": {
          "type": "object",
          "properties": {
            "search_user_request": {
              "type": "object",
              "properties": {
                "name":    { "type": "string" },
                "surname": { "type": "string" },
                "email":   { "type": "string" },
                "gender":  { "type": "string" }
              }
            }
          },
          "required": ["search_user_request"]
        }
      }
    }
  ]
}
```

---

### LLM response — tool call decision

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "choices": [
    {
      "index": 0,
      "finish_reason": "tool_calls",
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_x2",
            "type": "function",
            "function": {
              "name": "search_user",
              "arguments": "{\"search_user_request\": {\"name\": \"John\", \"surname\": \"Smith\"}}"
            }
          }
        ]
      }
    }
  ],
  "usage": { "prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150 }
}
```

---

### Request payload after tool result appended (recursive call)

```json
{
  "model": "gpt-4o",
  "stream": false,
  "messages": [
    {
      "role": "user",
      "content": "Find user John Smith"
    },
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "call_x2",
          "type": "function",
          "function": {
            "name": "search_user",
            "arguments": "{\"search_user_request\": {\"name\": \"John\", \"surname\": \"Smith\"}}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "call_x2",
      "content": "[{\"id\": 1, \"name\": \"John\", \"surname\": \"Smith\", \"email\": \"john@example.com\"}]"
    }
  ],
  "tools": [ "...same tools array..." ]
}
```

---

### LLM final response — no more tool calls

```json
{
  "id": "chatcmpl-def456",
  "object": "chat.completion",
  "choices": [
    {
      "index": 0,
      "finish_reason": "stop",
      "message": {
        "role": "assistant",
        "content": "Found user: John Smith, email: john@example.com.",
        "tool_calls": null
      }
    }
  ],
  "usage": { "prompt_tokens": 200, "completion_tokens": 25, "total_tokens": 225 }
}
```

---

## 6. Streaming Response (stream=True)

Instead of one full JSON object, the API sends a sequence of **chunks** over the connection.
Each chunk is a partial delta — you accumulate them to build the full message.

### What each chunk looks like

```json
data: {
  "id": "chatcmpl-abc123",
  "object": "chat.completion.chunk",
  "choices": [
    {
      "index": 0,
      "delta": {
        "role": "assistant",
        "content": "Found"
      },
      "finish_reason": null
    }
  ]
}

data: {
  "choices": [{ "delta": { "content": " user:" }, "finish_reason": null }]
}

data: {
  "choices": [{ "delta": { "content": " John Smith." }, "finish_reason": null }]
}

data: {
  "choices": [{ "delta": {}, "finish_reason": "stop" }]
}

data: [DONE]
```

### Streaming with tool calls — delta accumulation

When the LLM decides to call a tool mid-stream, `tool_calls` arrive in deltas too:

```json
data: { "choices": [{ "delta": { "role": "assistant", "content": null }, "finish_reason": null }] }

data: { "choices": [{ "delta": { "tool_calls": [{ "index": 0, "id": "call_x2", "type": "function", "function": { "name": "search_user", "arguments": "" } }] }, "finish_reason": null }] }

data: { "choices": [{ "delta": { "tool_calls": [{ "index": 0, "function": { "arguments": "{\"search_user_request\":" } }] }, "finish_reason": null }] }

data: { "choices": [{ "delta": { "tool_calls": [{ "index": 0, "function": { "arguments": " {\"name\": \"John\"}}" } }] }, "finish_reason": null }] }

data: { "choices": [{ "delta": {}, "finish_reason": "tool_calls" }] }

data: [DONE]
```

You must **concatenate** `arguments` fragments across chunks to get the full JSON string before calling the tool.

### Non-streaming vs Streaming — key difference

| | Non-streaming (`stream=False`) | Streaming (`stream=True`) |
|---|---|---|
| Response | One complete JSON object | Many small `chunk` objects |
| Access content | `response.choices[0].message.content` | Accumulate `delta.content` per chunk |
| Tool call args | Full string in one response | Fragments across multiple chunks |
| When to use | Tool calls, simple requests | Chat UI — show text as it arrives |

---

## Key Rules

| Rule | Why |
|------|-----|
| Assistant message with `tool_calls` must precede tool result | API matches `tool_call_id` to the assistant message |
| `content` is `null` when tool_calls are present | LLM defers text response until tools resolve |
| Recursive call sends full message history | LLM needs context of what tools returned |
| MCP vs local tool — same message structure | Only difference is where `_execute` sends the request |
