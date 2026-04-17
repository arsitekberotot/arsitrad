from __future__ import annotations

"""Semantic legal chunking for Arsitrad v2.

This module reparses raw PDFs and emits semantically meaningful chunks based on
Indonesian legal structure (BAB / Bagian / Paragraf / Pasal / Ayat) instead of
blind fixed-width windows.
"""

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import yaml

from pipeline.taxonomy import enrich_metadata, infer_building_use, infer_topic, normalize_lookup_text

PAGE_MARKER_RE = re.compile(r"^<<PAGE:(\d+)>>$")
YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
NUMBER_RE = re.compile(
    r"(?:\b(?:Nomor|No\.?)[\s:_-]*(\d+[A-Za-z/-]*))|(?:\b(?:UU|PP|Permen|Perda|Pergub|Perwali|SNI)[\s_-]*(\d+[A-Za-z/-]*))",
    re.IGNORECASE,
)
BAB_RE = re.compile(r"^BAB\s+[IVXLCDM]+(?:\b.*)?$", re.IGNORECASE)
BAGIAN_RE = re.compile(r"^Bagian\s+.*$", re.IGNORECASE)
PARAGRAF_RE = re.compile(r"^Paragraf\s+.*$", re.IGNORECASE)
PASAL_RE = re.compile(r"^Pasal\s+\d+[A-Za-z]?$", re.IGNORECASE)
AYAT_RE = re.compile(r"^\(?\d+[a-z]?\)|^Ayat\s*\(?\d+\)?$", re.IGNORECASE)
ISLANDS = {"jawa", "sumatera", "kalimantan", "sulawesi", "papua"}
CITY_PATTERNS = [
    re.compile(r"provinsi\s+([A-Za-z\s]+?)(?=\s+(?:Nomor|No\.?|Tahun|Tentang)\b|$)", re.IGNORECASE),
    re.compile(r"kota\s+([A-Za-z\s]+?)(?=\s+(?:Nomor|No\.?|Tahun|Tentang)\b|$)", re.IGNORECASE),
    re.compile(r"kabupaten\s+([A-Za-z\s]+?)(?=\s+(?:Nomor|No\.?|Tahun|Tentang)\b|$)", re.IGNORECASE),
]
FALLBACK_REGION_KEYWORDS = {
    "semarang": "Semarang",
    "jakarta": "DKI Jakarta",
    "bandung": "Bandung",
    "surabaya": "Surabaya",
    "balikpapan": "Balikpapan",
    "palembang": "Palembang",
    "samarinda": "Samarinda",
    "pontianak": "Pontianak",
    "singkawang": "Singkawang",
    "banjarmasin": "Banjarmasin",
    "banjarbaru": "Banjarbaru",
    "lampung": "Lampung",
    "medan": "Medan",
    "makassar": "Makassar",
    "jawa tengah": "Jawa Tengah",
    "jawa barat": "Jawa Barat",
    "jawa timur": "Jawa Timur",
    "sumatera utara": "Sumatera Utara",
    "sumatera selatan": "Sumatera Selatan",
    "sumatera barat": "Sumatera Barat",
    "kalimantan timur": "Kalimantan Timur",
    "kalimantan barat": "Kalimantan Barat",
    "kalimantan selatan": "Kalimantan Selatan",
    "kalimantan utara": "Kalimantan Utara",
    "sulawesi selatan": "Sulawesi Selatan",
    "papua barat": "Papua Barat",
}
REGION_STOPWORDS = {
    "perda", "pergub", "perwali", "peraturan", "daerah", "provinsi", "kota", "kabupaten",
    "nomor", "tahun", "tentang", "rencana", "tata", "ruang", "wilayah", "rdtr", "rtrw",
    "prov", "no", "thn", "ttg", "dan", "yang", "pdf", "bg"
}


@dataclass(slots=True)
class ExtractedPage:
    page_number: int
    text: str
    tables: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ChunkRecord:
    chunk_key: str
    content: str
    metadata: dict[str, object]
    start_page: int
    end_page: int

    def to_dict(self) -> dict[str, object]:
        return {
            "chunk_key": self.chunk_key,
            "content": self.content,
            "metadata": self.metadata,
            "start_page": self.start_page,
            "end_page": self.end_page,
        }


@dataclass(slots=True)
class ChunkerConfig:
    max_chars: int = 3200
    min_chars: int = 500
    overlap_chars: int = 200
    max_table_rows: int = 8


