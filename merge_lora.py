#!/usr/bin/env python3
"""
Merge Arsitrad LoRA into Gemma 4 base model, then push to HuggingFace.
Run ONCE on a machine with GPU + internet:
  pip install torch bitsandbytes peft transformers accelerate huggingface_hub
  python merge_lora.py
"""
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

BASE_MODEL = "google/gemma-4-e2b-it"
LORA_PATH  = "./arsitrad_finetuned_adapters"
HF_REPO   = "YOUR_HF_USERNAME/arsitrad-gemma4-2b-it"  # ← change this

print("Loading base model (bfloat16, auto device_map)...")
base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True,
)
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

print("Attaching LoRA adapters...")
model = PeftModel.from_pretrained(base_model, LORA_PATH)

print("Merging LoRA into base weights...")
merged_model = model.merge_and_unload()
merged_model.save_pretrained("./arsitrad_merged")
tokenizer.save_pretrained("./arsitrad_merged")
print(f"Merged model saved to ./arsitrad_merged")

print(f"Pushing to HuggingFace → {HF_REPO}...")
from huggingface_hub import HfApi
api = HfApi()
api.create_repo(repo_id=HF_REPO, repo_type="model", exist_ok=True)
api.upload_folder(folder_path="./arsitrad_merged", repo_id=HF_REPO, repo_type="model")
print(f"Done! On Kaggle load with:")
print(f'  model, tokenizer = FastLanguageModel.from_pretrained("{HF_REPO}", max_seq_length=2048, load_in_4bit=True)')
