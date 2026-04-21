import sys
import types

from pgvector import Vector

from pipeline.retriever import (
    CandidateChunk,
    HybridRetriever,
    PostgresDenseRetriever,
    authority_score_adjustment,
    dedupe_candidates,
    matches_filters,
    rebalance_contrastive_candidates,
    rrf_fusion,
)


class FakeSearchBackend:
    def __init__(self, results):
        self.results = results

    def search(self, query, filters, top_k=20):
        return list(self.results)[:top_k]


class RecordingSearchBackend(FakeSearchBackend):
    def __init__(self, results):
        super().__init__(results)
        self.calls = []

    def search(self, query, filters, top_k=20):
        self.calls.append({"query": query, "filters": dict(filters), "top_k": top_k})
        return super().search(query, filters, top_k=top_k)


class FakeReranker:
    def __init__(self, score):
        self.score = score

    def rerank(self, query, candidates, top_k=5):
        if not candidates:
            return []
        return [
            CandidateChunk(
                chunk_key=candidates[0].chunk_key,
                content=candidates[0].content,
                metadata=candidates[0].metadata,
                score=self.score,
                source="reranked",
            )
        ]


def test_rrf_fusion_rewards_shared_candidates():
    dense = [
        CandidateChunk("a", "chunk a", {"source_name": "A"}, 0.9, "dense"),
        CandidateChunk("b", "chunk b", {"source_name": "B"}, 0.8, "dense"),
    ]
    sparse = [
        CandidateChunk("b", "chunk b", {"source_name": "B"}, 7.0, "sparse"),
        CandidateChunk("c", "chunk c", {"source_name": "C"}, 6.0, "sparse"),
    ]

    fused = rrf_fusion(dense, sparse, k=60)

    assert fused[0].chunk_key == "b"


def test_dedupe_candidates_collapses_repeated_snippets():
    repeated = "Persetujuan Bangunan Gedung yang selanjutnya disingkat PBG adalah perizinan ..."
    candidates = [
        CandidateChunk("a", repeated, {"source_name": "PP_16_2021_A"}, 0.92, "reranked"),
        CandidateChunk("b", repeated, {"source_name": "PP_16_2021_B"}, 0.88, "reranked"),
        CandidateChunk(
            "c",
            "Izin Mendirikan Bangunan yang selanjutnya disingkat IMB adalah izin daerah ...",
            {"source_name": "Perda Kota X"},
            0.80,
            "reranked",
        ),
    ]

    deduped = dedupe_candidates(candidates)

    assert [candidate.chunk_key for candidate in deduped] == ["a", "c"]


def test_rebalance_contrastive_candidates_keeps_imb_and_pbg_definitions():
    candidates = [
        CandidateChunk(
            "imb-1",
            "Izin Mendirikan Bangunan Gedung yang selanjutnya disingkat IMB adalah izin daerah untuk membangun baru.",
            {"source_name": "Perda A"},
            0.95,
            "reranked",
        ),
        CandidateChunk(
            "imb-2",
            "Izin Mendirikan Bangunan Gedung yang selanjutnya disingkat IMB adalah izin daerah untuk mengubah bangunan.",
            {"source_name": "Perda B"},
            0.90,
            "reranked",
        ),
        CandidateChunk(
            "pbg-def",
            "Persetujuan Bangunan Gedung yang selanjutnya disingkat PBG adalah perizinan yang diberikan kepada pemilik bangunan gedung.",
            {"source_name": "PP 16/2021"},
            0.62,
            "reranked",
        ),
    ]

    balanced = rebalance_contrastive_candidates("Apa beda IMB dan PBG menurut aturan terbaru?", candidates, limit=3)

    assert any(candidate.chunk_key == "imb-1" for candidate in balanced)
    assert any(candidate.chunk_key == "pbg-def" for candidate in balanced)


