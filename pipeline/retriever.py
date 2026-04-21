from __future__ import annotations

"""Hybrid retrieval for Arsitrad v2."""

import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Sequence

import yaml

from pipeline.conversation_memory import contextualize_question
from pipeline.ingest import E5Embedder, load_config, resolve_database_url
from pipeline.query_expander import QueryInterpretation, interpret_query, is_regionless_spatial_query
from pipeline.taxonomy import (
    enrich_metadata,
    infer_building_use,
    infer_topic,
    is_rpjmd_source,
    is_spatial_source,
    source_name_matches,
)

TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ0-9]+")


@dataclass(slots=True)
class CandidateChunk:
    chunk_key: str
    content: str
    metadata: dict[str, object]
    score: float
    source: str


@dataclass(slots=True)
class RetrievalResult:
    question: str
    standalone_query: str
    expanded_queries: list[str]
    filters: dict[str, object]
    candidates: list[CandidateChunk]
    should_answer: bool
    confidence: float
    message: str | None = None


@dataclass(slots=True)
class RetrievalConfig:
    dense_top_k: int = 20
    sparse_top_k: int = 20
    rerank_top_k: int = 5
    rrf_k: int = 60
    confidence_threshold: float = 0.6
    include_national_for_local_queries: bool = True


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall((text or "").lower())


def matches_filters(
    metadata: dict[str, object],
    filters: dict[str, object],
    *,
    assume_enriched: bool = False,
) -> bool:
    enriched = metadata if assume_enriched else enrich_metadata(metadata)
    for key, expected in filters.items():
        if expected in (None, "", []):
            continue
        actual = enriched.get(key)
        if key == "year":
            if actual is None:
                return False
            if int(actual) != int(expected):
                return False
            continue
        if key == "region":
            if actual is None:
                return False
            if str(actual).lower() == str(expected).lower():
                continue
            if str(expected).lower() != "nasional" and str(actual).lower() == "nasional":
                continue
            return False
        if key in {"topic", "building_use"}:
            if actual in (None, "", "general_regulation"):
                continue
            if str(actual).lower() != str(expected).lower():
                return False
            continue
        if actual is None:
            return False
        if str(actual).lower() != str(expected).lower():
            return False
    return True


def rrf_fusion(*ranked_lists: Sequence[CandidateChunk], k: int = 60, limit: int | None = None) -> list[CandidateChunk]:
    fused: dict[str, CandidateChunk] = {}
    scores: dict[str, float] = {}

    for ranked in ranked_lists:
        for rank, item in enumerate(ranked, start=1):
            scores[item.chunk_key] = scores.get(item.chunk_key, 0.0) + 1.0 / (k + rank)
            existing = fused.get(item.chunk_key)
            if existing is None or item.score > existing.score:
                fused[item.chunk_key] = item

    ordered = sorted(fused.values(), key=lambda item: scores[item.chunk_key], reverse=True)
    reranked = [replace(item, score=scores[item.chunk_key], source="fused") for item in ordered]
    return reranked[:limit] if limit else reranked


def build_low_confidence_message(filters: dict[str, object]) -> str:
    region = filters.get("region")
    region_text = f" untuk wilayah {region}" if region else ""
    return (
        "Arsitrad tidak dapat menemukan regulasi yang cukup spesifik"
        f"{region_text} di dalam database saat ini. "
        "Mohon verifikasi langsung ke dinas tata ruang setempat atau profesional berlisensi."
    )


def build_out_of_scope_message() -> str:
    return (
        "Pertanyaan ini lebih dekat ke gaya atau konsep desain arsitektur, bukan regulasi atau perizinan bangunan. "
        "Coba tanyakan hal yang spesifik seperti PBG, SLF, KDB, KDH, RDTR, RTRW, aksesibilitas, atau proteksi kebakaran."
    )


