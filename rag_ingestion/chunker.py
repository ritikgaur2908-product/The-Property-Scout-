import re
from typing import List, Dict

def chunk_text(text: str, chunk_size: int = 2500, overlap: int = 300) -> List[str]:
    """
    Recursive semantic chunking strategy:
    Attempts to split by double newline (paragraphs), then single newline, then periods (sentences).
    Uses character counts (chunk_size) to keep semantic boundaries intact.
    """
    # 1. Split by paragraphs first
    paragraphs = re.split(r'\n\n+', text)
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        # If adding this paragraph exceeds chunk size, save current and start new
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            # For overlap, keep the last sentence of the previous chunk if possible
            sentences = re.split(r'(?<=[.!?]) +', current_chunk)
            current_chunk = sentences[-1] if sentences else ""
            
        if current_chunk:
            current_chunk += "\n\n" + para
        else:
            current_chunk = para
            
        # If a single paragraph is still too massive (rare but possible), hard split it
        while len(current_chunk) > chunk_size + 500:
            # Try to split by sentence
            sentences = re.split(r'(?<=[.!?]) +', current_chunk)
            if len(sentences) > 1:
                sub_chunk = " ".join(sentences[:len(sentences)//2])
                chunks.append(sub_chunk.strip())
                current_chunk = " ".join(sentences[len(sentences)//2:])
            else:
                # Fallback to hard word split if no punctuation
                words = current_chunk.split()
                sub_chunk = " ".join(words[:len(words)//2])
                chunks.append(sub_chunk.strip())
                current_chunk = " ".join(words[len(words)//2:])
                
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

def process_documents(documents: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Takes crawled documents and breaks them into smaller chunks.
    Tags them with relevant themes based on keyword matching for the LLM to use.
    """
    processed_chunks = []
    
    themes = {
        "safety": ["crime", "theft", "scam", "safe", "police", "hospital", "dark", "emergency", "snatching", "harassment"],
        "daily_life": ["noise", "traffic", "nightlife", "dogs", "trash", "clean", "pest", "bug", "garbage", "smell", "lake"],
        "transport": ["walk", "sidewalk", "footpath", "bus", "train", "metro", "parking", "garage", "auto", "commute", "cab", "flyover"],
        "culture": ["vibe", "quiet", "loud", "family", "student", "friendly", "curfew", "neighbor", "peaceful", "crowd"],
        "infrastructure": ["water", "tanker", "cauvery", "bescom", "power", "electricity", "cut", "flooding", "rain", "drain"],
        "housing": ["rent", "deposit", "owner", "broker", "society", "apartment", "gated", "maintenance"]
    }
    
    for doc in documents:
        chunks = chunk_text(doc["text"])
        
        for offset, chunk in enumerate(chunks):
            chunk_themes = []
            chunk_lower = chunk.lower()
            
            for theme, keywords in themes.items():
                if any(kw in chunk_lower for kw in keywords):
                    chunk_themes.append(theme)
                    
            if not chunk_themes:
                chunk_themes.append("general")
                
            processed_chunks.append({
                "url": doc["url"],
                "locality": doc["locality"],
                "text": chunk,
                "themes": chunk_themes,
                "offset": offset,
                "source_type": doc["source_type"]
            })
            
    # Save the intermediate chunks to a file for backup and visibility
    import json
    with open("rag_ingestion/chunks.json", "w", encoding="utf-8") as f:
        json.dump(processed_chunks, f, indent=2)
            
    return processed_chunks