def normalize_whitespace(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "chunk"


REG_TYPE_LABELS = {
    "uu": "UU",
    "pp": "PP",
    "sni": "SNI",
    "perpres": "Perpres",
    "permen": "Permen",
    "perda": "Perda",
    "pergub": "Pergub",
    "perwali": "Perwali",
    "perbup": "Perbup",
}
REG_TYPE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("peraturan presiden", "Perpres"),
    ("perpres", "Perpres"),
    ("peraturan menteri", "Permen"),
    ("permen", "Permen"),
    ("peraturan daerah", "Perda"),
    ("perda", "Perda"),
    ("peraturan gubernur", "Pergub"),
    ("pergub", "Pergub"),
    ("peraturan walikota", "Perwali"),
    ("peraturan wali kota", "Perwali"),
    ("perwali", "Perwali"),
    ("peraturan bupati", "Perbup"),
    ("perbup", "Perbup"),
    ("undang undang", "UU"),
    ("uu", "UU"),
    ("peraturan pemerintah", "PP"),
    ("pp", "PP"),
    ("sni", "SNI"),
)
LOCAL_PERDA_FALLBACK_HINTS = (
    "rdtr",
    "rtrw",
    "rencana tata ruang wilayah",
    "zonasi",
    "bangunan gedung",
)


def infer_reg_type(path: Path) -> str:
    lowered_parts = [part.lower() for part in path.parts]
    lookup = normalize_lookup_text(*lowered_parts, path.stem)
    for token in ("perpres", "permen", "perda", "pergub", "perwali", "perbup", "uu", "pp", "sni"):
        if token in lowered_parts:
            return REG_TYPE_LABELS[token]
    for pattern, label in REG_TYPE_PATTERNS:
        if pattern in lookup:
            return label
    if "local regulations" in lookup and any(hint in lookup for hint in LOCAL_PERDA_FALLBACK_HINTS):
        return "Perda"
    return "Unknown"


def infer_year(name: str) -> int | None:
    match = YEAR_RE.search(name)
    return int(match.group(0)) if match else None


def infer_number(name: str) -> str | None:
    match = NUMBER_RE.search(name)
    if not match:
        return None
    return next(group for group in match.groups() if group)


def normalize_region_from_segment(segment: str) -> str | None:
    normalized = normalize_lookup_text(segment)
    if not normalized:
        return None
    if normalized in FALLBACK_REGION_KEYWORDS:
        return FALLBACK_REGION_KEYWORDS[normalized]
    tokens = [
        token
        for token in normalized.split()
        if token not in {"kota", "kabupaten", "provinsi"}
    ]
    if not tokens:
        return None
    candidate = " ".join(tokens)
    return FALLBACK_REGION_KEYWORDS.get(candidate, candidate.title())


def infer_region_from_path(path: Path, is_local: bool) -> str | None:
    if not is_local:
        return "nasional"
    lowered_parts = [part.lower() for part in path.parts]
    try:
        start_index = lowered_parts.index("local_regulations") + 1
    except ValueError:
        return None

    relative_parts = list(path.parts[start_index:-1])
    locality_parts = [part for part in relative_parts if part.lower() not in ISLANDS]
    if not locality_parts:
        return None
    return normalize_region_from_segment(locality_parts[-1])


def infer_region(path: Path, name: str, is_local: bool) -> str:
    lowered = name.lower()
    if not is_local:
        return "nasional"
    if region_from_path := infer_region_from_path(path, is_local=is_local):
        return region_from_path
    for pattern in CITY_PATTERNS:
        match = pattern.search(name)
        if match:
            region = normalize_whitespace(match.group(1)).title()
            region_tokens = [
                token for token in re.split(r"[^a-z]+", region.lower())
                if token and token not in REGION_STOPWORDS and len(token) >= 3
            ]
            if region_tokens:
                return " ".join(token.title() for token in region_tokens)
    for keyword, region in FALLBACK_REGION_KEYWORDS.items():
        if keyword in lowered:
            return region
    tokens = [
        token
        for token in re.split(r"[^a-z]+", lowered)
        if token and token not in REGION_STOPWORDS and len(token) >= 3
    ]
    if tokens:
        return tokens[0].title()
    return "daerah"


def infer_metadata(pdf_path: str | Path) -> dict[str, object]:
    path = Path(pdf_path)
    parts = [part.lower() for part in path.parts]
    is_local = "local_regulations" in parts
    island = next((part for part in parts if part in ISLANDS), None)
    source_name = path.stem
    reg_type = infer_reg_type(path)
    year = infer_year(source_name)
    number = infer_number(source_name)
    region = infer_region(path, source_name, is_local=is_local)
    topic = infer_topic(source_name, str(path))
    building_use = infer_building_use(source_name, str(path))

    metadata = {
        "source_name": source_name,
        "source_path": str(path),
        "source_file": path.name,
        "reg_type": reg_type,
        "year": year,
        "number": number,
        "region": region,
        "island": island,
        "scope": "local" if is_local else "national",
        "typology": topic or "general_regulation",
        "title": source_name,
    }
    if topic:
        metadata["topic"] = topic
    if building_use:
        metadata["building_use"] = building_use
    return enrich_metadata(metadata)