def test_rebalance_contrastive_candidates_falls_back_to_pbg_context_when_definition_missing():
    candidates = [
        CandidateChunk(
            "imb-1",
            "Izin Mendirikan Bangunan Gedung yang selanjutnya disingkat IMB adalah izin daerah untuk membangun baru.",
            {"source_name": "Perda A"},
            0.95,
            "reranked",
        ),
        CandidateChunk(
            "imb-2",
            "Izin Mendirikan Bangunan Gedung yang selanjutnya disingkat IMB adalah izin daerah untuk mengubah bangunan.",
            {"source_name": "Perda B"},
            0.90,
            "reranked",
        ),
        CandidateChunk(
            "pbg-procedure",
            "Permohonan PBG dilakukan melalui SIMBG dan dilengkapi dokumen administratif serta teknis.",
            {"source_name": "PP_16_2021_BatangTubuh"},
            0.55,
            "reranked",
        ),
    ]

    balanced = rebalance_contrastive_candidates("Apa beda IMB dan PBG menurut aturan terbaru?", candidates, limit=2)

    assert [candidate.chunk_key for candidate in balanced] == ["imb-1", "pbg-procedure"]


def test_matches_filters_supports_topic_and_building_use():
    assert matches_filters(
        {"topic": "accessibility", "reg_type": "Permen"},
        {"topic": "accessibility", "building_use": "public", "reg_type": "Permen"},
    ) is True
    assert matches_filters(
        {"topic": "fire_safety", "reg_type": "Permen"},
        {"topic": "accessibility", "reg_type": "Permen"},
    ) is False
    assert matches_filters(
        {"region": "nasional", "topic": "fire_safety"},
        {"region": "Balikpapan", "topic": "fire_safety"},
    ) is True


def test_hybrid_retriever_respects_confidence_gate():
    candidate = CandidateChunk(
        chunk_key="pp16-pasal-1",
        content="Pasal 1 Bangunan Gedung wajib memenuhi persyaratan administratif.",
        metadata={"source_name": "PP 16/2021", "region": "nasional"},
        score=0.9,
        source="dense",
    )
    retriever = HybridRetriever(
        config_path="",
        dense_retriever=FakeSearchBackend([candidate]),
        sparse_index=FakeSearchBackend([]),
        reranker=FakeReranker(0.3),
        config_overrides={
            "dense_top_k": 5,
            "sparse_top_k": 5,
            "rerank_top_k": 1,
            "confidence_threshold": 0.6,
        },
    )

    result = retriever.retrieve("Apa syarat PBG untuk rumah tinggal?")

    assert result.should_answer is False
    assert result.confidence == 0.3
    assert "tidak dapat menemukan regulasi" in result.message.lower()


def test_authority_score_adjustment_penalizes_rpjmd_for_permit_queries():
    rpjmd = CandidateChunk(
        chunk_key="rpjmd",
        content="Rencana Pembangunan Jangka Menengah Daerah Kota Semarang.",
        metadata={"source_name": "Peraturan Daerah Kota Semarang tentang RPJMD", "region": "Semarang", "topic": None},
        score=0.5,
        source="reranked",
    )
    rdtr = CandidateChunk(
        chunk_key="rdtr",
        content="Rencana Detail Tata Ruang wilayah Semarang.",
        metadata={"source_name": "Perda Kota Semarang RDTR", "region": "Semarang", "topic": "spatial_planning"},
        score=0.5,
        source="reranked",
    )

    permit_query = "Berapa KDB maksimal untuk bangunan komersial di Semarang?"
    filters = {"region": "Semarang", "topic": "building_permit", "building_use": "commercial"}

    assert authority_score_adjustment(permit_query, filters, rdtr) > authority_score_adjustment(permit_query, filters, rpjmd)