def load_sparse_records(path: str | Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    sparse_path = Path(path)
    if not sparse_path.exists():
        return records
    with sparse_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def authority_score_adjustment(query: str, filters: dict[str, object], candidate: CandidateChunk) -> float:
    metadata = enrich_metadata(candidate.metadata, candidate.content)
    source_name = str(metadata.get("source_name") or "")
    lowered_query = query.lower()
    lowered_content = candidate.content.lower()
    topic = filters.get("topic") or infer_topic(query)
    building_use = filters.get("building_use") or infer_building_use(query)
    adjustment = 0.0
    zoning_terms = ("rdtr", "rtrw", "tata ruang", "zonasi", "kdb", "kdh", "klb", "gsb")
    permit_terms = ("imb", "pbg", "slf", "persetujuan bangunan gedung", "sertifikat laik fungsi")
    regionless_spatial = is_regionless_spatial_query(query)

    if is_rpjmd_source(source_name) and not any(
        term in lowered_query for term in ("rpjmd", "rencana pembangunan jangka menengah daerah")
    ):
        adjustment -= 0.75

    candidate_region = metadata.get("region")
    if candidate_region and filters.get("region") and str(candidate_region).lower() == str(filters["region"]).lower():
        adjustment += 0.12

    candidate_reg_type = metadata.get("reg_type")
    if candidate_reg_type and filters.get("reg_type") and str(candidate_reg_type).lower() == str(filters["reg_type"]).lower():
        adjustment += 0.10

    candidate_topic = metadata.get("topic")
    if topic and candidate_topic and str(candidate_topic).lower() == str(topic).lower():
        adjustment += 0.22
    elif topic == "building_permit" and source_name_matches(source_name, "rdtr", "rtrw", "tata ruang", "zonasi"):
        if any(term in lowered_query for term in zoning_terms):
            adjustment += 0.18
    elif topic and candidate_topic and str(candidate_topic).lower() != str(topic).lower():
        adjustment -= 0.05

    candidate_use = metadata.get("building_use")
    if building_use and candidate_use and str(candidate_use).lower() == str(building_use).lower():
        adjustment += 0.18
    elif building_use and candidate_use in (None, "", "general"):
        adjustment -= 0.12
    elif building_use:
        adjustment -= 0.10

    if topic == "spatial_planning" or any(term in lowered_query for term in ("rdtr", "rtrw", "tata ruang", "zonasi", "sempadan sungai")):
        if is_spatial_source(source_name):
            adjustment += 0.30
        if regionless_spatial:
            if source_name_matches(source_name, "pp_21_2021", "penataan ruang"):
                adjustment += 0.28
            if source_name_matches(source_name, "cipta kerja"):
                adjustment -= 0.12
        if filters.get("region") in (None, "", "nasional"):
            if source_name_matches(source_name, "provinsi"):
                adjustment += 0.10
            elif metadata.get("region") not in (None, "", "nasional"):
                adjustment -= 0.08
        if regionless_spatial and metadata.get("region") not in (None, "", "nasional"):
            if source_name_matches(source_name, "provinsi"):
                adjustment += 0.06
            else:
                adjustment -= 0.18

    if topic == "accessibility" and source_name_matches(source_name, "permen 14 2017", "permen_14_2017", "pkbg", "kemudahan"):
        adjustment += 0.35
    if topic == "fire_safety" and source_name_matches(source_name, "proteksi kebakaran", "kebakaran", "sprinkler", "hydrant"):
        adjustment += 0.35
    if topic == "ownership" and source_name_matches(source_name, "sbkbg"):
        adjustment += 0.45
    if topic == "heritage" and source_name_matches(source_name, "heritage", "konservasi", "cagar budaya"):
        adjustment += 0.35

    if topic == "building_permit" and any(term in lowered_query for term in permit_terms):
        if source_name_matches(source_name, "pp_16_2021", "pp 16 2021", "persetujuan bangunan gedung", "sertifikat laik fungsi"):
            adjustment += 0.18
        if source_name_matches(source_name, "pp_28_2025", "pp 28 2025", "perizinan berbasis risiko", "cipta kerja"):
            adjustment += 0.10
        if source_name_matches(source_name, "jasa konstruksi"):
            adjustment -= 0.25

    if topic == "building_permit" and any(term in lowered_query for term in ("dokumen", "administratif", "teknis")):
        if source_name_matches(source_name, "pp_16_2021", "pp 16 2021", "uu_28_2002", "bangunangedung"):
            adjustment += 0.12
        if source_name_matches(source_name, "standarkegiatan") or any(
            term in lowered_content for term in ("penyelenggaraan spam", "sistem oss", "perizinan berusaha", "pbbr")
        ):
            adjustment -= 0.30

    if topic == "building_permit" and filters.get("region") in (None, "", "nasional"):
        if metadata.get("region") not in (None, "", "nasional") and not any(term in lowered_query for term in zoning_terms):
            adjustment -= 0.22
        if str(candidate_reg_type or "").lower() in {"pp", "permen", "uu"}:
            adjustment += 0.10

    return adjustment


class JsonlSparseIndex:
    def __init__(self, records: Sequence[dict[str, object]] | None = None, path: str | Path | None = None):
        raw_records = list(records) if records is not None else load_sparse_records(path) if path else []
        self.records: list[dict[str, object]] = []
        self.metadatas: list[dict[str, object]] = []
        for record in raw_records:
            content = str(record.get("content", ""))
            metadata = enrich_metadata(record.get("metadata", {}), content)
            normalized_record = dict(record)
            normalized_record["content"] = content
            normalized_record["metadata"] = metadata
            self.records.append(normalized_record)
            self.metadatas.append(metadata)
        self.tokens = [tokenize(record["content"]) for record in self.records]
        self._bm25 = None
        if self.records:
            try:
                from rank_bm25 import BM25Okapi

                self._bm25 = BM25Okapi(self.tokens)
            except Exception:
                self._bm25 = None

    def search(self, query: str, filters: dict[str, object], top_k: int = 20) -> list[CandidateChunk]:
        if not self.records:
            return []

        filtered_records: list[tuple[int, dict[str, object], dict[str, object]]] = []
        for idx, record in enumerate(self.records):
            metadata = self.metadatas[idx]
            if matches_filters(metadata, filters, assume_enriched=True):
                filtered_records.append((idx, record, metadata))

        if not filtered_records:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        if self._bm25 is not None:
            all_scores = self._bm25.get_scores(query_tokens)
            scored = [
                (all_scores[idx], record, metadata)
                for idx, record, metadata in filtered_records
                if all_scores[idx] > 0
            ]
        else:
            query_terms = set(query_tokens)
            scored = []
            for idx, record, metadata in filtered_records:
                doc_terms = set(self.tokens[idx])
                overlap = len(query_terms & doc_terms)
                if overlap:
                    scored.append((overlap / max(len(query_terms), 1), record, metadata))

        ranked = sorted(scored, key=lambda item: item[0], reverse=True)[:top_k]
        return [
            CandidateChunk(
                chunk_key=record["chunk_key"],
                content=record["content"],
                metadata=metadata,
                score=float(score),
                source="sparse",
            )
            for score, record, metadata in ranked
        ]


class PostgresDenseRetriever:
    def __init__(
        self,
        database_url: str,
        table_name: str = "regulation_chunks",
        embedding_model: str = "intfloat/multilingual-e5-large",
        include_national_for_local_queries: bool = True,
    ):
        self.database_url = database_url
        self.table_name = table_name
        self.embedder = E5Embedder(embedding_model)
        self.include_national_for_local_queries = include_national_for_local_queries

    def search(self, query: str, filters: dict[str, object], top_k: int = 20) -> list[CandidateChunk]:
        import psycopg
        from pgvector import Vector
        from pgvector.psycopg import register_vector
        from psycopg.rows import dict_row

        query_embedding = Vector(self.embedder.embed_query(query))
        where_clauses = ["embedding IS NOT NULL"]
        candidate_limit = max(top_k * 3, top_k)
        params: dict[str, object] = {"embedding": query_embedding, "limit": candidate_limit}

        if region := filters.get("region"):
            if self.include_national_for_local_queries and str(region).lower() != "nasional":
                where_clauses.append("(region = %(region)s OR region = 'nasional')")
            else:
                where_clauses.append("region = %(region)s")
            params["region"] = region
        if year := filters.get("year"):
            where_clauses.append("year = %(year)s")
            params["year"] = year
        if reg_type := filters.get("reg_type"):
            where_clauses.append("reg_type = %(reg_type)s")
            params["reg_type"] = reg_type

        sql = f"""
            SELECT
                chunk_key,
                content,
                metadata,
                source_name,
                source_path,
                reg_type,
                region,
                typology,
                year,
                chunk_index,
                start_page,
                end_page,
                1 - (embedding <=> %(embedding)s) AS score
            FROM {self.table_name}
            WHERE {' AND '.join(where_clauses)}
            ORDER BY embedding <=> %(embedding)s
            LIMIT %(limit)s
        """

        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

        candidates: list[CandidateChunk] = []
        for row in rows:
            metadata = row["metadata"]
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            metadata = dict(metadata or {})
            metadata.setdefault("source_name", row.get("source_name"))
            metadata.setdefault("source_path", row.get("source_path"))
            metadata.setdefault("reg_type", row.get("reg_type"))
            metadata.setdefault("region", row.get("region"))
            metadata.setdefault("typology", row.get("typology"))
            metadata.setdefault("year", row.get("year"))
            metadata.setdefault("chunk_index", row.get("chunk_index"))
            metadata.setdefault("start_page", row.get("start_page"))
            metadata.setdefault("end_page", row.get("end_page"))
            metadata = enrich_metadata(metadata, row["content"])
            if not matches_filters(metadata, filters, assume_enriched=True):
                continue
            candidates.append(
                CandidateChunk(
                    chunk_key=row["chunk_key"],
                    content=row["content"],
                    metadata=metadata,
                    score=float(row["score"] or 0.0),
                    source="dense",
                )
            )
            if len(candidates) >= top_k:
                break
        return candidates


class CrossEncoderReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                from FlagEmbedding import FlagReranker

                self._model = FlagReranker(self.model_name, use_fp16=False)
            except Exception:
                self._model = False
        return self._model

    def _fallback_scores(self, query: str, candidates: Sequence[CandidateChunk]) -> list[float]:
        query_terms = set(tokenize(query))
        scores: list[float] = []
        for candidate in candidates:
            doc_terms = set(tokenize(candidate.content))
            overlap = len(query_terms & doc_terms)
            scores.append(overlap / max(len(query_terms), 1))
        return scores

    def rerank(
        self,
        query: str,
        candidates: Sequence[CandidateChunk],
        top_k: int = 5,
        filters: dict[str, object] | None = None,
    ) -> list[CandidateChunk]:
        if not candidates:
            return []

        if self.model:
            pairs = [[query, candidate.content] for candidate in candidates]
            try:
                scores = self.model.compute_score(pairs, normalize=True)
            except TypeError:
                scores = self.model.compute_score(pairs)
        else:
            scores = self._fallback_scores(query, candidates)

        ranked = sorted(
            [
                replace(
                    candidate,
                    score=float(score) + authority_score_adjustment(query, filters or {}, candidate),
                    source="reranked",
                )
                for candidate, score in zip(candidates, scores)
            ],
            key=lambda item: item.score,
            reverse=True,
        )
        return ranked[:top_k]


class HybridRetriever:
    def __init__(
        self,
        config_path: str | Path = "config.yaml",
        dense_retriever: object | None = None,
        sparse_index: object | None = None,
        reranker: object | None = None,
        config_overrides: dict[str, object] | None = None,
    ):
        config = load_config(config_path) if config_path and Path(config_path).exists() else {}
        v2 = config.get("v2", {})
        retrieval_block = v2.get("retrieval", {})
        corpus_block = v2.get("corpus", {})
        db_block = v2.get("database", {})

        merged = {
            "dense_top_k": retrieval_block.get("dense_top_k", 20),
            "sparse_top_k": retrieval_block.get("sparse_top_k", 20),
            "rerank_top_k": retrieval_block.get("rerank_top_k", 5),
            "rrf_k": retrieval_block.get("rrf_k", 60),
            "confidence_threshold": retrieval_block.get("confidence_threshold", 0.6),
            "include_national_for_local_queries": retrieval_block.get("include_national_for_local_queries", True),
        }
        if config_overrides:
            merged.update(config_overrides)
        self.settings = RetrievalConfig(**merged)
        self.embedding_model = v2.get("embedding_model", "intfloat/multilingual-e5-large")
        self.reranker_model = v2.get("reranker_model", "BAAI/bge-reranker-base")

        database_url = resolve_database_url(config) or db_block.get("default_url")
        if dense_retriever is not None:
            self.dense_retriever = dense_retriever
        elif database_url:
            self.dense_retriever = PostgresDenseRetriever(
                database_url=database_url,
                table_name=db_block.get("table", "regulation_chunks"),
                embedding_model=self.embedding_model,
                include_national_for_local_queries=self.settings.include_national_for_local_queries,
            )
        else:
            self.dense_retriever = None

        if sparse_index is not None:
            self.sparse_index = sparse_index
        else:
            self.sparse_index = JsonlSparseIndex(path=corpus_block.get("sparse_index_path"))

        self.reranker = reranker or CrossEncoderReranker(self.reranker_model)

    def retrieve(self, question: str, history: Sequence[dict[str, str]] | None = None) -> RetrievalResult:
        standalone_query = contextualize_question(question, history or [])
        interpretation: QueryInterpretation = interpret_query(standalone_query)

        if interpretation.filters.get("out_of_scope"):
            return RetrievalResult(
                question=question,
                standalone_query=standalone_query,
                expanded_queries=interpretation.expanded_queries,
                filters=interpretation.filters,
                candidates=[],
                should_answer=False,
                confidence=0.0,
                message=build_out_of_scope_message(),
            )

        dense_lists: list[list[CandidateChunk]] = []
        sparse_lists: list[list[CandidateChunk]] = []
        for query in interpretation.expanded_queries or [standalone_query]:
            if self.dense_retriever is not None:
                dense_lists.append(
                    self.dense_retriever.search(query, interpretation.filters, top_k=self.settings.dense_top_k)
                )
            if self.sparse_index is not None:
                sparse_lists.append(
                    self.sparse_index.search(query, interpretation.filters, top_k=self.settings.sparse_top_k)
                )

        if is_regionless_spatial_query(standalone_query):
            national_filters = {**interpretation.filters, "region": "nasional"}
            for query in interpretation.expanded_queries or [standalone_query]:
                if self.dense_retriever is not None:
                    dense_lists.append(
                        self.dense_retriever.search(query, national_filters, top_k=self.settings.dense_top_k)
                    )
                if self.sparse_index is not None:
                    sparse_lists.append(
                        self.sparse_index.search(query, national_filters, top_k=self.settings.sparse_top_k)
                    )

        fused = rrf_fusion(
            *dense_lists,
            *sparse_lists,
            k=self.settings.rrf_k,
            limit=max(self.settings.dense_top_k, self.settings.sparse_top_k),
        )
        try:
            reranked = self.reranker.rerank(
                standalone_query,
                fused,
                top_k=self.settings.rerank_top_k,
                filters=interpretation.filters,
            )
        except TypeError:
            reranked = self.reranker.rerank(standalone_query, fused, top_k=self.settings.rerank_top_k)
        confidence = reranked[0].score if reranked else 0.0
        should_answer = bool(reranked) and confidence >= self.settings.confidence_threshold
        message = None if should_answer else build_low_confidence_message(interpretation.filters)

        return RetrievalResult(
            question=question,
            standalone_query=standalone_query,
            expanded_queries=interpretation.expanded_queries,
            filters=interpretation.filters,
            candidates=reranked,
            should_answer=should_answer,
            confidence=float(confidence),
            message=message,
        )


def format_context(candidates: Sequence[CandidateChunk]) -> str:
    lines: list[str] = []
    for index, candidate in enumerate(candidates, start=1):
        source_name = candidate.metadata.get("source_name", "Sumber tidak diketahui")
        page_start = candidate.metadata.get("start_page") or candidate.metadata.get("page") or "?"
        page_end = candidate.metadata.get("end_page") or page_start
        page_text = f"hlm. {page_start}" if page_start == page_end else f"hlm. {page_start}-{page_end}"
        lines.append(f"[{index}] {candidate.content}\n(Sumber: {source_name}, {page_text})")
    return "\n\n".join(lines)
