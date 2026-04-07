"""Build instruction-tuning dataset for Arsitrad's Gemma 4 fine-tune."""

import json, os, random, re
from typing import List, Dict

# Set random seed for ML reproducibility
random.seed(1234) 

import chromadb
from sentence_transformers import SentenceTransformer

CORPUS_CHROMA_DIR = "/home/admin/hermes/projects/arsitrad/data/processed/chroma_db"
OUTPUT_PATH = "/home/admin/hermes/projects/arsitrad/data/processed/arsitrad_training.jsonl"
EMBEDDER_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

SYSTEM_PROMPT = (
    "Kamu adalah Arsitrad, asisten AI untuk regulasi dan saran arsitektur di Indonesia. "
    "Kamu menjawab berdasarkan peraturan pembangunan Indonesia (UU, PP, Permen, SNI, Perda) "
    "dan memberikan saran teknis yang akurat tentang bangunan gedung, tata ruang, dan konstruksi."
)

print("Loading embedding model...")
EMBEDDER = SentenceTransformer(EMBEDDER_MODEL)
print("✅ Embedding model loaded.")

def get_chroma_client(chroma_dir: str = CORPUS_CHROMA_DIR):
    return chromadb.PersistentClient(path=chroma_dir)


def query_regulation_chunks(query: str, n_results: int = 10,
                             chroma_dir: str = CORPUS_CHROMA_DIR) -> List[Dict]:
    client = get_chroma_client(chroma_dir)
    results = []
    # Use the globally loaded model instead of reloading it
    q_emb = EMBEDDER.encode([query]).tolist()
    for coll_name in ["arsitrad_national_regulations", "arsitrad_local_regulations"]:
        try:
            col = client.get_collection(coll_name)
            r = col.query(query_embeddings=q_emb, n_results=n_results)
            for doc, meta, dist in zip(r["documents"][0], r["metadatas"][0], r["distances"][0]):
                results.append({"text": doc, "metadata": meta,
                               "collection": coll_name, "similarity": 1 - dist})
        except Exception as e:
            print(f"    [!] Error querying {coll_name}: {e}")
            pass
    return results


REGULATION_QA_TEMPLATES = {
    "harus": ["Jelaskan persyaratan yang harus dipenuhi.", "Apa saja kewajiban yang harus dipenuhi?"],
    "wajib": ["Sebutkan hal-hal yang wajib dilakukan.", "Apa kewajiban yang wajib dipenuhi?"],
    "minimum": ["Apa batas minimum yang berlaku?", "Berapa nilai minimum yang dipersyaratkan?"],
    "maksimal": ["Apa batasan maksimal yang dizinkan?", "Apa saja yang tidak boleh dilampaui?"],
    "tidak boleh": ["Apa saja larangan yang berlaku?", "Sebutkan hal yang tidak boleh dilakukan."],
    "dilarang": ["Apa saja kegiatan yang dilarang?", "Sebutkan larangan dalam regulasi ini."],
    "persyaratan": ["Jelaskan persyaratan yang berlaku.", "Sebutkan persyaratan untuk kasus ini."],
    "ketentuan": ["Jelaskan ketentuan utama dalam regulasi ini.", "Bagaimana ketentuan ini diterapkan?"],
    "KDB": ["Berapa KDB yang berlaku untuk kawasan ini?", "Jelaskan ketentuan KDB."],
    "KDH": ["Berapa KDH minimal yang dipersyaratkan?", "Jelaskan ketentuan KDH."],
    "KLB": ["Berapa KLB maksimal yang dizinkan?", "Jelaskan ketentuan KLB."],
    "PBG": ["Apa saja langkah mengajukan PBG?", "Jelaskan prosedur PBG."],
    "IMB": ["Apa saja persyaratan mengajukan IMB?", "Jelaskan prosedur IMB."],
    "SLF": ["Apa persyaratan Sertifikat Layak Fungsi?", "Jelaskan proses perolehan SLF."],
    "gempa": ["Bagaimana persyaratan desain tahan gempa?", "Jelaskan ketentuan gempa untuk bangunan."],
    "kebakaran": ["Bagaimana sistem proteksi kebakaran?", "Jelaskan ketentuan kebakaran."],
    "ramp": ["Berapa rasio kemiringan ramp yang dizinkan?", "Jelaskan standar ramp."],
    "OTTV": ["Apa persyaratan OTTV?", "Berapa batas OTTV yang berlaku?"],
    "IKE": ["Apa standar IKE untuk bangunan?", "Berapa batas IKE yang berlaku?"],
    "GSB": ["Berapa jarak GSB dari jalan?", "Jelaskan ketentuan GSB."],
    "SRPMK": ["Kapan SRPMK wajib digunakan?", "Apa fungsi SRPMK dalam struktur?"],
    "MBR": ["Siapa yang termasuk MBR?", "Apa kriteria kelayakan MBR?"],
    "PSU": ["Apa komponen wajib PSU untuk perumahan?", "Jelaskan standar PSU."],
}


