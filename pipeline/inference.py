from __future__ import annotations

"""GGUF inference and structured answer assembly for Arsitrad v2."""

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import yaml

from pipeline.retriever import CandidateChunk, HybridRetriever, RetrievalResult, format_context

SYSTEM_PROMPT = """Kamu adalah Arsitrad, asisten AI regulasi bangunan Indonesia.
Jawab hanya berdasarkan konteks regulasi yang diberikan.
Gunakan Bahasa Indonesia.
Format jawaban wajib:
1. RINGKASAN
2. DETAIL REGULASI
3. SARAN TEKNIS
4. SUMBER
Selalu gunakan citation [N] saat mengacu ke konteks.
Jika konteks tidak cukup kuat, jangan mengarang.
"""


@dataclass(slots=True)
class InferenceConfig:
    model_path: str
    context_window: int = 8192
    max_tokens: int = 1024
    temperature: float = 0.2
    top_p: float = 0.9
    repeat_penalty: float = 1.1


@dataclass(slots=True)
class InferenceResult:
    answer: str
    retrieval: RetrievalResult
    used_model: bool
    model_path: str | None = None
    raw_text: str | None = None


def load_inference_config(config_path: str | Path = "config.yaml") -> InferenceConfig:
    with open(config_path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    inference = config.get("v2", {}).get("inference", {})
    return InferenceConfig(
        model_path=inference.get("model_path", "./models/gemma-4-E4B-it-Q4_K_M.gguf"),
        context_window=inference.get("context_window", 8192),
        max_tokens=inference.get("max_tokens", 1024),
        temperature=inference.get("temperature", 0.2),
        top_p=inference.get("top_p", 0.9),
        repeat_penalty=inference.get("repeat_penalty", 1.1),
    )


def build_sources_block(candidates: Sequence[CandidateChunk]) -> str:
    lines: list[str] = []
    for index, candidate in enumerate(candidates, start=1):
        source_name = candidate.metadata.get("source_name", "Sumber tidak diketahui")
        start_page = candidate.metadata.get("start_page") or candidate.metadata.get("page") or "?"
        end_page = candidate.metadata.get("end_page") or start_page
        if start_page == end_page:
            page_text = f"hlm. {start_page}"
        else:
            page_text = f"hlm. {start_page}-{end_page}"
        lines.append(f"[{index}] {source_name}, {page_text}")
    return "\n".join(lines) if lines else "- Tidak ada sumber tersedia"


def build_prompt(question: str, retrieval: RetrievalResult) -> str:
    context = format_context(retrieval.candidates)
    return (
        "<start_of_turn>system\n"
        + SYSTEM_PROMPT
        + "<end_of_turn>\n"
        + "<start_of_turn>user\n"
        + "KONTEKS REGULASI:\n"
        + context
        + "\n\nPERTANYAAN: "
        + retrieval.standalone_query
        + "\n\nJAWABAN:"
        + "<end_of_turn>\n"
        + "<start_of_turn>model\n"
    )


def build_no_answer_response(retrieval: RetrievalResult) -> str:
    disclaimer = (
        "Arsitrad adalah alat bantu informasi, bukan pengganti konsultasi dengan profesional "
        "berlisensi atau dinas tata ruang setempat."
    )
    return (
        "RINGKASAN\n"
        + (retrieval.message or "Arsitrad belum menemukan regulasi yang cukup kuat untuk menjawab.")
        + "\n\nDETAIL REGULASI\n"
        + "Belum ada kutipan yang memenuhi ambang kepercayaan untuk dijadikan jawaban final.\n\n"
        + "SARAN TEKNIS\n"
        + "- Perjelas lokasi, tipologi bangunan, atau jenis regulasi yang dicari.\n"
        + "- Coba gunakan istilah resmi seperti PBG, SLF, KDB, KDH, RDTR, atau RTRW.\n"
        + f"- {disclaimer}\n\n"
        + "SUMBER\n"
        + "- Tidak ada sumber yang lolos ambang kepercayaan"
    )


def build_retrieval_only_response(retrieval: RetrievalResult) -> str:
    candidate = retrieval.candidates[0]
    excerpt = candidate.content[:700].strip()
    return (
        "RINGKASAN\n"
        + "Model GGUF belum dimuat, jadi Arsitrad menampilkan konteks regulasi terbaik yang ditemukan.\n\n"
        + "DETAIL REGULASI\n"
        + f"[1] {excerpt}\n\n"
        + "SARAN TEKNIS\n"
        + "- Muat model GGUF untuk mendapatkan ringkasan generatif penuh.\n"
        + "- Tetap verifikasi kutipan utama sebelum dipakai untuk keputusan desain atau perizinan.\n\n"
        + "SUMBER\n"
        + build_sources_block(retrieval.candidates[:1])
    )


def ensure_structured_sections(text: str, candidates: Sequence[CandidateChunk]) -> str:
    normalized = text.strip()
    headings = ["RINGKASAN", "DETAIL REGULASI", "SARAN TEKNIS", "SUMBER"]
    if all(heading in normalized.upper() for heading in headings):
        return normalized
    return (
        "RINGKASAN\n"
        + normalized
        + "\n\nDETAIL REGULASI\n"
        + format_context(candidates)
        + "\n\nSARAN TEKNIS\n"
        + "- Verifikasi silang dengan regulasi asli sebelum implementasi.\n\n"
        + "SUMBER\n"
        + build_sources_block(candidates)
    )


class GGUFInferenceEngine:
    def __init__(self, config: InferenceConfig):
        self.config = config
        self._model = None

    @property
    def model(self):
        if self._model is None:
            if not Path(self.config.model_path).exists():
                raise FileNotFoundError(self.config.model_path)
            from llama_cpp import Llama

            self._model = Llama(
                model_path=self.config.model_path,
                n_ctx=self.config.context_window,
                verbose=False,
            )
        return self._model

    def generate(self, prompt: str) -> str:
        result = self.model(
            prompt,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            repeat_penalty=self.config.repeat_penalty,
            stop=["<end_of_turn>", "<eos>"],
        )
        return result["choices"][0]["text"].strip()


class ArsitradAnswerEngine:
    def __init__(
        self,
        config_path: str | Path = "config.yaml",
        retriever: HybridRetriever | None = None,
        inference_engine: GGUFInferenceEngine | None = None,
    ):
        self.config_path = str(config_path)
        self.retriever = retriever or HybridRetriever(config_path=config_path)
        self.inference_config = load_inference_config(config_path)
        self.inference_engine = inference_engine or GGUFInferenceEngine(self.inference_config)

    def answer(self, question: str, history: Sequence[dict[str, str]] | None = None) -> InferenceResult:
        retrieval = self.retriever.retrieve(question, history=history)
        if not retrieval.should_answer:
            answer = build_no_answer_response(retrieval)
            return InferenceResult(answer=answer, retrieval=retrieval, used_model=False)

        prompt = build_prompt(question, retrieval)
        try:
            raw_text = self.inference_engine.generate(prompt)
            answer = ensure_structured_sections(raw_text, retrieval.candidates)
            return InferenceResult(
                answer=answer,
                retrieval=retrieval,
                used_model=True,
                model_path=self.inference_config.model_path,
                raw_text=raw_text,
            )
        except FileNotFoundError:
            answer = build_retrieval_only_response(retrieval)
            return InferenceResult(
                answer=answer,
                retrieval=retrieval,
                used_model=False,
                model_path=self.inference_config.model_path,
            )
