from types import SimpleNamespace

from fastapi.testclient import TestClient

from api import server


class DummyResult:
    def __init__(self):
        candidate = SimpleNamespace(
            chunk_key="perm-12-2024-1",
            content="SBKBG diatur dalam Permen 12 Tahun 2024.",
            metadata={"source_name": "Permen_12_2024_SBKBG", "start_page": 1},
            score=1.23,
            source="reranked",
        )
        self.answer = "RINGKASAN\nSBKBG diatur.\n\nDETAIL REGULASI\nLihat Permen 12/2024.\n\nSARAN TEKNIS\nVerifikasi dokumen.\n\nSUMBER\n[1] Permen_12_2024_SBKBG"
        self.used_model = True
        self.model_path = "./models/demo.gguf"
        self.raw_text = self.answer
        self.retrieval = SimpleNamespace(
            question="Apa itu SBKBG?",
            standalone_query="Apa itu SBKBG?",
            expanded_queries=["Apa itu SBKBG?"],
            filters={"topic": "ownership"},
            candidates=[candidate],
            should_answer=True,
            confidence=1.23,
            message=None,
        )


class DummyEngine:
    def answer(self, question, history=None):
        return DummyResult()


class DummyPermitNavigator:
    def navigate(self, *args, **kwargs):
        return {"building_type": args[0], "steps": 5, "estimated_total_cost_idr": 1234567}


def test_health_endpoint(monkeypatch):
    monkeypatch.setattr(server, "load_ui_settings", lambda config_path=server.DEFAULT_CONFIG_PATH: {
        "app_title": "Arsitrad v2",
        "disclaimer": "demo",
        "default_question": "Apa itu PBG?",
    })
    monkeypatch.setattr(server, "get_runtime_config", lambda: {
        "v2": {
            "corpus": {"sparse_index_path": "./data/processed/v2/bm25_corpus.jsonl"},
            "inference": {"model_path": "./models/gemma-4-E4B-it-Q4_K_M.gguf"},
        }
    })

    client = TestClient(server.app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["app_title"] == "Arsitrad v2"
    assert "model_exists" in payload


def test_ask_endpoint_serializes_engine_result(monkeypatch):
    monkeypatch.setattr(server, "get_answer_engine", lambda: DummyEngine())

    client = TestClient(server.app)
    response = client.post(
        "/api/ask",
        json={
            "question": "Apa itu SBKBG?",
            "history": [{"role": "user", "content": "Konteks awal"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["used_model"] is True
    assert payload["retrieval"]["standalone_query"] == "Apa itu SBKBG?"
    assert payload["retrieval"]["candidates"][0]["metadata"]["source_name"] == "Permen_12_2024_SBKBG"


def test_permit_endpoint_returns_payload(monkeypatch):
    monkeypatch.setattr(server, "get_building_permit_navigator", lambda: DummyPermitNavigator())

    client = TestClient(server.app)
    response = client.post(
        "/api/permit",
        json={
            "building_type": "rumah_tinggal",
            "location": "Semarang",
            "floor_area_m2": 120,
            "land_area_m2": 150,
            "building_height_m": 8,
            "building_function": "hunian",
        },
    )

    assert response.status_code == 200
    payload = response.json()["payload"]
    assert payload["building_type"] == "rumah_tinggal"
    assert payload["steps"] == 5