def extract_sentences(text: str, min_len: int = 80, max_len: int = 600) -> List[str]:
    # 1. Negative lookbehinds for things we DO NOT want to split on.
    abbreviations = (
        r"(?<!\b[a-zA-Z]\.)"                      # Ignores single letters: "a.", "b.", "Z." (huruf)
        r"(?<!\bNo\.)"                            # Ignores Nomor: "No."
        r"(?<!\bPT\.)(?<!\bCV\.)(?<!\bFa\.)"      # Ignores badan usaha: "PT.", "CV.", "Fa."
        r"(?<!\bdll\.)(?<!\bdsb\.)(?<!\bdst\.)"   # Ignores singkatan: "dll.", "dsb.", "dst."
        r"(?<!\bDr\.)(?<!\bIr\.)(?<!\bProf\.)"    # Ignores gelar: "Dr.", "Ir.", "Prof."
        r"(?<!\bH\.)(?<!\bHj\.)"                  # Ignores gelar haji: "H.", "Hj."
        r"(?<!\bRp\.)"                            # Ignores Rupiah if written as "Rp."
    )
    
    # 2. Combine with the standard split (period/semicolon followed by space)
    pattern = re.compile(rf"{abbreviations}(?<=[.;])\s+", flags=re.IGNORECASE)
    
    # 3. Execute the split
    sentences = pattern.split(text)
    
    # 4. Clean and filter by length
    return [s.strip() for s in sentences if min_len <= len(s.strip()) <= max_len]


def generate_qa_from_chunk(chunk_text: str, source: str, keyword: str) -> List[Dict]:
    pairs = []
    question_templates = REGULATION_QA_TEMPLATES.get(keyword, [])
    if not question_templates:
        return pairs
    sentences = extract_sentences(chunk_text)
    keyword_sentences = [s for s in sentences if keyword.lower() in s.lower()]
    for sentence in keyword_sentences[:2]:
        q_template = random.choice(question_templates)
        question = f"{q_template} (Sumber: {source})"
        answer = sentence.strip()
        if len(answer) < 30:
            continue
        pairs.append({
            "instruction": "", "input": question, "output": answer,
            "source": source, "keyword": keyword, "category": "regulation_qa",
        })
    return pairs


def build_regulation_qa_dataset(samples_per_keyword: int = 15,
                                 chroma_dir: str = CORPUS_CHROMA_DIR) -> List[Dict]:
    dataset = []
    for keyword in REGULATION_QA_TEMPLATES:
        chunks = query_regulation_chunks(keyword, n_results=samples_per_keyword, chroma_dir=chroma_dir)
        for chunk in chunks:
            meta = chunk["metadata"]
            source = meta.get("source", meta.get("city", "unknown"))
            dataset.extend(generate_qa_from_chunk(chunk["text"], source, keyword))
    seen = set()
    deduped = []
    for item in dataset:
        # FIX: Combine input and output to create a unique signature for each Q&A pair
        key = f"{item['input'].strip()}::{item['output'].strip()}"
        
        # We still only want to keep items where the output is substantial (>30 chars)
        if key not in seen and len(item["output"]) > 30:
            seen.add(key)
            deduped.append(item)
    random.shuffle(deduped)
    return deduped

