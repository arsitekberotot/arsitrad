# Arsitrad v2 — Pure RAG Pipeline Specification

## Apa Itu Arsitrad v2

Tidak ada fine-tuning. Tidak ada LoRA. Tidak ada training data yang rusak.
Semua pengetahuan berasal dari retrieval — embeddings yang bagus, database yang stabil,
dan model GGUF yang bisa jalan di mana saja.

**Arsitektur:** GGUF Gemma 4 E4B + Hybrid Search (pgvector + BM25) + Reranking + Structured Output

---

## Use Cases (Concrete Scenarios)

### Use Case 1: Arsitek bantu klienurus PBG

**Scenario:** Rina, arsitek di Semarang, mau bikin rumah tinggal 2 lantai di tanah 120m². Kliennya minta bantuanurus PBG.

**User input:** *"Rumah tinggal 2 lantai di Semarang, tanah 120m², luas bangunan 90m². Apa saja dokumen untuk PBG dan estimasi biayanya?"*

**v2 output:**
```
RINGKASAN
Untuk PBG rumah tinggal 2 lantai di Semarang, Anda memerlukan dokumen teknis dan administratif. Estimasi biaya varier berdasarkan luas dan lokasi.

DETAIL REGULASI
[1] PP 16/2021 Pasal 15-20 — Persyaratan Administratif PBG meliputi: identitas pemohon, bukti hak atas tanah, dan rencana teknis arsitektur.
[2] Perda Kota Semarang No. 5/2009 Pasal 12 — KDB maksimal 70% untuk permukiman, KDH minimal 20% untuk ruang terbuka hijau.

SARAN TEKNIS
- Pastikan site plan menunjukkan RTH minimal 20% dari luas tanah
- KDB = (90/120) × 100% = 75% ← MELEBIHI batas 70%, perlu penyesuaian
- Gunakan koefisien lantai dasar (KLB) yang sesuai dengan RDTR kawasan
- Siapkan teknis struktur dan MEP untuk submit bersama PBG

SUMBER
[1] PP 16/2021, Pasal 15-20, hlm. 8-12
[2] Perda Semarang No. 5/2009, Pasal 12, hlm. 5
```

---

### Use Case 2: Investor cek regulasi untuk gudang industri

**Scenario:**PT Jaya Makmur mau bangun gudang 5.000m² di kawasan industri Balikpapan. Mereka perlu tahu KDB, KDH, dan syarat proteksi kebakaran.

**User input:** *"Bangun gudang 5000m² di kawasan industri Balikpapan. KDB, KDH, dan syarat proteksi kebakaran apa yang berlaku?"*

**v2 output:**
```
RINGKASAN
Untuk gudang di kawasan industri Balikpapan: KDB 60-70%, KDH minimal 10%, dan wajib dilengkapi sistem proteksi kebakaran sprinkler + hydrant.

DETAIL REGULASI
[1] Perda Kota Balikpapan No. 3/2009 Pasal 8 — KDB kawasan industri 60-70%, KDH minimal 10% dari luas lahan.
[2] Permen PU 26/2008 Pasal 15 — Bangunan >2.500m² wajib sprinkler otomatis dan hydrant.
[3] SNI 03-1746-2000 — Standar sistem proteksi kebakaran untuk gedung industri.

SARAN TEKNIS
- Untuk gudang 5.000m², KDB 60-70% berarti luas tanah minimal ~7.143m²
- Wajib memiliki kolam pemadam (jika tidak tersedia jaringan hydrant publik)
- Tangga darurat bukan wajib untuk gudang, tapiEXIT route tetap harus tersedia
- Koordinasi dengan Dinas Pekerjaan Umum untuk KDB/KDH clearance

SUMBER
[1] Perda Balikpapan No. 3/2009, Pasal 8, hlm. 4
[2] Permen PU 26/2008, Pasal 15, hlm. 22
[3] SNI 03-1746-2000, Pasal 10, hlm. 15
```

---

### Use Case 3: Mahasiswa arsiteksi belajar untuk ujian

**Scenario:**Andi, mahasiswa semester 7, sedang belajar untuk ujian Tata Cara Perencanaan Ketahanan Gempa. Dia tanya tentang spektrum respons desain.

**User input:** *"Jelaskan spektrum respons desain untuk zona gempa 3 di Indonesia, dan bagaimana cara menghitung gaya geser dasar?"*

**v2 output:**
```
RINGKASAN
Zona gempa 3 di Indonesia menggunakan percepatan puncak batuan dasar (PGA) 0,25g. Spektrum respons desain dihitung berdasarkan SNI 1726:2019 dengan período karakteristik (Ss dan S1) untuk lokasi spesifik.

DETAIL REGULASI
[1] SNI 1726:2019 Pasal 6 — Spektrum respons desain ditentukan dari nilai Ss (percepatan respons spektral 0,2 detik) dan S1 (1 detik).
[2] SNI 1726:2019 Pasal 7 — Untuk zona 3, faktor redundansi (ρ) minimum 1,0 untuk sistem seismik reguler.
[3] SNI 1727:2020 Pasal 4 — Kombinasi beban: 1,2D + 1,0E + 1,0L untuk kondisi ordinary.

SARAN TEKNIS
- Gunakan peta hazard gempa Indonesia 2010 untuk cari Ss dan S1 lokasi proyek
- Hitung gaya geser dasar: V = Cs × W, dimana Cs = SDS / (Rd/I)
- Untuk bangunan biasa, Rd = 5,5 (SRPMK) atau Rd = 3,5 (SRPB)
- Perioda fundamental pendekatan: Ta = Ct × hn^x (lihat Tabel SNI 1726)

SUMBER
[1] SNI 1726:2019, Pasal 6, hlm. 14
[2] SNI 1726:2019, Pasal 7, hlm. 18
[3] SNI 1727:2020, Pasal 4, hlm. 6
```