class LegalChunker:
    def __init__(self, config: ChunkerConfig | None = None):
        self.config = config or ChunkerConfig()

    def table_to_markdown(self, table: Sequence[Sequence[object]] | None) -> str:
        if not table:
            return ""

        rows = [
            [normalize_whitespace(str(cell or "-")) for cell in row]
            for row in table[: self.config.max_table_rows]
            if row and any(str(cell or "").strip() for cell in row)
        ]
        if not rows:
            return ""

        header = rows[0]
        body = rows[1:] if len(rows) > 1 else []
        if len(set(header)) == 1 and header[0] == "-":
            width = len(header)
            header = [f"kolom_{idx + 1}" for idx in range(width)]

        markdown_lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(["---"] * len(header)) + " |",
        ]
        for row in body:
            padded = row + ["-"] * (len(header) - len(row))
            markdown_lines.append("| " + " | ".join(padded[: len(header)]) + " |")

        summary_bits = [f"Tabel dengan {len(rows)} baris terdeteksi."]
        if body:
            preview = "; ".join(
                ", ".join(cell for cell in row if cell and cell != "-") for row in body[:2]
            )
            if preview:
                summary_bits.append(f"Ringkasan isi: {preview}.")

        return "\n".join(summary_bits + markdown_lines)

    def extract_pdf(self, pdf_path: str | Path) -> list[ExtractedPage]:
        import pdfplumber

        pages: list[ExtractedPage] = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = normalize_whitespace(page.extract_text() or "")
                tables = [
                    markdown
                    for markdown in (
                        self.table_to_markdown(table) for table in (page.extract_tables() or [])
                    )
                    if markdown
                ]
                pages.append(ExtractedPage(page_number=page_number, text=text, tables=tables))
        return pages

    def pages_to_text(self, pages: Sequence[ExtractedPage]) -> str:
        parts: list[str] = []
        for page in pages:
            parts.append(f"<<PAGE:{page.page_number}>>")
            if page.text:
                parts.append(page.text)
            for table_index, table in enumerate(page.tables, start=1):
                parts.append(f"Tabel halaman {page.page_number} nomor {table_index}:\n{table}")
        return "\n".join(parts)

    def _iter_content_lines(self, text: str) -> Iterator[tuple[int, str]]:
        current_page = 1
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            marker = PAGE_MARKER_RE.match(line)
            if marker:
                current_page = int(marker.group(1))
                continue
            yield current_page, line

    def _make_chunk_key(self, source_path: str, chunk_index: int, start_page: int, end_page: int) -> str:
        digest = hashlib.sha1(
            f"{source_path}:{chunk_index}:{start_page}:{end_page}".encode("utf-8")
        ).hexdigest()[:12]
        return f"{slugify(Path(source_path).stem)}-{chunk_index:04d}-{digest}"

    def _finalize_chunk(
        self,
        chunks: list[ChunkRecord],
        lines: list[str],
        metadata: dict[str, object],
        start_page: int,
        end_page: int,
    ) -> None:
        content = normalize_whitespace("\n".join(lines))
        if not content:
            return

        chunk_index = len(chunks)
        if len(content) <= self.config.max_chars:
            chunk_metadata = dict(metadata)
            chunk_metadata.update(
                {
                    "chunk_index": chunk_index,
                    "start_page": start_page,
                    "end_page": end_page,
                }
            )
            chunks.append(
                ChunkRecord(
                    chunk_key=self._make_chunk_key(str(metadata["source_path"]), chunk_index, start_page, end_page),
                    content=content,
                    metadata=chunk_metadata,
                    start_page=start_page,
                    end_page=end_page,
                )
            )
            return

        for split_content in self._split_long_content(content):
            split_content = normalize_whitespace(split_content)
            if not split_content:
                continue
            chunk_index = len(chunks)
            chunk_metadata = dict(metadata)
            chunk_metadata.update(
                {
                    "chunk_index": chunk_index,
                    "start_page": start_page,
                    "end_page": end_page,
                    "overflow_split": True,
                }
            )
            chunks.append(
                ChunkRecord(
                    chunk_key=self._make_chunk_key(str(metadata["source_path"]), chunk_index, start_page, end_page),
                    content=split_content,
                    metadata=chunk_metadata,
                    start_page=start_page,
                    end_page=end_page,
                )
            )

    def _split_long_content(self, content: str) -> list[str]:
        pieces = [piece.strip() for piece in re.split(r"(?=\nPasal\s+\d+[A-Za-z]?$)|(?=\n\(\d+\))|\n\n", content) if piece.strip()]
        if not pieces:
            return [content]

        chunks: list[str] = []
        current = ""
        for piece in pieces:
            candidate = f"{current}\n{piece}".strip() if current else piece
            if len(candidate) <= self.config.max_chars or not current:
                current = candidate
                continue
            chunks.append(current)
            overlap = current[-self.config.overlap_chars :]
            current = f"{overlap}\n{piece}".strip()
        if current:
            chunks.append(current)
        return chunks

    def chunk_text(self, text: str, metadata: dict[str, object]) -> list[ChunkRecord]:
        chunks: list[ChunkRecord] = []
        context = {"bab": None, "bagian": None, "paragraf": None}
        preamble: list[str] = []
        current_lines: list[str] = []
        current_start_page = 1
        current_end_page = 1

        def start_new_chunk(page_number: int, pasal_line: str) -> None:
            nonlocal current_lines, current_start_page, current_end_page
            current_start_page = page_number
            current_end_page = page_number
            current_lines = [
                header
                for header in [context["bab"], context["bagian"], context["paragraf"], pasal_line]
                if header
            ]

        for page_number, line in self._iter_content_lines(text):
            current_end_page = page_number
            if BAB_RE.match(line):
                context["bab"] = line
                context["bagian"] = None
                context["paragraf"] = None
                if not current_lines:
                    preamble.append(line)
                continue
            if BAGIAN_RE.match(line):
                context["bagian"] = line
                context["paragraf"] = None
                if not current_lines:
                    preamble.append(line)
                continue
            if PARAGRAF_RE.match(line):
                context["paragraf"] = line
                if not current_lines:
                    preamble.append(line)
                continue
            if PASAL_RE.match(line):
                if current_lines:
                    self._finalize_chunk(chunks, current_lines, metadata, current_start_page, current_end_page)
                elif preamble:
                    preamble_text = normalize_whitespace("\n".join(preamble))
                    if len(preamble_text) >= self.config.min_chars:
                        self._finalize_chunk(chunks, preamble, metadata, 1, page_number)
                    preamble = []
                start_new_chunk(page_number, line)
                continue
            if current_lines:
                current_lines.append(line)
            else:
                preamble.append(line)

        if current_lines:
            self._finalize_chunk(chunks, current_lines, metadata, current_start_page, current_end_page)
        elif preamble:
            self._finalize_chunk(chunks, preamble, metadata, 1, current_end_page)

        if not chunks:
            self._finalize_chunk(chunks, [text], metadata, 1, 1)
        return chunks

    def chunk_pdf(self, pdf_path: str | Path) -> list[ChunkRecord]:
        metadata = infer_metadata(pdf_path)
        pages = self.extract_pdf(pdf_path)
        text = self.pages_to_text(pages)
        return self.chunk_text(text, metadata)


