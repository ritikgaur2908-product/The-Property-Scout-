import os
from typing import List, Dict
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
import uuid
import logging
from backend.config import settings

logger = logging.getLogger(__name__)

def get_qdrant_client() -> QdrantClient:
    url = settings.VECTOR_DB_URL
    api_key = settings.VECTOR_DB_API_KEY
    if not url or not api_key:
        raise ValueError("VECTOR_DB_URL and VECTOR_DB_API_KEY must be set in .env")
        
    return QdrantClient(
        url=url,
        api_key=api_key,
        timeout=30
    )

from qdrant_client.models import PointStruct, VectorParams, Distance, PayloadSchemaType

def ensure_collection(client: QdrantClient, collection_name: str = "neighborhoods"):
    if client.collection_exists(collection_name):
        logger.info(f"Deleting old collection '{collection_name}'...")
        client.delete_collection(collection_name)
        
    logger.info(f"Creating collection '{collection_name}' in Qdrant with 3072 dimensions...")
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=3072, distance=Distance.COSINE)
    )
    # Create payload index for filtered searches by locality and themes
    logger.info(f"Creating payload indexes for '{collection_name}'...")
    client.create_payload_index(
        collection_name=collection_name,
        field_name="locality",
        field_schema=PayloadSchemaType.KEYWORD
    )
    client.create_payload_index(
        collection_name=collection_name,
        field_name="themes",
        field_schema=PayloadSchemaType.KEYWORD
    )

def upsert_to_qdrant(chunks: List[Dict], collection_name: str = "neighborhoods"):
    """
    Upserts the embedded chunks into the Qdrant vector database.
    """
    client = get_qdrant_client()
    ensure_collection(client, collection_name)
    
    points = []
    for chunk in chunks:
        # Generate a deterministic ID based on URL and offset so we can safely re-run this
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{chunk['url']}#{chunk['offset']}"))
        
        points.append(
            PointStruct(
                id=point_id,
                vector=chunk["embedding"],
                payload={
                    "text": chunk["text"],
                    "url": chunk["url"],
                    "locality": chunk["locality"],
                    "themes": chunk["themes"],
                    "source_type": chunk["source_type"]
                }
            )
        )
        
    logger.info(f"Upserting {len(points)} points to Qdrant...")
    client.upsert(
        collection_name=collection_name,
        points=points
    )
    logger.info("Upsert complete.")
    
if __name__ == "__main__":
    from rag_ingestion.crawler import crawl_sources
    from rag_ingestion.chunker import process_documents
    from rag_ingestion.embedder import embed_chunks
    
    docs = crawl_sources()
    chunks = process_documents(docs)
    embedded_chunks = embed_chunks(chunks)
    upsert_to_qdrant(embedded_chunks)
