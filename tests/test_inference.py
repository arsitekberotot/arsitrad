import yaml

from pipeline.inference import (
    build_no_answer_response,
    build_prompt,
    ensure_structured_sections,
    load_inference_config,
)
from pipeline.retriever import CandidateChunk, RetrievalResult


def make_result(should_answer=True):
    candidate = CandidateChunk(
        chunk_key="pp16-1",
        content="Pasal 1 Bangunan Gedung wajib memenuhi persyaratan administratif.",
        metadata={"source_name": "PP 16/2021", "start_page": 1, "end_page": 1},
        score=0.92,
        source="reranked",
    )
    return RetrievalResult(
        question="Apa syarat PBG?",
        standalone_query="Apa syarat PBG?",
        expanded_queries=["Apa syarat PBG?"],
        filters={"region": "Semarang"},
        candidates=[candidate],
        should_answer=should_answer,
        confidence=0.92 if should_answer else 0.2,
        message="Arsitrad tidak dapat menemukan regulasi yang cukup spesifik.",
    )


def test_build_prompt_includes_question_and_citations():
    prompt = build_prompt("Apa syarat PBG?", make_result())

    assert "KONTEKS REGULASI" in prompt
    assert "PERTANYAAN: Apa syarat PBG?" in prompt
    assert "[1]" in prompt


def test_no_answer_response_is_structured():
    response = build_no_answer_response(make_result(should_answer=False))

    assert "RINGKASAN" in response
    assert "DETAIL REGULASI" in response
    assert "SUMBER" in response


def test_ensure_structured_sections_wraps_plain_text():
    response = ensure_structured_sections("Jawaban singkat saja.", make_result().candidates)

    assert "RINGKASAN" in response
    assert "SUMBER" in response


def test_load_inference_config_reads_repo_defaults(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "v2": {
                    "inference": {
                        "model_path": "./models/demo.gguf",
                        "context_window": 4096,
                        "max_tokens": 512,
                        "temperature": 0.1,
                        "top_p": 0.8,
                        "repeat_penalty": 1.05,
                        "n_gpu_layers": 12,
                        "n_threads": 4,
                        "n_batch": 128,
                        "verbose": True,
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    cfg = load_inference_config(config_path)

    assert cfg.model_path == "./models/demo.gguf"
    assert cfg.context_window == 4096
    assert cfg.max_tokens == 512
    assert cfg.n_gpu_layers == 12
    assert cfg.n_threads == 4
    assert cfg.n_batch == 128
    assert cfg.verbose is True


def test_load_inference_config_allows_env_overrides(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "v2": {
                    "inference": {
                        "model_path": "./models/demo.gguf",
                        "context_window": 4096,
                        "n_gpu_layers": 0,
                        "n_threads": 2,
                        "n_batch": 256,
                        "verbose": False,
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("ARSITRAD_GGUF_MODEL_PATH", "/kaggle/working/arsitrad/models/gemma.gguf")
    monkeypatch.setenv("ARSITRAD_GGUF_CONTEXT_WINDOW", "3072")
    monkeypatch.setenv("ARSITRAD_GGUF_MAX_TOKENS", "768")
    monkeypatch.setenv("ARSITRAD_GGUF_TEMPERATURE", "0.15")
    monkeypatch.setenv("ARSITRAD_GGUF_TOP_P", "0.85")
    monkeypatch.setenv("ARSITRAD_GGUF_REPEAT_PENALTY", "1.2")
    monkeypatch.setenv("ARSITRAD_GGUF_N_GPU_LAYERS", "-1")
    monkeypatch.setenv("ARSITRAD_GGUF_N_THREADS", "3")
    monkeypatch.setenv("ARSITRAD_GGUF_N_BATCH", "192")
    monkeypatch.setenv("ARSITRAD_GGUF_VERBOSE", "true")

    cfg = load_inference_config(config_path)

    assert cfg.model_path == "/kaggle/working/arsitrad/models/gemma.gguf"
    assert cfg.context_window == 3072
    assert cfg.max_tokens == 768
    assert cfg.temperature == 0.15
    assert cfg.top_p == 0.85
    assert cfg.repeat_penalty == 1.2
    assert cfg.n_gpu_layers == -1
    assert cfg.n_threads == 3
    assert cfg.n_batch == 192
    assert cfg.verbose is True