CONVERSATION_EXAMPLES = [
    {
        "instruction": "",
        "input": "Bangunan saya rusak akibat gempa di Yogyakarta. Dinding retak diagonal dan atap bergeser sekitar 15 cm. Bagaimana cara memperbaikinya?",
        "output": "Berdasarkan SNI 1726:2019 dan SNI 9274:2025, kerusakan tersebut termasuk kategori rusak berat. Langkah-langkah: (1) Evaluasi struktural wajib dilakukan oleh ahli struktur bersertifikat untuk menentukan apakah bangunan dapat diperbaiki atau harus dibongkar. (2) Jika kapasitas struktur <100% persyaratan gempa terbaru, retrofit wajib dilakukan dengan Sistem Rangka Pemikul Momen Khusus (SRPMK) sesuai Pasal 7 SNI 1726. (3) Kerusakan dinding retak diagonal >5mm mengindikasikan kegagalan geser - dinding perlu diperkuat atau diganti. (4) Pergeseran atap 15cm menunjukkan kegagalan sambungan balok-kolom - sambungan harus diperkuat dengan plat baja dan baut mutu tinggi. (5) Setelah perbaikan, bangunan harus lulus uji beban sebelum dihuni kembali.",
        "source": "disaster_module",
        "category": "disaster_conversation",
    },
    {
        "instruction": "",
        "input": "Kami ingin membangun gedung 10 lantai di Jakarta. Persyaratan gempa apa yang berlaku?",
        "output": "Untuk gedung 10 lantai di Jakarta (zona gempa tinggi): (1) Klasifikasi Risiko Gempa = Kategori Desain Seismik (KDS) D minimum berdasarkan SNI 1726:2019 Pasal 4. (2) Untuk KDS D, struktur wajib menggunakan SRPMK dengan daktilitas penuh sesuai Pasal 7. (3) Kombinasi beban: 1.2D + 1.0E + 1.0L (SNI 1727:2020). (4) Setiap lantai di atas 24m wajib dilengkapi tangga darurat terpresurisasi sesuai Permen PU 26/2008. (5) Kolam lift dan shaft harus diberi penulangan khusus terhadap beban gempa lateral.",
        "source": "disaster_module",
        "category": "disaster_conversation",
    },
    {
        "instruction": "",
        "input": "Apa saja persyaratan aksesibilitas untuk bangunan publik di Indonesia?",
        "output": "Berdasarkan Permen PU 14/2017, bangunan publik wajib memenuhi: (1) Ramp dengan kemiringan maksimal 1:12 (8.3%) dengan bordes setiap 12m. (2) Pintu dengan lebar bukaan minimal 90cm untuk akses kursi roda. (3) Lift dengan tombol pada ketinggian 90-120cm dari lantai. (4) Toilet disabilitas dengan luas minimal 1.5m x 1.6m. (5) Parkir khusus dengan lebar minimal 3.5m dekat akses lift. (6) Permukaan lantai tidak licin (koefisien gesek minimal 0.5). (7) Rambu taktil untuk tuna netra pada jalur utama.",
        "source": "permit_module",
        "category": "accessibility_conversation",
    },
    {
        "instruction": "",
        "input": "Saya mau renovasi rumah tipe 45 di Bandung. Butuh izin apa saja dan berapa biayanya?",
        "output": "Berdasarkan Perda Kota Bandung No. 5 Tahun 2010 dan PP 16/2021: (1) Rumah tipe 45 termasuk bangunan risiko rendah, cukup NIB melalui OSS. (2) Jika lokasi di kawasan padat, tetap perlu verifikasi KDB dan KDH. (3) KDB maksimal untuk kawasan Bandung = 60-70%, KDH minimal = 10% (Perda Bandung). (4) Retribusi IMB dihitung dari luas bangunan x NJOP per m2, umumnya 1-2% dari nilai bangunan.",
        "source": "permit_module",
        "category": "permit_conversation",
    },
    {
        "instruction": "",
        "input": "Desain apartemen saya di lantai 15 menghadap barat terasa sangat panas. WWR saya 60%. Apa yang harus saya lakukan?",
        "output": "Berdasarkan Permen PU 21/2021 (BGH): (1) WWR 60% tergolong tinggi (batas maksimal umumnya 30-40%) - ini menyebabkan gain panas matahari besar melalui kaca. (2) Hitung OTTV: OTTV = (U x WWR x SC x SHGF) + (alpha x Kolektor). Untuk WWR 60%, OTTV kemungkinan >35 W/m2 (melebihi batas BGH). (3) Rekomendasi: Pasang Low-E glass dengan emissivity <0.1. (4) Tambahkan overhang atau vertical fin pada sisi barat dengan projection factor >0.5. (5) Gunakan curtain wall dengan double glass dan argon fill.",
        "source": "cooling_module",
        "category": "cooling_conversation",
    },
    {
        "instruction": "",
        "input": "Apa saja persyaratan ruang terbuka hijau untuk bangunan komersial di Semarang?",
        "output": "Berdasarkan Perda Kota Semarang No. 5 Tahun 2009 dan Permen PU 21/2021: (1) KDH minimal di Semarang = 20% dari luas lahan - paling ketat di Jawa Tengah. (2) Untuk bangunan komersial bersertifikasi BGH, wajib memenuhi OTTV <= 35 W/m2 dan penggunaan kembali air hujan minimal 10%. (3) Ruang terbuka hijau harus ditanami pohon dengan luas minimal 50% dari total area hijau. (4) Atap hijau dapat dihitung sebagai KDH dengan faktor pengali 1.5.",
        "source": "cooling_module",
        "category": "settlement_conversation",
    },
    {
        "instruction": "",
        "input": "Saya mau bangun rumah subsidi di pinggiran Semarang. Apakah termasuk MBR dan apa syaratnya?",
        "output": "Berdasarkan Permen PKP 5/2025 dan UU 1/2011: (1) MBR adalah rumah tangga dengan penghasilan <=Rp 8 juta/bulan untuk rumah subsidi flat. (2) Rumah subsidi FLPP dengan luas tanah 60-200m2 dan bangunan 22-36m2. (3) Persyaratan MBR: belum punya rumah, rumah pertama, bukan derivatif properti. (4) Subsidi: BP2 sebesar Rp 4 juta untuk rumah tapak, atau subsidi bunga hingga 5% untuk KPR. (5) Tanah harus bersertifikat dan memenuhi KDB/KDH setempat (Semarang: KDH min 20%).",
        "source": "settlement_module",
        "category": "settlement_conversation",
    },
    {
        "instruction": "",
        "input": "Berapa KDB dan KDH untuk bangunan Gudang di kawasan industri Balikpapan?",
        "output": "Berdasarkan Perda Kota Balikpapan No. 3 Tahun 2009: (1) KDB untuk kawasan industri umumnya 60-70% untuk memaksimalkan luas gudang. (2) KDH minimal = 10% dari luas lahan - wajib ditanami vegetasi. (3) Untuk gudang dengan luas >5,000m2, wajib memiliki sistem proteksi kebakaran dengan sprinkler dan hydrant sesuai Permen PU 26/2008. (4) KLB untuk kawasan industri Balikpapan maksimal 240-360% (sesuai sub-zona). (5) GSB minimal 6m dari jalan access.",
        "source": "local_module",
        "category": "local_regulation_conversation",
    },
]