---

### Use Case 4: Owner mau renovasi heritage building

**Scenario:**Pak Hendra punya bangunan tua di kawasan heritage Bandung. Mau renovasiFacade tapi tidak boleh ubah struktur. Dia bingung apa boleh.

**User input:** *"Renovasi fasad bangunan tua di kawasan heritage Bandung. Apa saja yang boleh dan tidak boleh diubah?"*

**v2 output:**
```
RINGKASAN
Di kawasan heritage Bandung, renovasi fasad umumnya DILARANG diubah karena masuk kategori bangunan cagar budaya. Yang boleh: interior, MEP, dan struktur penahan beban tambahan.

DETAIL REGULASI
[1] Perda Kota Bandung No. 11/2011 Pasal 18 — Bangunan di kawasan heritage禁止direnovasi padafasad tanpa izin konservasi.
[2] PP 18/2015 Pasal 45 — Renovasi bangunan cagar budaya wajib mempertahankan minimum 75% elemen arsitektur asli.
[3] Permen CKMP No. 6/2012 — Izin renovasi heritage diajukan ke Badan Konservasi Daerah.

SARAN TEKNIS
- Urus izin ke Badan Konservasi Kota Bandung terlebih dahulu
- Jika mengubah struktur, wajib ajukanSLF baru setelah renovasi
- Interior boleh diubah, tapiutilitas (listrik, air) harus sesuai SNI terkini
- Simpan dokumentasi foto sebelum renovasi untuk提交ke konservasi

SUMBER
[1] Perda Bandung No. 11/2011, Pasal 18, hlm. 9
[2] PP 18/2015, Pasal 45, hlm. 22
[3] Permen CKMP No. 6/2012, Pasal 8, hlm. 4
```

---

### Use Case 5:边缘案例 — tidak ada regulasi yang relevan

**User input:** *"Buat saya desain rumah minimalis 100m² dengan tema Jepang skandinavia fusion."*

**v2 output:**
```
Maaf, saya tidak menemukan regulasi yang relevan untuk pertanyaan Anda.

Pertanyaan Anda berkaitan dengan desain arsitektur (gaya Jepang-Skandinavia fusion),
bukan regulasi konstruksi atau perizinan bangunan.

Saran saya:
- Untuk ide desain, Anda bisa konsultasi dengan arsitek atau browse platform seperti ArchDaily, Pinterest, atau Dezeen.
- Untuk regulasi, coba tanyakan hal spesifik seperti: "Syarat PBG untuk rumah tinggal di [kota]?" atau "KDB KDH untuk kawasan [nama kawasan]?"

Apakah ada pertanyaan lain tentang regulasi atau perizinan bangunan di Indonesia?
```

---

## Pipeline Architecture

```
User Question (Bahasa Indonesia)
        │
        ▼
┌─────────────────────────┐
│  Query Embedding         │  ← intfloat/multilingual-e5-base-v2
│  (1024-dim vector)      │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Hybrid Search           │
│  ├─ Dense: pgvector     │  ← top 20 cosine similarity
│  └─ Sparse: BM25        │  ← top 20 lexical match
│       → RRF Fusion       │  ← combine both ranked lists
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Reranker               │  ← BAAI/bge-reranker-base
│  top 20 → top 5         │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Prompt Builder         │  ← system + context + question
│  with citations [N]     │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  GGUF Inference         │  ← llama.cpp + gemma-4-E4B-it Q4_K_M
│  gemma-4-e4b-it.gguf    │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Response Formatter      │  ← structured output
│  Ringkasan / Detail /   │
│  Sumber [1][2][3]       │
└─────────────────────────┘
```

---

## Komponen Spec

### 1. Embedder

```
Model: intfloat/multilingual-e5-base-v2
Dimensionality: 1024 (vs 384 dari MiniLM-L12-v2)
Size: ~515MB
```

**Kenapa lebih baik untuk legal Indonesia:**
- D training涵盖140+语言，包括Bahasa Indonesia
- D训练数据包含140多种语言，包括印度尼西亚语
- E5 model family专为retrieval优化，performance强于MiniLM
- 1024维 vs 384维 =更多信息density untuk legal text

**Alternative:** `BAAI/bge-base-indonesian` —专用Indonesian embedder, tapi E5 lebihterbukti secaraumum

**Chunking strategy:**
```
Chunk size: 768 tokens (bukan 512 character)
Overlap: 128 tokens
Split by: "\n\n" (pasal) > "\n" (paragraf) > ". " (kalimat)
Jangan split tengah article —legal text butuh konteks penuh
```

### 2. Vector Database — Postgres + pgvector

```
Setup: Postgres 15+ dengan extension pgvector
Schema:
  regulations (
    id          UUID PRIMARY KEY,
    content     TEXT NOT NULL,
    embedding   vector(1024),
    metadata    JSONB  -- source, page, article_num, reg_type
    created_at  TIMESTAMP DEFAULT NOW()
  )

Index: CREATE INDEX ON regulations USING hnsw (embedding vector_cosine_ops)
```

**Kenapa Postgres:**
- Kaggle support Postgres via Cloud SQL atau local
- pgvector lebihstabil dari ChromaDB di notebook environment
- Tidak ada filesystem corruption
- Bisa query SQL biasa + vector search bersamaan
- Backup/restore trivial

