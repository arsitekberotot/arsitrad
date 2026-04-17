import json
from pathlib import Path

import yaml

from pipeline.chunker import ChunkRecord
from pipeline.ingest import (
    EmbeddingCheckpoint,
    build_ingest_config,
    chunk_records_to_sparse_records,
    ingest_corpus,
    load_chunk_records_from_sparse,
    load_embedding_checkpoint,
    prepare_passage,
    prepare_query,
    rebuild_record_metadata,
    resolve_database_url,
    save_embedding_checkpoint,
    write_sparse_records,
)


def test_prepare_helpers_add_e5_prefixes():
    assert prepare_passage("aturan bangunan") == "passage: aturan bangunan"
    assert prepare_query("apa itu pbg") == "query: apa itu pbg"


def test_chunk_records_are_serialized_for_sparse_index(tmp_path: Path):
    chunks = [
        ChunkRecord(
            chunk_key="abc",
            content="Pasal 1 Bangunan Gedung wajib aman.",
            metadata={"source_name": "PP 16/2021", "region": "nasional"},
            start_page=1,
            end_page=1,
        )
    ]

    records = chunk_records_to_sparse_records(chunks)
    assert records[0]["chunk_key"] == "abc"
    assert records[0]["metadata"]["source_name"] == "PP 16/2021"

    output = tmp_path / "bm25.jsonl"
    written = write_sparse_records(output, records)
    assert written == 1
    assert output.exists()
    assert "Pasal 1" in output.read_text(encoding="utf-8")


def test_sparse_records_round_trip_into_chunk_records(tmp_path: Path):
    chunks = [
        ChunkRecord(
            chunk_key="abc",
            content="Pasal 1 Bangunan Gedung wajib aman.",
            metadata={
                "source_name": "PP 16/2021",
                "source_path": "./docs/pp16.pdf",
                "chunk_index": 0,
                "start_page": 1,
                "end_page": 1,
            },
            start_page=1,
            end_page=1,
        )
    ]
    output = tmp_path / "bm25.jsonl"
    write_sparse_records(output, chunk_records_to_sparse_records(chunks))

    loaded = load_chunk_records_from_sparse(output)

    assert loaded == chunks


def test_embedding_checkpoint_resets_when_source_changes(tmp_path: Path):
    checkpoint_path = tmp_path / "embedding_checkpoint.json"
    save_embedding_checkpoint(
        checkpoint_path,
        EmbeddingCheckpoint(source_path="/tmp/original.jsonl", next_index=12, total_records=20),
    )

    restored = load_embedding_checkpoint(
        checkpoint_path,
        expected_source_path="/tmp/other.jsonl",
        total_records=20,
    )

    assert restored.source_path == "/tmp/other.jsonl"
    assert restored.next_index == 0
    assert restored.total_records == 20


def test_resolve_database_url_prefers_environment(monkeypatch):
    config = {"v2": {"database": {"url_env": "ARSITRAD_DATABASE_URL", "default_url": "postgres://fallback"}}}
    monkeypatch.setenv("ARSITRAD_DATABASE_URL", "postgres://env-db")

    assert resolve_database_url(config) == "postgres://env-db"


def test_build_ingest_config_reads_v2_block():
    config = {
        "v2": {
            "embedding_model": "intfloat/multilingual-e5-large",
            "corpus": {
                "processed_root": "./data/processed/v2",
                "sparse_index_path": "./data/processed/v2/bm25.jsonl",
            },
            "database": {"table": "regulation_chunks", "default_url": "postgres://fallback"},
        }
    }

    ingest_config = build_ingest_config(config)
    assert ingest_config.embedding_model == "intfloat/multilingual-e5-large"
    assert ingest_config.processed_root == Path("./data/processed/v2")
    assert ingest_config.sparse_index_path == Path("./data/processed/v2/bm25.jsonl")
    assert ingest_config.embedding_checkpoint_path == Path("./data/processed/v2/embedding_checkpoint.json")
    assert ingest_config.database_table == "regulation_chunks"


