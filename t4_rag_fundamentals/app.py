import openai
import os

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.vectorstores import VectorStore
from langchain_openai import AzureOpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import SecretStr

from commons.constants import OPENAI_API_KEY, DIAL_HOST, DIAL_API_VERSION

_LLM_DEPLOYMENT = "gpt-5.2-2025-12-11"

#TODO:
# Create system prompt with:
# - role: explains the role for LLM and what it should do
# - Structure of User message, consists of 2 blocks:
#   - `RAG CONTEXT`: information retrieved on the Retrieval step based on user request
#   - `USER QUESTION`: The user's actual question
# - Instructions:
#   - Model must use only information from conversation
#   - Strictly forbid to answer questions that are not in the conversation or not present in `RAG CONTEXT`
_SYSTEM_PROMPT = """
NEED_TO_IMPLEMENT
"""

_USER_PROMPT = """##RAG CONTEXT:
{context}


##USER QUESTION:
{query}"""


class MicrowaveRAG:

    def __init__(self, embeddings: AzureOpenAIEmbeddings, llm_client: openai.AzureOpenAI):
        self.llm_client = llm_client
        self.embeddings = embeddings
        self.vectorstore = self._setup_vectorstore()

    def _setup_vectorstore(self) -> VectorStore:
        """
        Load existing FAISS index from disk or create a new one.
        Returns:
              VectorStore: Initialized FAISS vectorstore.
        """
        #TODO:
        # - Print a startup message
        # - Check if 'microwave_faiss_index' folder already exists
        # - If yes, load the index from disk using FAISS.load_local()
        # - If no, call _create_new_index() to build and save a fresh index
        # - Return the vectorstore
        print("Setting up vectorstore...")
        index_path = "microwave_faiss_index"
        if os.path.exists(index_path):
            print(f"Loading existing FAISS index from '{index_path}'.")
            return FAISS.load_local(index_path, self.embeddings, allow_dangerous_deserialization=True)
        print("No existing index found. Creating a new one.")
        return self._create_new_index()

    def _create_new_index(self) -> VectorStore:
        """
        Load the manual, split into chunks, embed, and save a new FAISS index.
        Returns:
              VectorStore: Newly created and saved FAISS vectorstore.
        """
        #TODO:
        # - Load 'microwave_manual.txt' using TextLoader
        # - Split documents into chunks using RecursiveCharacterTextSplitter
        #   (chunk_size=300, chunk_overlap=50, separators=["\n\n", "\n", "."])
        # - Create a FAISS vectorstore from chunks and self.embeddings using FAISS.from_documents()
        # - Save the index locally using vectorstore.save_local("microwave_faiss_index")
        # - Return the vectorstore
        loader = TextLoader("microwave_manual.txt", encoding="utf-8")
        documents = loader.load()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,
            chunk_overlap=50,
            separators=["\n\n", "\n", "."],
        )
        chunks = splitter.split_documents(documents)
        vectorstore = FAISS.from_documents(chunks, self.embeddings)
        vectorstore.save_local("microwave_faiss_index")
        return vectorstore

    def retrieve_context(self, query: str, k: int = 4, score=0.3):
        """
        Retrieve the context for a given query.
        Args:
              query (str): The query to retrieve the context for.
              k (int): The number of relevant documents(chunks) to retrieve.
              score (float): The similarity score between documents and query. Range 0.0 to 1.0.
        """
        #TODO:
        # - Search the vectorstore using similarity_search_with_relevance_scores() with k and score_threshold parameters
        # - Iterate over results, collect each doc's page_content, and print its relevance score
        # - Return all collected chunks joined with "\n\n" as a single context string
        results = self.vectorstore.similarity_search_with_relevance_scores(
            query, k=k, score_threshold=score
        )
        chunks = []
        for doc, relevance_score in results:
            print(f"Relevance score: {relevance_score:.4f}")
            chunks.append(doc.page_content)
        return "\n\n".join(chunks)

    def augment_prompt(self, query: str, context: str):
        """
        Inject retrieved context and user query into the prompt template.
        Args:
              query (str): The user's question.
              context (str): Retrieved context from the vectorstore.
        Returns:
              str: Formatted prompt ready for the LLM.
        """
        #TODO:
        # - Format _USER_PROMPT template substituting {context} and {query}
        # - Print the resulting augmented prompt
        # - Return the formatted string
        augmented = _USER_PROMPT.format(context=context, query=query)
        print(augmented)
        return augmented

    def generate_answer(self, augmented_prompt: str):
        """
        Send the augmented prompt to the LLM and return its response.
        Args:
              augmented_prompt (str): The prompt with injected context and query.
        Returns:
              str: The LLM-generated answer.
        """
        #TODO:
        # - Build a messages list: [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=augmented_prompt)]
        # - Invoke self.llm_client with the messages list
        # - Print the response content
        # - Return the response content string
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": augmented_prompt},
        ]
        response = self.llm_client.chat.completions.create(
            model=_LLM_DEPLOYMENT,
            messages=messages,
        )
        content = response.choices[0].message.content
        print(content)
        return content


def main(rag: MicrowaveRAG):
    #TODO:
    # - Print a welcome message
    # - Run an infinite loop that reads user input with input()
    # - For each question execute the 3-step RAG pipeline:
    #   - Step 1 (Retrieval):   call rag.retrieve_context() to fetch relevant chunks
    #   - Step 2 (Augmentation): call rag.augment_prompt() to build the prompt
    #   - Step 3 (Generation):  call rag.generate_answer() to get the LLM answer
    print("===> Ask any question about your microwave manual.")
    while True:
        query = input("User: ")
        if query.strip().lower() == "exit":
            print("Goodbye!")
            break
        context = rag.retrieve_context(query)
        augmented_prompt = rag.augment_prompt(query, context)
        rag.generate_answer(augmented_prompt)


#TODO:
# Start the application by calling main() and passing a MicrowaveRAG instance:
# - Create OpenAIEmbeddings with model='text-embedding-3-small' and api_key=OPENAI_API_KEY
# - Create ChatOpenAI with temperature=0.0, model='gpt-5.2' and api_key=OPENAI_API_KEY
# - Wrap both in a MicrowaveRAG instance and pass it to main()
embeddings = AzureOpenAIEmbeddings(
    model="text-embedding-3-small-1",
    azure_endpoint=DIAL_HOST,
    api_key=SecretStr(OPENAI_API_KEY),
    api_version=DIAL_API_VERSION,
)
#gpt-5.6-terra-2026-07-09
llm_client = openai.AzureOpenAI(
    azure_deployment=_LLM_DEPLOYMENT,
    azure_endpoint=DIAL_HOST,
    api_key=OPENAI_API_KEY,
    api_version=DIAL_API_VERSION,
)
print('==> try to run application !!!!!!!!!!!!!!!!')
print(embeddings.embed_query("enot")[:5])
RAG = MicrowaveRAG(embeddings=embeddings, llm_client=llm_client)
main(RAG)