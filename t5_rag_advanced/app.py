from commons.constants import OPENAI_API_KEY, OPENAI_EMBEDDINGS_ENDPOINT, OPENAI_CHAT_COMPLETIONS_ENDPOINT
from commons.models.conversation import Conversation
from commons.models.message import Message
from commons.models.role import Role
from t5_rag_advanced.chat.chat_completion_client import ChatCompletionClient
from t5_rag_advanced.embeddings.embeddings_client import EmbeddingsClient
from t5_rag_advanced.embeddings.text_processor import TextProcessor, SearchMode


from commons.constants import OPENAI_API_KEY, DIAL_HOST, DIAL_API_VERSION

_LLM_DEPLOYMENT = "gpt-5.2-2025-12-11"

#TODO:
# Create system prompt with info that it is RAG powered assistant.
# Explain user message structure (firstly will be provided RAG context and the user question).
# Provide instructions that LLM should use RAG Context when answer on User Question, will restrict LLM to answer
# questions that are not related microwave usage, not related to context or out of history scope
SYSTEM_PROMPT = """You are a RAG-powered assistant that helps users with microwave oven questions.

Each user message has two sections:
1. RAG Context — relevant excerpts retrieved from the microwave manual
2. User Question — the actual question from the user

Rules:
- Answer ONLY using the information provided in the RAG Context
- If the answer is not found in the RAG Context, respond: "I don't have information about that in the microwave manual."
- Do NOT answer questions unrelated to microwave usage or the provided manual
- Do NOT use your own training knowledge to fill in gaps
"""

#TODO:
# Provide structured system prompt, with RAG Context and User Question sections.
USER_PROMPT = """
RAG Context:
  {context}

User Question:
  {question}
"""

#TODO:
# - create embeddings client with 'text-embedding-3-small' model, OPENAI_EMBEDDINGS_ENDPOINT endpoint and OPENAI_API_KEY
# - create chat completion client with 'gpt-5.2' model, OPENAI_CHAT_COMPLETIONS_ENDPOINT endpoint and OPENAI_API_KEY
# - create text processor, DB config: {'host': 'localhost','port': 5433,'database': 'vectordb','user': 'postgres','password': 'postgres'}
# ---
# Create method that will run console chat with such steps:
# - get user input from console
# - retrieve context
# - perform augmentation
# - perform generation
# - it should run in `while` loop (since it is console chat)
embeddings_client = EmbeddingsClient(
    endpoint=f"{OPENAI_EMBEDDINGS_ENDPOINT}/text-embedding-3-small-1/embeddings",
    model_name="text-embedding-3-small-1",
    api_key=OPENAI_API_KEY
)

chat = ChatCompletionClient(
  api_key=OPENAI_API_KEY, 
  endpoint=f"{DIAL_HOST}/openai/deployments/{_LLM_DEPLOYMENT}/chat/completions?api-version={DIAL_API_VERSION}", 
  model_name=_LLM_DEPLOYMENT
  )

# result = embeddings_client.get_embeddings("Hello microwave!", dimensions=10, print_response=True)
# result = embeddings_client.get_embeddings(["Hello", "microwave!"], dimensions=10, print_response=True)

# print(result)
# print(f"Got {len(result)} embedding(s), first vector length: {len(result[0])}")

text_processor = TextProcessor(
    embeddings_client=embeddings_client,
    db_config={
        'host': 'localhost',
        'port': 5433,
        'database': 'vectordb',
        'user': 'postgres',
        'password': 'postgres'
    }
)

# print('=====>> text processing')
text_processor.process_text_file('./embeddings/microwave_manual.txt', document_name='microwave_manual')
# text_processor.inspect_table()

while True:
  user_input = input("Hello! Print something that you want to ask.\nType 'exit' to quit:\n")
  if user_input.lower().strip() == "exit":
    break
  vector_search_result = text_processor.search(user_request=user_input)
  # print(vector_search_result)
  context = "\n".join(vector_search_result)
  augmentation_promt = USER_PROMPT.format(context=context, question=user_input)
  messages = [
    Message(Role.SYSTEM, SYSTEM_PROMPT),
    Message(Role.USER, augmentation_promt),
  ]
  response = chat.get_completion(messages=messages)
  print(f"\nAssistant: {response.content}\n")
# TODO:
#  PAY ATTENTION THAT YOU NEED TO RUN Postgres DB ON THE 5433 WITH PGVECTOR EXTENSION!
#  RUN docker-compose.yml
