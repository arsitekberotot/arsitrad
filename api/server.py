from __future__ import annotations

import json
import os
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Literal, TypeVar

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

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
DEFAULT_ALLOWED_ORIGIN_REGEX = r"https://.*\.trycloudflare\.com"
T = TypeVar("T")


class ApiModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class ChatMessage(ApiModel):
    role: Literal["user", "assistant"]
    content: str


class ImageAttachment(ApiModel):
    name: str = Field(min_length=1, max_length=160)
    content_type: str = Field(pattern=r"^image/")
    size_bytes: int = Field(ge=0, le=8_000_000)
    data_url: str = Field(min_length=16)


class AskRequest(ApiModel):
    question: str = Field(min_length=3)
    history: list[ChatMessage] = Field(default_factory=list)
    images: list[ImageAttachment] = Field(default_factory=list, max_length=4)


class PermitRequest(ApiModel):
    building_type: str = Field(min_length=1)
    location: str = Field(min_length=1)
    floor_area_m2: float = Field(gt=0)
    land_area_m2: float = Field(gt=0)
    building_height_m: float | None = Field(default=None, gt=0)
    building_function: str = "hunian"


class CoolingDimensions(ApiModel):
    length_m: float = Field(gt=0)
    width_m: float = Field(gt=0)
    height_m: float = Field(gt=0)
    floor_count: int = Field(default=1, ge=1)


class CoolingMaterials(ApiModel):
    wall_material: str = Field(min_length=1)
    roof_material: str = Field(min_length=1)


class CoolingRequest(ApiModel):
    dimensions: CoolingDimensions
    orientation: str = Field(min_length=1)
    materials: CoolingMaterials
    climate_zone: str = Field(min_length=1)
    budget_idr: float | None = Field(default=None, ge=0)


class DisasterRequest(ApiModel):
    location: str = Field(min_length=1)
    disaster_type: str = Field(min_length=1)
    building_type: str = Field(min_length=1)
    damage_description: str = Field(min_length=5)
    floor_area_m2: float | None = Field(default=None, ge=0)
    photo_urls: list[str] = Field(default_factory=list)


class SettlementRequest(ApiModel):
    location: str = Field(min_length=1)
    population_density: float = Field(gt=0)
    current_infrastructure: str = Field(min_length=5)
    budget_constraint_idr: float = Field(gt=0)
    priority_goals: list[str] = Field(default_factory=list)


class CandidateResponse(ApiModel):
    chunk_key: str
    content: str
    metadata: dict[str, Any]
    score: float
    source: str


class RetrievalResponse(ApiModel):
    question: str
    standalone_query: str
    expanded_queries: list[str]
    filters: dict[str, Any]
    candidates: list[CandidateResponse]
    should_answer: bool
    confidence: float
    message: str | None = None


class AskResponse(ApiModel):
    answer: str
    used_model: bool
    model_path: str | None = None
    raw_text: str | None = None
    retrieval: RetrievalResponse
    visual_analysis: str | None = None


class ModuleResponse(ApiModel):
    payload: dict[str, Any]


class BootstrapResponse(ApiModel):
    app_title: str
    disclaimer: str
    default_question: str
    quick_prompts: list[str]
    modules: list[dict[str, str]]


class HealthResponse(ApiModel):
    status: Literal["ok"]
    config_path: str
    model_path: str
    model_exists: bool
    sparse_index_exists: bool
    dense_enabled: bool
    app_title: str
    vision_enabled: bool = False
    vision_base_url: str | None = None


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


class NoopVisionAnalyzer:
    def analyze(self, images: list[ImageAttachment]) -> str:
        return ""


