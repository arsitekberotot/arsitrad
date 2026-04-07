"""Grounded Generation — RAG-powered answer generation with Gemma 4.

Two modes:
  1. grounded  — retrieve from ChromaDB, generate with fine-tuned Gemma 4
  2. ungrounded — fine-tuned Gemma 4 only (no retrieval)
"""

import os
import torch
from typing import Optional, List, Dict
from .retrieve import RegulationRetriever


SYSTEM_PROMPT = (
    "Kamu adalah Arsitrad, asisten AI untuk regulasi dan saran arsitektur di Indonesia. "
    "Kamu menjawab berdasarkan peraturan pembangunan Indonesia (UU, PP, Permen, SNI, Perda) "
    "dan memberikan saran teknis yang akurat tentang bangunan gedung, tata ruang, dan konstruksi. "
    "Selalu cite sumber dengan nomor [N] saat menggunakan konteks regulasi."
)


class GroundedGenerator:
    """RAG-grounded generation using Gemma 4 with ChromaDB retrieval.

    Args:
        retriever: RegulationRetriever instance connected to ChromaDB
        model_path: Path to fine-tuned Gemma 4 checkpoint
        base_model: Base Gemma 4 model for initialization
        device: Compute device (cuda or cpu)
    """

    def __init__(
        self,
        retriever: Optional[RegulationRetriever] = None,
        model_path: Optional[str] = None,
        base_model: str = "google/gemma-4-2b-it",
        device: Optional[str] = None,
    ):
        self.retriever = retriever
        self.model_path = model_path or os.environ.get(
            "ARSTRAD_MODEL_PATH", "./fine_tuned_model"
        )
        self.base_model = base_model
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model = None
        self._tokenizer = None

    # ── Model loading ──────────────────────────────────────────────────────

    def _load_model(self):
        """Lazy-load Gemma 4 on first use."""
        if self._model is not None:
            return

        model_path = self.model_path
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found at {model_path}. "
                f"Run lora_train.py first or set ARSTRAD_MODEL_PATH."
            )

        from transformers import AutoTokenizer, AutoModelForCausalLM
        from peft import PeftModel

        print(f"Loading model from {model_path} on {self.device}...")

        tokenizer = AutoTokenizer.from_pretrained(self.base_model)
        base_model = AutoModelForCausalLM.from_pretrained(
            self.base_model,
            torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32,
            device_map=self.device,
        )

        try:
            self._model = PeftModel.from_pretrained(base_model, model_path)
            print("Loaded LoRA adapters (merged)")
        except Exception:
            self._model = base_model
            print("Loaded base model (no LoRA)")

        self._model.eval()
        self._tokenizer = tokenizer
        print("Model ready.")

    @property
    def model(self):
        if self._model is None:
            self._load_model()
        return self._model

    @property
    def tokenizer(self):
        if self._tokenizer is None:
            self._load_model()
        return self._tokenizer

    # ── Prompt building ───────────────────────────────────────────────────

    def _build_prompt(self, question: str, context: Optional[str] = None) -> str:
        """Build Gemma turn-formatted prompt."""
        if context:
            body = (
                "Konteks dari regulasi Indonesia:\n\n"
                + context
                + "\n\n---\n\nPertanyaan: "
                + question
                + "\n\nJawaban (dalam Bahasa Indonesia, dengan cite sumber sebagai [N]):"
            )
        else:
            body = question

        return (
            "<start_of_turn>system\n"
            + SYSTEM_PROMPT
            + "<end_of_turn>\n"
            "<start_of_turn>user\n"
            + body
            + "<end_of_turn>\n"
            "<start_of_turn>model\n"
        )

    def _generate(
        self,
        prompt: str,
        max_new_tokens: int = 1024,
        temperature: float = 0.3,
        top_p: float = 0.9,
    ) -> str:
        """Run inference on Gemma 4."""
        tokenizer = self.tokenizer
        input_ids = tokenizer(
            prompt, return_tensors="pt", return_token_type_ids=False
        ).to(self.device)

        with torch.no_grad():
            output = self.model.generate(
                **input_ids,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=temperature > 0,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )

        full = tokenizer.decode(output[0], skip_special_tokens=False)
        assistant_marker = "<start_of_turn>model\n"
        idx = full.rfind(assistant_marker)
        if idx != -1:
            return full[idx + len(assistant_marker) :]
        # Fallback: strip input
        return tokenizer.decode(
            output[0][input_ids["input_ids"].shape[1] :], skip_special_tokens=True
        )

    # ── Public API ───────────────────────────────────────────────────────

    def generate(
        self,
        question: str,
        top_k: int = 5,
        max_new_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> Dict:
        """Grounded generation: retrieve context then generate with Gemma 4.

        Args:
            question: User question in Bahasa Indonesia
            top_k: Number of regulation chunks to retrieve
            max_new_tokens: Max tokens in generated answer
            temperature: Sampling temperature (0 = greedy)

        Returns:
            Dict with answer, citations, context_used, retrieved_count, mode
        """
        if self._model is None:
            # Model not available — return retrieval-only response
            if self.retriever is None:
                return {
                    "answer": "[MODEL_NOT_READY] Model belum tersedia. Jalankan lora_train.py.",
                    "citations": "N/A",
                    "context_used": "",
                    "retrieved_count": 0,
                    "mode": "grounded",
                }
            context, citations = self.retriever.retrieve_with_citation(question, top_k=top_k)
            return {
                "answer": "[RETRIEVAL_ONLY] Berikut konteks regulasi yang relevan:\n\n"
                          + context[:1500]
                          + "\n\n[Jawaban akan dihasilkan setelah model Gemma 4 di-fine-tune]",
                "citations": citations,
                "context_used": context[:2000],
                "retrieved_count": len(context.split("[1]")) - 1,
                "mode": "grounded_retrieval_only",
            }

        if self.retriever is None:
            return self._generate_ungrounded(question, max_new_tokens, temperature)

        context, citations = self.retriever.retrieve_with_citation(question, top_k=top_k)
        prompt = self._build_prompt(question, context=context)
        answer = self._generate(prompt, max_new_tokens=max_new_tokens, temperature=temperature)

        return {
            "answer": answer.strip(),
            "citations": citations,
            "context_used": context[:2000],
            "retrieved_count": len(context.split("[1]")) - 1,
            "mode": "grounded",
        }

    def _generate_ungrounded(
        self,
        question: str,
        max_new_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> Dict:
        """Fine-tuned model only — no retrieval."""
        if self._model is None:
            # Model not available yet — return a placeholder
            return {
                "answer": "[MODEL_NOT_READY] Fine-tuned model belum tersedia. "
                          "Jalankan lora_train.py terlebih dahulu untuk melatih model.",
                "citations": "N/A (model belum dilatih)",
                "context_used": "",
                "retrieved_count": 0,
                "mode": "ungrounded",
            }
        prompt = self._build_prompt(question)
        answer = self._generate(prompt, max_new_tokens=max_new_tokens, temperature=temperature)
        return {
            "answer": answer.strip(),
            "citations": "N/A (ungrounded)",
            "context_used": "",
            "retrieved_count": 0,
            "mode": "ungrounded",
        }

    def generate_with_fallback(
        self,
        question: str,
        use_grounding: bool = True,
        top_k: int = 5,
        max_new_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> Dict:
        """Generate with optional grounding — falls back to ungrounded on failure."""
        if use_grounding:
            try:
                return self.generate(question, top_k=top_k,
                                     max_new_tokens=max_new_tokens, temperature=temperature)
            except Exception as e:
                print(f"Grounded generation failed ({e}) — falling back to ungrounded")
        return self._generate_ungrounded(question, max_new_tokens, temperature)


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Arsitrad Grounded Generation")
    parser.add_argument("question", nargs="?", help="Question in Bahasa Indonesia")
    parser.add_argument("--ungrounded", action="store_true", help="Skip RAG retrieval")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--temperature", type=float, default=0.3)
    parser.add_argument(
        "--model-path",
        default=os.environ.get("ARSTRAD_MODEL_PATH", "./fine_tuned_model"),
    )
    args = parser.parse_args()

    retriever = None
    if not args.ungrounded:
        try:
            retriever = RegulationRetriever(
                persist_dir="/home/admin/hermes/projects/arsitrad/data/processed",
                collection_name="arsitrad_national_regulations",
            )
        except Exception as e:
            print(f"Warning: Could not connect to ChromaDB ({e}) — using ungrounded mode")
            args.ungrounded = True

    generator = GroundedGenerator(retriever=retriever, model_path=args.model_path)

    if args.question:
        result = generator.generate_with_fallback(
            args.question,
            use_grounding=not args.ungrounded,
            top_k=args.top_k,
            max_new_tokens=args.max_tokens,
            temperature=args.temperature,
        )
        print("\n" + "=" * 60)
        print(result["answer"])
        print("=" * 60)
        print(f"\n[Sumber: {result.get('retrieved_count', 0)} chunks retrieved]")
        if result.get("citations") and result["citations"] != "N/A":
            print("\nCitations:")
            print(result["citations"])
    else:
        print("Arsitrad Grounded Generation REPL (Ctrl+C to exit)")
        print(f"Mode: {'grounded' if not args.ungrounded else 'ungrounded'}")
        print()
        while True:
            try:
                q = input("Q: ").strip()
                if not q:
                    continue
                result = generator.generate_with_fallback(
                    q,
                    use_grounding=not args.ungrounded,
                    top_k=args.top_k,
                    max_new_tokens=args.max_tokens,
                    temperature=args.temperature,
                )
                print("\nA:", result["answer"])
                print(f"\n[retrieved: {result.get('retrieved_count', 0)} | mode: {result.get('mode', '?')}]")
                print()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting.")
                break


if __name__ == "__main__":
    main()
