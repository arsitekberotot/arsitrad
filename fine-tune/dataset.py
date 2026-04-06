"""Build instruction-tuning dataset for Arsitrad's Gemma 4 fine-tune."""

import json
import os
from pathlib import Path
from typing import List, Dict


def load_regulations_from_db(chroma_dir: str = "./data/processed/chroma_db") -> List[Dict]:
    """Load processed regulation chunks from ChromaDB for dataset creation."""
    # Placeholder — will be connected after embed pipeline runs
    return []


def generate_qa_pairs_from_regulation(text: str, source: str) -> List[Dict]:
    """Generate Q&A pairs from regulation text chunks."""
    # Simplified generation — in production use LLM to generate diverse Q&A
    pairs = []
    
    # Keywords that signal Q&A-worthy content
    qa_keywords = ["harus", "wajib", "minimum", "maksimal", "tidak boleh", "dilarang", "persyaratan", "ketentuan"]
    
    for keyword in qa_keywords:
        if keyword in text.lower():
            # Generate question template
            qa_pairs = {
                "harus": "Apa persyaratan yang harus dipenuhi?",
                "wajib": "Apa yang wajib dilakukan sesuai regulasi ini?",
                "minimum": "Berapa minimum yang dipersyaratkan?",
                "maksimal": "Apa batasan maksimum yang berlaku?",
                "tidak boleh": "Apa yang tidak boleh dilakukan?",
                "dilarang": "Apa saja yang dilarang menurut regulasi ini?",
                "persyaratan": "Apa saja persyaratan yang berlaku?",
                "ketentuan": "Apa ketentuan yang berlaku untuk kasus ini?"
            }
            
            pairs.append({
                "instruction": qa_pairs.get(keyword, "Jelaskan isi regulasi ini."),
                "input": f"Berikan penjelasan tentang ketentuan dalam {source}.",
                "output": text[:500],  # Truncate for training
                "source": source,
                "category": "regulation_qa"
            })
            break
    
    return pairs


def generate_conversation_examples() -> List[Dict]:
    """Generate conversation-style training examples for agent modules."""
    examples = []
    
    # Disaster damage conversations
    examples.extend([
        {
            "instruction": "",
            "input": "Bangunan saya rusak akibat gempa di Yogyakarta. Dinding retak dan atap bergeser. Bagaimana cara memperbaikinya?",
            "output": "Berdasarkan UU No. 28/2002 dan SNI 1726:2019, kerusakan bangunan akibat gempa harus dievaluasi terlebih dahulu oleh ahli struktur... [disaster report output]",
            "source": "disaster_module",
            "category": "disaster_conversation"
        },
        {
            "instruction": "",
            "input": "Saya ingin membangun rumah di daerah Jakarta Selatan. Bagaimana proses pengurusan IMB?",
            "output": "Proses pengurusan IMB meliputi... [permit navigation output]",
            "source": "permit_module",
            "category": "permit_conversation"
        },
        {
            "instruction": "",
            "input": "Desain apartemen saya terasa panas. Lantai 10, menghadap barat. Apa yang bisa saya lakukan untuk passive cooling?",
            "output": "Berdasarkan zona iklim dataran rendah pesisir dan sifat termal material... [cooling advice output]",
            "source": "cooling_module",
            "category": "cooling_conversation"
        }
    ])
    
    return examples


def generate_instruction_dataset(
    regulations_dir: str = "./data/regulations",
    output_path: str = "./data/processed/instruction_dataset.jsonl"
) -> List[Dict]:
    """Generate full instruction-tuning dataset."""
    dataset = []
    
    # 1. Add conversation examples
    dataset.extend(generate_conversation_examples())
    
    # 2. Add regulation Q&A (placeholder — fills after RAG pipeline)
    # TODO: Load regulations from chroma and generate Q&A
    
    # 3. Add tool-calling examples
    tool_examples = [
        {
            "instruction": "Gunakan tool report_disaster_damage untuk menganalisis kerusakan bangunan.",
            "input": "Gempa magnitudo 6.2 di Cianjur. Rumah tipe 36 dengan dinding retak diagonal dan beberapa genteng jatuh.",
            "output": json.dumps({
                "tool_calls": [{
                    "name": "report_disaster_damage",
                    "arguments": {
                        "location": "Cianjur, Jawa Barat",
                        "disaster_type": "gempa",
                        "building_type": "rumah_tinggal",
                        "damage_description": "Dinding retak diagonal, genteng jatuh > 10%",
                        "floor_area_m2": 36
                    }
                }]
            }),
            "source": "tool_example",
            "category": "function_calling"
        }
    ]
    dataset.extend(tool_examples)
    
    # Save as JSONL
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    print(f"Generated {len(dataset)} training examples -> {output_path}")
    return dataset


def load_jsonl(path: str) -> List[Dict]:
    """Load dataset from JSONL file."""
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            data.append(json.loads(line))
    return data