TOOL_CALLING_EXAMPLES = [
    {
        "instruction": "Gunakan tool report_disaster_damage untuk menganalisis kerusakan bangunan.",
        "input": "Gempa magnitudo 6.2 di Cianjur. Rumah tinggal tipe 36 dengan dinding retak diagonal dan beberapa genteng jatuh.",
        "output": json.dumps({"tool_calls": [{"name": "report_disaster_damage", "arguments": {
            "location": "Cianjur, Jawa Barat", "disaster_type": "gempa",
            "building_type": "rumah_tinggal",
            "damage_description": "Dinding retak diagonal, genteng jatuh > 10%",
            "floor_area_m2": 36}}]}),
        "source": "tool_example",
        "category": "function_calling",
    },
    {
        "instruction": "Gunakan tool advise_settlement_upgrading untuk menilai kawasan permukiman.",
        "input": "Kawasan permukiman kumuh di bantaran sungai di Semarang dengan kepadatan 450 orang/hektar, infrastruktur jalan 2m, belum ada drainase.",
        "output": json.dumps({"tool_calls": [{"name": "advise_settlement_upgrading", "arguments": {
            "location": "Semarang, Jawa Tengah", "population_density": 450,
            "current_infrastructure": "Jalan 2m, tanpa drainase, bantaran sungai",
            "budget_constraint_idr": 500000000,
            "priority_goals": ["meningkat_keselamatan", "memperbaiki_drainase", "menambah_fasilitas_air"]}}]}),
        "source": "tool_example",
        "category": "function_calling",
    },
    {
        "instruction": "Gunakan tool navigate_permit untuk memandu pengurusan izin bangunan.",
        "input": "Saya mau bangun ruko 3 lantai di Jakarta Selatan, luas tanah 90m2, di jalan 8m. Proses apa yang perlu dilalui?",
        "output": json.dumps({"tool_calls": [{"name": "navigate_building_permit", "arguments": {
            "location": "Jakarta Selatan, DKI Jakarta", "building_type": "ruko",
            "floors": 3, "land_area_m2": 90, "road_width_m": 8, "public_function": True}}]}),
        "source": "tool_example",
        "category": "function_calling",
    },
    {
        "instruction": "Gunakan tool advise_passive_cooling untuk memberikan rekomendasi pendinginan pasif.",
        "input": "Apartemen 2BR di lantai 8 Surabaya menghadap barat, WWR 50%, tanpa balkon. Bagaimana strategi pendinginan pasif?",
        "output": json.dumps({"tool_calls": [{"name": "advise_passive_cooling", "arguments": {
            "location": "Surabaya, Jawa Timur", "building_type": "apartemen",
            "floors": 8, "orientation": "barat", "wwr": 0.5,
            "has_balcony": False, "climate_zone": "dataran_rendah_pesisir"}}]}),
        "source": "tool_example",
        "category": "function_calling",
    },
]