**Connection:**
```python
import psycopg2
conn = psycopg2.connect(os.environ["DATABASE_URL"])
```

### 3. Hybrid Search

**Dense search (pgvector):**
```sql
SELECT id, content, metadata,
  1 - (embedding <=> %s) AS similarity
FROM regulations
ORDER BY embedding <=> %s
LIMIT 20;
```

**Sparse search (BM25):**
```python
from rank_bm25 import BM25Okapi
# tokenize semua chunks → build BM25 index
# query → top 20 scores
```

**Fusion — Reciprocal Rank Fusion (RRF):**
```python
def rrf_fusion(dense_results, sparse_results, k=60):
    scores = {}
    for rank, item in enumerate(dense_results):
        scores[item['id']] += 1 / (k + rank)
    for rank, item in enumerate(sparse_results):
        scores[item['id']] += 1 / (k + rank)
    return sorted(scores, key=scores.get, reverse=True)
```

RRF lebih baik dari weighted sum — tidak perlu tuning alpha.

### 4. Reranker

```
Model: BAAI/bge-reranker-base
Size: ~400MB
Input: (query, document) pairs
Output: relevance score 0-1
Process: top 20 → rerank → top 5
```

**Kenapa perlu reranker:**
Retrieval awal mengambil 20 candidate, banyak noise.
Cross-encoder reranker punya akses ke query + document bersamaan,
bukan terpisah seperti bi-encoder embedding.

### 5. Inference — GGUF Gemma 4 E4B

```
Model: ggml-org/gemma-4-E4B-it-GGUF
Quantization: Q4_K_M
File size: ~4.5GB
Backend: llama-cpp-python
```

**GGUF file selection di HuggingFace:**
- `ggml-org/gemma-4-E4B-it-GGUF` — official ggml release
- `unsloth/gemma-4-E4B-it-GGUF` — Unsloth optimized
- `lmstudio-community/gemma-4-E4B-it-GGUF` — LM Studio community

**Generation config:**
```python
{
    "temperature": 0.2,      # low = lebih factual, kurang halusin
    "max_tokens": 1024,
    "top_p": 0.9,
    "repeat_penalty": 1.1,
    "stop": ["<end_of_turn>", "<eos>"]
}
```

**System prompt:**
```
Kamu adalah Arsitrad, asisten AI untuk regulasi dan saran arsitektur di Indonesia.
Kamu menjawab berdasarkan peraturan pembangunan Indonesia (UU, PP, Permen, SNI, Perda).
Selalu cite sumber dengan [N] saat menggunakan konteks regulasi.
Format jawaban: Ringkasan, Detail Regulasi, Saran Teknis, Sumber.
```

### 6. Response Formatting

**Target format:**
```
══════════════════════════════════════
RINGKASAN
Gedung 10 lantai di Jakarta wajib memenuhi KDS D berdasarkan SNI 1726:2019.
Struktur harus SRPMK dengan daktilitas penuh.

DETAIL REGULASI
[1] SNI 1726:2019 Pasal 4 — Klasifikasi Desain Seismik
[2] Permen PU 26/2008 Pasal 7 — Persyaratan SRPMK

SARAN TEKNIS
- Gunakan kolom lift dengan tulangan khusus gempa
- Tangga darurat terpresurisasi setiap 24m
- Kombinasi beban: 1.2D + 1.0E + 1.0L

SUMBER
[1] SNI 1726:2019, Pasal 4, hlm. 12
[2] Permen PU 26/2008, Pasal 7, hlm. 45
══════════════════════════════════════
```

**Format rules:**
- Always Indonesian language
- Citations [N] wajib untuk setiap klaim dari regulasi
- Ringkasan singkat dulu (2-3 sentences), baru detail
- Graceful fallback kalau tidak ada context: "Maaf, saya tidak menemukan regulasi yang relevan untuk pertanyaan ini."

---

## Prompt Template

```python
SYSTEM_PROMPT = """Kamu adalah Arsitrad, asisten AI untuk regulasi dan saran arsitektur di Indonesia.
Kamu menjawab berdasarkan peraturan pembangunan Indonesia (UU, PP, Permen, SNI, Perda).
Selalu cite sumber dengan [N] saat menggunakan konteks regulasi.
Format jawaban:
1. RINGKASAN — jawaban singkat 2-3 kalimat
2. DETAIL REGULASI — penjelasan dengan [N] citation
3. SARAN TEKNIS — rekomendasi praktis jika applicable
4. SUMBER — daftar semua sumber [N] dengan nama dan halaman

Jika tidak ada regulasi yang relevan, jawab: "Maaf, saya tidak menemukan regulasi yang relevan untuk pertanyaan ini."
"""

USER_PROMPT = """KONTEKS REGULASI:
{context}

PERTANYAAN: {question}

JAWABAN (dalam Bahasa Indonesia):"""

def build_prompt(question, retrieved_chunks):
    context = "\n\n".join([
        f"[{i+1}] {c['content']}\n(Source: {c['metadata']['source']}, {c['metadata'].get('article', 'N/A')})"
        for i, c in enumerate(retrieved_chunks)
    ])
    return SYSTEM_PROMPT + "\n\n" + USER_PROMPT.format(
        context=context,
        question=question
    )
```

---

## Kaggle Notebook Structure