def test_authority_score_adjustment_penalizes_missing_building_use_against_specific_query():
    missing = CandidateChunk(
        chunk_key="missing",
        content="Dokumen teknis bangunan gedung diatur dalam perda daerah.",
        metadata={"source_name": "Perda Kota Tarakan Bangunan Gedung", "region": "Tarakan", "topic": "building_permit"},
        score=0.5,
        source="reranked",
    )
    matched = CandidateChunk(
        chunk_key="matched",
        content="Dokumen teknis bangunan komersial bertingkat wajib memenuhi syarat administratif dan teknis.",
        metadata={
            "source_name": "PP_16_2021_BatangTubuh",
            "region": "nasional",
            "topic": "building_permit",
            "building_use": "commercial",
            "reg_type": "PP",
        },
        score=0.5,
        source="reranked",
    )

    query = "Apa kewajiban dokumen teknis untuk gedung komersial bertingkat?"
    filters = {"topic": "building_permit", "building_use": "commercial"}

    assert authority_score_adjustment(query, filters, matched) > authority_score_adjustment(query, filters, missing)


def test_authority_score_adjustment_prefers_pp16_over_jasa_konstruksi_for_pbg_query():
    jasa = CandidateChunk(
        chunk_key="jasa",
        content="Undang-undang jasa konstruksi.",
        metadata={"source_name": "UU_2_2017_JasaKonstruksi", "region": "nasional", "topic": "building_permit", "reg_type": "UU"},
        score=0.5,
        source="reranked",
    )
    pp16 = CandidateChunk(
        chunk_key="pp16",
        content="PP 16 Tahun 2021 mengatur PBG dan SLF.",
        metadata={"source_name": "PP_16_2021_BatangTubuh", "region": "nasional", "topic": "building_permit", "reg_type": "PP"},
        score=0.5,
        source="reranked",
    )

    query = "Apa beda IMB dan PBG menurut aturan terbaru?"
    filters = {"topic": "building_permit", "region": "nasional"}

    assert authority_score_adjustment(query, filters, pp16) > authority_score_adjustment(query, filters, jasa)


def test_authority_score_adjustment_prefers_province_level_spatial_doc_for_regionless_query():
    province = CandidateChunk(
        chunk_key="province",
        content="Peraturan daerah provinsi tentang rencana tata ruang wilayah.",
        metadata={"source_name": "Peraturan Daerah Provinsi Jawa Tengah tentang RTRW", "region": "Jawa Tengah", "topic": "spatial_planning", "reg_type": "Perda"},
        score=0.5,
        source="reranked",
    )
    city = CandidateChunk(
        chunk_key="city",
        content="Peraturan daerah kota tentang RDTR.",
        metadata={"source_name": "Perda Kota Metro tentang RTRW", "region": "Metro", "topic": "spatial_planning", "reg_type": "Perda"},
        score=0.5,
        source="reranked",
    )

    query = "Apa yang harus dicek untuk bangunan di dekat sungai menurut tata ruang?"
    filters = {"topic": "spatial_planning"}

    assert authority_score_adjustment(query, filters, province) > authority_score_adjustment(query, filters, city)


def test_authority_score_adjustment_prefers_pp21_over_cipta_kerja_for_regionless_spatial_query():
    pp21 = CandidateChunk(
        chunk_key="pp21",
        content="PP 21 Tahun 2021 mengatur penyelenggaraan penataan ruang dan hirarki RTRW/RDTR.",
        metadata={"source_name": "PP_21_2021_PenataanRuang", "region": "nasional", "topic": "spatial_planning", "reg_type": "PP"},
        score=0.5,
        source="reranked",
    )
    cipta = CandidateChunk(
        chunk_key="cipta",
        content="UU Cipta Kerja memuat ketentuan umum terkait penataan ruang.",
        metadata={"source_name": "UU_6_2023_CiptaKerja", "region": "nasional", "topic": "spatial_planning", "reg_type": "UU"},
        score=0.5,
        source="reranked",
    )

    query = "Apakah RDTR wajib dicek sebelum mengurus PBG?"
    filters = {"topic": "spatial_planning"}

    assert authority_score_adjustment(query, filters, pp21) > authority_score_adjustment(query, filters, cipta)


