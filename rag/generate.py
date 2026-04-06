"""Grounded Generation — uses Gemma 4 to generate answers grounded in retrieved regulations."""

from typing import Optional
from .retrieve import RegulationRetriever


SYSTEM_PROMPT = """You are Arsitrad, an expert AI assistant for Indonesian architecture and construction regulations.

Your role is to answer questions about Indonesian building codes, SNI standards, and construction regulations by citing the provided regulation context. Be precise, cite specific articles/sections, and note any limitations in the context.

IMPORTANT RULES:
- Only answer based on the provided regulation context
- If the context doesn't fully answer the question, say so explicitly
- Always cite specific sources using [N] notation where N is the citation number
- Respond in Bahasa Indonesia when the question is in Bahasa Indonesia
- Use formal but accessible language appropriate for construction professionals
- For ambiguous questions, provide the most likely interpretation and note alternatives
"""


class GroundedGenerator:
    def __init__(self, retriever: RegulationRetriever, model_path: Optional[str] = None):
        self.retriever = retriever
        self.model_path = model_path  # Will be initialized with fine-tuned Gemma 4
        
    def generate(
        self,
        question: str,
        top_k: int = 5,
        max_new_tokens: int = 1024,
        temperature: float = 0.3
    ) -> dict:
        """Generate grounded answer using retrieved context + Gemma 4."""
        # Step 1: Retrieve relevant regulations
        context, citations = self.retriever.retrieve_with_citation(question, top_k=top_k)
        
        # Step 2: Build prompt
        prompt = f"""Context from Indonesian regulations:
{context}

---

Question: {question}

Answer:"""
        
        # Step 3: Generate (placeholder — replace with actual Gemma 4 inference)
        # TODO: integrate fine-tuned Gemma 4 model here
        # from transformers import AutoTokenizer, AutoModelForCausalLM
        # model_id = self.model_path or "google/gemma-4-2b-it"
        # tokenizer = AutoTokenizer.from_pretrained(model_id)
        # model = AutoModelForCausalLM.from_pretrained(model_id, ...)
        
        generated_text = f"[PLACEHOLDER] Based on regulations:\n{context[:500]}...\n\nJawaban akan dihasilkan oleh model Gemma 4 yang sudah di-fine-tune."
        
        return {
            "answer": generated_text,
            "citations": citations,
            "context_used": context,
            "retrieved_count": len(context.split("[1]"))
        }
    
    def generate_with_fallback(
        self,
        question: str,
        use_grounding: bool = True,
        **kwargs
    ) -> dict:
        """Generate with optional grounding — falls back to general knowledge if retrieval fails."""
        if use_grounding:
            return self.generate(question, **kwargs)
        else:
            return {
                "answer": "[UNGROUNDED] Gemma 4 general response here",
                "citations": "No citations",
                "context_used": "",
                "retrieved_count": 0
            }