from pipeline.query_expander import (
    extract_filters_from_query,
    expand_query,
    interpret_query,
    is_non_regulatory_design_query,
)


def test_expand_query_bridges_imb_and_pbg():
    expansions = expand_query("cara urus IMB rumah 2 lantai di Semarang")

    lowered = [item.lower() for item in expansions]
    assert any("pbg" in item for item in lowered)
    assert expansions[0] == "cara urus IMB rumah 2 lantai di Semarang"


def test_extract_filters_reads_region_building_use_and_year():
    filters = extract_filters_from_query("Perda Semarang 2024 untuk rumah tinggal")

    assert filters["region"] == "Semarang"
    assert filters["building_use"] == "residential"
    assert filters["year"] == 2024
    assert filters["reg_type"] == "Perda"


def test_extract_filters_identifies_accessibility_topic():
    filters = extract_filters_from_query("Apa kewajiban aksesibilitas bangunan publik menurut Permen 14/2017?")

    assert filters["topic"] == "accessibility"
    assert filters["building_use"] == "public"
    assert filters["reg_type"] == "Permen"
    assert filters["year"] == 2017


def test_extract_filters_identifies_fire_safety_for_industrial_queries():
    filters = extract_filters_from_query("Apa syarat sprinkler untuk gudang 5000 m2 di kawasan industri Balikpapan?")

    assert filters["region"] == "Balikpapan"
    assert filters["topic"] == "fire_safety"
    assert filters["building_use"] == "industrial"


def test_interpret_query_returns_expansions_and_filters():
    interpretation = interpret_query("KDB rumah di Jakarta")

    assert interpretation.expanded_queries
    assert interpretation.filters["region"] == "DKI Jakarta"
    assert interpretation.filters["topic"] == "building_permit"
    assert interpretation.filters["building_use"] == "residential"


def test_extract_filters_detects_building_permit_from_document_requirements_query():
    filters = extract_filters_from_query("Apa kewajiban dokumen teknis untuk gedung komersial bertingkat?")

    assert filters["topic"] == "building_permit"
    assert filters["building_use"] == "commercial"


def test_non_regulatory_design_query_is_flagged_out_of_scope():
    query = "Apa regulasi yang relevan untuk desain rumah minimalis Jepang skandinavia?"

    assert is_non_regulatory_design_query(query) is True
    assert extract_filters_from_query(query) == {"out_of_scope": True}


def test_expand_query_adds_spatial_hint_for_sungai_queries():
    expansions = expand_query("Apa yang harus dicek untuk bangunan di dekat sungai menurut tata ruang?")

    assert any("sempadan sungai" in item.lower() for item in expansions)


def test_expand_query_adds_pp21_hint_for_regionless_spatial_queries():
    expansions = expand_query("Apakah RDTR wajib dicek sebelum mengurus PBG?")

    assert any("pp 21 2021 penataan ruang" in item.lower() for item in expansions)


def test_extract_filters_detects_spatial_topic_with_punctuation():
    filters = extract_filters_from_query("Apa yang harus dicek untuk bangunan di dekat sungai menurut tata ruang?")

    assert filters["topic"] == "spatial_planning"