def collect_pdf_paths(*roots: str | Path) -> list[Path]:
    pdf_paths: list[Path] = []
    for root in roots:
        if not root:
            continue
        root_path = Path(root)
        if not root_path.exists():
            continue
        pdf_paths.extend(sorted(root_path.rglob("*.pdf")))
    return pdf_paths


def load_chunker_from_config(config_path: str | Path = "config.yaml") -> LegalChunker:
    with open(config_path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    chunking = config.get("v2", {}).get("chunking", {})
    return LegalChunker(
        ChunkerConfig(
            max_chars=chunking.get("max_chars", 3200),
            min_chars=chunking.get("min_chars", 500),
            overlap_chars=chunking.get("overlap_chars", 200),
            max_table_rows=chunking.get("max_table_rows", 8),
        )
    )


def sample_chunks(corpus_roots: Sequence[str | Path], limit: int = 2) -> list[dict[str, object]]:
    chunker = load_chunker_from_config()
    samples: list[dict[str, object]] = []
    for pdf_path in collect_pdf_paths(*corpus_roots)[:limit]:
        chunks = chunker.chunk_pdf(pdf_path)
        samples.append(
            {
                "pdf_path": str(pdf_path),
                "chunk_count": len(chunks),
                "sample_chunk": chunks[0].to_dict() if chunks else None,
            }
        )
    return samples


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic legal chunking for Arsitrad v2")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--sample", action="store_true", help="Print chunk samples instead of full extraction")
    parser.add_argument("--limit", type=int, default=2, help="How many PDFs to inspect in sample mode")
    parser.add_argument("--pdf", help="Chunk a specific PDF path")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    roots = [
        config.get("v2", {}).get("corpus", {}).get("national_root"),
        config.get("v2", {}).get("corpus", {}).get("local_root"),
    ]
    chunker = load_chunker_from_config(args.config)

    if args.pdf:
        chunks = chunker.chunk_pdf(args.pdf)
        print(json.dumps([chunk.to_dict() for chunk in chunks[: args.limit]], ensure_ascii=False, indent=2))
        return

    if args.sample:
        print(json.dumps(sample_chunks(roots, limit=args.limit), ensure_ascii=False, indent=2))
        return

    samples = sample_chunks(roots, limit=args.limit)
    print(json.dumps(samples, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
