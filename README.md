# Arsitrad — AI Advisor for Indonesian Architecture & Construction

<h3 align="center">Hybrid RAG Indonesian Building Regulation Advisor</h3>

<p align="center">
  <a href="https://github.com/arsitekberotot/arsitrad">GitHub</a> ·
  <a href="https://github.com/arsitekberotot/arsitrad/releases/tag/v2.0.0">Release v2.0.0</a> ·
  <a href="#-quick-start">Quick Start</a> ·
  <a href="#-architecture">Architecture</a> ·
  <a href="#-capabilities">Capabilities</a> ·
  <a href="#-evaluation--validation">Evaluation</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Release-v2.0.0-2563eb?style=flat" alt="Release v2.0.0" />
  <img src="https://img.shields.io/badge/Model-Gemma_4_E4B_GGUF-cc785c?style=flat&logo=google&logoColor=white" alt="Gemma 4 E4B GGUF" />
  <img src="https://img.shields.io/badge/Retrieval-Hybrid_RAG-2B6150?style=flat" alt="Hybrid RAG" />
  <img src="https://img.shields.io/badge/Dense-pgvector-9333FF?style=flat" alt="pgvector" />
  <img src="https://img.shields.io/badge/Sparse-BM25_JSONL-F97316?style=flat" alt="BM25 JSONL" />
  <img src="https://img.shields.io/badge/Corpus-110_PDFs-059669?style=flat" alt="Corpus 110 PDFs" />
  <img src="https://img.shields.io/badge/Sparse_Index-21,418_records-F59E0B?style=flat" alt="Sparse Index 21418 records" />
</p>

---

## The Problem

Indonesia has national and local building regulations spread across UU, PP, Permen, SNI, Perda, Pergub, and Perwali.
The hard part is not just finding a regulation — it is finding the right layer of regulation, prioritizing national rules correctly, handling local context when needed, and refusing when the question is outside regulatory scope.

Arsitrad v2 solves that with a hybrid retrieval pipeline grounded in real Indonesian building-regulation documents, plus confidence-aware answering so the system is less likely to bluff when the evidence is weak.

---

## What We Built

| | Feature | Description |
|---|---|---|
| **Hybrid Retrieval** | pgvector + BM25 + RRF + reranker | Dense and lexical retrieval are fused instead of trusting one signal blindly |
| **Semantic Chunking** | Legal-structure-aware parsing | Chunks follow `BAB`, `Bagian`, `Paragraf`, `Pasal`, `Ayat` instead of dumb fixed windows |
| **Grounded Inference** | GGUF Gemma 4 answer engine | Uses retrieved regulatory context, structured sections, and source citations |
| **Safe Fallbacks** | Confidence gate + out-of-scope refusal | Weak evidence and design-style questions are rejected cleanly instead of hallucinated |
| **Portable Runtime** | Sparse-first local path | Works with checked-in JSONL/BM25 without requiring a machine-specific database config |
| **Interactive UI** | Streamlit chat + helper tabs | Main regulation assistant plus permit, cooling, disaster, and settlement tools |

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/arsitekberotot/arsitrad.git
cd arsitrad
```

### 2. Install dependencies

```bash
python -m venv .venv-rag
source .venv-rag/bin/activate
python -m pip install -r requirements.txt
```

### 3. Optional: connect pgvector

Tracked `config.yaml` is intentionally portable.
It does not ship with a machine-local Postgres socket anymore.

If you want dense retrieval or embedding writes into Postgres, set your own database URL:

```bash
export ARSITRAD_DATABASE_URL='postgresql://user:***@host:5432/arsitrad_v2'
```

If you do not set `ARSITRAD_DATABASE_URL`, Arsitrad still runs with the checked-in sparse JSONL + BM25 path.

### 4. Run the UI

```bash
streamlit run ui/app.py
```

### 5. Or ask from Python

```python
from pipeline.inference import ArsitradAnswerEngine

engine = ArsitradAnswerEngine(config_path="config.yaml")
result = engine.answer("Apa syarat PBG untuk rumah tinggal 2 lantai di Semarang?")
print(result.answer)
print(result.retrieval.confidence)
```

If the GGUF model file is not available yet, Arsitrad falls back to retrieval-only output instead of crashing.

---

## Release Status

| Metric | Value |
|---|---|
| Release | `v2.0.0` |
| Main model runtime | `ggml-org/gemma-4-E4B-it-GGUF` |
| Dense retrieval | Postgres + `pgvector` |
| Sparse retrieval | `data/processed/v2/bm25_corpus.jsonl` |
| Checked-in corpus snapshot | 110 PDF documents |
| Sparse records | 21,418 |
| Full test suite | 57 passing |
| Starter evaluation set | `data/eval/golden_queries.json` |

---

## Architecture

```
                    +--------------------------------------------------+
                    |         Regulation Corpus (110 PDFs)             |
                    |   UU . PP . Permen . SNI . Perda . Pergub        |
                    +------------------------+-------------------------+
                                             |
                    +------------------------v-------------------------+
                    |  Semantic Legal Chunker                          |
                    |  BAB . Bagian . Paragraf . Pasal . Ayat          |
                    +------------------------+-------------------------+
                                             |
                          +------------------+-------------------+
                          |                                      |
          +---------------v----------------+   +---------------v----------------+
          |  Sparse Artifact                |   |  Dense Embeddings              |
          |  JSONL + BM25                   |   |  multilingual-e5-large         |
          |  21,418 records                 |   |  Postgres + pgvector           |
          +---------------+----------------+   +---------------+----------------+
                          |                                      |
                          +------------------+-------------------+
                                             |
                    +------------------------v-------------------------+
                    |  Hybrid Retrieval                               |
                    |  Query expansion . metadata filters . RRF       |
                    +------------------------+-------------------------+
                                             |
                    +------------------------v-------------------------+
                    |  Reranker + confidence gate                     |
                    |  fallback / refusal when evidence is weak       |
                    +------------------------+-------------------------+
                                             |
                    +------------------------v-------------------------+
                    |  Gemma 4 GGUF answer engine                     |
                    |  structured answer + citations                  |
                    +------------------------+-------------------------+
                                             |
                    +------------------------v-------------------------+
                    |  Streamlit UI + helper tabs                     |
                    +--------------------------------------------------+
