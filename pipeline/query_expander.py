from __future__ import annotations

"""Query expansion and filter extraction for Arsitrad v2."""

import re
from dataclasses import dataclass, field

from pipeline.taxonomy import infer_building_use, infer_topic, normalize_lookup_text

TERM_EQUIVALENTS: dict[str, tuple[str, ...]] = {
    "pbg": ("persetujuan bangunan gedung", "imb", "izin mendirikan bangunan"),
    "imb": ("pbg", "persetujuan bangunan gedung", "izin mendirikan bangunan"),
    "slf": ("sertifikat laik fungsi",),
    "kdb": ("koefisien dasar bangunan", "building coverage ratio"),
    "kdh": ("koefisien dasar hijau", "koefisien daerah hijau", "open space ratio"),
    "klb": ("koefisien lantai bangunan", "floor area ratio"),
    "gsb": ("garis sempadan bangunan", "setback bangunan"),
    "rdtr": ("rencana detail tata ruang",),
    "rtrw": ("rencana tata ruang wilayah",),
    "sni": ("standar nasional indonesia",),
    "sbkbg": ("surat bukti kepemilikan bangunan gedung",),
}

REGION_KEYWORDS = {
    "semarang": "Semarang",
    "jakarta": "DKI Jakarta",
    "bandung": "Bandung",
    "surabaya": "Surabaya",
    "balikpapan": "Balikpapan",
    "palembang": "Palembang",
    "lampung": "Lampung",
    "jawa tengah": "Jawa Tengah",
    "jawa barat": "Jawa Barat",
    "jawa timur": "Jawa Timur",
    "kalimantan timur": "Kalimantan Timur",
    "sumatera utara": "Sumatera Utara",
}

REG_TYPE_KEYWORDS = {
    "perda": "Perda",
    "pergub": "Pergub",
    "perwali": "Perwali",
    "permen": "Permen",
    "pp": "PP",
    "uu": "UU",
    "sni": "SNI",
}

YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
NON_REGULATORY_STYLE_KEYWORDS = (
    "minimalis",
    "skandinavia",
    "scandinavian",
    "jepang",
    "industrial style",
    "mediterania",
    "boho",
    "bohemian",
    "klasik",
    "modern tropis",
)
NON_REGULATORY_DESIGN_KEYWORDS = (
    "desain",
    "tema",
    "gaya",
    "interior",
    "eksterior",
    "konsep",
)
REGULATORY_ANCHORS = (
    "pbg",
    "imb",
    "slf",
    "kdb",
    "kdh",
    "klb",
    "gsb",
    "rdtr",
    "rtrw",
    "zonasi",
    "kkpr",
    "perda",
    "pergub",
    "perwali",
    "permen",
    "perpres",
    "pp",
    "uu",
    "sni",
    "sbkbg",
    "sprinkler",
    "hydrant",
    "aksesibilitas",
    "gempa",
    "heritage",
    "konservasi",
)
COMPARISON_KEYWORDS = (
    "beda",
    "bedanya",
    "perbedaan",
    "perbandingan",
    "banding",
    "versus",
    "vs",
)


@dataclass(slots=True)
class QueryInterpretation:
    original_query: str
    expanded_queries: list[str] = field(default_factory=list)
    filters: dict[str, object] = field(default_factory=dict)


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = re.sub(r"\s+", " ", value.strip())
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(normalized)
    return result


def has_explicit_region(query: str) -> bool:
    normalized = normalize_lookup_text(query)
    return any(keyword in normalized for keyword in REGION_KEYWORDS)


def is_regionless_spatial_query(query: str) -> bool:
    return infer_topic(query) == "spatial_planning" and not has_explicit_region(query)


def is_imb_pbg_comparison_query(query: str) -> bool:
    normalized = normalize_lookup_text(query)
    has_imb = "imb" in normalized or "izin mendirikan bangunan" in normalized
    has_pbg = "pbg" in normalized or "persetujuan bangunan gedung" in normalized
    has_comparison = any(keyword in normalized for keyword in COMPARISON_KEYWORDS)
    return has_imb and has_pbg and has_comparison


