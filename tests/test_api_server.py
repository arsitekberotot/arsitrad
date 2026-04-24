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
    def __init__(self):
        self.calls = []

    def answer(self, question, history=None):
        self.calls.append({"question": question, "history": history or []})
        return DummyResult()


class FailingEngine:
    def answer(self, question, history=None):
        raise RuntimeError("model exploded with an ugly internal error")


class DummyPermitNavigator:
    def navigate(self, *args, **kwargs):
        return {"building_type": args[0], "steps": 5, "estimated_total_cost_idr": 1234567}


class DummyCoolingAdvisor:
    def advise(self, **kwargs):
        return {"strategy": "cross_ventilation", "inputs": kwargs}


class DummyDisasterReporter:
    def report(self, *args):
        return {"damage_classification": "rusak_sedang", "location": args[0]}


class DummySettlementAdvisor:
    def advise(self, *args):
        return {"priority": "sanitasi", "location": args[0]}


def test_health_endpoint_is_fast_and_does_not_load_answer_engine(monkeypatch):
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
    monkeypatch.setattr(
        server,
        "get_answer_engine",
        lambda: (_ for _ in ()).throw(AssertionError("health must not load the RAG engine")),
    )

    client = TestClient(server.app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["app_title"] == "Arsitrad v2"
    assert "model_exists" in payload
    assert "sparse_index_exists" in payload


def test_bootstrap_endpoint_returns_frontend_contract(monkeypatch):
    monkeypatch.setattr(server, "load_ui_settings", lambda config_path=server.DEFAULT_CONFIG_PATH: {
        "app_title": "Arsitrad v2",
        "disclaimer": "demo disclaimer",
        "default_question": "Apa itu PBG?",
    })

    client = TestClient(server.app)
    response = client.get("/api/bootstrap")

    assert response.status_code == 200
    payload = response.json()
    assert payload["app_title"] == "Arsitrad v2"
    assert payload["default_question"] == "Apa itu PBG?"
    assert payload["quick_prompts"]
    assert {module["id"] for module in payload["modules"]} == {
        "regulation",
        "permit",
        "cooling",
        "disaster",
        "settlement",
    }


def test_trycloudflare_origin_is_allowed_by_default(monkeypatch):
    monkeypatch.delenv("ARSITRAD_WEB_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("ARSITRAD_WEB_ALLOWED_ORIGIN_REGEX", raising=False)
    server.get_allowed_origins.cache_clear()
    server.get_allowed_origin_regex.cache_clear()

    client = TestClient(server.create_app())
    response = client.options(
        "/health",
        headers={
            "Origin": "https://scheme-yale-museum-seventh.trycloudflare.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://scheme-yale-museum-seventh.trycloudflare.com"


def test_allowed_origins_env_is_trimmed(monkeypatch):
    monkeypatch.setenv("ARSITRAD_WEB_ALLOWED_ORIGINS", " https://front.example.com/ , http://127.0.0.1:3000 ")
    monkeypatch.setenv("ARSITRAD_WEB_ALLOWED_ORIGIN_REGEX", "")
    server.get_allowed_origins.cache_clear()
    server.get_allowed_origin_regex.cache_clear()

    client = TestClient(server.create_app())
    response = client.options(
        "/health",
        headers={
            "Origin": "https://front.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://front.example.com"


def test_ask_endpoint_serializes_engine_result_and_strips_question(monkeypatch):
    engine = DummyEngine()
    monkeypatch.setattr(server, "get_answer_engine", lambda: engine)

    client = TestClient(server.app)
    response = client.post(
        "/api/ask",
        json={
            "question": "  Apa itu SBKBG?  ",
            "history": [{"role": "user", "content": "Konteks awal"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["used_model"] is True
    assert payload["retrieval"]["standalone_query"] == "Apa itu SBKBG?"
    assert payload["retrieval"]["candidates"][0]["metadata"]["source_name"] == "Permen_12_2024_SBKBG"
    assert engine.calls[0]["question"] == "Apa itu SBKBG?"
    assert engine.calls[0]["history"] == [{"role": "user", "content": "Konteks awal"}]


def test_ask_endpoint_returns_clean_503_on_engine_failure(monkeypatch):
    monkeypatch.setattr(server, "get_answer_engine", lambda: FailingEngine())

    client = TestClient(server.app)
    response = client.post("/api/ask", json={"question": "Apa itu PBG?"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Regulation QA is temporarily unavailable"}


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


def test_cooling_endpoint_returns_payload(monkeypatch):
    monkeypatch.setattr(server, "get_passive_cooling_advisor", lambda: DummyCoolingAdvisor())

    client = TestClient(server.app)
    response = client.post(
        "/api/cooling",
        json={
            "dimensions": {"length_m": 8, "width_m": 6, "height_m": 3, "floor_count": 1},
            "orientation": "utara-selatan",
            "materials": {"wall_material": "bata", "roof_material": "genteng"},
            "climate_zone": "tropical_basah",
            "budget_idr": 5000000,
        },
    )

    assert response.status_code == 200
    payload = response.json()["payload"]
    assert payload["strategy"] == "cross_ventilation"
    assert payload["inputs"]["dimensions"]["length_m"] == 8


def test_disaster_endpoint_returns_payload(monkeypatch):
    monkeypatch.setattr(server, "get_disaster_damage_reporter", lambda: DummyDisasterReporter())

    client = TestClient(server.app)
    response = client.post(
        "/api/disaster",
        json={
            "location": "Cianjur",
            "disaster_type": "gempa",
            "building_type": "rumah_tinggal",
            "damage_description": "Dinding retak lebar dan lantai turun",
            "floor_area_m2": 80,
            "photo_urls": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()["payload"]
    assert payload["damage_classification"] == "rusak_sedang"
    assert payload["location"] == "Cianjur"


def test_settlement_endpoint_returns_payload(monkeypatch):
    monkeypatch.setattr(server, "get_settlement_upgrading_advisor", lambda: DummySettlementAdvisor())

    client = TestClient(server.app)
    response = client.post(
        "/api/settlement",
        json={
            "location": "Kampung Tambakrejo",
            "population_density": 450,
            "current_infrastructure": "Air bersih ada, sanitasi kurang, drainase buruk",
            "budget_constraint_idr": 25000000,
            "priority_goals": ["sanitasi", "drainase"],
        },
    )

    assert response.status_code == 200
    payload = response.json()["payload"]
    assert payload["priority"] == "sanitasi"
    assert payload["location"] == "Kampung Tambakrejo"