def test_authority_score_adjustment_prefers_pp16_over_permen6_for_document_requirements_query():
    pp16 = CandidateChunk(
        chunk_key="pp16-docs",
        content="Dokumen rencana teknis diajukan untuk memperoleh PBG sebelum pelaksanaan konstruksi.",
        metadata={"source_name": "PP_16_2021_BGPelaksanaanBG_BatangTubuh", "region": "nasional", "topic": "building_permit", "reg_type": "PP"},
        score=0.5,
        source="reranked",
    )
    permen6 = CandidateChunk(
        chunk_key="permen6-docs",
        content="Kebutuhan kegiatan usaha telah dipertimbangkan dalam verifikasi penyelenggaraan SPAM dan persyaratan teknis.",
        metadata={
            "source_name": "Permen_6_2025_StandarKegiatan",
            "region": "nasional",
            "reg_type": "Permen",
            "topic": "building_permit",
            "building_use": "commercial",
        },
        score=0.5,
        source="reranked",
    )

    query = "Apa kewajiban dokumen teknis untuk gedung komersial bertingkat?"
    filters = {"topic": "building_permit", "building_use": "commercial", "region": "nasional"}

    assert authority_score_adjustment(query, filters, pp16) > authority_score_adjustment(query, filters, permen6)


def test_authority_score_adjustment_boosts_definition_chunks_for_imb_pbg_comparison():
    imb_definition = CandidateChunk(
        chunk_key="imb-def",
        content="Izin Mendirikan Bangunan Gedung yang selanjutnya disingkat IMB adalah perizinan yang diberikan oleh Pemerintah Daerah kepada pemilik bangunan gedung.",
        metadata={"source_name": "Perda Kota Example", "region": "Example", "topic": "building_permit", "reg_type": "Perda"},
        score=0.5,
        source="reranked",
    )
    pbg_procedure = CandidateChunk(
        chunk_key="pbg-procedure",
        content="Permohonan PBG dilakukan melalui SIMBG dan dilengkapi dokumen administratif serta teknis.",
        metadata={"source_name": "PP_16_2021_BatangTubuh", "region": "nasional", "topic": "building_permit", "reg_type": "PP"},
        score=0.5,
        source="reranked",
    )

    query = "Apa beda IMB dan PBG menurut aturan terbaru?"
    filters = {"topic": "building_permit"}

    assert authority_score_adjustment(query, filters, imb_definition) > authority_score_adjustment(query, filters, pbg_procedure)


def test_authority_score_adjustment_boosts_transition_chunks_for_imb_pbg_comparison():
    transition = CandidateChunk(
        chunk_key="transition",
        content="Bangunan Gedung yang telah memperoleh perizinan yang dikeluarkan oleh Pemerintah Daerah kabupaten/kota sebelum berlakunya Peraturan Pemerintah ini izinnya dinyatakan masih tetap berlaku.",
        metadata={"source_name": "PP_16_2021_BGPelaksanaanBG_BatangTubuh", "region": "nasional", "topic": "building_permit", "reg_type": "PP"},
        score=0.5,
        source="reranked",
    )
    pbg_procedure = CandidateChunk(
        chunk_key="pbg-procedure",
        content="Permohonan PBG dilakukan melalui SIMBG dan dilengkapi dokumen administratif serta teknis.",
        metadata={"source_name": "PP_16_2021_BatangTubuh", "region": "nasional", "topic": "building_permit", "reg_type": "PP"},
        score=0.5,
        source="reranked",
    )

    query = "Apa beda IMB dan PBG menurut aturan terbaru?"
    filters = {"topic": "building_permit"}

    assert authority_score_adjustment(query, filters, transition) > authority_score_adjustment(query, filters, pbg_procedure)


