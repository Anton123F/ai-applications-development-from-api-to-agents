# Streaming + Tool Call Flow — Deep Explanation

---

## The Problem: Streaming Breaks Tool Calls Into Fragments

In non-streaming mode the API returns one complete JSON object.
In streaming mode it sends many small **chunks (deltas)** — including tool call data.

The challenge: a single tool call's data arrives split across multiple chunks.
You must **reconstruct** it before you can execute the tool.

---

## Step 1: What a Single Chunk Looks Like

Each chunk has this shape:

```json
{
  "choices": [
    {
      "delta": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "index": 0,
            "id": "call_abc",
            "type": "function",
            "function": {
              "name": "search_user",
              "arguments": "{\"search_user_requ"
            }
          }
        ]
      },
      "finish_reason": null
    }
  ]
}
```

Notice: `arguments` is **cut off mid-string** — `"{\"search_user_requ"`.
The rest arrives in the next chunk:

```json
{
  "choices": [{ "delta": { "tool_calls": [{ "index": 0, "id": null, "function": { "name": null, "arguments": "est\": {\"name\": \"John\"}}" } }] } }]
}
```

**This is why `arguments` uses `+=` not `=`** — each chunk gives you a fragment.
If you use `=` you overwrite the previous fragment and lose data.
If you use `+=` you concatenate all fragments into the complete JSON string.

Same logic applies to `id` — though in practice `id` usually arrives in one chunk,
it's still accumulated with `+=` defensively.

`name` uses `=` because the function name always arrives complete in the first chunk.

---

## Step 2: Collecting All Deltas (Inside the Loop)

```python
tool_deltas = []

async for chunk in stream:
    delta = chunk.choices[0].delta

    # content → yield immediately to frontend (text tokens)
    if delta.content is not None:
        yield f"data: {json.dumps({'type': 'content', 'delta': delta.content})}\n\n"
        full_content.append(delta.content)

    # tool call fragments → collect, don't process yet
    if delta.tool_calls:
        tool_deltas.extend(delta.tool_calls)
```

Why collect and not process immediately?
Because you need ALL fragments before you can `json.loads(arguments)`.
Calling `json.loads` on a partial string crashes.

---

## Step 3: _collect_tool_calls — Reconstructing Complete Tool Calls

After the loop, `tool_deltas` contains all raw delta objects.
`_collect_tool_calls` merges them by `index` into complete tool call dicts.

```python
# tool_deltas raw input (simplified):
[
  { index: 0, id: "call_abc", type: "function", function: { name: "search_user", arguments: "{\"name\":" } },
  { index: 0, id: None,       type: None,       function: { name: None,          arguments: " \"John\"}" } },
]

# After _collect_tool_calls output:
[
  { "id": "call_abc", "type": "function", "function": { "name": "search_user", "arguments": "{\"name\": \"John\"}" } }
]
```

The `defaultdict` keyed by `index` ensures each tool call gets its own accumulator bucket.
Multiple tool calls arrive with `index: 0`, `index: 1` etc — that's how you separate them.

Why `defaultdict`?
Because you don't know in advance how many tool calls there are.
`defaultdict` auto-creates the bucket on first access — no need to check `if index not in dict`.

---

## Step 4: After the Loop — Two Paths

### Path A: Tool calls found

```
tool_calls = _collect_tool_calls(tool_deltas)  # reconstruct

ai_message = Message(role=ASSISTANT, content=None)
ai_message.tool_calls = tool_calls
messages.append(ai_message)        # ← MUST append before _call_tools
                                   #   API requires assistant message with tool_calls
                                   #   to precede tool result messages

yield SSE "call" notification      # tell frontend: tool is being called
await _call_tools(...)             # execute tools, append tool result messages
yield SSE "result" notification    # tell frontend: tool result received

async for chunk in self.stream_response(messages):  # recursive call
    yield chunk                    # stream the final LLM answer
return
```

Why recursive call?
After tool results are appended, you need another LLM call to generate the final answer.
Instead of duplicating the stream logic, you call `stream_response` again with the updated messages.

Why `messages.append(ai_message)` BEFORE `_call_tools`?
The API enforces strict message ordering:
```
assistant message (with tool_calls)  ← must exist first
tool message (with tool_call_id)     ← references assistant message's id
```
If you append in the wrong order, the API throws a validation error.

### Path B: No tool calls

```
ai_message = Message(role=ASSISTANT, content="".join(full_content))
messages.append(ai_message)           # save to conversation history

yield finish_reason="stop" SSE chunk  # signal end of generation
yield "data: [DONE]\n\n"              # SSE protocol end marker
```

---

## Step 5: _call_tools — Executing Each Tool

```python
for tool in ai_message.tool_calls:
    tool_call_id = tool.id              # needed to link result back to call
    tool_name = tool.function.name
    tool_arguments = json.loads(tool.function.arguments)  # now safe — string is complete

    if tool_name in self.tools:
        result_message = await self.tools[tool_name].execute(
            tool_call_id=tool_call_id,
            arguments=tool_arguments
        )
        messages.append(result_message)   # result_message is already a Message object
    else:
        messages.append(Message(
            role=Role.TOOL,
            content=f"Error: Tool '{tool_name}' not found.",
            tool_call_id=tool_call_id     # ← always include, even for errors
        ))
```

Why pass `tool_call_id` to the error message too?
The API matches every `role: "tool"` message to an `role: "assistant"` tool_call by `id`.
If you omit `tool_call_id` on the error, the API can't match it and throws a validation error.

Why `json.loads` only here and not inside the loop?
Inside the loop `arguments` is still a fragment — invalid JSON.
Here, after `_collect_tool_calls`, it's the complete reconstructed string — safe to parse.

---

## Full Message Array After One Tool Call Cycle

```
messages = [
  { role: "system",    content: "You are UMS Agent..." },
  { role: "user",      content: "Find John Smith" },
  { role: "assistant", content: null, tool_calls: [{ id: "call_abc", function: { name: "search_user", arguments: "{...}" } }] },
  { role: "tool",      tool_call_id: "call_abc", content: "[{ id: 1, name: John... }]" },
  { role: "assistant", content: "Found user: John Smith, email: john@example.com" },
]
```

This full array is what gets sent on the recursive call.
The LLM sees the complete context and generates the final answer.

---

## Summary: Why Each Design Decision

| Decision | Why |
|----------|-----|
| `arguments +=` not `=` | Arguments arrive as fragments across chunks — must concatenate |
| `name =` not `+=` | Function name arrives complete in the first chunk |
| `defaultdict` by `index` | Multiple tools can be called in parallel; index separates them |
| Collect deltas in loop, process after | Can't `json.loads` a partial string |
| Append `ai_message` before `_call_tools` | API requires tool results to follow the assistant tool_calls message |
| Pass `tool_call_id` even on errors | API validates every tool message has a matching assistant tool_call id |
| Recursive `stream_response` | Reuse streaming logic for the follow-up LLM call after tool execution |
