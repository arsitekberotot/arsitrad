# Arsitrad v2 Implementation Plan

> For Hermes: execute on branch `feat/arsitrad-v2-rag` using subagent-driven-development principles where practical.

Goal: Replace the current v1 MiniLM + ChromaDB + LoRA/Gradio stack with a shipped v2 based on semantic legal chunking, E5 embeddings, pgvector hybrid retrieval, confidence-gated GGUF inference, and a Streamlit UI.

Architecture: Build v2 alongside the legacy code so the repo keeps historical context while the new pipeline lives in `pipeline/`, `db/`, `tests/`, and updated `ui/`. Re-parse the raw PDF corpus from `/home/admin/hermes/projects/arsitrad/data/corpus/` instead of reusing v1 chunks, because v1 chunk boundaries and embedding space are not suitable for the final system.

Tech Stack: Python 3.11, pdfplumber, sentence-transformers, psycopg, pgvector, rank-bm25, FlagEmbedding, llama-cpp-python, Streamlit, ragas, pytest.

---

## Task 1: Establish v2 foundation

Objective: Create the new package structure, database schema, configuration, and dependency definitions for v2.

Files:
- Create: `db/schema.sql`
- Create: `pipeline/__init__.py`
- Create: `pipeline/eval/__init__.py`
- Create: `tests/__init__.py`
- Modify: `config.yaml`
- Modify: `requirements.txt`

Verification:
- `python -m compileall pipeline`
- `python -c "import yaml; print(yaml.safe_load(open('config.yaml'))['v2']['embedding_model'])"`

---

## Task 2: Build semantic legal chunker and metadata extraction

Objective: Re-parse raw PDFs with structural legal chunking by BAB/Bagian/Pasal/Ayat plus table-aware extraction.

Files:
- Create: `pipeline/chunker.py`
- Create: `tests/test_chunker.py`

Requirements:
- Extract text per page from PDF.
- Extract tables with pdfplumber and convert to markdown-like text.
- Split documents using structural markers before fallback token windows.
- Produce normalized metadata for `region`, `island`, `reg_type`, `year`, `number`, `typology`, `source_path`, `source_name`, and page spans.
- Support both national corpus and local regulations.

Verification:
- `pytest tests/test_chunker.py -q`
- `python -m pipeline.chunker --sample --limit 2`

---

## Task 3: Build ingestion pipeline for E5 + Postgres/pgvector

Objective: Embed semantic chunks with `intfloat/multilingual-e5-base-v2` and load them into pgvector.

Files:
- Create: `pipeline/ingest.py`
- Create: `tests/test_ingest.py`

Requirements:
- Load raw docs from corpus roots.
- Prefix E5 inputs correctly (`passage:` / `query:`).
- Batch embeddings.
- Upsert documents into `regulation_chunks`.
- Store full metadata JSONB.
- Support dry-run and JSON export mode for local testing.

Verification:
- `pytest tests/test_ingest.py -q`
- `python -m pipeline.ingest --dry-run --limit-docs 2`

---

## Task 4: Build retrieval pipeline

Objective: Implement hybrid retrieval with dense pgvector search, sparse BM25 search, RRF fusion, reranking, metadata filters, and confidence gating.

Files:
- Create: `pipeline/retriever.py`
- Create: `tests/test_retriever.py`

Requirements:
- Dense search with pgvector cosine distance.
- Sparse search over loaded corpus using BM25.
- Reciprocal Rank Fusion for dense+sparse candidates.
- Cross-encoder reranking with `BAAI/bge-reranker-base`.
- Metadata pre-filters for region/typology/year/reg_type.
- Confidence threshold fallback under configured score.

Verification:
- `pytest tests/test_retriever.py -q`

---

## Task 5: Build query rewriting helpers

Objective: Improve recall for real user phrasing and follow-up questions.

Files:
- Create: `pipeline/query_expander.py`
- Create: `pipeline/conversation_memory.py`
- Create: `tests/test_query_expander.py`
- Create: `tests/test_conversation_memory.py`

Requirements:
- Rule-based Indonesian legal term expansion (IMB -> PBG, etc.).
- Optional lightweight LLM-ready prompt path for richer expansion.
- Conversation contextualizer to rewrite follow-up questions into standalone retrieval queries.

Verification:
- `pytest tests/test_query_expander.py tests/test_conversation_memory.py -q`

---

## Task 6: Build GGUF inference layer

Objective: Generate structured Indonesian answers using Gemma 4 E4B GGUF via llama.cpp.

Files:
- Create: `pipeline/inference.py`
- Create: `tests/test_inference.py`

Requirements:
- Lazy model loading.
- Structured answer format: Ringkasan / Detail Regulasi / Saran Teknis / Sumber.
- Confidence-gated fallback output.
- Citation-aware prompt building.
- Configurable generation parameters.

Verification:
- `pytest tests/test_inference.py -q`

---

## Task 7: Replace UI with Streamlit

Objective: Ship a clean Streamlit interface for demo and thesis use.

Files:
- Modify: `ui/app.py`
- Create: `tests/test_ui_smoke.py`

Requirements:
- Streamlit chat UI.
- Display disclaimers and confidence state.
- Preserve advisory module entry points where practical, but make regulation QA the primary flow.
- Render structured outputs cleanly without Gradio HTML/CSS pain.

Verification:
- `pytest tests/test_ui_smoke.py -q`
- `python -m compileall ui`

---

## Task 8: Add evaluation harness

Objective: Prove v2 quality with a reusable RAGas evaluation flow.

Files:
- Create: `pipeline/eval/ragas_eval.py`
- Create: `tests/test_ragas_eval.py`

Requirements:
- Golden query loader.
- RAGas metrics: context precision, answer relevancy, faithfulness.
- Export results to JSON/CSV.
- Support small local dry-run without live model.

Verification:
- `pytest tests/test_ragas_eval.py -q`

---

## Task 9: Add Colab wrapper and update docs

Objective: Support both proper repo usage and one-click Colab execution.

Files:
- Create: `arsitrad_v2.ipynb`
- Modify: `README.md`

Requirements:
- Notebook clones repo, installs deps, downloads GGUF, and launches the app or sample pipeline.
- README reflects v2 architecture and usage.

Verification:
- Notebook JSON validates.
- README commands match actual file paths.

---

## Final verification

- `pytest tests -q`
- `python -m compileall pipeline ui`
- `git diff --stat`

Done means:
- Raw PDFs are re-parsed with semantic legal chunking.
- Retrieval stack is hybrid and confidence-gated.
- UI is Streamlit, not Gradio.
- Evaluation harness exists.
- Repo supports both standalone and Colab execution.