```python
# Cell 1 — Install dependencies
!pip install llama-cpp-python psycopg2-binary \
  sentence-transformers rank-bm25 FlagEmbedding \
  gradio psycopg2-ext

# Cell 2 — Postgres setup
# Option A: Kaggle Cloud SQL
# Option B: Local Postgres via docker
# Option C: Connect to remote Postgres

import os
os.environ["DATABASE_URL"] = "postgresql://user:pass@host:5432/arsitrad"

# Cell 3 — Data ingestion
from pipeline.ingest import RegulationIngester
ingester = RegulationIngester(embedder_model="intfloat/multilingual-e5-base-v2")
ingester.load_regulations("./data/regulations/")
ingester.chunk_and_embed()
ingester.store_to_postgres(os.environ["DATABASE_URL"])

# Cell 4 — Retrieval setup
from pipeline.retrieval import HybridRetriever
retriever = HybridRetriever(
    embedder="intfloat/multilingual-e5-base-v2",
    reranker="BAAI/bge-reranker-base",
    db_url=os.environ["DATABASE_URL"]
)

# Cell 5 — GGUF model loading
from pipeline.inference import GGUFInference
model = GGUFInference(
    model_path="./models/gemma-4-E4B-it-Q4_K_M.gguf",
    n_ctx=4096,
    n_gpu_layers=33  # T4: 16GB VRAM, set to use full GPU
)

# Cell 6 — Generation
def ask(question: str):
    chunks = retriever.retrieve(question, top_k=5)
    prompt = build_prompt(question, chunks)
    answer = model.generate(prompt)
    return format_answer(answer, chunks)

# Cell 7 — Gradio UI
import gradio as gr
gr.ChatInterface(fn=ask, ...).launch()
```

---

## File Structure v2

```
arsitrad_v2/
├── data/
│   ├── regulations/           # HTML/PDF source files
│   │   ├── pp_16_2021/
│   │   ├── sni_1726_2019/
│   │   └── perda_*/           # Regional regulations
│   └── processed/
│       ├── chunks.json        # Pre-chunked documents
│       └── metadata.json
├── pipeline/
│   ├── __init__.py
│   ├── ingest.py              # Chunking + embedding + PG storage
│   ├── retrieval.py           # Hybrid search + reranking
│   ├── inference.py           # GGUF loading + generation
│   └── format.py              # Response structuring
├── db/
│   ├── postgres_schema.sql    # Table + index DDL
│   └── migrations/
├── models/
│   └── gemma-4-E4B-it-Q4_K_M.gguf
├── notebooks/
│   └── arsitrad_v2_kaggle.ipynb
├── ui/
│   └── gradio_app.py
├── config.yaml
└── requirements.txt
```

---

## Implementation Priority

```
Priority 1 —的基础 (能不能跑起来)
  [ ] Setup Postgres + pgvector
  [ ] Buat schema + index
  [ ] Load existing ChromaDB data → Postgres (mapping)

Priority 2 — Retrieval (答案质量)
  [ ] Hybrid search (dense + BM25 + RRF)
  [ ] Add reranker
  [ ] Test retrieval precision dengan sample queries

Priority 3 — Inference (能不能生成)
  [ ] Download GGUF file
  [ ] Test llama.cpp inference
  [ ] Integrate retrieval → generation pipeline

Priority 4 — Output (格式化)
  [ ] Structured prompt template
  [ ] Output parsing + validation
  [ ] Graceful "tidak ditemukan" responses

Priority 5 — UI + Demo
  [ ] Gradio chat interface
  [ ] Fix UI/UX (current v1 UI is bad)
  [ ] Test full pipeline E2E
```

---

## Sample Queries untuk Testing

```python
TEST_QUERIES = [
    "Apa persyaratan PBG untuk gedung 5 lantai di Jakarta?",
    "Berapa KDB dan KDH maksimum untuk kawasan permukiman di Semarang?",
    "Bagaimana prosedur mendapatkan Sertifikat Layak Fungsi?",
    "Ketentuan tangga darurat untuk bangunan gedung tinggi?",
    "Syarat minimum通风 untuk bangunan gedung laboratorium?",
]
```

---

## Perbandingan v1 → v2

| Aspek | v1 (LoRA fine-tune) | v2 (Pure RAG) |
|-------|---------------------|----------------|
| Training | 151 examples, many broken | No training |
| Model | E2B 4-bit | E4B GGUF Q4_K_M |
| Retrieval | ChromaDB (broken on Kaggle) | pgvector (stable) |
| Embedder | MiniLM 384-dim | E5-base 1024-dim |
| Indonesian | Weak | Better (E4B) |
| Offline | No (needs HF download) | GGUF cached = yes |
| Response format | Raw text | Structured [citation] |
| Maintenance | Retrain when data bad | Update DB only |
| Hackathon risk | High (OOM, ChromaDB errors) | Low (proven stack) |

---

## Expected Improvements

- **Retrieval precision:** ~60-70% → ~85% (better embedder + reranker)
- **Answer quality:** Generic → Specific dengan citation yang benar
- **Kaggle stability:** ChromaDB errors → Zero filesystem issues
- **Indonesian fluency:** Cramped E2B → Natural E4B
- **Offline capability:** No (needs HF) → Yes (GGUF cached)
- **Response format:** Unstructured → Ringkasan/Detail/Sumber/Saran

---

## Catatan untuk Thesis

Arsitrad v2 lebih align dengan judul thesis:
"RAG Chatbot untuk Regulatory Perundang-undangan Konstruksi Indonesia"

Fine-tuning itu research yang interesting, tapi:
1. 151 training examples tidak cukup untuk 2B model
2. Half-baked fine-tune menghasilkan jawaban generic
3. Pure RAG dengan retrieval berkualitas lebih baik untuk use case ini

Thesis narrative: "Kami membangun RAG pipeline dengan hybrid search + reranking
untuk grounding jawaban Gemma 4 pada regulasi Indonesia."