def test_ingest_corpus_can_resume_from_existing_sparse_without_rechunking(tmp_path: Path, monkeypatch):
    processed_root = tmp_path / "processed"
    sparse_path = processed_root / "bm25.jsonl"
    chunk = ChunkRecord(
        chunk_key="abc",
        content="Pasal 1 Bangunan Gedung wajib aman.",
        metadata={
            "source_name": "PP 16/2021",
            "source_path": "/tmp/pp16.pdf",
            "reg_type": "PP",
            "region": "nasional",
            "typology": "building_permit",
            "year": 2021,
            "chunk_index": 0,
            "start_page": 1,
            "end_page": 1,
        },
        start_page=1,
        end_page=1,
    )
    write_sparse_records(sparse_path, chunk_records_to_sparse_records([chunk]))

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "v2": {
                    "corpus": {
                        "processed_root": str(processed_root),
                        "sparse_index_path": str(sparse_path),
                    },
                    "database": {
                        "table": "regulation_chunks",
                        "default_url": "postgres://fake-db",
                    },
                    "embedding_model": "intfloat/multilingual-e5-large",
                }
            }
        ),
        encoding="utf-8",
    )

    def fail_chunker(_config_path):
        raise AssertionError("chunker should not be loaded when resuming from sparse artifact")

    monkeypatch.setattr("pipeline.ingest.load_chunker_from_config", fail_chunker)

    class FakeEmbedder:
        def __init__(self, model_name: str):
            self.model_name = model_name

        def embed_passages(self, texts, batch_size: int = 16):
            return [[0.1, 0.2] for _ in texts]

    store_calls: list[tuple[str, int]] = []

    class FakeStore:
        def __init__(self, database_url: str, table_name: str):
            self.database_url = database_url
            self.table_name = table_name

        def ensure_schema(self):
            store_calls.append(("ensure_schema", 0))

        def upsert_chunks(self, chunks, embeddings):
            store_calls.append(("upsert_chunks", len(chunks)))
            assert len(chunks) == len(embeddings) == 1
            return len(chunks)

    monkeypatch.setattr("pipeline.ingest.E5Embedder", FakeEmbedder)
    monkeypatch.setattr("pipeline.ingest.PostgresChunkStore", FakeStore)

    report = ingest_corpus(
        config_path=config_path,
        with_embeddings=True,
        use_existing_sparse=True,
    )

    assert report.documents_seen == 1
    assert report.chunks_emitted == 1
    assert report.embeddings_written == 1
    assert report.sparse_records_written == 0
    assert report.used_existing_sparse is True
    assert store_calls == [("ensure_schema", 0), ("upsert_chunks", 1)]

    checkpoint = json.loads((processed_root / "embedding_checkpoint.json").read_text(encoding="utf-8"))
    assert checkpoint["next_index"] == 1
    assert checkpoint["total_records"] == 1
    assert checkpoint["source_path"] == str(sparse_path)


def test_rebuild_record_metadata_refreshes_weak_region_and_adds_taxonomy():
    record = {
        "chunk_key": "bandung-001",
        "content": "Peraturan ini mengatur bangunan gedung dan KDB di Kota Bandung.",
        "metadata": {
            "source_name": "PERDA No.05 Thn.2010",
            "source_path": "/data/corpus/local_regulations/jawa/jawa_barat/bandung/PERDA No.05 Thn.2010.pdf",
            "region": "Thn",
            "reg_type": "Unknown",
            "chunk_index": 7,
        },
        "start_page": 3,
        "end_page": 4,
    }

    rebuilt = rebuild_record_metadata(record)

    assert rebuilt["region"] == "Bandung"
    assert rebuilt["reg_type"] == "Perda"
    assert rebuilt["chunk_index"] == 7
    assert rebuilt["start_page"] == 3
    assert rebuilt["end_page"] == 4
    assert rebuilt["topic"] == "building_permit"