```

---

## Capabilities

### 1. Regulation Q&A Assistant
The main shipped path in v2. Handles PBG, SLF, RDTR, RTRW, KDB, KDH, GSB, fire safety, accessibility, seismic requirements, and other regulation-grounded questions using hybrid retrieval and structured answers.

### 2. Building Permit Navigator
Generates permit-oriented guidance from project details such as building type, location, floor area, height, and function.

### 3. Passive Cooling Advisor
Provides climate- and material-aware passive-cooling guidance through the UI helper module.

### 4. Disaster Damage Reporter
Keeps the earlier damage-assessment helper available in the interface as a supporting module.

### 5. Settlement Upgrading Advisor
Retains the settlement-upgrading helper for broader architecture/planning workflows.

Note: the repo still contains legacy v1-era code, but the primary implementation path is now `pipeline/`, `db/`, `ui/`, `tests/`, and the `v2` block in `config.yaml`.

---

## Corpus & Retrieval Snapshot

| Category | Status |
|---|---|
| Raw corpus roots | `data/corpus/indonesian-construction-law` and `data/corpus/local_regulations` |
| Checked-in sparse artifact | `data/processed/v2/bm25_corpus.jsonl` |
| Sparse corpus size | 21,418 records |
| Dense storage target | `regulation_chunks` table in Postgres + pgvector |
| Eval goldens | `data/eval/golden_queries.json` |
| Audit outputs | `data/eval/results/` |

The current retrieval stack deliberately rewrites colloquial permit terms such as `IMB` ↔ `PBG`, handles follow-up questions as standalone retrieval queries, and routes weak or out-of-scope prompts toward fallback behavior instead of confident nonsense.

---

## Evaluation & Validation

Run the test suite:

```bash
pytest tests -q
```

Target retrieval-focused tests when iterating:

```bash
pytest tests/test_query_expander.py tests/test_retriever.py tests/test_taxonomy.py -q
```

RAGAS dry-run example:

```bash
python -m pipeline.eval.ragas_eval \
  --questions data/eval/golden_queries.json \
  --output /tmp/arsitrad_eval.json \
  --dry-run
```

Latest lightweight retrieval audit artifacts live in:

```text
data/eval/results/
```

---

## Tech Stack

- **Inference**: GGUF Gemma 4 E4B via `llama-cpp-python`
- **Dense retrieval**: Postgres + `pgvector`
- **Sparse retrieval**: JSONL + BM25
- **Embedder**: `intfloat/multilingual-e5-large`
- **Reranker**: `BAAI/bge-reranker-base`
- **Chunking / parsing**: semantic legal chunker + `pdfplumber`
- **UI**: Streamlit
- **Validation**: pytest + retrieval audits + RAGAS dry-run hooks

---

## Project Structure

```text
arsitrad/
├── agent/                         # helper/advisory modules reused by UI tabs
├── data/
│   ├── corpus/                    # raw national + local regulation PDFs
│   ├── eval/                      # golden queries + audit outputs
│   └── processed/v2/              # sparse artifacts and derived outputs
├── db/
│   └── schema.sql                 # pgvector schema
├── docs/plans/
│   └── 2026-04-16-arsitrad-v2-implementation.md
├── pipeline/
│   ├── chunker.py
│   ├── ingest.py
│   ├── retriever.py
│   ├── query_expander.py
│   ├── taxonomy.py
│   ├── conversation_memory.py
│   ├── inference.py
│   └── eval/ragas_eval.py
├── tests/
├── ui/
│   └── app.py
├── arsitrad_v2.ipynb              # wrapper notebook for repo-driven runs
├── legacy/
│   └── Arsitrad_Gemma4_Indonesian_Architecture_AI.ipynb  # legacy end-to-end notebook
├── config.yaml
└── requirements.txt
```

---

## Legacy v1 Context

The old v1 stack is still in the repository for historical reference:

- `rag/`
- `fine-tune/`
- `legacy/Arsitrad_Gemma4_Indonesian_Architecture_AI.ipynb`
- older MiniLM / Chroma / LoRA assumptions in repo history

That is reference material now, not the main shipped path.
If you are extending Arsitrad today, extend v2.

---

## Safety Note

Arsitrad is an advisory tool.
It is not a substitute for:

- licensed professionals
- local planning authority guidance
- formal legal review

If the evidence is weak or the question is outside regulatory scope, the correct behavior is to say so.

---

## License

CC BY 4.0 — see [`LICENSE`](LICENSE).
This repository is part of an entry for The Gemma 4 Good Hackathon by Google Deepmind on Kaggle.