def expand_query(query: str, max_expansions: int = 6) -> list[str]:
    normalized = re.sub(r"\s+", " ", query.strip())
    lowered = normalized.lower()
    expansions = [normalized]
    imb_pbg_comparison = is_imb_pbg_comparison_query(query)

    if is_regionless_spatial_query(query):
        expansions.append(f"{normalized} pp 21 2021 penataan ruang")

    for anchor, equivalents in TERM_EQUIVALENTS.items():
        variants = (anchor, *equivalents)
        matched_term = next((variant for variant in variants if variant in lowered), None)
        if not matched_term:
            continue
        if any(variant in lowered for variant in variants if variant != matched_term):
            continue
        for variant in variants:
            if variant == matched_term:
                continue
            expansions.append(re.sub(re.escape(matched_term), variant, lowered, count=1))

    if "imb" in lowered and "pbg" not in lowered:
        expansions.append(f"{normalized} persetujuan bangunan gedung")
    if "pbg" in lowered and "imb" not in lowered:
        expansions.append(f"{normalized} izin mendirikan bangunan")
    if any(term in lowered for term in ("sprinkler", "hydrant", "kebakaran")):
        expansions.append(f"{normalized} proteksi kebakaran")
    if any(term in lowered for term in ("aksesibilitas", "kursi roda", "ramp")):
        expansions.append(f"{normalized} kemudahan bangunan gedung desain universal")
    if "sbkbg" in lowered:
        expansions.append(f"{normalized} surat bukti kepemilikan bangunan gedung")
    if "rdtr" in lowered and any(term in lowered for term in ("pbg", "imb", "slf")):
        expansions.append(f"{normalized} zonasi tata ruang persetujuan bangunan gedung")
    if "imb" in lowered and "pbg" in lowered and not imb_pbg_comparison:
        expansions.append(f"{normalized} pp 16 2021 persetujuan bangunan gedung")
    if "sungai" in lowered and "sempadan sungai" not in lowered:
        expansions.append(f"{normalized} sempadan sungai")
    if "rdtr" in lowered and "rtrw" not in lowered:
        expansions.append(f"{normalized} rtrw")
    if imb_pbg_comparison:
        expansions.append(f"{normalized} perbedaan izin mendirikan bangunan dan persetujuan bangunan gedung")
        expansions.append("izin mendirikan bangunan gedung yang selanjutnya disingkat IMB adalah")
        expansions.append("persetujuan bangunan gedung yang selanjutnya disingkat PBG adalah")

    return dedupe_preserve_order(expansions)[:max_expansions]


def is_non_regulatory_design_query(query: str) -> bool:
    normalized = normalize_lookup_text(query)
    has_design_intent = any(keyword in normalized for keyword in NON_REGULATORY_DESIGN_KEYWORDS)
    has_style = any(keyword in normalized for keyword in NON_REGULATORY_STYLE_KEYWORDS)
    has_regulatory_anchor = any(keyword in normalized for keyword in REGULATORY_ANCHORS)
    return has_design_intent and has_style and not has_regulatory_anchor


def extract_filters_from_query(query: str) -> dict[str, object]:
    lowered = query.lower()
    filters: dict[str, object] = {}
    imb_pbg_comparison = is_imb_pbg_comparison_query(query)

    if is_non_regulatory_design_query(query):
        return {"out_of_scope": True}

    for keyword, region in REGION_KEYWORDS.items():
        if keyword in lowered:
            filters["region"] = region
            break

    topic = infer_topic(query)
    if topic:
        filters["topic"] = topic

    building_use = infer_building_use(query)
    if building_use:
        filters["building_use"] = building_use

    for keyword, reg_type in REG_TYPE_KEYWORDS.items():
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            filters["reg_type"] = reg_type
            break

    year_match = YEAR_RE.search(query)
    if year_match:
        filters["year"] = int(year_match.group(0))

    if "region" not in filters:
        if topic in {"accessibility", "seismic", "ownership"}:
            filters["region"] = "nasional"
        elif (
            topic == "building_permit"
            and not imb_pbg_comparison
            and not any(term in lowered for term in ("rdtr", "rtrw", "zonasi", "kdb", "kdh", "klb"))
        ):
            filters["region"] = "nasional"

    return filters


def interpret_query(query: str, max_expansions: int = 6) -> QueryInterpretation:
    return QueryInterpretation(
        original_query=query,
        expanded_queries=expand_query(query, max_expansions=max_expansions),
        filters=extract_filters_from_query(query),
    )
