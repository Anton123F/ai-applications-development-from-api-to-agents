from enum import StrEnum

import psycopg2
from psycopg2.extras import RealDictCursor

from t5_rag_advanced.embeddings.embeddings_client import EmbeddingsClient
from t5_rag_advanced.utils.text import chunk_text


class SearchMode(StrEnum):
    EUCLIDIAN_DISTANCE = "euclidean"  # Euclidean distance (<->)
    COSINE_DISTANCE = "cosine"  # Cosine distance (<=>)


class TextProcessor:
    """Processor for text documents that handles chunking, embedding, storing, and retrieval"""

    def __init__(self, embeddings_client: EmbeddingsClient, db_config: dict):
        self.embeddings_client = embeddings_client
        self.db_config = db_config

    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(
            host=self.db_config['host'],
            port=self.db_config['port'],
            database=self.db_config['database'],
            user=self.db_config['user'],
            password=self.db_config['password']
        )

    #TODO:
    # provide method `process_text_file` that will:
    #   - apply file name, chunk size, overlap, dimensions and bool of the table should be truncated
    #   - truncate table with vectors if needed
    #   - load content from file and generate chunks (in `utils.text` present `chunk_text` that will help do that)
    #   - generate embeddings from chunks
    #   - save (insert) embeddings and chunks to DB
    #       hint 1: embeddings should be saved as string list
    #       hint 2: embeddings string list should be casted to vector ({embeddings}::vector)
    def process_text_file(
            self,
            file_path: str,
            document_name: str,
            chunk_size: int = 300,
            overlap: int = 40,
            dimensions: int = 384,
            truncate: bool = False
    ) -> None:
        if truncate:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("TRUNCATE TABLE vectors;")
                conn.commit()

        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = chunk_text(text, chunk_size, overlap)
        embeddings = self.embeddings_client.get_embeddings(chunks, dimensions)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                for i, chunk in enumerate(chunks):
                    cur.execute(
                        "INSERT INTO vectors (document_name, text, embedding) VALUES (%s, %s, %s::vector)",
                        (document_name, chunk, str(embeddings[i]))
                    )
            conn.commit()
        print(f"Stored {len(chunks)} chunks from '{document_name}'")


    def inspect_table(self) -> None:
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, document_name, text, embedding::text FROM vectors;")
                rows = cur.fetchall()
        print(f"Total rows: {len(rows)}")
        for row in rows:
            print(f"  id={row['id']} | doc='{row['document_name']}' | text='{row['text'][:60]}...' | embedding={row['embedding'][:40]}...")

    #TODO:
    # provide method `search` that will:
    #   - apply search mode, user request, top k for search, min score threshold and dimensions
    #   - generate embeddings from user request
    #   - search in DB relevant context
    #     hint 1: to search it in DB you need to create just regular select query
    #     hint 2: Euclidean distance `<->`, Cosine distance `<=>`
    #     hint 3: You need to extract `text` from `vectors` table
    #     hint 4: You need to filter distance in WHERE clause
    #     hint 5: To get top k use `limit`
    def search(
            self,
            user_request: str,
            search_mode: SearchMode = SearchMode.COSINE_DISTANCE,
            top_k: int = 5,
            min_score: float = 0.5,
            dimensions: int = 384
    ) -> list[str]:
        embeddings = self.embeddings_client.get_embeddings(user_request, dimensions)
        query_vector = str(embeddings[0])

        operator = "<=>" if search_mode == SearchMode.COSINE_DISTANCE else "<->"

        sql = f"""
            SELECT text, embedding {operator} %s::vector AS distance
            FROM vectors
            WHERE embedding {operator} %s::vector <= %s
            ORDER BY distance
            LIMIT %s;
        """

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (query_vector, query_vector, min_score, top_k))
                rows = cur.fetchall()

        return [row["text"] for row in rows]
        


# SELECT text, embedding <->  '[0.23, -0.45, 0.67, ..., 0.12]'::vector AS distance
# FROM vectors
# WHERE embedding <->  '[0.23, -0.45, 0.67, ..., 0.12]'::vector <= {score}
# ORDER BY distance
# LIMIT {top_k};