---

## Database Schema (Postgres + pgvector)

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Main regulations table
CREATE TABLE regulations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content     TEXT NOT NULL,
    embedding   vector(1024),  -- e5-base-v2 outputs 1024-dim

    -- Metadata
    metadata    JSONB NOT NULL DEFAULT '{}',
    -- metadata fields: {
    --   "source": "PP_16_2021",
    --   "title": "Peraturan Pemerintah Nomor 16 Tahun 2021",
    --   "reg_type": "pp|nasional|sni|perda|pergub",
    --   "article": "Pasal 15",
    --   "page": 12,
    --   "year": 2021,
    --   "region": "nasional|jakarta|semarang|bandung|etc",
    --   "tags": ["pbg", "perizinan", "bangunan_gedung"]
    -- }

    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

-- HNSW index for fast cosine similarity search
CREATE INDEX ON regulations
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- B-tree indexes on metadata fields for filtering
CREATE INDEX ON regulations USING btree ((metadata->>'reg_type'));
CREATE INDEX ON regulations USING btree ((metadata->>'source'));
CREATE INDEX ON regulations USING btree ((metadata->>'region'));

-- Full-text search index (for BM25 hybrid)
CREATE INDEX ON regulations USING gin(to_tsvector('indonesian', content));

-- View for BM25-amenable search
CREATE MATERIALIZED VIEW regulation_fts AS
SELECT id, to_tsvector('indonesian', content) AS fts_vector
FROM regulations;

CREATE INDEX ON regulation_fts USING gin(fts_vector);
```

---

## BM25 Implementation

```python
# pipeline/bm25.py
from rank_bm25 import BM25Okapi
import os
import json

class BM25Index:
    def __init__(self, persist_path="./data/bm25_index.json"):
        self.persist_path = persist_path
        self.bm25 = None
        self.corpus_ids = []
        self.tokenized_corpus = []

    def build(self, chunks: list[dict]):
        """Build BM25 index from regulation chunks.

        Args:
            chunks: list of {"id": uuid, "content": text, "metadata": {...}}
        """
        self.corpus_ids = [c["id"] for c in chunks]
        self.tokenized_corpus = [self._tokenize(c["content"]) for c in chunks]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

        # Persist for reuse
        with open(self.persist_path, "w") as f:
            json.dump({"corpus_ids": self.corpus_ids}, f)

    def _tokenize(self, text: str) -> list[str]:
        """Indonesian-aware tokenization."""
        import re
        text = text.lower()
        # Split on alphanumeric sequences
        tokens = re.findall(r'\w+', text)
        # Remove very short tokens
        tokens = [t for t in tokens if len(t) > 2]
        return tokens

    def search(self, query: str, top_k: int = 20) -> list[dict]:
        """Search BM25 index.

        Returns: list of {"id": uuid, "score": float}
        """
        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        # Get top-k
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        return [
            {"id": self.corpus_ids[i], "bm25_score": float(scores[i])}
            for i in top_indices if scores[i] > 0
        ]

    def load(self):
        """Load persisted index."""
        if os.path.exists(self.persist_path):
            with open(self.persist_path) as f:
                data = json.load(f)
            self.corpus_ids = data["corpus_ids"]
            # Rebuild tokenized corpus from DB
            # (skipped for brevity — in practice, reload from DB)
```

---

## Hybrid Retrieval Code

```python
# pipeline/retrieval.py
from typing import Optional
import numpy as np

