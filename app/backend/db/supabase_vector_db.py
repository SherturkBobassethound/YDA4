"""
supabase_vector_db.py

This module defines the SupabaseVectorDB class for interacting with Supabase's pgvector
for storing and retrieving document embeddings.

The SupabaseVectorDB class:
  - Uses Supabase's pgvector extension for vector storage and similarity search
  - Stores document chunks with embeddings directly in PostgreSQL
  - Provides automatic traceability through source_id foreign key
  - Leverages Row Level Security (RLS) for user data isolation
  - Provides methods to add texts (document chunks) with embeddings
  - Provides a method to perform similarity searches

Benefits over Qdrant:
  - Single source of truth (no sync issues)
  - Automatic cascade deletion when sources are removed
  - Native RLS security
  - ACID transaction guarantees
  - Simpler deployment (no separate vector DB container)
"""
import os
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from supabase import Client

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

logger = logging.getLogger(__name__)


class SupabaseVectorDB:
    def __init__(self, user_id: str, embedding_model: Embeddings, supabase_client: Client):
        """
        Initialize the SupabaseVectorDB instance.

        Args:
            user_id (str): The UUID of the user (from auth.users)
            embedding_model (Embeddings): LangChain embeddings model
            supabase_client (Client): Authenticated Supabase client with user's token
        """
        self.user_id = user_id
        self.embedding_model = embedding_model
        self.supabase = supabase_client

    def add_texts(
        self,
        texts: List[str],
        source_id: str,
        metadata: Optional[List[Dict]] = None
    ) -> None:
        """
        Add a list of text chunks to the document_chunks table with embeddings.

        Args:
            texts (list): List of text strings to add
            source_id (str): UUID of the source these chunks belong to
            metadata (list): Optional list of metadata dictionaries for each text
        """
        if metadata and len(metadata) != len(texts):
            raise ValueError("Length of metadata must match length of texts")

        if not texts:
            logger.warning("No texts provided to add_texts")
            return

        # Generate embeddings for all texts
        logger.info(f"Generating embeddings for {len(texts)} text chunks...")
        embeddings = self.embedding_model.embed_documents(texts)

        # Prepare batch insert data
        chunks_to_insert = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            chunk_metadata = metadata[i] if metadata else {}

            chunks_to_insert.append({
                "user_id": self.user_id,
                "source_id": source_id,
                "content": text,
                "embedding": embedding,  # pgvector will handle the vector type
                "metadata": chunk_metadata,
                "chunk_index": i
            })

        # Batch insert all chunks
        try:
            result = self.supabase.table('document_chunks').insert(chunks_to_insert).execute()
            logger.info(f"Successfully inserted {len(texts)} chunks for source {source_id}")
        except Exception as e:
            logger.error(f"Error inserting chunks into Supabase: {str(e)}")
            raise

    def search(self, query: str, k: int = 5, source_id: Optional[str] = None) -> List[Dict]:
        """
        Perform similarity search against the user's document chunks.

        Args:
            query (str): The search query
            k (int): Number of results to return (default 5)
            source_id (str): Optional source_id to filter results

        Returns:
            list: List of dictionaries containing content and metadata
        """
        try:
            # Generate embedding for the query
            query_embedding = self.embedding_model.embed_query(query)

            # Use the match_document_chunks function for similarity search
            # We'll use RPC to call the PostgreSQL function
            response = self.supabase.rpc(
                'match_document_chunks',
                {
                    'query_embedding': query_embedding,
                    'match_count': k,
                    'filter_user_id': self.user_id
                }
            ).execute()

            results = []
            for item in response.data:
                # If source_id filter is provided, apply it
                if source_id and item.get('metadata', {}).get('source_id') != source_id:
                    continue

                results.append({
                    'page_content': item['content'],
                    'metadata': item.get('metadata', {}),
                    'similarity': item.get('similarity', 0.0)
                })

            logger.info(f"Found {len(results)} similar chunks for query")
            return results[:k]  # Ensure we don't exceed k results after filtering

        except Exception as e:
            logger.error(f"Error performing similarity search: {str(e)}")
            raise

    def delete_by_source(self, source_id: str) -> None:
        """
        Delete all document chunks associated with a source.
        This is automatically handled by CASCADE, but can be called explicitly.

        Args:
            source_id (str): UUID of the source to delete chunks for
        """
        try:
            result = self.supabase.table('document_chunks').delete().eq('source_id', source_id).eq('user_id', self.user_id).execute()
            logger.info(f"Deleted chunks for source {source_id}")
        except Exception as e:
            logger.error(f"Error deleting chunks for source {source_id}: {str(e)}")
            raise

    def get_chunks_by_source(self, source_id: str) -> List[Dict]:
        """
        Get all chunks for a specific source.

        Args:
            source_id (str): UUID of the source

        Returns:
            list: List of chunk dictionaries
        """
        try:
            result = self.supabase.table('document_chunks').select('*').eq('source_id', source_id).eq('user_id', self.user_id).order('chunk_index').execute()
            return result.data
        except Exception as e:
            logger.error(f"Error fetching chunks for source {source_id}: {str(e)}")
            raise

    def get_source_count(self, source_id: str) -> int:
        """
        Get the number of chunks stored for a source.

        Args:
            source_id (str): UUID of the source

        Returns:
            int: Number of chunks
        """
        try:
            result = self.supabase.table('document_chunks').select('id', count='exact').eq('source_id', source_id).eq('user_id', self.user_id).execute()
            return result.count or 0
        except Exception as e:
            logger.error(f"Error counting chunks for source {source_id}: {str(e)}")
            return 0


# -------------------- Testing Block --------------------

if __name__ == "__main__":
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

    from langchain_community.embeddings import HuggingFaceEmbeddings
    from app.backend.services.text_splitter import TextSplitter
    from app.backend.services.supabase_client import get_user_supabase_client

    # This is a test - you'll need a real user token
    print("Note: This test requires a valid user access token")
    print("In production, the token comes from the authenticated user")

    embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # You would get these from the authenticated user
    # user_id = "some-uuid"
    # user_token = "some-jwt-token"
    # supabase_client = get_user_supabase_client(user_token)

    # db = SupabaseVectorDB(user_id=user_id, embedding_model=embedding_model, supabase_client=supabase_client)

    print("SupabaseVectorDB class is ready to use with authenticated users")