def test_hybrid_retriever_short_circuits_out_of_scope_design_question():
    retriever = HybridRetriever(
        config_path="",
        dense_retriever=FakeSearchBackend([]),
        sparse_index=FakeSearchBackend([]),
        reranker=FakeReranker(0.9),
    )

    result = retriever.retrieve("Apa regulasi yang relevan untuk desain rumah minimalis Jepang skandinavia?")

    assert result.should_answer is False
    assert result.confidence == 0.0
    assert result.candidates == []
    assert "gaya atau konsep desain" in result.message.lower()


def test_hybrid_retriever_runs_national_supplement_for_regionless_spatial_query():
    candidate = CandidateChunk(
        chunk_key="pp21",
        content="PP 21 Tahun 2021 mengatur penyelenggaraan penataan ruang.",
        metadata={"source_name": "PP_21_2021_PenataanRuang", "region": "nasional", "topic": "spatial_planning", "reg_type": "PP"},
        score=0.9,
        source="dense",
    )
    dense = RecordingSearchBackend([candidate])
    sparse = RecordingSearchBackend([candidate])
    retriever = HybridRetriever(
        config_path="",
        dense_retriever=dense,
        sparse_index=sparse,
        reranker=FakeReranker(0.9),
        config_overrides={"dense_top_k": 3, "sparse_top_k": 3, "rerank_top_k": 1},
    )

    retriever.retrieve("Apakah RDTR wajib dicek sebelum mengurus PBG?")

    dense_regions = [call["filters"].get("region") for call in dense.calls]
    sparse_regions = [call["filters"].get("region") for call in sparse.calls]

    assert None in dense_regions
    assert "nasional" in dense_regions
    assert None in sparse_regions
    assert "nasional" in sparse_regions


def test_hybrid_retriever_runs_national_supplement_for_imb_pbg_comparison():
    candidate = CandidateChunk(
        chunk_key="pp16",
        content="PP 16 Tahun 2021 mengatur PBG dan standar teknis bangunan gedung.",
        metadata={"source_name": "PP_16_2021_BatangTubuh", "region": "nasional", "topic": "building_permit", "reg_type": "PP"},
        score=0.9,
        source="dense",
    )
    dense = RecordingSearchBackend([candidate])
    sparse = RecordingSearchBackend([candidate])
    retriever = HybridRetriever(
        config_path="",
        dense_retriever=dense,
        sparse_index=sparse,
        reranker=FakeReranker(0.9),
        config_overrides={"dense_top_k": 3, "sparse_top_k": 3, "rerank_top_k": 1},
    )

    retriever.retrieve("Apa beda IMB dan PBG menurut aturan terbaru?")

    dense_regions = [call["filters"].get("region") for call in dense.calls]
    sparse_regions = [call["filters"].get("region") for call in sparse.calls]

    assert None in dense_regions
    assert "nasional" in dense_regions
    assert None in sparse_regions
    assert "nasional" in sparse_regions


def test_postgres_dense_retriever_wraps_query_embedding_as_pgvector(monkeypatch):
    captured: dict[str, object] = {}

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params):
            captured["sql"] = sql
            captured["params"] = params

        def fetchall(self):
            return []

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return FakeCursor()

    fake_psycopg = types.SimpleNamespace(connect=lambda *args, **kwargs: FakeConnection())
    fake_rows = types.SimpleNamespace(dict_row=object())
    fake_pgvector_psycopg = types.SimpleNamespace(register_vector=lambda conn: None)

    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)
    monkeypatch.setitem(sys.modules, "psycopg.rows", fake_rows)
    monkeypatch.setitem(sys.modules, "pgvector.psycopg", fake_pgvector_psycopg)

    retriever = PostgresDenseRetriever(database_url="postgresql:///example")
    monkeypatch.setattr(retriever.embedder, "embed_query", lambda query: [0.1, 0.2, 0.3])

    retriever.search("apa itu pbg", {}, top_k=1)

    assert isinstance(captured["params"]["embedding"], Vector)
