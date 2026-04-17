# Arsitrad v2

> RAG assistant for Indonesian building regulations, permits, and architecture-adjacent compliance questions.

Arsitrad v2 is the current path in this repo.

It uses:
- semantic legal chunking by structure (`BAB`, `Bagian`, `Paragraf`, `Pasal`, `Ayat`)
- `intfloat/multilingual-e5-large` embeddings
- Postgres + pgvector for dense retrieval
- JSONL + BM25 for sparse retrieval
- RRF fusion + reranking
- confidence-gated answers and explicit fallback behavior
- GGUF Gemma 4 inference
- Streamlit for the UI

The old v1 stack (`rag/`, `fine-tune/`, older notebooks, MiniLM/Chroma/LoRA-era code) is still in the repo as reference material, but it is not the primary implementation anymore.

## What Arsitrad is for

Arsitrad is built to answer questions like:
- what documents are needed for PBG or SLF
- what KDB / KDH / GSB / RTRW / RDTR constraints apply
- what fire-safety, accessibility, seismic, or heritage rules are relevant
- which national rules should be prioritized before falling back to local regulations

It is intentionally not a general design assistant. If the question is about style, aesthetics, or vague concept design, the system should refuse cleanly instead of bluffing.

## Current repo reality

- Main repo path: `arsitrad/`
- Current implementation branch in active use: `feat/arsitrad-v2-rag`
- Corpus roots:
  - `data/corpus/indonesian-construction-law`
  - `data/corpus/local_regulations`
- Checked-in corpus snapshot: 110 PDF documents
- Sparse artifact path: `data/processed/v2/bm25_corpus.jsonl`
- Starter evaluation set: `data/eval/golden_queries.json`
- Tests: `tests/`
- Streamlit app: `ui/app.py`
- Colab wrapper notebook: `arsitrad_v2.ipynb`

## Architecture

```text
Raw PDFs
  -> semantic chunker
  -> sparse JSONL corpus
  -> E5 embeddings
  -> pgvector storage
  -> dense retrieval + BM25 retrieval
  -> RRF fusion
  -> reranker
  -> confidence gate
  -> GGUF inference
  -> Streamlit UI
```

## Repo layout

```text
arsitrad/
├── agent/                         # legacy advisory modules still reused by UI tabs
├── data/
│   ├── corpus/                    # raw national + local PDF corpus
│   ├── eval/                      # starter goldens + audit outputs
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
└── arsitrad_v2.ipynb
```

## Quick start

### 1. Create an environment and install dependencies

```bash
python -m venv .venv-rag
source .venv-rag/bin/activate
python -m pip install -r requirements.txt
```

### 2. Configure the database

Tracked `config.yaml` is now portable on purpose.
It does not ship with a machine-specific Postgres socket DSN anymore.

If you want pgvector-backed ingest or dense retrieval, set your own database URL first:

```bash
export ARSITRAD_DATABASE_URL='postgresql://user:***@host:5432/arsitrad_v2'
```

If `ARSITRAD_DATABASE_URL` is not set, Arsitrad can still use the sparse JSONL/BM25 path, but dense retrieval and embedding writes to Postgres will be unavailable.

Schema lives in `db/schema.sql`.

### 3. Dry-run the ingestion pipeline

This reparses PDFs and writes sparse artifacts without writing embeddings to Postgres.

```bash
python -m pipeline.ingest --config config.yaml --dry-run --limit-docs 5
```

### 4. Full ingest from PDFs

```bash
python -m pipeline.ingest --config config.yaml --with-embeddings
```

### 5. Reuse an existing sparse artifact

If the JSONL sparse corpus already exists and you only want to rebuild embeddings into pgvector:

```bash
python -m pipeline.ingest --config config.yaml --from-sparse --with-embeddings
```

### 6. Rewrite sparse metadata without recomputing embeddings

Useful when taxonomy or metadata heuristics change.

```bash
python -m pipeline.ingest \
  --config config.yaml \
  --from-sparse \
  --rewrite-sparse-metadata \
  --metadata-only
```

### 7. Run the Streamlit app

```bash
streamlit run ui/app.py
```

## Retrieval behavior

Arsitrad v2 does a few deliberate things:
- rewrites colloquial permit terms such as `IMB` <-> `PBG`
- rewrites follow-up questions into standalone retrieval queries
- applies metadata filters like region, topic, building use, year, and regulation type when detectable
- blends dense and lexical retrieval instead of trusting one signal blindly
- uses fallback behavior when confidence is too low
- short-circuits obviously out-of-scope design-style questions

In a legal-regulatory assistant, refusal is better than confident nonsense.

## Evaluation

Starter goldens live at:

```text
data/eval/golden_queries.json
```

RAGAS dry-run example:

```bash
python -m pipeline.eval.ragas_eval \
  --questions data/eval/golden_queries.json \
  --output /tmp/arsitrad_eval.json \
  --dry-run
```

Lightweight retrieval audit outputs are stored under:

```text
data/eval/results/
```

## Tests

Run the full test suite:

```bash
pytest tests -q
```

Target specific modules when iterating on retrieval logic:

```bash
pytest tests/test_query_expander.py tests/test_retriever.py tests/test_taxonomy.py -q
```

## Notebook usage

Use `arsitrad_v2.ipynb` as a wrapper notebook, not as a separate source of truth.

The notebook is meant to clone the repo, install dependencies, load the GGUF model, and run the v2 pipeline from this codebase.

## Legacy code

The following are still present as references, but they are not the main shipped path:
- `rag/`
- `fine-tune/`
- older notebook artifacts
- older MiniLM / Chroma / LoRA assumptions in the repo history

If you are deciding where to extend Arsitrad today, use `pipeline/`, `db/`, `ui/`, `tests/`, and the v2 config block in `config.yaml`.

## Safety and scope

Arsitrad is an advisory tool.

It is not a substitute for:
- licensed professionals
- local planning authority guidance
- formal legal review

If retrieval confidence is weak or the question is outside regulatory scope, the correct behavior is to say so.
