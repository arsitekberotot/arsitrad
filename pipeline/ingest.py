from __future__ import annotations

"""Ingestion pipeline for Arsitrad v2.

Reparses the raw PDF corpus, emits semantic legal chunks, optionally embeds them
with multilingual E5, persists them into pgvector, and always writes a JSONL
artifact for BM25 / offline inspection.

The embedding stage supports resumable batch upserts from an existing sparse
JSONL artifact so large CPU-only ingests do not have to repeat chunking after an
interrupted run.
"""

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import yaml

from pipeline.chunker import ChunkRecord, collect_pdf_paths, infer_metadata, load_chunker_from_config
from pipeline.taxonomy import enrich_metadata, normalize_lookup_text, source_name_matches


@dataclass(slots=True)
class IngestConfig:
    embedding_model: str
    processed_root: Path
    sparse_index_path: Path
    embedding_checkpoint_path: Path
    database_url: str | None
    database_table: str = "regulation_chunks"
    batch_size: int = 16
    persist_batch_size: int = 64


@dataclass(slots=True)
class IngestionReport:
    documents_seen: int
    chunks_emitted: int
    embeddings_written: int
    metadata_rows_written: int = 0
    sparse_records_written: int = 0
    dry_run: bool = False
    used_existing_sparse: bool = False
    checkpoint_path: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "documents_seen": self.documents_seen,
            "chunks_emitted": self.chunks_emitted,
            "embeddings_written": self.embeddings_written,
            "metadata_rows_written": self.metadata_rows_written,
            "sparse_records_written": self.sparse_records_written,
            "dry_run": self.dry_run,
            "used_existing_sparse": self.used_existing_sparse,
            "checkpoint_path": self.checkpoint_path,
        }


@dataclass(slots=True)
class EmbeddingCheckpoint:
    source_path: str
    next_index: int
    total_records: int


