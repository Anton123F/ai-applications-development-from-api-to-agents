import asyncio
from typing import Any

from openai import AsyncAzureOpenAI

from commons.constants import OPENAI_API_KEY, OPENAI_CHAT_COMPLETIONS_ENDPOINT
from t6_grounding.user_service_client import UserServiceClient

#TODO:
# Define BATCH_SYSTEM_PROMPT - instructs the LLM to act as a user search assistant:
#   - Analyze the search criteria from the user question
#   - Examine each user in the provided list and determine if they match
#   - Return full details of matching users in their original format
#   - Return exactly "NO_MATCHES_FOUND" if no users match
BATCH_SYSTEM_PROMPT = (
    "You are a user search assistant. "
    "Given a user question containing search criteria and a list of users, "
    "perform the following steps: "
    "1. Analyze the search criteria from the user question. "
    "2. Examine each user in the provided list to determine if they match the criteria. "
    "3. Return the full details of all matching users in their original format. "
    "4. If no users match, return exactly 'NO_MATCHES_FOUND'."
)

#TODO:
# Define FINAL_SYSTEM_PROMPT - instructs the LLM to compile final search results:
#   - Review all batch search results
#   - Combine and deduplicate matching users found across batches
#   - Present results in a clear, organized manner
FINAL_SYSTEM_PROMPT = (
    "You are compiling final search results from multiple batch search outputs. "
    "Follow these steps: "
    "1. Review all batch search results provided. "
    "2. Combine and deduplicate any matching users found across batches, ensuring each user appears only once. "
    "3. Present the final list of matching users in a clear and organized manner, preserving their original format. "
    "If no users are found, return exactly 'NO_MATCHES_FOUND'."
)

#TODO:
# Define USER_PROMPT template with two placeholders:
#   - {context} - the formatted user data
#   - {query}   - the user's search question
USER_PROMPT = """
RAG Context - the formatted user data:
  {context}

User Question:
  {query}
"""


class TokenTracker:

    def __init__(self):
        #TODO:
        # - Initialize total_tokens counter to 0
        # - Initialize batch_tokens as an empty list to store per-batch token counts
        self.total_tokens = 0
        self.batch_tokens = []

    def add_tokens(self, tokens: int):
        #TODO:
        # - Add tokens to the total_tokens counter
        # - Append tokens to the batch_tokens list
        self.total_tokens += tokens
        self.batch_tokens.append(tokens)

    def get_summary(self) -> dict:
        #TODO:
        # - Return a dict with:
        #   - 'total_tokens': total accumulated tokens
        #   - 'batch_count': number of batches processed (length of batch_tokens list)
        #   - 'batch_tokens': list of tokens per batch
        return {
            "total_tokens": self.total_tokens,
            "batch_count": len(self.batch_tokens),
            "batch_tokens": self.batch_tokens
        }




llm_client = AsyncAzureOpenAI(
    api_key=OPENAI_API_KEY, 
    api_version="2025-04-01-preview", 
    azure_endpoint=OPENAI_CHAT_COMPLETIONS_ENDPOINT
)

token_tracker = TokenTracker()


def join_context(context: list[dict[str, Any]]) -> str:
    #TODO:
    # - Initialize an empty string for the result
    # - Iterate through each user in the context list
    # - For each user, add a "User:" header line
    # - For each key-value pair in the user dict, add an indented "  key: value" line
    # - Add a blank line after each user for readability
    # - Return the formatted string
    result = ""
    for user in context:
        result += "User:\n"
        for key, value in user.items():
            result += f"  {key}: {value}\n"
        result += "\n"
    return result


