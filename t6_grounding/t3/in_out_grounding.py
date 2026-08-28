import asyncio
from typing import Any, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import AzureOpenAIEmbeddings
# from langchain_openai import OpenAIEmbeddings
from openai import AzureOpenAI
# from openai import OpenAI
from pydantic import BaseModel, Field

from commons.constants import OPENAI_API_KEY, OPENAI_CHAT_COMPLETIONS_ENDPOINT
from t6_grounding.user_service_client import UserServiceClient

#TODO: Info about app:
# HOBBIES SEARCHING WIZARD
# Searches users by hobbies and provides their full info in JSON format:
#   Input: `I need people who love to go to mountains`
#   Output:
#     ```json
#       "rock climbing": [{full user info JSON},...],
#       "hiking": [{full user info JSON},...],
#       "camping": [{full user info JSON},...]
#     ```
# ---
# 1. Since we are searching hobbies that persist in `about_me` section - we need to embed only user `id` and `about_me`!
#    It will allow us to reduce context window significantly.
# 2. Pay attention that every 5 minutes in User Service will be added new users and some will be deleted. We will at the
#    'cold start' add all users for current moment to vectorstor and with each user request we will update vectorstor on
#    the retrieval step, we will remove deleted users and add new - it will also resolve the issue with consistency
#    within this 2 services and will reduce costs (we don't need on each user request load vectorstor from scratch and pay for it).
# 3. We ask LLM make NEE (Named Entity Extraction) https://cloud.google.com/discover/what-is-entity-extraction?hl=en
#    and provide response in format:
#    {
#       "{hobby}": [{user_id}, 2, 4, 100...]
#    }
#    It allows us to save significant money on generation, reduce time on generation and eliminate possible
#    hallucinations (corrupted personal info or removed some parts of PII (Personal Identifiable Information)). After
#    generation we also need to make output grounding (fetch full info about user and in the same time check that all
#    presented IDs are correct).
# 4. In response we expect JSON with grouped users by their hobbies.
# ---
# This sample is based on the real solution where one Service provides our Wizard with user request, we fetch all
# required data and then returned back to 1st Service response in JSON format.
# ---
# Useful links:
# Chroma DB: https://docs.langchain.com/oss/python/integrations/vectorstores/index#chroma
# Document#id: https://docs.langchain.com/oss/python/langchain/knowledge-base#1-documents-and-document-loaders
# ---
# TASK:
# Implement such application as described on the `flow.png` with adaptive vector based grounding and 'lite' version of
# output grounding (verification that such user exist and fetch full user info)

SYSTEM_PROMPT = (
    "You are a Named Entity Extraction system for hobby-based user search. "
    "Given a list of users with their IDs and about_me descriptions, and a user question about hobbies, "
    "identify which users match the hobbies mentioned in the question. "
    "Group matching users by the specific hobby. Only include users that genuinely match. "
    "Return user IDs only — never fabricate or modify any information."
)

USER_PROMPT = """
User Question: {query}

Available Users:
{context}
"""


class HobbyGroup(BaseModel):
    hobby: str = Field(description="Hobby name matching the user question")
    user_ids: list[int] = Field(description="IDs of users that match this hobby", default_factory=list)


class HobbyExtractionResult(BaseModel):
    groups: list[HobbyGroup] = Field(description="Hobby groups with matching user IDs", default_factory=list)


llm_client = AzureOpenAI(
    api_key=OPENAI_API_KEY,
    api_version="2025-04-01-preview",
    azure_endpoint=OPENAI_CHAT_COMPLETIONS_ENDPOINT,
)
# llm_client = OpenAI(api_key=OPENAI_API_KEY)

embeddings = AzureOpenAIEmbeddings(
    model="text-embedding-3-small-1",
    api_key=OPENAI_API_KEY,
    azure_endpoint=OPENAI_CHAT_COMPLETIONS_ENDPOINT,
    api_version="2025-04-01-preview",
    dimensions=384,
)

# embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=OPENAI_API_KEY, dimensions=384)

user_client = UserServiceClient()


