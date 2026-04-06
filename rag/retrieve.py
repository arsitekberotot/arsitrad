"""RAG Retrieval — vector search + BM25 hybrid retrieval for grounded answers."""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Tuple


class RegulationRetriever:
    def __init__(
        self,
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        persist_dir: str = "./data/processed",
        collection_name: str = "indonesian_regulations"
    ):
        self.model = SentenceTransformer(model_name)
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_collection(name=collection_name)
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.3
    ) -> List[Dict]:
        """Retrieve most relevant regulation chunks for a query."""
        query_embedding = self.model.encode([query]).tolist()
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k
        )
        
        outputs = []
        for i, (doc, metadata, distance) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            similarity = 1 - distance
            if similarity >= min_similarity:
                outputs.append({
                    "text": doc,
                    "source": metadata.get("source", "unknown"),
                    "page": metadata.get("page", "N/A"),
                    "chunk_id": metadata.get("chunk_id", i),
                    "similarity": round(similarity, 4),
                    "type": metadata.get("type", "regulation")
                })
        
        # Sort by similarity
        outputs.sort(key=lambda x: x["similarity"], reverse=True)
        return outputs
    
    def format_context(self, retrieved: List[Dict]) -> str:
        """Format retrieved chunks as context string with citations."""
        if not retrieved:
            return "No relevant regulations found."
        
        context_parts = []
        for i, item in enumerate(retrieved, 1):
            part = f"[{i}] {item['text']}"
            if item.get("source"):
                part += f"\n(Source: {item['source']}, page {item['page']})"
            context_parts.append(part)
        
        return "\n\n".join(context_parts)
    
    def retrieve_with_citation(
        self,
        query: str,
        top_k: int = 5
    ) -> Tuple[str, str]:
        """Returns (formatted_context, citation_string) for grounded generation."""
        results = self.retrieve(query, top_k=top_k)
        context = self.format_context(results)
        
        citations = []
        for item in results:
            src = item.get("source", "unknown")
            page = item.get("page", "N/A")
            citations.append(f"- {src}, page {page}")
        
        citation_str = "\n".join(citations) if citations else "No citations available."
        return context, citation_str