async def generate_response(system_prompt: str, user_message: str) -> str:
    print("Processing...")

    #TODO:
    # - Build a messages list with a system role entry and a user role entry
    # - Call llm_client.chat.completions.create with:
    #   - model='gpt-4.1-nano'
    #   - temperature=0.0
    #   - messages=messages
    # - Extract total_tokens from response.usage (default to 0 if usage is None)
    # - Track tokens using token_tracker.add_tokens(...)
    # - Extract the content string from response.choices[0].message.content (default to "")
    # - Print the response content and token count to console
    # - Return the content string
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    response = await llm_client.chat.completions.create(model="gpt-4.1-nano-2025-04-14", messages=messages, temperature=0.0)
    total_tokens = getattr(response.usage, "total_tokens", 0) if response.usage else 0
    token_tracker.add_tokens(total_tokens)
    content = response.choices[0].message.content or ""
    print(f"Response content: => {content} \n total token usage {token_tracker.get_summary()}")
    return content


async def main():
    print("Query samples:")
    print(" - Do we have someone with name John that loves traveling?")

    user_question = input("> ").strip()
    #TODO:
    # - Check if user_question is not empty, then:
    # 1. FETCH & BATCH USERS:
    #    - Print "\n--- Searching user database ---"
    #    - Fetch all users via UserServiceClient().get_all_users()
    #    - Split users into batches of 100 using list slicing
    #      Hint: [users[i:i + 100] for i in range(0, len(users), 100)]
    # 2. PARALLEL BATCH SEARCH:
    #    - Build a list of coroutines: for each batch call generate_response(...)
    #      with BATCH_SYSTEM_PROMPT and USER_PROMPT formatted with join_context(batch) and user_question
    #    - Run all coroutines IN PARALLEL using asyncio.gather(...)
    #    - Store results in batch_results
    # 3. FILTER RESULTS:
    #    - Print "\n--- Compiling results ---"
    #    - Filter batch_results to keep only results where result.strip() != "NO_MATCHES_FOUND"
    #    - Store filtered results in relevant_results
    # 4. FINAL GENERATION:
    #    - Print "\n=== SEARCH RESULTS ==="
    #    - If relevant_results is not empty:
    #      - Join relevant_results with "\n\n" into combined_results
    #      - Call generate_response with FINAL_SYSTEM_PROMPT and a message combining
    #        combined_results and user_question
    #    - Otherwise:
    #      - Print "\n=== SEARCH RESULTS ===" and a "No users found" message
    #      - Suggest refining the search
    # 5. PRINT PERFORMANCE SUMMARY:
    #    - Get the token usage summary from token_tracker.get_summary()
    #    - Print "\n=== Performance ===" with total API calls (batch_count) and total tokens
    if user_question.strip() != "":
        print("\n--- Searching user database ---")
        all_users = UserServiceClient().get_all_users();
        batches = [all_users[i:i + 100] for i in range(0, len(all_users), 100)]
        coroutines = [generate_response(
            system_prompt=BATCH_SYSTEM_PROMPT, 
            user_message=USER_PROMPT.format(context=join_context(batch), query=user_question)
        ) for batch in batches]
        batch_results = await asyncio.gather(*coroutines)
        print("\n--- Compiling results ---")
        relevant_results = [result for result in batch_results if result.strip() != "NO_MATCHES_FOUND"]
        print("\n=== SEARCH RESULTS ===")
        if relevant_results:
            combined_results = "\n\n".join(relevant_results)
            final_response = await generate_response(system_prompt=FINAL_SYSTEM_PROMPT, user_message=f"{combined_results}\n\n{user_question}")
            token_usage_summary = token_tracker.get_summary()
            print(f"\n{final_response}")
            print("\n=== Performance ===")
            print(token_usage_summary)

        else:
            print("\n=== SEARCH RESULTS ===")
            print("No users found")
    



if __name__ == "__main__":
    asyncio.run(main())


# The problems with No Grounding approach are:
#   - If we load whole users as context in one request to LLM we will hit context window
#   - Huge token usage == Higher price per request
#   - Added + one chain in flow where original user data can be changed by LLM (before final generation)
# User Question -> Get all users -> ‼️parallel search of possible candidates‼️ -> probably changed original context -> final generation