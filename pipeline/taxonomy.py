from __future__ import annotations

"""Shared taxonomy helpers for Arsitrad retrieval and metadata tagging."""

import re
from typing import Iterable

TOPIC_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ownership", ("sbkbg", "surat bukti kepemilikan bangunan gedung", "bangunan gedung negara")),
    (
        "accessibility",
        (
            "aksesibilitas",
            "akses kursi roda",
            "kursi roda",
            "desain universal",
            "kemudahan bangunan gedung",
            "kemudahan",
            "pkbg",
            "ramp",
        ),
    ),
    ("heritage", ("heritage", "cagar budaya", "konservasi", "fasad")),
    (
        "fire_safety",
        (
            "sprinkler",
            "hydrant",
            "proteksi kebakaran",
            "sistem proteksi kebakaran",
            "kebakaran",
        ),
    ),
    (
        "seismic",
        (
            "sni 1726",
            "gaya geser dasar",
            "kds",
            "ketahanan gempa",
            "tahan gempa",
            "gempa",
            "seismik",
        ),
    ),
    (
        "spatial_planning",
        (
            "rdtr",
            "rtrw",
            "tata ruang",
            "zonasi",
            "kkpr",
            "sempadan sungai",
        ),
    ),
    ("thermal_comfort", ("ventilasi", "termal", "pendinginan", "penghawaan", "thermal comfort")),
    (
        "building_permit",
        (
            "pbg",
            "imb",
            "slf",
            "gsb",
            "kdb",
            "kdh",
            "klb",
            "dokumen teknis",
            "rencana teknis",
            "persyaratan teknis bangunan gedung",
            "persyaratan administratif bangunan gedung",
            "persetujuan bangunan gedung",
            "izin mendirikan bangunan",
            "sertifikat laik fungsi",
            "bangunan gedung",
        ),
    ),
)

BUILDING_USE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("industrial", ("kawasan industri", "industri", "gudang", "pabrik")),
    ("public", ("bangunan publik", "publik", "umum", "gedung negara", "sekolah", "rumah sakit", "pasar")),
    (
        "commercial",
        (
            "komersial",
            "kantor",
            "ruko",
            "ritel",
            "mall",
            "mal",
            "bangunan usaha",
            "tempat usaha",
            "usaha komersial",
            "fungsi usaha",
            "tempat melakukan kegiatan usaha",
        ),
    ),
    ("residential", ("rumah tinggal", "rumah", "hunian", "apartemen", "perumahan")),
)

TOPIC_FROM_LEGACY_TYPOLOGY = {
    "building_permit": "building_permit",
    "fire_safety": "fire_safety",
    "seismic": "seismic",
    "spatial_planning": "spatial_planning",
    "thermal_comfort": "thermal_comfort",
    "accessibility": "accessibility",
    "heritage": "heritage",
    "ownership": "ownership",
    "utilities": None,
    "general_regulation": None,
    "": None,
}


def normalize_lookup_text(*parts: object) -> str:
    text = " ".join(str(part or "") for part in parts)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^\w\s]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def contains_normalized_keyword(text: str, keyword: str) -> bool:
    normalized_text = f" {text.strip()} "
    normalized_keyword = normalize_lookup_text(keyword)
    if not normalized_keyword:
        return False
    return f" {normalized_keyword} " in normalized_text


def _find_first_label(text: str, keyword_groups: Iterable[tuple[str, tuple[str, ...]]]) -> str | None:
    for label, keywords in keyword_groups:
        if any(contains_normalized_keyword(text, keyword) for keyword in keywords):
            return label
    return None


def infer_topic(*parts: object) -> str | None:
    text = normalize_lookup_text(*parts)
    if not text:
        return None
    return _find_first_label(text, TOPIC_KEYWORDS)


def infer_building_use(*parts: object) -> str | None:
    text = normalize_lookup_text(*parts)
    if not text:
        return None
    label = _find_first_label(text, BUILDING_USE_KEYWORDS)
    if label:
        return label
    if any(keyword in text for keyword in ("aksesibilitas", "kursi roda", "pkbg", "kemudahan bangunan gedung")):
        return "public"
    return None


def enrich_metadata(metadata: dict[str, object] | None, content: str = "") -> dict[str, object]:
    enriched = dict(metadata or {})
    source_name = str(enriched.get("source_name") or "")
    source_path = str(enriched.get("source_path") or "")
    legacy_typology = str(enriched.get("typology") or "")

    topic = enriched.get("topic") or TOPIC_FROM_LEGACY_TYPOLOGY.get(legacy_typology) or infer_topic(source_name, source_path, content)
    building_use = enriched.get("building_use") or infer_building_use(source_name, source_path, content)

    if topic:
        enriched["topic"] = topic
    if building_use:
        enriched["building_use"] = building_use

    enriched["typology"] = topic or legacy_typology or "general_regulation"
    return enriched


def source_name_matches(source_name: str, *keywords: str) -> bool:
    normalized = normalize_lookup_text(source_name)
    return any(normalize_lookup_text(keyword) in normalized for keyword in keywords if normalize_lookup_text(keyword))


def is_rpjmd_source(source_name: str) -> bool:
    return source_name_matches(source_name, "rpjmd", "rencana pembangunan jangka menengah daerah")


def is_spatial_source(source_name: str) -> bool:
    return source_name_matches(source_name, "rdtr", "rtrw", "tata ruang", "zonasi")