def format_for_training(example: Dict) -> Dict:
    instruction = example.get('instruction', '').strip()
    input_text = example.get('input', '').strip()
    user_content = f"{instruction}\n\n{input_text}" if instruction else input_text
    
    # Merge system prompt into the user turn for Gemma compatibility
    prompt = (
        "<start_of_turn>user\n"
        f"{SYSTEM_PROMPT}\n\n{user_content}<end_of_turn>\n"
        "<start_of_turn>model\n"
        f"{example['output']}<end_of_turn>"
    )
    return {"text": prompt, "category": example.get("category"), "source": example.get("source")}


def build_dataset(
    qa_per_keyword: int = 15,
    max_conversation_examples: int = 100,
    output_path: str = OUTPUT_PATH,
    chroma_dir: str = CORPUS_CHROMA_DIR,
) -> List[Dict]:
    print("Building Arsitrad training dataset...")

    print("  [1/3] Generating regulation Q&A from ChromaDB...")
    try:
        qa_dataset = build_regulation_qa_dataset(
            samples_per_keyword=qa_per_keyword, chroma_dir=chroma_dir)
        print(f"    Generated {len(qa_dataset)} Q&A pairs")
    except Exception as e:
        print(f"    Warning: ChromaDB query failed ({e}) - conversation examples only")
        qa_dataset = []

    print("  [2/3] Adding agent conversations...")
    conversation_examples = random.sample(
        CONVERSATION_EXAMPLES,
        min(len(CONVERSATION_EXAMPLES), max_conversation_examples))
    print(f"    Added {len(conversation_examples)} conversation examples")

    print("  [3/3] Adding tool-calling examples...")
    print(f"    Added {len(TOOL_CALLING_EXAMPLES)} tool-calling examples")

    all_examples = qa_dataset + conversation_examples + TOOL_CALLING_EXAMPLES
    random.shuffle(all_examples)
    formatted = [format_for_training(ex) for ex in all_examples]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for item in formatted:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\nDataset complete: {len(formatted)} examples -> {output_path}")
    print(f"  Regulation Q&A: {len(qa_dataset)}")
    print(f"  Conversations: {len(conversation_examples)}")
    print(f"  Tool-calling: {len(TOOL_CALLING_EXAMPLES)}")
    return formatted


def load_jsonl(path: str) -> List[Dict]:
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


if __name__ == "__main__":
    build_dataset()