class LlamaCppVisionAnalyzer:
    def __init__(self, base_url: str, model: str = "gemma-4-E4B-it", timeout_seconds: float = 45.0, max_tokens: int = 220):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens

    def analyze(self, images: list[ImageAttachment]) -> str:
        if not images:
            return ""

        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "Analyze the attached building image(s) as preliminary architectural visual triage. "
                    "Return concise observations only: visible damage, likely risk category, what must be verified on site, "
                    "and any readable OCR text. Do not invent hidden structural conditions. Use Indonesian."
                ),
            }
        ]
        for image in images:
            content.append({"type": "image_url", "image_url": {"url": image.data_url}})

        request_payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a cautious building-photo triage assistant for Arsitrad. "
                        "You describe visible evidence, not final engineering certification."
                    ),
                },
                {"role": "user", "content": content},
            ],
            "temperature": 0.1,
            "max_tokens": self.max_tokens,
        }
        request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(request_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))

        choice = response_payload.get("choices", [{}])[0]
        message = choice.get("message", {})
        content_text = message.get("content") or choice.get("text") or ""
        if isinstance(content_text, list):
            content_text = "\n".join(str(item.get("text", item)) for item in content_text)
        return str(content_text).strip()


@lru_cache(maxsize=1)
def get_visual_analyzer() -> NoopVisionAnalyzer | LlamaCppVisionAnalyzer:
    base_url = os.getenv("ARSITRAD_VISION_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        return NoopVisionAnalyzer()
    return LlamaCppVisionAnalyzer(
        base_url=base_url,
        model=os.getenv("ARSITRAD_VISION_MODEL", "gemma-4-E4B-it"),
        timeout_seconds=float(os.getenv("ARSITRAD_VISION_TIMEOUT_SECONDS", "45")),
        max_tokens=int(os.getenv("ARSITRAD_VISION_MAX_TOKENS", "220")),
    )


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
    return [item.strip().rstrip("/") for item in raw_origins.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_allowed_origin_regex() -> str | None:
    raw_regex = os.getenv("ARSITRAD_WEB_ALLOWED_ORIGIN_REGEX")
    if raw_regex == "":
        return None
    return raw_regex or DEFAULT_ALLOWED_ORIGIN_REGEX


def clean_question(question: str) -> str:
    cleaned = question.strip()
    if len(cleaned) < 3:
        raise HTTPException(status_code=400, detail="Question must contain at least 3 non-space characters")
    return cleaned


def build_visual_context(images: list[ImageAttachment]) -> str:
    if not images:
        return ""

    lines = ["Visual attachments submitted:"]
    for index, image in enumerate(images, start=1):
        lines.append(
            f"[{index}] {image.name} ({image.content_type}, {image.size_bytes} bytes) — "
            "user-provided visual input such as a floor plan, site photo, or building reference."
        )
    lines.append(
        "Use these visual attachment notes as context. If detailed visual inspection is required, "
        "state what must be verified from the image and avoid inventing unseen details."
    )
    return "\n".join(lines)


def analyze_visual_attachments(images: list[ImageAttachment]) -> str:
    if not images:
        return ""
    try:
        return get_visual_analyzer().analyze(images).strip()
    except Exception:
        return (
            "Vision bridge unavailable. Treat uploaded images as user-provided context only; "
            "ask the user to describe visible damage before making specific recommendations."
        )


def build_building_doctor_context(visual_analysis: str) -> str:
    if not visual_analysis:
        return ""
    return "\n".join(
        [
            "Building Doctor mode:",
            "Use the Gemma vision observations as preliminary visual triage, then answer as an architectural AI advisor.",
            "Give: visible issue summary, urgent safety checks, likely repair direction, missing site data, and regulation/SNI/PUPR evidence to verify.",
            "Be explicit that this is not a final structural diagnosis and do not claim structural certification from an image alone.",
            "",
            "Gemma vision observations:",
            visual_analysis,
        ]
    )


def question_with_visual_context(question: str, images: list[ImageAttachment], visual_analysis: str = "") -> str:
    visual_context = build_visual_context(images)
    building_doctor_context = build_building_doctor_context(visual_analysis)
    contexts = [context for context in [building_doctor_context, visual_context] if context]
    if not contexts:
        return question
    return f"{question}\n\n" + "\n\n".join(contexts)


def run_api_call(operation: str, fn: Callable[[], T]) -> T:
    try:
        return fn()
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - exact failures vary by environment
        raise HTTPException(status_code=503, detail=f"{operation} is temporarily unavailable") from exc


def to_json_payload(payload: Any) -> dict[str, Any]:
    encoded = jsonable_encoder(payload)
    if not isinstance(encoded, dict):
        return {"result": encoded}
    return encoded


QUICK_PROMPTS = [
    "Apa yang perlu dicek dari retak diagonal pada dinding rumah tinggal?",
    "Upload foto bangunan rusak, lalu minta Arsitrad membuat triase awal dan checklist inspeksi.",
    "Apa syarat PBG untuk renovasi rumah tinggal 2 lantai di Semarang?",
    "Apa yang harus dicek untuk bangunan di dekat sungai menurut tata ruang?",
]


MODULES = [
    {
        "id": "regulation",
        "title": "AI Advisor",
        "description": "Building Doctor: triase foto/keluhan bangunan lalu kaitkan saran ke regulasi, SNI, PUPR, PBG, RDTR, dan RTRW.",
    },
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
        allow_origin_regex=get_allowed_origin_regex(),
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
            vision_enabled=bool(os.getenv("ARSITRAD_VISION_BASE_URL", "").strip()),
            vision_base_url=os.getenv("ARSITRAD_VISION_BASE_URL", "").strip().rstrip("/") or None,
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
        question = clean_question(payload.question)
        visual_analysis = analyze_visual_attachments(payload.images)
        engine_question = question_with_visual_context(question, payload.images, visual_analysis)

        result = run_api_call(
            "AI Advisor",
            lambda: get_answer_engine().answer(
                engine_question,
                history=[message.model_dump() for message in payload.history],
            ),
        )
        response_payload = serialize_result(result)
        response_payload["visual_analysis"] = visual_analysis or None
        return AskResponse(**response_payload)

    @app.post("/api/permit", response_model=ModuleResponse)
    def permit(payload: PermitRequest) -> ModuleResponse:
        guidance = run_api_call(
            "Permit Navigator",
            lambda: get_building_permit_navigator().navigate(
                payload.building_type,
                payload.location,
                payload.floor_area_m2,
                payload.land_area_m2,
                payload.building_height_m,
                payload.building_function,
            ),
        )
        return ModuleResponse(payload=to_json_payload(guidance))

    @app.post("/api/cooling", response_model=ModuleResponse)
    def cooling(payload: CoolingRequest) -> ModuleResponse:
        advice = run_api_call(
            "Passive Cooling",
            lambda: get_passive_cooling_advisor().advise(
                dimensions=payload.dimensions.model_dump(),
                orientation=payload.orientation,
                materials=payload.materials.model_dump(),
                climate_zone=payload.climate_zone,
                budget_idr=payload.budget_idr,
            ),
        )
        return ModuleResponse(payload=to_json_payload(advice))

    @app.post("/api/disaster", response_model=ModuleResponse)
    def disaster(payload: DisasterRequest) -> ModuleResponse:
        report = run_api_call(
            "Disaster Reporter",
            lambda: get_disaster_damage_reporter().report(
                payload.location,
                payload.disaster_type,
                payload.building_type,
                payload.damage_description,
                payload.floor_area_m2,
                payload.photo_urls,
            ),
        )
        return ModuleResponse(payload=to_json_payload(report))

    @app.post("/api/settlement", response_model=ModuleResponse)
    def settlement(payload: SettlementRequest) -> ModuleResponse:
        advice = run_api_call(
            "Settlement Upgrading",
            lambda: get_settlement_upgrading_advisor().advise(
                payload.location,
                payload.population_density,
                payload.current_infrastructure,
                payload.budget_constraint_idr,
                payload.priority_goals,
            ),
        )
        return ModuleResponse(payload=to_json_payload(advice))

    return app


app = create_app()
