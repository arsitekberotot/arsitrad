"""QLoRA fine-tuning pipeline for Gemma 4 using Unsloth."""

import torch
from unsloth import FastLanguageModel
from transformers import AutoTokenizer, AutoModelForCausalLM
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import load_dataset
import os


def load_model_and_tokenizer(
    model_name: str = "google/gemma-4-2b-it",
    max_seq_length: int = 2048,
    load_in_4bit: bool = True
):
    """Load Gemma 4 model with 4-bit quantization for QLoRA."""
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        load_in_4bit=load_in_4bit,
        dtype=None,  # Auto-detect (bfloat16 if supported)
        rope_scaling=None,
    )
    
    # Add LoRA adapters
    model = FastLanguageModel.get_peft_model(
        model,
        r=64,  # LoRA rank
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=128,
        lora_dropout=0.05,
        bias="none",
        use_gradient_checkpointing=True,
        random_state=42,
        use_rslora=False,
        loftq_config=None,
    )
    
    return model, tokenizer


def format_for_training(example):
    """Format dataset example for Gemma instruction tuning."""
    # Alpaca-style prompt format
    SYSTEM = "Kamu adalah Arsitrad, asisten AI untuk regulasi dan saran arsitektur Indonesia."
    
    prompt = f"<start_of_turn>system\n{SYSTEM}<end_of_turn>\n<start_of_turn>user\n{example['instruction']} {example['input']}<end_of_turn>\n<start_of_turn>model\n{example['output']}<end_of_turn>"
    return {"text": prompt}


def train(
    model,
    tokenizer,
    train_dataset,
    eval_dataset=None,
    output_dir: str = "./fine_tuned_model",
    num_epochs: int = 3,
    per_device_batch_size: int = 4,
    learning_rate: float = 2e-4,
    warmup_steps: int = 100,
    logging_steps: int = 10,
    save_steps: int = 500,
):
    """Run QLoRA fine-tuning."""
    
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=per_device_batch_size,
        gradient_accumulation_steps=4,
        learning_rate=learning_rate,
        weight_decay=0.01,
        warmup_steps=warmup_steps,
        logging_steps=logging_steps,
        save_steps=save_steps,
        save_total_limit=2,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        max_grad_norm=0.3,
        group_by_length=True,
        lr_scheduler_type="cosine",
        report_to="tensorboard",
        eval_strategy="steps" if eval_dataset else "no",
    )
    
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        args=training_args,
        max_seq_length=2048,
        dataset_text_field="text",
    )
    
    print("Starting training...")
    trainer.train()
    
    print(f"Saving model to {output_dir}")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    return model, tokenizer


def merge_and_export(model_path: str, output_path: str):
    """Merge LoRA weights and export as standalone model."""
    from unsloth import FastLanguageModel
    
    model, tokenizer = FastLanguageModel.from_pretrained(model_name=model_path)
    FastLanguageModel.for_inference(model)
    
    model.save_pretrained_merged(output_path, tokenizer)
    print(f"Merged model saved to {output_path}")