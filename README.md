<pre>
 █████╗ ██████╗ ███████╗██╗████████╗██████╗  █████╗ ██████╗ 
██╔══██╗██╔══██╗██╔════╝██║╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗
███████║██████╔╝███████╗██║   ██║   ██████╔╝███████║██║  ██║
██╔══██║██╔══██╗╚════██║██║   ██║   ██╔══██╗██╔══██║██║  ██║
██║  ██║██║  ██║███████║██║   ██║   ██║  ██║██║  ██║██████╔╝
╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ 
                                                            </pre>
# Arsitrad — AI Advisor for Indonesian Architecture & Construction
<h3 align="center">AI-Powered Indonesian Building Regulation Advisor</h3>

<p align="center">
  <a href="https://github.com/arsitekberotot/arsitrad">GitHub</a> ·
  <a href="#-demo">Demo Video</a> ·
  <a href="#-try-it">Try It</a> ·
  <a href="#-architecture">Architecture</a> ·
  <a href="#-advisory-modules">Modules</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Model-Gemma_4_E2B-cc785c?style=flat&logo=google&logoColor=white" alt="Gemma 4" />
  <img src="https://img.shields.io/badge/Fine--Tune-QLoRA_4bit-2B6150?style=flat" alt="QLoRA" />
  <img src="https://img.shields.io/badge/RAG-ChromaDB-9333FF?style=flat" alt="ChromaDB" />
  <img src="https://img.shields.io/badge/Embedder-paraphrase--multilingual--MiniLM-F97316?style=flat" alt="Embedder" />
  <img src="https://img.shields.io/badge/Corpus-110_Regulations-059669?style=flat" alt="Corpus" />
  <img src="https://img.shields.io/badge/Chunks-59K_vectors-F59E0B?style=flat" alt="Chunks" />
</p>

---

## The Problem

Indonesia has **hundreds of building regulations** — UU, PP, Permen, SNI, Perda — but architects and construction professionals have **no practical AI tool** to navigate them. Existing AI assistants hallucinate article numbers and cite non-existent regulations. When someone asks about earthquake-resistant design requirements in Semarang, they get confident nonsense instead of actual SNI 1726 citations.

Arsitrad solves this by grounding every answer in **real Indonesian regulations**, with a fine-tuned model that speaks the language of Indonesian architecture.

---

## What We Built

| | Feature | Description |
|---|---|---|
| **RAG Pipeline** | 59,000+ Chunk Vector DB | ChromaDB with national + local regulations (UU, PP, Permen, SNI, Perda) |
| **Fine-Tuned Model** | Gemma 4 2B E2B + QLoRA | Domain-adapted on 151 Indonesian architecture Q&A pairs |
| **5 Advisory Modules** | Disaster · Settlement · Permit · Cooling · Local Regulations | Domain-specific guidance with regulatory grounding |
| **Multi-Island Coverage** | Jawa · Kalimantan · Sumatera · Sulawesi · Papua | 77 Perda/Pergub/Perwali across 40+ cities |
| **Citation-Grounded** | Every answer cites specific regulations | No hallucination — sources in the output |

---

## Try It

### 1. Download LoRA Adapters

