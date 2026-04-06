# Arsitrad — Indonesian Architecture AI Advisor

**Mission:** Build a comprehensive AI platform for Indonesian architecture and construction professionals — combining regulatory RAG (SNI, UU, PP, Permen) with advisory modules for disaster damage reporting, settlement upgrading, building permits, and passive cooling design.

**Tech Stack:** Gemma 4 (fine-tuned), RAG pipeline, function calling, Gradio UI, Docker (offline-capable)

**Reference:** Pasal.id won Anthropic's hackathon proving Indonesian law + AI works. We extend this into architecture-specific domains with advisory capabilities.

## Project Structure

```
arsitrad/
├── data/
│   ├── sni_corpus/          # SNI standards PDFs (to be downloaded)
│   ├── regulations/         # UU, PP, Permen text (scraped)
│   └── processed/          # chunked, embedded data
├── rag/
│   ├── embed.py             # Chunking + embedding pipeline
│   ├── retrieve.py          # Vector search (Chroma/FAISS)
│   └── generate.py          # Grounded generation with citations
├── fine-tune/
│   ├── dataset.py           # Instruction tuning dataset builder
│   └── lora_train.py        # Unsloth QLoRA training
├── agent/
│   ├── schema.py            # Function calling schemas
│   ├── disaster.py          # Disaster damage reporter module
│   ├── settlement.py        # Settlement upgrading advisor
│   ├── permit.py            # Building permit navigator
│   └── cooling.py          # Passive cooling advisor
├── ui/
│   └── app.py               # Gradio chat interface
├── docker/
│   └── Dockerfile
└── demo.py                  # Main entry point
```

## Timeline

| Week | Focus |
|------|-------|
| Week 1-2 | Data gathering + RAG pipeline |
| Week 3 | Fine-tune Gemma 4 + advisory modules |
| Week 4 | UI + demo video + submission |

## Data Sources (Priority Order)

1. SNI Standards — BSN (Badan Standardisasi Nasional) website
2. UU No. 28/2002 — Bangunan Gedung (Law on Buildings)
3. PP No. 36/2005 — Peraturan Pelaksanaan UU 28/2002
4. Permen PU — Ministry of Public Works regulations
5. BNPB — Disaster data and damage classification standards
6. Indonesian thermal comfort / climate zone data

## Advisory Modules

### 1. Disaster Damage Reporter
- Input: site photos + damage description
- Output: damage classification (Rusak Ringan/Sedang/Berat), repair priority, cost estimates
- Integrates: BNPB damage classification + SNI construction standards

### 2. Settlement Upgrading Advisor
- Input: site survey data, budget, population density
- Output: prioritized upgrade recommendations with cost/impact scoring

### 3. Building Permit (IMB) Navigator
- Input: project description (type, location, floor area)
- Output: step-by-step IMB checklist, required documents, fee estimator

### 4. Passive Cooling Advisor
- Input: building dimensions, orientation, materials, climate zone
- Output: passive cooling strategy + thermal comfort score

## Gemma 4 Configuration

- Base model: Gemma 4 2B E2B (edge-optimized)
- Fine-tuning: QLoRA via Unsloth (4-bit)
- Function calling: Native Gemma 4 function calling