class HybridRetriever:
    def __init__(
        self,
        embedder,          # SentenceTransformer
        reranker,          # FlagReranker
        pg_conn,           # psycopg2 connection
        bm25_index: BM25Index,
    ):
        self.embedder = embedder
        self.reranker = reranker
        self.conn = pg_conn
        self.bm25 = bm25_index

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Full hybrid retrieval pipeline.

        1. Dense search via pgvector (top 20)
        2. BM25 search (top 20)
        3. Reciprocal Rank Fusion
        4. Rerank top 20 → top 5
        5. Return enriched chunk objects
        """
        # Step 1: Dense vector search
        dense_results = self._dense_search(query, top_k=20)

        # Step 2: BM25 search
        bm25_results = self.bm25.search(query, top_k=20)

        # Step 3: RRF fusion
        fused = self._rrf_fusion(dense_results, bm25_results, k=60)

        # Step 4: Rerank
        reranked = self._rerank(query, fused, top_k=top_k)

        return reranked

    def _dense_search(self, query: str, top_k: int) -> list[dict]:
        """pgvector cosine similarity search."""
        import psycopg2
        q_emb = self.embedder.encode([query])[0]
        # Normalize
        q_emb = q_emb / np.linalg.norm(q_emb)

        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT id, content, metadata,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM regulations
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (q_emb.tolist(), q_emb.tolist(), top_k))

                results = cur.fetchall()
                return [
                    {"id": str(r[0]), "content": r[1], "metadata": r[2], "dense_score": float(r[3])}
                    for r in results
                ]

    def _rrf_fusion(
        self,
        dense_results: list[dict],
        bm25_results: list[dict],
        k: int = 60
    ) -> list[dict]:
        """Reciprocal Rank Fusion — combine ranked lists."""
        scores = {}
        rrf_scores = {}

        # Normalize dense scores to [0, 1]
        max_dense = max(r["dense_score"] for r in dense_results) if dense_results else 1
        for rank, r in enumerate(dense_results):
            normalized = r["dense_score"] / max_dense
            r["dense_score_norm"] = normalized
            r["rrf_score"] = 1 / (k + rank)
            scores[r["id"]] = r

        # BM25 scores — normalize
        max_bm25 = max(r["bm25_score"] for r in bm25_results) if bm25_results else 1
        for rank, r in enumerate(bm25_results):
            r["bm25_score_norm"] = r["bm25_score"] / max_bm25
            r["rrf_score"] = r.get("rrf_score", 0) + 1 / (k + rank)
            if r["id"] in scores:
                scores[r["id"]].update(r)
            else:
                scores[r["id"]] = r

        # Sort by RRF score
        sorted_results = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)
        return sorted_results[:20]  # Return top 20 for reranking

    def _rerank(self, query: str, candidates: list[dict], top_k: int) -> list[dict]:
        """Cross-encoder reranking."""
        if not candidates:
            return []

        pairs = [(query, c["content"]) for c in candidates]
        rerank_scores = self.reranker.compute_score(pairs)

        for c, score in zip(candidates, rerank_scores):
            c["rerank_score"] = float(score)

        reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
        return reranked[:top_k]
```

---

## Response Formatting Code

```python
# pipeline/format.py
import re

def format_answer(
    raw_output: str,
    retrieved_chunks: list[dict],
    min_citation_score: float = 0.3
) -> str:
    """
    Parse and restructure Gemma output into standardized format.

    Args:
        raw_output: raw text from GGUF inference
        retrieved_chunks: list of chunk dicts with rerank_score
        min_citation_score: minimum rerank_score to include in sources

    Returns:
        Formatted string with RINGKASAN/DETAIL/SARAN/SUMBER sections
    """
    # Filter chunks above threshold
    cited_chunks = [
        c for c in retrieved_chunks
        if c.get("rerank_score", 0) >= min_citation_score
    ]

    # Extract citation numbers from raw output
    cited_numbers = set(int(n) for n in re.findall(r'\[(\d+)\]', raw_output))
    cited_numbers = sorted(cited_numbers)

    # Build source list (only cite chunks that appear in answer)
    sources = []
    for i, chunk in enumerate(cited_chunks[:len(cited_numbers)], 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", "Unknown")
        article = meta.get("article", "")
        page = meta.get("page", "N/A")
        sources.append(f"[{i}] {source}, {article}, hlm. {page}")

    # Structure: put raw output under RINGKASAN, add sources
    lines = raw_output.strip().split("\n")
    ringkasan = "\n".join(lines[:6])  # First 6 lines as ringkasan

    output = f"""══════════════════════════════════════
RINGKASAN
{ringkasan}

SUMBER
""" + "\n".join(sources) if sources else ""

    return output


def graceful_not_found(user_query: str) -> str:
    """Response when no relevant regulations found."""
    return """Maaf, saya tidak menemukan regulasi yang relevan untuk pertanyaan Anda.

Pertanyaan Anda mungkin berkaitan dengan topik di luar cakupan regulasi
konstruksi dan perizinan bangunan di Indonesia.

Saran:
• Untuk regulasi spesifik: cantumkan nama kota/kawasan
• Untuk perizinan: sebutkan tipe bangunan (residensial, komersial, industri)
• Untuk SNI/teknis: sebutkan nomer SNI jika已知