**👉 [Download arsitrad_finetuned_adapters.zip (747 MB)](https://github.com/arsitekberotot/arsitrad/releases/download/v1.0.0/arsitrad_finetuned_adapters.zip)**

The fine-tuned LoRA adapters (~747MB).

### 2. Load with Base Model

```python
from unsloth import FastLanguageModel
from transformers import AutoTokenizer

# Base model (google/gemma-4-E2B-it) is free on HuggingFace
# Download LoRA adapters from Releases, then:

model, _ = FastLanguageModel.from_pretrained(
    model_name="./arsitrad_finetuned",  # LoRA adapter path
    max_seq_length=2048,
    load_in_4bit=True,
)
tokenizer = AutoTokenizer.from_pretrained("./arsitrad_finetuned")
FastLanguageModel.for_inference(model)
```

### 3. Ask

```python
SYSTEM = (
    "Kamu adalah Arsitrad, asisten AI untuk regulasi arsitektur Indonesia. "
    "Jawab dalam Bahasa Indonesia, cite sumber regulasi jika relevan."
)

prompt = (
    "<start_of_turn>system\n" + SYSTEM + "<end_of_turn>\n"
    "<start_of_turn>user\nApa syarat minimum ventilasi alami untuk rumah tinggal di Indonesia?<end_of_turn>\n"
    "<start_of_turn>model\n"
)

inputs = tokenizer([prompt], return_tensors='pt').to('cuda')
outputs = model.generate(**inputs, max_new_tokens=512, temperature=0.3, do_sample=True)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

---

## Fine-Tuning Results

| Metric | Value |
|---|---|
| Base model | `google/gemma-4-E2B-it` (5B params) |
| Fine-tune method | QLoRA 4-bit (Unsloth) |
| Training examples | 151 Q&A pairs from ChromaDB retrieval |
| Trainable parameters | 62,078,976 / 5,185,256,992 (**1.2%**) |
| Epochs | 3 |
| Effective batch size | 16 |
| Initial loss | 12.23 |
| Final loss | 2.16 |
| Training time | ~5 minutes (Colab T4) |

```
Step 10: 12.23
Step 20:  4.55
Step 30:  2.16  <- after epoch 3
```

Loss converged from 12.2 -> 2.2, indicating the model learned domain-specific regulation answering.

---

## Architecture

```
                    +--------------------------------------------------+
                    |         Regulation Corpus (110 docs)              |
                    |   UU . PP . Permen . SNI . Perda                |
                    +------------------------+-------------------------+
                                             |
                    +------------------------v-------------------------+
                    |  PDF Scraper (peraturan.go.id)                   |
                    |  PyMuPDF . Structure Parser                       |
                    +------------------------+-------------------------+
                                             |
                    +------------------------v-------------------------+
                    |   Chunking (512 chars, 64 olap)                   |
                    |   paraphrase-multilingual-MiniLM                   |
                    +------------------------+-------------------------+
                                             |
                          +------------------+-------------------+
                          |                                     |
          +---------------v----------------+   +---------------v----------------+
          |  ChromaDB - National            |   |  ChromaDB - Local             |
          |  22,649 chunks                 |   |  36,854 chunks                |
          |  UU . PP . Permen . SNI        |   |  Perda . Pergub . Perwali    |
          +---------------+----------------+   +---------------+----------------+
                          |                                     |
                          +------------------+------------------+
                                             |
                    +------------------------v-------------------------+
                    |    Retrieval (query norm)                       |
                    +------------------------+-------------------------+
                                             |
                    +------------------------v-------------------------+
                    |  Gemma 4 2B + LoRA Adapter                     |
                    |  (fine-tuned on 151 Q&A)                        |
                    +------------------------+-------------------------+
                                             |
                          +------------------+-------------------+
                          |                                     |
          +---------------v----------------+   +---------------v----------------+
          |  Disaster Damage               |   |  Settlement Upgrading        |
          |  reporter_structural_dmg       |   |  assess_upgrade_needs         |
          +---------------+----------------+   +---------------+----------------+
          |  Building Permit               |   |  Passive Cooling              |
          |  navigate_permit_process       |   |  analyze_thermal_comfort      |
          +---------------+----------------+   +---------------+----------------+
                          |                                     |
                          +------------------+------------------+
                                             |
                    +------------------------v-------------------------+
                    |  Gradio Chat UI                             |
                    |  (local / Docker)                            |
                    +--------------------------------------------------+
```

---

## Advisory Modules

### 1. Disaster Damage Reporter
Classifies building damage from earthquake, flood, tsunami, landslide and generates repair recommendations grounded in BNPB standards and SNI construction codes.

### 2. Settlement Upgrading Advisor
Assesses informal settlement conditions and recommends prioritized upgrades with cost/impact scoring based on applicable regulations.

### 3. Building Permit (IMB) Navigator
Takes project description (type, location, floor area) and outputs a step-by-step IMB checklist, required documents, and fee estimator.

### 4. Passive Cooling Advisor
Analyzes building dimensions, orientation, materials, and climate zone to recommend passive cooling strategies with thermal comfort scoring.

### 5. Local Regulations
Grounded answers from Perda/Pergub/Perwali across 40+ Indonesian cities — Jawa, Kalimantan, Sumatera, Sulawesi, Papua.

---

## Corpus Statistics

| Category | Count | Documents |
|---|---|---|
| UU (Undang-Undang) | 7 | UU 28/2002, UU 2/2017, UU 6/2017, UU 6/2023, UU 11/2014 |
| PP (Peraturan Pemerintah) | 11 | PP 14-16/2021, PP 21/2021, PP 28/2025 |
| Permen PU | 11 | Permen 6/2025, 8/2023, 9/2021, 12/2024, 14/2017, 21/2021, 26/2008 |
| SNI Standards | 5 | SNI 1726/2019, 1727/2020, 2847/2019, 8153/2025, 9274/2025 |
| Local Regulations | 77 | Perda/Pergub/Perwali — Jawa, Kalimantan, Sumatera |

**Total embedded:** 59,503 chunks in ChromaDB

---

## Tech Stack

- **Model**: google/gemma-4-E2B-it (fine-tuned)
- **Fine-tuning**: Unsloth QLoRA (4-bit NF4, rank 32, alpha 64)
- **Vector DB**: ChromaDB (local, offline-capable)
- **Embedder**: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- **PDF Extraction**: PyMuPDF + BeautifulSoup4
- **UI**: Gradio chat interface
- **Deployment**: Docker (offline-capable)

---

## Project Structure

```
arsitrad/
  data/
    corpus/
      indonesian-construction-law/   # UU, PP, Permen, SNI (33 docs)
      local_regulations/            # Perda/Pergub/Perwali by city (77 docs)
    processed/
      chroma_db/                    # Embedded vector database
      arsitrad_training.jsonl       # 151 fine-tune Q&A pairs
  rag/
    embed.py                        # Chunking + embedding pipeline
    retrieve.py                     # Vector search with query normalization
    generate.py                     # Grounded generation
  fine-tune/
    dataset.py                       # Builds instruction dataset from ChromaDB
    lora_train.py                   # QLoRA training pipeline
  agent/
    schema.py                        # Function calling schemas
    disaster.py                     # Disaster damage module
    settlement.py                   # Settlement upgrading module
    permit.py                       # Building permit module
    cooling.py                      # Passive cooling module
  scraper/
    scraper.py                       # CLI for crawling regulations
    extractors.py                    # PDF text extraction
    peraturan_go_id.py               # Handler for peraturan.go.id
  ui/
    app.py                          # Gradio chat interface
  demo.py                           # Demo entry point
```

---

## Setup

```bash
git clone https://github.com/arsitekberotot/arsitrad
cd arsitrad
pip install -r requirements.txt
python ui/app.py
```

---

---




## Gemma Good Hackathon — Impact Alignment

Arsitrad was built for the [Gemma Good Hackathon](https://www.kaggle.com/competitions/gemma-good-hackathon-ne-2/overview) on Kaggle, targeting impact in safety, trust, and global resilience.

### Impact Tracks

| Track | How Arsitrad Fits |
|---|---|
| **Safety & Trust** | Citation-grounded answers prevent AI hallucination in building regulations — architects get verifiable, sourced advice, not made-up article numbers |
| **Global Resilience** | Disaster damage reporter + settlement upgrading advisor built on BNPB standards — directly supports disaster preparedness and recovery for Indonesia's most vulnerable communities |
| **Digital Equity & Inclusivity** | Opens Indonesian building code knowledge to 270M+ Indonesians who currently have zero practical access to these regulations |

### Technology Tracks

| Track | How Arsitrad Fits |
|---|---|
| **Unsloth** | Gemma 4 2B E2B fine-tuned using QLoRA via Unsloth — 62M trainable params (1.2%), 4-bit quantization, loss 12.2 -> 2.16 in 3 epochs |
| **llama.cpp** | LoRA adapters ship at ~747MB — lightweight enough to run locally via llama.cpp on consumer hardware |

### Why This Matters

Indonesia is one of the world's most disaster-prone countries — earthquake, flood, tsunami, and landslide risk affects hundreds of millions. Yet the architects and construction workers who build Indonesia's buildings have no AI tool to navigate the country's own building codes. When they need to verify earthquake resistance requirements or IMB permit steps, they have no one to ask except PDFs they can't practically search.

Arsitrad changes that — grounded, citation-backed answers from real Indonesian regulations (UU, PP, Permen, SNI, Perda), fine-tuned into a model any architect can run.


## License

CC BY 4.0 — free to use, share, and adapt with attribution.