def test_rebuild_record_metadata_drops_stale_building_use_when_current_heuristics_do_not_support_it():
    record = {
        "chunk_key": "permen-6-stale",
        "content": "Kebutuhan kegiatan usaha telah dipertimbangkan dalam verifikasi penyelenggaraan SPAM.",
        "metadata": {
            "source_name": "Permen_6_2025_StandarKegiatan",
            "source_path": "/data/corpus/indonesian-construction-law/permen/Permen_6_2025_StandarKegiatan.pdf",
            "reg_type": "Permen",
            "region": "nasional",
            "topic": "building_permit",
            "building_use": "commercial",
            "chunk_index": 35,
        },
        "start_page": 15,
        "end_page": 393,
    }

    rebuilt = rebuild_record_metadata(record)

    assert rebuilt.get("topic") is None
    assert rebuilt.get("building_use") is None


def test_rebuild_record_metadata_recomputes_precise_commercial_building_use_from_content():
    record = {
        "chunk_key": "pp16-fungsi-usaha",
        "content": "Bangunan Gedung fungsi usaha mempunyai fungsi utama sebagai tempat melakukan kegiatan usaha.",
        "metadata": {
            "source_name": "PP_16_2021_BGPelaksanaanBG_BatangTubuh",
            "source_path": "/data/corpus/indonesian-construction-law/pp/PP_16_2021_BGPelaksanaanBG_BatangTubuh.pdf",
            "reg_type": "PP",
            "region": "nasional",
            "topic": "building_permit",
            "chunk_index": 5,
        },
        "start_page": 5,
        "end_page": 5,
    }

    rebuilt = rebuild_record_metadata(record)

    assert rebuilt["building_use"] == "commercial"


def test_ingest_corpus_can_refresh_sparse_metadata_and_backfill_existing_db_rows(tmp_path: Path, monkeypatch):
    processed_root = tmp_path / "processed"
    sparse_path = processed_root / "bm25.jsonl"
    chunk = ChunkRecord(
        chunk_key="abc",
        content="KDB bangunan gedung di Kota Bandung diatur dalam perda ini.",
        metadata={
            "source_name": "PERDA No.05 Thn.2010",
            "source_path": "/data/corpus/local_regulations/jawa/jawa_barat/bandung/PERDA No.05 Thn.2010.pdf",
            "reg_type": "Unknown",
            "region": "Thn",
            "typology": "general_regulation",
            "year": 2010,
            "chunk_index": 0,
            "start_page": 1,
            "end_page": 1,
        },
        start_page=1,
        end_page=1,
    )
    write_sparse_records(sparse_path, chunk_records_to_sparse_records([chunk]))

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "v2": {
                    "corpus": {
                        "processed_root": str(processed_root),
                        "sparse_index_path": str(sparse_path),
                    },
                    "database": {
                        "table": "regulation_chunks",
                        "default_url": "postgres://fake-db",
                    },
                    "embedding_model": "intfloat/multilingual-e5-large",
                }
            }
        ),
        encoding="utf-8",
    )

    class FakeStore:
        def __init__(self, database_url: str, table_name: str):
            self.database_url = database_url
            self.table_name = table_name

        def ensure_schema(self):
            pass

        def upsert_metadata_only(self, chunks):
            assert chunks[0].metadata["region"] == "Bandung"
            assert chunks[0].metadata["reg_type"] == "Perda"
            assert chunks[0].metadata["topic"] == "building_permit"
            return len(chunks)

    monkeypatch.setattr("pipeline.ingest.PostgresChunkStore", FakeStore)

    report = ingest_corpus(
        config_path=config_path,
        use_existing_sparse=True,
        rewrite_sparse=True,
        metadata_only=True,
    )

    assert report.metadata_rows_written == 1
    refreshed = load_chunk_records_from_sparse(sparse_path)
    assert refreshed[0].metadata["region"] == "Bandung"
    assert refreshed[0].metadata["reg_type"] == "Perda"
    assert refreshed[0].metadata["topic"] == "building_permit"