def make_document(user: dict[str, Any]) -> Document:
    return Document(
        id=str(user["id"]),
        page_content=user.get("about_me", ""),
        metadata={"user_id": user["id"]},
    )


def load_vectorstore() -> Chroma:
    print("=== Cold start: loading all users into vectorstore ===")
    users = user_client.get_all_users()
    # print(users)
    vectorstore = Chroma(embedding_function=embeddings)
    for i in range(0, len(users), 100):
        batch = users[i:i + 100]
        docs = [make_document(u) for u in batch]
        vectorstore.add_documents(docs, ids=[doc.id for doc in docs])
        print(f"  Embedded batch {i // 100 + 1} ({len(batch)} users)")
    print(f"Vectorstore ready with {len(users)} users.\n")
    return vectorstore


def sync_vectorstore(vectorstore: Chroma) -> None:
    print("\n--- Syncing vectorstore ---")
    service_users = user_client.get_all_users()
    service_ids = {str(u["id"]) for u in service_users}
    service_users_by_id = {str(u["id"]): u for u in service_users}

    stored_ids = set(vectorstore.get()["ids"])

    to_add = service_ids - stored_ids
    to_delete = stored_ids - service_ids

    if to_delete:
        vectorstore.delete(ids=list(to_delete))
        print(f"  Removed {len(to_delete)} deleted users")
    if to_add:
        new_docs = [make_document(service_users_by_id[uid]) for uid in to_add]
        vectorstore.add_documents(new_docs, ids=[doc.id for doc in new_docs])
        print(f"  Added {len(to_add)} new users")
    if not to_add and not to_delete:
        print("  Vectorstore is up to date")


def retrieve(vectorstore: Chroma, query: str, k: int = 20) -> list[Document]:
    print("\n--- Retrieving context from vectorstore ---")
    docs = vectorstore.similarity_search(query, k=k)
    print(f"  Found {len(docs)} similar users")
    return docs


def extract_hobbies(query: str, docs: list[Document]) -> HobbyExtractionResult:
    print("\n--- LLM Named Entity Extraction ---")
    context = "\n\n".join(
        f"User ID: {doc.metadata['user_id']}\nAbout: {doc.page_content}"
        for doc in docs
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT.format(query=query, context=context)},
    ]

    #parse vs create , prase create a respoonse based on validation schema pointed inside response_format
    response = llm_client.beta.chat.completions.parse(
        model="gpt-4.1-nano-2025-04-14",
        temperature=0.0,
        messages=messages,
        response_format=HobbyExtractionResult,
    )
    return response.choices[0].message.parsed


async def output_grounding(result: HobbyExtractionResult) -> dict[str, list[dict[str, Any]]]:
    print("\n--- Output grounding: fetching full user data ---")
    final: dict[str, list[dict[str, Any]]] = {}
    for group in result.groups:
        users = []
        for uid in group.user_ids:
            try:
                user = await user_client.get_user(uid)
                users.append(user)
            except Exception:
                print(f"  User ID {uid} not found (hallucinated or already deleted)")
        if users:
            final[group.hobby] = users
    return final


async def main():
    import json
    print("=== HOBBIES SEARCHING WIZARD ===")
    print("Query samples:")
    print(" - I need people who love to go to mountains")
    print(" - Find users interested in painting or music\n")

    vectorstore = load_vectorstore()

    return

    while True:
        user_question = input("> ").strip()
        if not user_question:
            continue
        if user_question.lower() in ["quit", "exit"]:
            break

        sync_vectorstore(vectorstore)
        #extract releval data from vector DB
        docs = retrieve(vectorstore, user_question)

        if not docs:
            print("\n--- No relevant users found ---")
            continue

        #handle data from vector db leave obly really relevant data
        extraction = extract_hobbies(user_question, docs)
        final_result = await output_grounding(extraction)

        print('exptraction ========================>')
        print(extraction)

        print("\n=== SEARCH RESULTS ===")
        if final_result:
            print(json.dumps(final_result, indent=2))
        else:
            print("No matching users found.")


if __name__ == "__main__":
    asyncio.run(main())