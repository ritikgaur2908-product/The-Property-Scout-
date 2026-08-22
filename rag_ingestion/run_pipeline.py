import json
import logging
import os
import sys

# Ensure backend modules can be found
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from rag_ingestion.crawler import crawl_all_public_sources
from rag_ingestion.reddit_crawler import crawl_all_reddit_localities, BENGALURU_LOCALITIES
from rag_ingestion.chunker import process_documents
from rag_ingestion.embedder import embed_chunks
from rag_ingestion.upserter import upsert_to_qdrant

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def run_full_pipeline():
    # 1. Crawl 100% Real Public Sources (blrexplorer quotes & metrics, Citizen Matters news)
    logger.info("Crawling 100% real public sources (blrexplorer citizen quotes across 105 localities, GeoJSON civic metrics across 57 localities, Citizen Matters news)...")
    docs = crawl_all_public_sources()
    logger.info(f"Collected {len(docs)} real public documents (0% synthetic data).")
            
    # 3. Chunk Documents & Tag Themes
    logger.info(f"Processing and tagging {len(docs)} total documents...")
    chunks = process_documents(docs)
    logger.info(f"Generated {len(chunks)} chunks with semantic tags.")
    
    # 4. Embed Chunks using Gemini API
    logger.info("Generating Gemini embeddings (3072 dims)...")
    embedded_chunks = embed_chunks(chunks)
    logger.info(f"Successfully embedded {len(embedded_chunks)} chunks.")
    
    # 5. Upsert to Qdrant Vector Database
    logger.info("Upserting vectors and metadata into Qdrant collection 'neighborhoods'...")
    upsert_to_qdrant(embedded_chunks)
    logger.info("🎉 Ingestion pipeline complete! All Bengaluru neighborhood data is live in Qdrant.")

if __name__ == "__main__":
    run_full_pipeline()