def load_config(config_path: str | Path = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def resolve_database_url(config: dict) -> str | None:
    v2_db = config.get("v2", {}).get("database", {})
    env_name = v2_db.get("url_env", "ARSITRAD_DATABASE_URL")
    return os.environ.get(env_name) or v2_db.get("default_url") or None


def build_ingest_config(config: dict) -> IngestConfig:
    v2 = config.get("v2", {})
    corpus = v2.get("corpus", {})
    db = v2.get("database", {})
    processed_root = Path(corpus.get("processed_root", "./data/processed/v2"))
    return IngestConfig(
        embedding_model=v2.get("embedding_model", "intfloat/multilingual-e5-large"),
        processed_root=processed_root,
        sparse_index_path=Path(corpus.get("sparse_index_path", "./data/processed/v2/bm25_corpus.jsonl")),
        embedding_checkpoint_path=processed_root / "embedding_checkpoint.json",
        database_url=resolve_database_url(config),
        database_table=db.get("table", "regulation_chunks"),
    )


def prepare_passage(text: str) -> str:
    return f"passage: {text.strip()}"


def prepare_query(text: str) -> str:
    return f"query: {text.strip()}"


class E5Embedder:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_passages(self, texts: Sequence[str], batch_size: int = 16) -> list[list[float]]:
        prefixed = [prepare_passage(text) for text in texts]
        embeddings = self.model.encode(
            prefixed,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        embedding = self.model.encode(
            [prepare_query(text)],
            batch_size=1,
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]
        return embedding.tolist()


def chunk_records_to_sparse_records(chunks: Sequence[ChunkRecord]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for chunk in chunks:
        record = {
            "chunk_key": chunk.chunk_key,
            "content": chunk.content,
            "metadata": chunk.metadata,
            "start_page": chunk.start_page,
            "end_page": chunk.end_page,
        }
        records.append(record)
    return records


def write_sparse_records(path: str | Path, records: Sequence[dict[str, object]]) -> int:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return len(records)


PLACEHOLDER_REGION_VALUES = {"daerah", "bg", "thn", "perubahan"}
RETAG_CLEAR_SOURCE_TERMS = ("standarkegiatan",)
RETAG_CLEAR_CONTENT_TERMS = ("penyelenggaraan spam", "sistem oss", "perizinan berusaha", "pbbr")


def metadata_value_is_weak(key: str, value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return True
        if key == "reg_type" and normalized == "Unknown":
            return True
        if key == "region" and normalized.lower() in PLACEHOLDER_REGION_VALUES:
            return True
    return False


def should_clear_stale_taxonomy(existing: dict[str, object], content: str) -> bool:
    source_name = str(existing.get("source_name") or "")
    normalized_content = normalize_lookup_text(content)
    return source_name_matches(source_name, *RETAG_CLEAR_SOURCE_TERMS) or any(
        term in normalized_content for term in RETAG_CLEAR_CONTENT_TERMS
    )


def rebuild_record_metadata(record: dict[str, object]) -> dict[str, object]:
    existing = dict(record.get("metadata") or {})
    source_path = str(existing.get("source_path") or "")
    if not source_path:
        raise ValueError(f"sparse record missing source_path: {record.get('chunk_key')}")

    fresh = infer_metadata(source_path)
    merged = dict(existing)
    for key, value in fresh.items():
        if not metadata_value_is_weak(key, value):
            merged[key] = value
        else:
            merged.setdefault(key, value)

    content = str(record.get("content") or "")
    if should_clear_stale_taxonomy(existing, content):
        for key in ("topic", "building_use", "typology"):
            merged.pop(key, None)

    start_page = int(record.get("start_page") or existing.get("start_page") or 0)
    end_page = int(record.get("end_page") or existing.get("end_page") or start_page)
    merged["chunk_index"] = int(existing.get("chunk_index") or 0)
    merged["start_page"] = start_page
    merged["end_page"] = end_page
    return enrich_metadata(merged, content=content)


def rewrite_sparse_metadata(path: str | Path) -> int:
    sparse_path = Path(path)
    records: list[dict[str, object]] = []
    with sparse_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            record["metadata"] = rebuild_record_metadata(record)
            records.append(record)
    return write_sparse_records(sparse_path, records)


def sparse_record_to_chunk(record: dict[str, object]) -> ChunkRecord:
    metadata = dict(record.get("metadata") or {})
    start_page = int(record.get("start_page") or metadata.get("start_page") or 0)
    end_page = int(record.get("end_page") or metadata.get("end_page") or start_page)
    return ChunkRecord(
        chunk_key=str(record["chunk_key"]),
        content=str(record["content"]),
        metadata=metadata,
        start_page=start_page,
        end_page=end_page,
    )


def load_chunk_records_from_sparse(path: str | Path) -> list[ChunkRecord]:
    sparse_path = Path(path)
    if not sparse_path.exists():
        raise FileNotFoundError(f"Sparse index not found: {sparse_path}")

    chunks: list[ChunkRecord] = []
    with sparse_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            chunks.append(sparse_record_to_chunk(json.loads(line)))
    return chunks


def infer_documents_seen(chunks: Sequence[ChunkRecord]) -> int:
    document_keys = {
        chunk.metadata.get("source_path") or chunk.metadata.get("source_name") or chunk.chunk_key
        for chunk in chunks
    }
    return len(document_keys)


def load_embedding_checkpoint(
    path: str | Path,
    expected_source_path: str | Path,
    total_records: int,
) -> EmbeddingCheckpoint:
    checkpoint_path = Path(path)
    expected_source = str(Path(expected_source_path))
    default = EmbeddingCheckpoint(
        source_path=expected_source,
        next_index=0,
        total_records=total_records,
    )
    if not checkpoint_path.exists():
        return default

    data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint = EmbeddingCheckpoint(
        source_path=str(data.get("source_path") or expected_source),
        next_index=int(data.get("next_index", 0)),
        total_records=int(data.get("total_records", total_records)),
    )

    if checkpoint.source_path != expected_source or checkpoint.total_records != total_records:
        return default

    checkpoint.next_index = max(0, min(checkpoint.next_index, total_records))
    return checkpoint


def save_embedding_checkpoint(path: str | Path, checkpoint: EmbeddingCheckpoint) -> None:
    checkpoint_path = Path(path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text(json.dumps(asdict(checkpoint), ensure_ascii=False, indent=2), encoding="utf-8")


class PostgresChunkStore:
    def __init__(self, database_url: str, table_name: str = "regulation_chunks"):
        self.database_url = database_url
        self.table_name = table_name

    def ensure_schema(self, schema_path: str | Path = "db/schema.sql") -> None:
        import psycopg

        ddl = Path(schema_path).read_text(encoding="utf-8")
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
            conn.commit()

    def upsert_chunks(self, chunks: Sequence[ChunkRecord], embeddings: Sequence[Sequence[float]]) -> int:
        import psycopg
        from pgvector.psycopg import register_vector

        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")

        sql = f"""
            INSERT INTO {self.table_name} (
                chunk_key,
                content,
                embedding,
                metadata,
                source_name,
                source_path,
                reg_type,
                region,
                typology,
                year,
                chunk_index,
                start_page,
                end_page
            )
            VALUES (
                %(chunk_key)s,
                %(content)s,
                %(embedding)s,
                %(metadata)s,
                %(source_name)s,
                %(source_path)s,
                %(reg_type)s,
                %(region)s,
                %(typology)s,
                %(year)s,
                %(chunk_index)s,
                %(start_page)s,
                %(end_page)s
            )
            ON CONFLICT (chunk_key) DO UPDATE SET
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                metadata = EXCLUDED.metadata,
                reg_type = EXCLUDED.reg_type,
                region = EXCLUDED.region,
                typology = EXCLUDED.typology,
                year = EXCLUDED.year,
                start_page = EXCLUDED.start_page,
                end_page = EXCLUDED.end_page,
                updated_at = NOW()
        """

        payloads = []
        for chunk, embedding in zip(chunks, embeddings):
            payloads.append(
                {
                    "chunk_key": chunk.chunk_key,
                    "content": chunk.content,
                    "embedding": embedding,
                    "metadata": json.dumps(chunk.metadata, ensure_ascii=False),
                    "source_name": chunk.metadata.get("source_name"),
                    "source_path": chunk.metadata.get("source_path"),
                    "reg_type": chunk.metadata.get("reg_type"),
                    "region": chunk.metadata.get("region"),
                    "typology": chunk.metadata.get("typology"),
                    "year": chunk.metadata.get("year"),
                    "chunk_index": chunk.metadata.get("chunk_index", 0),
                    "start_page": chunk.start_page,
                    "end_page": chunk.end_page,
                }
            )

        with psycopg.connect(self.database_url) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                cur.executemany(sql, payloads)
            conn.commit()
        return len(payloads)

    def upsert_metadata_only(self, chunks: Sequence[ChunkRecord]) -> int:
        import psycopg

        sql = f"""
            UPDATE {self.table_name}
            SET
                content = %(content)s,
                metadata = %(metadata)s,
                source_name = %(source_name)s,
                source_path = %(source_path)s,
                reg_type = %(reg_type)s,
                region = %(region)s,
                typology = %(typology)s,
                year = %(year)s,
                chunk_index = %(chunk_index)s,
                start_page = %(start_page)s,
                end_page = %(end_page)s,
                updated_at = NOW()
            WHERE chunk_key = %(chunk_key)s
        """
        payloads = []
        for chunk in chunks:
            payloads.append(
                {
                    "chunk_key": chunk.chunk_key,
                    "content": chunk.content,
                    "metadata": json.dumps(chunk.metadata, ensure_ascii=False),
                    "source_name": chunk.metadata.get("source_name"),
                    "source_path": chunk.metadata.get("source_path"),
                    "reg_type": chunk.metadata.get("reg_type"),
                    "region": chunk.metadata.get("region"),
                    "typology": chunk.metadata.get("typology"),
                    "year": chunk.metadata.get("year"),
                    "chunk_index": chunk.metadata.get("chunk_index", 0),
                    "start_page": chunk.start_page,
                    "end_page": chunk.end_page,
                }
            )

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, payloads)
                updated = cur.rowcount
            conn.commit()
        return updated


def ingest_corpus(
    config_path: str | Path = "config.yaml",
    limit_docs: int | None = None,
    dry_run: bool = False,
    with_embeddings: bool = False,
    specific_paths: Sequence[str] | None = None,
    use_existing_sparse: bool = False,
    checkpoint_path: str | Path | None = None,
    rewrite_sparse: bool = False,
    metadata_only: bool = False,
) -> IngestionReport:
    config = load_config(config_path)
    ingest_config = build_ingest_config(config)

    if use_existing_sparse and specific_paths:
        raise ValueError("specific_paths cannot be combined with use_existing_sparse")

    if checkpoint_path is None:
        checkpoint_path = ingest_config.embedding_checkpoint_path

    sparse_count = 0
    metadata_rows_written = 0
    if rewrite_sparse:
        sparse_count = rewrite_sparse_metadata(ingest_config.sparse_index_path)
        print(
            f"[metadata] rewrote metadata for {sparse_count} sparse record(s) in {ingest_config.sparse_index_path}",
            flush=True,
        )
    if use_existing_sparse:
        all_chunks = load_chunk_records_from_sparse(ingest_config.sparse_index_path)
        if limit_docs is not None:
            allowed_sources: list[str] = []
            seen_sources: set[str] = set()
            for chunk in all_chunks:
                source = str(chunk.metadata.get("source_path") or chunk.metadata.get("source_name") or "")
                if source and source not in seen_sources:
                    seen_sources.add(source)
                    allowed_sources.append(source)
                if len(allowed_sources) >= limit_docs:
                    break
            allowed_source_set = set(allowed_sources)
            all_chunks = [
                chunk for chunk in all_chunks
                if str(chunk.metadata.get("source_path") or chunk.metadata.get("source_name") or "") in allowed_source_set
            ]
        documents_seen = infer_documents_seen(all_chunks)
        print(
            f"[ingest] loaded {len(all_chunks)} chunk(s) from existing sparse artifact {ingest_config.sparse_index_path}",
            flush=True,
        )
    else:
        chunker = load_chunker_from_config(config_path)
        v2_corpus = config.get("v2", {}).get("corpus", {})
        corpus_paths = specific_paths or collect_pdf_paths(
            v2_corpus.get("national_root"),
            v2_corpus.get("local_root"),
        )
        if limit_docs is not None:
            corpus_paths = list(corpus_paths)[:limit_docs]

        all_chunks: list[ChunkRecord] = []
        for pdf_path in corpus_paths:
            all_chunks.extend(chunker.chunk_pdf(pdf_path))

        sparse_records = chunk_records_to_sparse_records(all_chunks)
        sparse_count = write_sparse_records(ingest_config.sparse_index_path, sparse_records)
        documents_seen = len(corpus_paths)
        print(
            f"[ingest] chunked {documents_seen} document(s) into {len(all_chunks)} chunk(s); wrote {sparse_count} sparse record(s)",
            flush=True,
        )

    if metadata_only and not dry_run and ingest_config.database_url and all_chunks:
        store = PostgresChunkStore(ingest_config.database_url, ingest_config.database_table)
        store.ensure_schema()
        metadata_rows_written = store.upsert_metadata_only(all_chunks)
        print(f"[metadata] updated {metadata_rows_written} existing DB row(s)", flush=True)

    embedding_count = 0
    if with_embeddings and all_chunks:
        checkpoint = load_embedding_checkpoint(
            checkpoint_path,
            expected_source_path=ingest_config.sparse_index_path,
            total_records=len(all_chunks),
        )
        if checkpoint.next_index >= len(all_chunks):
            print(
                f"[embed] checkpoint already complete at {checkpoint.next_index}/{len(all_chunks)} chunk(s)",
                flush=True,
            )
        else:
            embedder = E5Embedder(ingest_config.embedding_model)
            store = None
            if not dry_run and ingest_config.database_url:
                store = PostgresChunkStore(ingest_config.database_url, ingest_config.database_table)
                store.ensure_schema()

            start_index = checkpoint.next_index
            for batch_start in range(start_index, len(all_chunks), ingest_config.persist_batch_size):
                batch_end = min(batch_start + ingest_config.persist_batch_size, len(all_chunks))
                batch_chunks = all_chunks[batch_start:batch_end]
                embeddings = embedder.embed_passages(
                    [chunk.content for chunk in batch_chunks],
                    batch_size=ingest_config.batch_size,
                )
                if store is not None:
                    store.upsert_chunks(batch_chunks, embeddings)

                embedding_count += len(batch_chunks)
                checkpoint.next_index = batch_end
                checkpoint.total_records = len(all_chunks)
                checkpoint.source_path = str(Path(ingest_config.sparse_index_path))
                save_embedding_checkpoint(checkpoint_path, checkpoint)
                print(
                    f"[embed] persisted {batch_end}/{len(all_chunks)} chunk(s) ({batch_end / len(all_chunks) * 100:.1f}%)",
                    flush=True,
                )

    return IngestionReport(
        documents_seen=documents_seen,
        chunks_emitted=len(all_chunks),
        embeddings_written=embedding_count if with_embeddings and not dry_run else 0,
        metadata_rows_written=metadata_rows_written,
        sparse_records_written=sparse_count,
        dry_run=dry_run,
        used_existing_sparse=use_existing_sparse,
        checkpoint_path=str(Path(checkpoint_path)),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Arsitrad v2 corpus into sparse index and pgvector")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--limit-docs", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--with-embeddings", action="store_true", help="Embed chunks with E5")
    parser.add_argument("--pdf", action="append", help="Specific PDF path(s) to ingest")
    parser.add_argument(
        "--from-sparse",
        action="store_true",
        help="Reuse the existing sparse JSONL artifact instead of re-chunking PDFs",
    )
    parser.add_argument(
        "--checkpoint-path",
        help="Optional checkpoint path for resumable embedding progress",
    )
    parser.add_argument(
        "--rewrite-sparse-metadata",
        action="store_true",
        help="Recompute metadata in the existing sparse JSONL artifact using current heuristics",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Update DB metadata/content from the sparse artifact without recomputing embeddings",
    )
    args = parser.parse_args()

    report = ingest_corpus(
        config_path=args.config,
        limit_docs=args.limit_docs,
        dry_run=args.dry_run,
        with_embeddings=args.with_embeddings,
        specific_paths=args.pdf,
        use_existing_sparse=args.from_sparse,
        checkpoint_path=args.checkpoint_path,
        rewrite_sparse=args.rewrite_sparse_metadata,
        metadata_only=args.metadata_only,
    )
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