Contoh pertanyaan yangvalid:
• "Syarat PBG untuk rumah tinggal di Surabaya?"
• "KDB KDH kawasan permukiman Jakarta Selatan?"
• "Ketentuan tangga darurat untuk gedung 8 lantai?"
"""


def parse_off_topic(query: str) -> bool:
    """Detect if query is off-topic (not about Indonesian building regulations)."""
    OFF_TOPIC_KEYWORDS = [
        "desain rumah", "cat warna", "furniture", "taman",
        "dapur", "kamar tidur", "dekorasi", "hjz", "skandinavia"
    ]
    query_lower = query.lower()
    return any(kw in query_lower for kw in OFF_TOPIC_KEYWORDS)
```

---

## More Use Cases

### Use Case 6: Dinas Pekerja Umum cek Kesesuaian Bangunan

**Scenario:** Bu Sri, inspector from DPU kota Semarang, sedang audit bangunan komersial di jalan utama. Mereka mau verifikasi apakah bangunan sesuai dengan PBG yang disetujui.

**User input:** *"Lapak di Jalan Pandanaran No. 45 Semarang, 3 lantai, luas bangunan 200m². Bagaimana prosedur audit kesesuaian dengan PBG dan apa konsekuensi jika tidak sesuai?"*

**v2 output:**
```
RINGKASAN
Audit kesesuaian PBG dilakukan oleh DPU/Dinas Teknis dengan memeriksa dokumen izin, kondisi fisik bangunan, dan kesesuaian dengan rencana teknis yang disetujui. Bangunan yang tidak sesuaifaces sanksi administratif.

DETAIL REGULASI
[1] PP 16/2021 Pasal 274 — Bangunan gedung wajib sesuai dengan PBG yang telah diterbitkan. Pemilik wajib melaporkan perubahan jika ada modifikasi.
[2] Perda Kota Semarang No. 5/2009 Pasal 45 — DPU berwenang melakukan inspeksi bangunan gedung minimal 1x per tahun untuk bangunan komersial.
[3] UU 28/2009 Pasal 37 — Bangunan tidak sesuai PBG subject terhadap penertiban dan sanksi dendas hingga penghentian penggunaan.

SARAN TEKNIS
- Minta salinan PBG dari pemilik dan bandingkan dengan kondisi eksisting
- Cek: luasan, ketinggian, KDB/KDH, jumlah lantai
- Jika ada deviasi: laporkan ke DPPMPTSP untuk proses penertiban
- Dacumentasi photo setiap ketidaksesuaian untuk laporan audit

SUMBER
[1] PP 16/2021, Pasal 274, hlm. 120
[2] Perda Semarang No. 5/2009, Pasal 45, hlm. 18
[3] UU 28/2009, Pasal 37, hlm. 25
```

---

### Use Case 7: Kontraktor cek Syarat Tender Proyek Pemerintah

**Scenario:** PT Konstruksi Indonesia mau ikut tender pembangunan rumah sakit di daerah. Mereka perlu tahu persyaratan khusus untuk bangunan kesehatan.

**User input:** *"Syarat tender pembangunan rumah sakit Kelas B di Jawa Tengah. Apa saja persyaratan khusus untuk bangunan kesehatan dan bagaimana ketentuan TKDN-nya?"*

**v2 output:**
```
RINGKASAN
Untuk rumah sakit Kelas B di Jawa Tengah, tender harus memenuhi Persyaratan Kualifikasi, ketentuan bangunan kesehatan sesuai Permenkes, dan TKDN minimum 25% sesuai Perpres 16/2018.

DETAIL REGULASI
[1] Permenkes 24/2020 Pasal 12 — Rumah sakit Kelas B wajib memiliki ruang terbuka hijau minimal 20% dari luas tanah, sistem proteksi radiasi, dan sistem udara bertekanan positif untuk ruang operasi.
[2] Perpres 16/2018 Pasal 12 — TKDN untuk jasa konstruksi minimum 25% untuk proyek pemerintah. Nilai TKDN dihitung dari komponen lokal: tenaga kerja, materials, dan overhead.
[3] PP 29/2000 Pasal 8 — Bangunan kesehatan wajib memenuhi standar kesehatan masyarakat termasuk standar air bersih, limbah medis, dan kontrol infeksi.

SARAN TEKNIS
- Pastikantim engineer memiliki Sertifikat Keahlian (SKA) dan SKT yang valid
- TKDN disclosure: hitung komponen lokal dari semua subkontraktor
- Persiapkan data dukungan: referensi proyek sejenis, daftar peralatan, dan CV tenaga ahli
- Checklist kelengkapan: izin lokasi, AMDAL, dan rekomendasi dari Dinas Kesehatan setempat

SUMBER
[1] Permenkes 24/2020, Pasal 12, hlm. 8
[2] Perpres 16/2018, Pasal 12, hlm. 6
[3] PP 29/2000, Pasal 8, hlm. 5
```

---

### Use Case 8: Warga affected flood evacuation planning

**Scenario:** Banjir bandang di Kalimantan Selatan mengancam permukiman di bantaran sungai. Warga perlu tahu apakah bangunan mereka di zone bahaya dan standar evakuasi.

**User input:** *"Apakah bangunan di bantaran Sungai Barito, Kalimantan Selatan, masuk zona bahaya banjir? Apa standar evakuasi dan tempat evakuasi sementara yang harus disediakan?"*

**v2 output:**
```
RINGKASAN
Bangunan di bantaran Sungai Barito dengan jarak <50m dari tepi sungai MASUK zona bahaya banjir bandang. Evakuasi wajib dilakukan untuk bangunan di zona berbahaya, dengan tempat evakuasi minimal 500m dari bantaran.

DETAIL REGULASI
[1] Perda Kalselteng No. 4/2018 Pasal 22 — Zona berbahaya banjir adalah area dengan jarak <50m dari tepi sungai untuk sungai dengan debit >500m³/detik.
[2] BNPB Peraturan 3/2016 Pasal 15 — Setiap permukiman di zona banjir wajib memiliki tempat evakuasi sementara dengan kapasitas minimal 30% dari penduduk, dengan jarak maksimal 1km dari permukiman.
[3] SNI 03-1746-2019 Pasal 11 — Perencanaan evkuensi untuk daerah banjir harus memperhitungkan kecepatan aliran dan ketinggian genangan.

SARAN TEKNIS
- Identifikasi elevasi bangunan vs Banjir Rencana (100 tahun ulang)
- Jika elevasi < banjir rencana: wajib_evakuasi, jangan digunakan sebagai tempat refuge
- Koordinasi dengan BNPB daerah untuk location tempat evakuasi sementara
- Pasang early warning system (EWS) dengan sensor ketinggian air
- Rencana jalur evakuasi: minimal 2 jalur, hindari throughfare yang bisa ter Ген flooded

SUMBER
[1] Perda Kalselteng No. 4/2018, Pasal 22, hlm. 12
[2] BNPB Peraturan 3/2016, Pasal 15, hlm. 9
[3] SNI 03-1746-2019, Pasal 11, hlm. 14
```

---

### Use Case 9: Mahasiswa arsitek hitung补贴(UTILITIES) untuk tugas

**Scenario:** Maya, mahasiswi arsitektur, lagi ngerjain tugas studio desain. Mereka harus hitung KDB, KLB, dan GSB untuk siteplan di Surabaya.

**User input:** *"Lahan 30x40 meter di Surabaya, zoning residensial. KDB 70%, KDH 20%, GSB 6m dari jalan. Hitung: (1) luas bangunan maksimal, (2) jumlah lantai jika bangunan 60% dari luas tanah, (3) jarak minimal ke batas samping."*

**v2 output:**
```
RINGKASAN
Untuk lahan 1.200m² di Surabaya zona residensial: bangunan maksimal 840m², GSB 6m dari jalan, jarak ke batas samping minimal 1,5m untuk 1 lantai.

PERHITUNGAN

(1) Luas Bangunan Maksimal (KDB 70%)
    KDB = 70% × 1.200m² = 840m²

(2) Jumlah Lantai (KLB = 0,6)
    KLB = 0,6 = Luas Total Lantai / Luas Tanah
    Luas Total Lantai = 0,6 × 1.200m² = 720m²
    → Cukup untuk 1 lantai penuh (720m² < 840m² KDB maks)

(3) GSB dan Jarak Batas Samping
    GSB = 6m dari tepi jalan
    Jarak batas samping (setback):
    - 1-2 lantai: minimal 1,5m
    - 3-4 lantai: minimal 2,0m
    - >4 lantai: minimal 3,0m

    Untuk bangunan 1 lantai: jarak minimal 1,5m ke batas samping

SUMBER
[1] Perda Surabaya No. 12/2014 tentang RWTR, Pasal 15
[2] Perda Surabaya No. 6/2009 tentang Bangunan Gedung, Pasal 8
```

---

### Use Case 10: Realtor cek izin短期居住(boarding house) di Bali

**Scenario:** Investor mau konversi villa menjadi penginapan (homestay/hostel) di area Wisata Ubud. Perlu tahu perizinan pariwisata dan bangunan.

**User input:** *"Konversi villa jadi penginapan 10 kamar di Ubud, Gianyar Bali. Izin apa saja yang diperlukan dari sisi bangunan dan pariwisata?"*

**v2 output:**
```
RINGKASAN
Konversi villa ke penginapan di Ubud membutuhkan PBG atau SLF变更 (jika sudah ada PBG), plus Tanda Daftar Usaha Pariwisata (TDUP) dari Dinas Pariwisata Bali.

DETAIL REGULASI
[1] Perda Gianyar No. 8/2017 Pasal 14 — Perubahan fungsi bangunan dari residensial ke komersial/tourism wajib mengajukan PBG baru atau perubahan PBG eksisting.
[2] Perda Bali No. 5/2020 Pasal 22 — TDUP untuk usaha penginapan dengan kapasitas >5 kamar wajib diajukan ke Dinas Pariwisata Kabupaten/Kota.
[3] Permen PU 24/2018 Pasal 8 — Penginapan dengan >8 kamar wajib memiliki sistem hydrant dan APAR sesuai standar.
[4] Perda Gianyar No. 9/2019 — homestay di kawasan wisata wajib memiliki minimum 2 parkiran untuk kendaraan roda 4.

SARAN TEKNIS
1. Urus dokumen: Sertifikat Laik Fungsi (SLF)变更 — karena ada perubahan jumlah pengguna
2. Parkiran: Siapkan 2-3 lot untuk tamu, perhitungkan dimensi 2,5m × 5m per mobil
3. Proteksi kebakaran: wajib tambah hydrant atau APAR CO2 untuk setiap lantai
4. Limbah: pisahkan limbah grey water dan black water, harus ada septic tank yang sesuai
5. TDUP: apply setelah IMB/PBG变更 selesai

SUMBER
[1] Perda Gianyar No. 8/2017, Pasal 14, hlm. 7
[2] Perda Bali No. 5/2020, Pasal 22, hlm. 11
[3] Permen PU 24/2018, Pasal 8, hlm. 4
[4] Perda Gianyar No. 9/2019, Pasal 5, hlm. 3
```

---

## Hackathon Demo Script

Untuk demo di hackathon, jalankan pipeline ini step-by-step:

```
DEMO FLOW (5 menit):

[0:00-0:30]开场
"Arsitrad — RAG chatbot untuk regulasi konstruksi Indonesia.
Menggunakan Gemma 4 E4B + hybrid search + pgvector.
Tidak ada fine-tuning — semua knowledge dari retrieval."

[0:30-1:30] Demo Query 1 — PBG Documents
Input: "Rumah tinggal 2 lantai di Semarang, tanah 120m². Dokumen PBG?"
Output: Structured answer dengan [1] PP 16/2021, KDB warning (75% > 70%)

[1:30-2:30] Demo Query 2 — KDB/KDH Check
Input: "Berapa KDB dan KDH maksimal untuk kawasan permukiman Surabaya?"
Output: Specific numbers dari Perda Surabaya dengan article citation

[2:30-3:30] Demo Query 3 — Disaster Resilience
Input: "Syarat tangga darurat untuk gedung 10 lantai di zona gempa tinggi?"
Output: Detailed requirements dari SNI + Permen PU

[3:30-4:30] Demo Query 4 — Graceful Decline
Input: "Buat saya desain interior minimalis"
Output: "Maaf, tidak ditemukan regulasi yang relevan. Saran..."

[4:30-5:00] Closing
"Arsitrad v2 — pure RAG, no fine-tuning.
Pipeline: E5 embedder → pgvector → BM25 → RRF → Reranker → Gemma 4 GGUF."
```

---

## Evaluation Metrics

```python
EVALUATION_METRICS = {
    "retrieval": {
        "precision@5": "Apakah 5 chunks teratas relevan dengan query?",
        "mrr": "Mean Reciprocal Rank — posisi chunk pertama yang relevan",
        "ndcg@5": "Normalized Discounted Cumulative Gain",
    },
    "generation": {
        "citation_accuracy": "Apakah [N] citation sesuai dengan chunk yang digunakan?",
        "answer_relevance": "Skor 1-5: apakah answer menjawab pertanyaan?",
        "hallucination_rate": "Apakah ada klaim yang tidak didukung chunk?",
    },
    "system": {
        "latency_p50": "Median response time (target: <3 detik)",
        "latency_p95": "95th percentile response time",
        "kaggle_stability": "Berapa % notebook runs yang berhasil tanpa error?",
    }
}
```
