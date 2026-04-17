from pipeline.chunker import ExtractedPage, LegalChunker, infer_metadata


def test_table_to_markdown_formats_detected_table():
    chunker = LegalChunker()
    markdown = chunker.table_to_markdown(
        [
            ["Zona", "KDB", "KDH"],
            ["Komersial", "70%", "20%"],
            ["Hunian", "60%", "30%"],
        ]
    )

    assert "| Zona | KDB | KDH |" in markdown
    assert "Komersial" in markdown
    assert "Tabel dengan" in markdown


def test_chunk_text_splits_by_pasal_and_carries_context():
    chunker = LegalChunker()
    metadata = infer_metadata("/tmp/PP_16_2021_BatangTubuh.pdf")
    text = """
<<PAGE:1>>
BAB I
KETENTUAN UMUM
Pasal 1
Dalam Peraturan Pemerintah ini yang dimaksud dengan:
(1) Bangunan Gedung adalah hasil pekerjaan konstruksi.
Pasal 2
Bangunan Gedung harus memenuhi persyaratan administratif.
""".strip()

    chunks = chunker.chunk_text(text, metadata)

    assert len(chunks) == 2
    assert "BAB I" in chunks[0].content
    assert "Pasal 1" in chunks[0].content
    assert "Pasal 2" in chunks[1].content
    assert chunks[0].metadata["reg_type"] == "PP"


def test_pages_to_text_includes_tables_after_page_text():
    chunker = LegalChunker()
    pages = [
        ExtractedPage(
            page_number=3,
            text="Pasal 10\nKetentuan zonasi berlaku.",
            tables=["| Zona | KDB |\n| --- | --- |\n| A | 70% |"],
        )
    ]

    merged = chunker.pages_to_text(pages)

    assert "<<PAGE:3>>" in merged
    assert "Pasal 10" in merged
    assert "Tabel halaman 3 nomor 1" in merged


def test_infer_metadata_detects_local_scope_and_region():
    metadata = infer_metadata(
        "/data/corpus/local_regulations/jawa/Perda Provinsi Jawa Tengah Nomor 8 Tahun 2024 tentang RTRW.pdf"
    )

    assert metadata["scope"] == "local"
    assert metadata["region"] == "Jawa Tengah"
    assert metadata["reg_type"] == "Perda"
    assert metadata["year"] == 2024
    assert metadata["topic"] == "spatial_planning"
    assert metadata["typology"] == "spatial_planning"


def test_infer_metadata_handles_filename_style_region_hints():
    metadata = infer_metadata("/data/corpus/local_regulations/jawa/Semarang_Perda_5_2015.pdf")

    assert metadata["region"] == "Semarang"
    assert metadata["scope"] == "local"


def test_infer_metadata_adds_accessibility_and_building_use():
    metadata = infer_metadata("/data/corpus/indonesian-construction-law/Permen_14_2017_PKBG.pdf")

    assert metadata["topic"] == "accessibility"
    assert metadata["building_use"] == "public"
    assert metadata["typology"] == "accessibility"


def test_infer_metadata_adds_ownership_topic_for_sbkbg_docs():
    metadata = infer_metadata("/data/corpus/indonesian-construction-law/Permen_12_2024_SBKBG.pdf")

    assert metadata["topic"] == "ownership"
    assert metadata["typology"] == "ownership"


def test_infer_metadata_avoids_short_garbage_region_tokens():
    metadata = infer_metadata("/data/corpus/local_regulations/jawa/jawa_barat/bandung/PERDA No.05 Thn.2010.pdf")

    assert metadata["region"] == "Bandung"
    assert metadata["reg_type"] == "Perda"


def test_infer_metadata_uses_path_region_for_ambiguous_local_titles():
    metadata = infer_metadata(
        "/data/corpus/local_regulations/jawa/jakarta/PERDA NO 7 TAHUN 2010.pdf"
    )

    assert metadata["region"] == "DKI Jakarta"
    assert metadata["reg_type"] == "Perda"


def test_infer_metadata_infers_spatial_local_docs_as_perda_when_filename_is_ambiguous():
    metadata = infer_metadata(
        "/data/corpus/local_regulations/jawa/jawa_timur/surabaya/RDTR KOTA SURABAYA NO 8 THN 2018.pdf"
    )

    assert metadata["region"] == "Surabaya"
    assert metadata["reg_type"] == "Perda"
    assert metadata["topic"] == "spatial_planning"



def test_infer_metadata_detects_perpres_and_perbup_local_docs():
    perpres = infer_metadata(
        "/data/corpus/local_regulations/kalimantan/kalimantan_timur/ikn/Perpres Nomor 64 Tahun 2022.pdf"
    )
    perbup = infer_metadata(
        "/data/corpus/local_regulations/kalimantan/kalimantan_utara/kabupaten_tanjungselor/Perbup-No.-25-tahun-2018-ttg-Zonasi-Tata-Ruang-Kecamatan-Tanjung-Selor.pdf"
    )

    assert perpres["reg_type"] == "Perpres"
    assert perbup["reg_type"] == "Perbup"
    assert perbup["region"] == "Tanjungselor"
