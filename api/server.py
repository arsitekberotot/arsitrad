from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent.cooling import PassiveCoolingAdvisor
from agent.disaster import DisasterDamageReporter
from agent.permit import BuildingPermitNavigator
from agent.settlement import SettlementUpgradingAdvisor
from pipeline.inference import ArsitradAnswerEngine

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = Path(os.getenv("ARSITRAD_CONFIG_PATH", REPO_ROOT / "config.yaml"))
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AskRequest(BaseModel):
    question: str = Field(min_length=3)
    history: list[ChatMessage] = Field(default_factory=list)


class PermitRequest(BaseModel):
    building_type: str
    location: str
    floor_area_m2: float = Field(gt=0)
    land_area_m2: float = Field(gt=0)
    building_height_m: float | None = Field(default=None, gt=0)
    building_function: str = "hunian"


class CoolingDimensions(BaseModel):
    length_m: float = Field(gt=0)
    width_m: float = Field(gt=0)
    height_m: float = Field(gt=0)
    floor_count: int = Field(default=1, ge=1)


class CoolingMaterials(BaseModel):
    wall_material: str
    roof_material: str


class CoolingRequest(BaseModel):
    dimensions: CoolingDimensions
    orientation: str
    materials: CoolingMaterials
    climate_zone: str
    budget_idr: float | None = Field(default=None, ge=0)


class DisasterRequest(BaseModel):
    location: str
    disaster_type: str
    building_type: str
    damage_description: str = Field(min_length=5)
    floor_area_m2: float | None = Field(default=None, ge=0)
    photo_urls: list[str] = Field(default_factory=list)


class SettlementRequest(BaseModel):
    location: str
    population_density: float = Field(gt=0)
    current_infrastructure: str = Field(min_length=5)
    budget_constraint_idr: float = Field(gt=0)
    priority_goals: list[str] = Field(default_factory=list)


class CandidateResponse(BaseModel):
    chunk_key: str
    content: str
    metadata: dict[str, Any]
    score: float
    source: str


class RetrievalResponse(BaseModel):
    question: str
    standalone_query: str
    expanded_queries: list[str]
    filters: dict[str, Any]
    candidates: list[CandidateResponse]
    should_answer: bool
    confidence: float
    message: str | None = None


class AskResponse(BaseModel):
    answer: str
    used_model: bool
    model_path: str | None = None
    raw_text: str | None = None
    retrieval: RetrievalResponse


class ModuleResponse(BaseModel):
    payload: dict[str, Any]


class BootstrapResponse(BaseModel):
    app_title: str
    disclaimer: str
    default_question: str
    quick_prompts: list[str]
    modules: list[dict[str, str]]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    config_path: str
    model_path: str
    model_exists: bool
    sparse_index_exists: bool
    dense_enabled: bool
    app_title: str


@lru_cache(maxsize=1)
def load_ui_settings(config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, str]:
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    ui_settings = config.get("v2", {}).get("ui", {})
    return {
        "app_title": ui_settings.get("app_title", "Arsitrad v2"),
        "disclaimer": ui_settings.get(
            "disclaimer",
            "Arsitrad adalah alat bantu informasi regulasi, bukan pengganti konsultasi profesional.",
        ),
        "default_question": ui_settings.get(
            "default_question",
            "Apa syarat PBG untuk rumah tinggal 2 lantai di Semarang?",
        ),
    }


@lru_cache(maxsize=1)
def get_answer_engine() -> ArsitradAnswerEngine:
    return ArsitradAnswerEngine(config_path=DEFAULT_CONFIG_PATH)


@lru_cache(maxsize=1)
def get_building_permit_navigator() -> BuildingPermitNavigator:
    return BuildingPermitNavigator()


@lru_cache(maxsize=1)
def get_passive_cooling_advisor() -> PassiveCoolingAdvisor:
    return PassiveCoolingAdvisor()


@lru_cache(maxsize=1)
def get_disaster_damage_reporter() -> DisasterDamageReporter:
    return DisasterDamageReporter()


@lru_cache(maxsize=1)
def get_settlement_upgrading_advisor() -> SettlementUpgradingAdvisor:
    return SettlementUpgradingAdvisor()


@lru_cache(maxsize=1)
def get_runtime_config() -> dict[str, Any]:
    with DEFAULT_CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@lru_cache(maxsize=1)
def get_allowed_origins() -> list[str]:
    raw_origins = os.getenv("ARSITRAD_WEB_ALLOWED_ORIGINS")
    if not raw_origins:
        return DEFAULT_ALLOWED_ORIGINS
    return [item.strip() for item in raw_origins.split(",") if item.strip()]


QUICK_PROMPTS = [
    "Apa syarat PBG untuk rumah tinggal 2 lantai di Semarang?",
    "Apa aturan bangunan gedung negara terkait SBKBG?",
    "Apakah RDTR wajib dicek sebelum mengurus PBG?",
    "Apa yang harus dicek untuk bangunan di dekat sungai menurut tata ruang?",
]


MODULES = [
    {"id": "regulation", "title": "Regulation QA", "description": "Tanya regulasi, PBG, RDTR, RTRW, SBKBG, dan standar teknis."},
    {"id": "permit", "title": "Permit Navigator", "description": "Hitung checklist dan alur pengurusan izin bangunan."},
    {"id": "cooling", "title": "Passive Cooling", "description": "Rancang strategi pendinginan pasif untuk iklim tropis."},
    {"id": "disaster", "title": "Disaster Reporter", "description": "Klasifikasi kerusakan dan estimasi langkah perbaikan."},
    {"id": "settlement", "title": "Settlement Upgrading", "description": "Prioritaskan intervensi permukiman sesuai budget."},
]


def serialize_candidate(candidate: Any) -> dict[str, Any]:
    return {
        "chunk_key": candidate.chunk_key,
        "content": candidate.content,
        "metadata": dict(candidate.metadata),
        "score": float(candidate.score),
        "source": candidate.source,
    }


def serialize_retrieval(retrieval: Any) -> dict[str, Any]:
    return {
        "question": retrieval.question,
        "standalone_query": retrieval.standalone_query,
        "expanded_queries": list(retrieval.expanded_queries),
        "filters": dict(retrieval.filters),
        "candidates": [serialize_candidate(candidate) for candidate in retrieval.candidates],
        "should_answer": bool(retrieval.should_answer),
        "confidence": float(retrieval.confidence),
        "message": retrieval.message,
    }


def serialize_result(result: Any) -> dict[str, Any]:
    return {
        "answer": result.answer,
        "used_model": bool(result.used_model),
        "model_path": result.model_path,
        "raw_text": result.raw_text,
        "retrieval": serialize_retrieval(result.retrieval),
    }


def create_app() -> FastAPI:
    app = FastAPI(title="Arsitrad API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        config = get_runtime_config().get("v2", {})
        corpus = config.get("corpus", {})
        inference = config.get("inference", {})
        model_path = REPO_ROOT / str(inference.get("model_path", "./models/gemma-4-E4B-it-Q4_K_M.gguf"))
        sparse_index_path = REPO_ROOT / str(corpus.get("sparse_index_path", "./data/processed/v2/bm25_corpus.jsonl"))
        settings = load_ui_settings()

        return HealthResponse(
            status="ok",
            config_path=str(DEFAULT_CONFIG_PATH),
            model_path=str(model_path),
            model_exists=model_path.exists(),
            sparse_index_exists=sparse_index_path.exists(),
            dense_enabled=bool(os.getenv("ARSITRAD_DATABASE_URL")),
            app_title=settings["app_title"],
        )

    @app.get("/api/bootstrap", response_model=BootstrapResponse)
    def bootstrap() -> BootstrapResponse:
        settings = load_ui_settings()
        return BootstrapResponse(
            app_title=settings["app_title"],
            disclaimer=settings["disclaimer"],
            default_question=settings["default_question"],
            quick_prompts=QUICK_PROMPTS,
            modules=MODULES,
        )

    @app.post("/api/ask", response_model=AskResponse)
    def ask(payload: AskRequest) -> AskResponse:
        question = payload.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="Question must not be empty")

        result = get_answer_engine().answer(
            question,
            history=[message.model_dump() for message in payload.history],
        )
        return AskResponse(**serialize_result(result))

    @app.post("/api/permit", response_model=ModuleResponse)
    def permit(payload: PermitRequest) -> ModuleResponse:
        guidance = get_building_permit_navigator().navigate(
            payload.building_type,
            payload.location,
            payload.floor_area_m2,
            payload.land_area_m2,
            payload.building_height_m,
            payload.building_function,
        )
        return ModuleResponse(payload=guidance)

    @app.post("/api/cooling", response_model=ModuleResponse)
    def cooling(payload: CoolingRequest) -> ModuleResponse:
        advice = get_passive_cooling_advisor().advise(
            dimensions=payload.dimensions.model_dump(),
            orientation=payload.orientation,
            materials=payload.materials.model_dump(),
            climate_zone=payload.climate_zone,
            budget_idr=payload.budget_idr,
        )
        return ModuleResponse(payload=advice)

    @app.post("/api/disaster", response_model=ModuleResponse)
    def disaster(payload: DisasterRequest) -> ModuleResponse:
        report = get_disaster_damage_reporter().report(
            payload.location,
            payload.disaster_type,
            payload.building_type,
            payload.damage_description,
            payload.floor_area_m2,
            payload.photo_urls,
        )
        return ModuleResponse(payload=report)

    @app.post("/api/settlement", response_model=ModuleResponse)
    def settlement(payload: SettlementRequest) -> ModuleResponse:
        advice = get_settlement_upgrading_advisor().advise(
            payload.location,
            payload.population_density,
            payload.current_infrastructure,
            payload.budget_constraint_idr,
            payload.priority_goals,
        )
        return ModuleResponse(payload=advice)

    return app


app = create_app()
