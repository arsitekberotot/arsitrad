
"""
Pasal.id-based Regulation Scraper for Arsitrad
===============================================
Scrapes Indonesian legal/regulation domains and outputs
ChromaDB-ready documents for the Arsitrad RAG pipeline.

Approved domains:
  - peraturan.go.id          (primary — UU, PP, Perpres, Permen, etc.)
  - jdih.kemenkeu.go.id     (Kementerian Keuangan)
  - jdih.kemendagri.go.id   (Kementerian Dalam Negeri)
  - jdih.kemnaker.go.id     (Kementerian Ketenagakerjaan)
  - jdih.esdm.go.id         (Kementerian ESDM)
  - jdih.setneg.go.id       (Sekretariat Negara)
  - peraturan.bpk.go.id      (BPK)

Usage:
  python -m scraper.pasal_scraper --domain peraturan --type UU --max-pages 5
  python -m scraper.pasal_scraper --domain all --type all --max-pages 10
  python -m scraper.pasal_scraper --scrape-pdfs --max-pdfs 50
"""

import os
import re
import json
import time
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Optional, Iterator, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import pdfplumber
from tqdm import tqdm

# Config
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "pasal_scraped"
RAW_DIR = DATA_DIR / "raw"
PARSED_DIR = DATA_DIR / "parsed"
CHROMA_DIR = DATA_DIR / "chroma"

DOMAINS = {
    "peraturan": {
        "base_url": "https://peraturan.go.id",
        "list_url": "https://peraturan.go.id/uu",
        "types": {
            "UUD":     {"path": "uud", "label": "Undang-Undang Dasar"},
            "UU":      {"path": "uu", "label": "Undang-Undang"},
            "PP":      {"path": "pp", "label": "Peraturan Pemerintah"},
            "PERPRES": {"path": "perpres", "label": "Peraturan Presiden"},
            "PERMEN":  {"path": "permen", "label": "Peraturan Menteri"},
            "PERDA":   {"path": "perda", "label": "Peraturan Daerah"},
        }
    },
    "bpk": {
        "base_url": "https://peraturan.bpk.go.id",
        "list_url": "https://peraturan.bpk.go.id/home/regulation/all",
        "types": {
            "UU":      {"path": "home/regulation/uu", "label": "Undang-Undang"},
            "PP":      {"path": "home/regulation/pp", "label": "Peraturan Pemerintah"},
            "PERPRES": {"path": "home/regulation/perpres", "label": "Peraturan Presiden"},
        }
    },
    "jdih_kemenkeu": {
        "base_url": "https://jdih.kemenkeu.go.id",
        "types": {
            "UU":     {"path": "regulation/list/type/1", "label": "Undang-Undang"},
            "PP":      {"path": "regulation/list/type/2", "label": "Peraturan Pemerintah"},
            "PERMEN":  {"path": "regulation/list/type/3", "label": "Peraturan Menteri"},
        }
    },
    "jdih_kemendagri": {
        "base_url": "https://jdih.kemendagri.go.id",
        "types": {
            "UU":     {"path": "home/product/uu", "label": "Undang-Undang"},
            "PP":     {"path": "home/product/pp", "label": "Peraturan Pemerintah"},
            "PERDA":  {"path": "home/product/perda", "label": "Peraturan Daerah"},
        }
    },
    "jdih_kemnaker": {
        "base_url": "https://jdih.kemnaker.go.id",
        "types": {
            "PP":     {"path": "home/page/regulasi/1", "label": "Peraturan Pemerintah"},
            "PERMEN": {"path": "home/page/regulasi/2", "label": "Peraturan Menteri"},
        }
    },
    "jdih_esdm": {
        "base_url": "https://jdih.esdm.go.id",
        "types": {
            "UU":     {"path": "produk-hukum/undang-undangnya", "label": "Undang-Undang"},
            "PP":     {"path": "produk-hukum/peraturan-pemerintah", "label": "Peraturan Pemerintah"},
            "PERMEN": {"path": "produk-hukum/peraturan-menteri", "label": "Peraturan Menteri"},
        }
    },
    "jdih_setneg": {
        "base_url": "https://jdih.setneg.go.id",
        "types": {
            "UUD": {"path": "web/pages/regulation_list.jsf", "label": "Undang-Undang Dasar"},
            "UU":  {"path": "web/pages/regulation_list.jsf", "label": "Undang-Undang"},
            "PP":  {"path": "web/pages/regulation_list.jsf", "label": "Peraturan Pemerintah"},
        }
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ArsitradBot/1.0; +https://arsitrad.id/bot) "
                  "(+https://github.com/ilhamfp/pasal)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s -- %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pasal_scraper")


@dataclass
class RegulationMeta:
    frbr_uri: str = ""
    type: str = ""
    number: str = ""
    year: int = 0
    title_id: str = ""
    source_url: str = ""
    source_domain: str = ""
    pdf_url: str = ""
    status: str = ""
    effective_date: str = ""
    issued_date: str = ""


@dataclass
class ParsedRegulation:
    meta: RegulationMeta
    preamble: str = ""
    nodes: List[Dict] = None
    elucidation_general: str = ""
    elucidation_per_pasal: str = ""
    attachments: List[str] = None
    full_text: str = ""

    def __post_init__(self):
        if self.nodes is None:
            self.nodes = []
        if self.attachments is None:
            self.attachments = []

    def to_rag_document(self) -> Dict:
        return {
            "text": self.full_text,
            "metadata": {
                "frbr_uri": self.meta.frbr_uri,
                "type": self.meta.type,
                "number": self.meta.number,
                "year": self.meta.year,
                "title": self.meta.title_id,
                "source_url": self.meta.source_url,
                "source_domain": self.meta.source_domain,
                "effective_date": self.meta.effective_date,
                "status": self.meta.status,
            }
        }

    def to_pasal_json(self) -> Dict:
        return {
            "frbr_uri": self.meta.frbr_uri,
            "type": self.meta.type,
            "number": self.meta.number,
            "year": self.meta.year,
            "title_id": self.meta.title_id,
            "source_url": self.meta.source_url,
            "nodes": self.nodes,
        }


def get_session(domain_key: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    session.headers["Referer"] = DOMAINS[domain_key]["base_url"]
    return session


def fetch_with_retry(url: str, session: requests.Session, max_retries: int = MAX_RETRIES) -> Optional[requests.Response]:
    for attempt in range(max_retries):
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code in (200, 404):
                return resp
            log.warning("HTTP %d for %s (attempt %d/%d)", resp.status_code, url, attempt+1, max_retries)
        except requests.RequestException as e:
            log.warning("Request failed for %s (attempt %d/%d): %s", url, attempt+1, max_retries, e)

        if attempt < max_retries - 1:
            time.sleep(RETRY_DELAY * (2 ** attempt))
    return None


def parse_title_to_meta(title: str, href: str) -> Dict:
    meta = {"type": "", "number": "", "year": 0, "title_id": title}

    type_patterns = [
        (r"Undang-Undang\s*Dasar\s*(?:1945)?", "UUD"),
        (r"Undang-Undang\s*(?:Nomor|No\.?)\s*(\d+)", "UU"),
        (r"UU\s*(?:No\.?)?\s*(\d+)", "UU"),
        (r"Peraturan\s*Pemerintah\s*(?:Nomor|No\.?)?\s*(\d+)", "PP"),
        (r"PP\s*(?:No\.?)?\s*(\d+)", "PP"),
        (r"Peraturan\s*Presiden\s*(?:Nomor|No\.?)?\s*(\d+)", "PERPRES"),
        (r"Perpres\s*(?:No\.?)?\s*(\d+)", "PERPRES"),
        (r"Peraturan\s*Menteri\s*(?:Nomor|No\.?)?\s*(\d+)", "PERMEN"),
        (r"Permen\s*(?:No\.?)?\s*(\d+)", "PERMEN"),
        (r"Peraturan\s*Daerah\s*(?:Nomor|No\.?)?\s*(\d+)", "PERDA"),
        (r"Perda\s*(?:No\.?)?\s*(\d+)", "PERDA"),
    ]

    for pattern, reg_type in type_patterns:
        m = re.search(pattern, title, re.IGNORECASE)
        if m:
            meta["type"] = reg_type
            num_m = re.search(r"(?:Nomor|No\.?)\s*(\d+)", title, re.IGNORECASE)
            if num_m:
                meta["number"] = num_m.group(1)
            else:
                meta["number"] = m.group(1) if m.lastindex and m.group(m.lastindex) else ""
            break

    year_m = re.search(r"(?:Tahun|Year)\s*(\d{4})", title, re.IGNORECASE) or \
             re.search(r"\b(19\d{2}|20\d{2})\b", title)
    if year_m:
        meta["year"] = int(year_m.group(1))

    if meta["type"] and meta["number"] and meta["year"]:
        type_code = meta["type"].lower()
        meta["frbr_uri"] = f"/akn/id/act/{type_code}/{meta['year']}/{meta['number']}"

    return meta


# =============================================================================
# List Page Scrapers
# =============================================================================

def scrape_peraturan_list(session: requests.Session, reg_type: str, max_pages: int = 10) -> Iterator[Dict]:
    domain = DOMAINS["peraturan"]
    type_path = domain["types"].get(reg_type, domain["types"]["UU"])["path"]
    base_list_url = f"{domain['base_url']}/{type_path}"

    for page in range(1, max_pages + 1):
        page_url = f"{base_list_url}?page={page}" if page > 1 else base_list_url
        log.info("  Fetching page %d: %s", page, page_url)

        resp = fetch_with_retry(page_url, session)
        if not resp or resp.status_code != 200:
            log.warning("Failed to fetch page %d", page)
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        items = (soup.select("table.table-regulasi tbody tr") or
                  soup.select("div.list-regulasi a.item") or
                  soup.select("ul.list-group li a") or
                  soup.select("div.card-regulasi"))

        found = False
        for item in items:
            try:
                link_el = item if item.name == "a" else item.select_one("a")
                if not link_el:
                    continue

                href = link_el.get("href", "")
                title = link_el.get_text(strip=True)

                if not href or not title:
                    continue

                skip_patterns = ["download", "lihat", "cetak", "унк", "#"]
                if any(p in href.lower() for p in skip_patterns if len(p) > 2):
                    continue

                meta = parse_title_to_meta(title, href)

                # Try to find PDF link in same row
                pdf_link = ""
                parent = item.find_parent("tr") or item
                pdf_el = (parent.select_one("a[href*='.pdf']") or
                          item.select_one("a[href$='.pdf']") or
                          item.find_next("a[href$='.pdf']"))
                if pdf_el:
                    pdf_link = pdf_el.get("href", "")

                full_url = urljoin(page_url, href)
                if pdf_link and not pdf_link.startswith("http"):
                    pdf_link = urljoin(domain["base_url"], pdf_link)

                found = True
                yield {
                    "title": title,
                    "detail_url": full_url,
                    "pdf_url": pdf_link,
                    **meta
                }
            except Exception as e:
                log.debug("Error parsing item: %s", e)
                continue

        if not found and page == 1:
            for a in soup.select("a[href]"):
                href = a.get("href", "")
                if re.match(r"/\w+/\d+/", href) or re.match(r"/\w+/nomor", href):
                    title = a.get_text(strip=True)
                    if title and len(title) > 10:
                        meta = parse_title_to_meta(title, href)
                        full_url = urljoin(page_url, href)
                        yield {
                            "title": title,
                            "detail_url": full_url,
                            "pdf_url": "",
                            **meta
                        }

        next_btn = soup.select_one("a.page-link[rel='next'], a[aria-label='next']")
        if not next_btn and page < max_pages:
            page_links = soup.select("a.page-link, ul.pagination a")
            has_more = any(f"page={page+1}" in a.get("href", "") for a in page_links)
            if not has_more:
                log.info("No more pages after page %d", page)
                break

        time.sleep(1)


def scrape_bpk_list(session: requests.Session, reg_type: str = "UU", max_pages: int = 10) -> Iterator[Dict]:
    domain = DOMAINS["bpk"]
    base_url = f"{domain['base_url']}/{domain['types'].get(reg_type, {'path': ''})['path']}"

    for page in range(1, max_pages + 1):
        page_url = f"{base_url}?page={page}"
        log.info("  Fetching page %d: %s", page, page_url)

        resp = fetch_with_retry(page_url, session)
        if not resp or resp.status_code != 200:
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("div.card, table tbody tr, div.law-item")

        for item in items:
            link = item.select_one("a[href]") if hasattr(item, 'select_one') else None
            if not link:
                continue

            href = link.get("href", "")
            title = link.get_text(strip=True)

            if not href or not title:
                continue

            meta = parse_title_to_meta(title, href)
            pdf_el = item.select_one("a[href$='.pdf']") if hasattr(item, 'select_one') else None
            pdf_link = pdf_el.get("href", "") if pdf_el else ""

            full_url = urljoin(page_url, href)
            if pdf_link and not pdf_link.startswith("http"):
                pdf_link = urljoin(domain["base_url"], pdf_link)

            yield {
                "title": title,
                "detail_url": full_url,
                "pdf_url": pdf_link,
                **meta
            }

        next_link = soup.select_one("a[rel='next'], a.next, a[aria-label='Next']")
        if not next_link:
            break

        time.sleep(1)


def scrape_jdih_generic(session: requests.Session, domain_key: str, reg_type: str = "UU", max_pages: int = 10) -> Iterator[Dict]:
    domain = DOMAINS[domain_key]
    type_path = domain["types"].get(reg_type, {"path": ""})["path"]
    base_url = domain["base_url"]
    base_list_url = f"{base_url}/{type_path}"

    for page in range(1, max_pages + 1):
        if "?" in base_list_url:
            page_url = f"{base_list_url}&page={page}"
        else:
            page_url = f"{base_list_url}/{page}"

        log.info("  Fetching page %d: %s", page, page_url)
        resp = fetch_with_retry(page_url, session)
        if not resp or resp.status_code != 200:
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        items = (soup.select("table tbody tr, div.list-item, div.row-regulasi, ul.list-unstyled li") or
                 soup.select("a[href*='/detail/'], a[href*='/product/']"))

        for item in items:
            link_el = item.select_one("a[href]") if hasattr(item, 'select_one') else item
            if not link_el:
                continue

            href = link_el.get("href", "")
            title = link_el.get_text(strip=True)

            if not href or not title or len(title) < 5:
                continue

            if any(x in href.lower() for x in ["page", "prev", "next", "first", "last"]):
                continue

            meta = parse_title_to_meta(title, href)

            pdf_link = ""
            if hasattr(item, 'select_one'):
                pdf_el = item.select_one("a[href$='.pdf']")
                if pdf_el:
                    pdf_link = pdf_el.get("href", "")

            full_url = urljoin(page_url, href)
            if pdf_link and not pdf_link.startswith("http"):
                pdf_link = urljoin(base_url, pdf_link)

            yield {
                "title": title,
                "detail_url": full_url,
                "pdf_url": pdf_link,
                **meta
            }

        time.sleep(1.5)


# =============================================================================
# PDF Extraction
# =============================================================================

def extract_pdf_text(pdf_url: str, output_path: Path, max_pages: int = 0) -> Tuple[Optional[str], Path]:
    if not pdf_url:
        return None, output_path

    try:
        resp = requests.get(pdf_url, headers=HEADERS, timeout=REQUEST_TIMEOUT, stream=True)
        if resp.status_code != 200:
            log.warning("PDF download failed: HTTP %d for %s", resp.status_code, pdf_url)
            return None, output_path

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(resp.content)
        log.debug("Downloaded PDF: %s -> %s", pdf_url, output_path)
    except Exception as e:
        log.warning("Failed to download PDF %s: %s", pdf_url, e)
        return None, output_path

    try:
        text_parts = []
        with pdfplumber.open(output_path) as pdf:
            pages = pdf.pages[:max_pages] if max_pages > 0 else pdf.pages
            for i, page in enumerate(pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"[Halaman {i}]\n{page_text}")

        full_text = "\n\n".join(text_parts)
        return full_text, output_path
    except Exception as e:
        log.warning("Failed to extract PDF text from %s: %s", output_path, e)
        return None, output_path


# =============================================================================
# Structure Parser (Pasal.id-style regex state machine)
# =============================================================================

BAB_PATTERNS = [
    r"^BAB\s+[IVXLCDM\d]+\s*[-]?\s*(.+)$",
    r"^BAB\s+[IVXLCDM\d]+$",
]
BAGIAN_PATTERNS = [
    r"^Bagian\s+(Ke)?(pertama|kedua|ketiga|keempat|kelima|keenam|ketujuh|kedelapan|kesembilan|kesepuluh)\s*[-]?\s*(.+)?$",
    r"^Bagian\s+[A-Z]\s*[-]?\s*(.+)?$",
]
PARAGRAF_PATTERNS = [
    r"^Paragraf\s+\d+\s*[-]?\s*(.+)?$",
    r"^Paragraf\s+[IVXLCDM]+\s*[-]?\s*(.+)?$",
]
PASAL_PATTERNS = [
    r"^Pasal\s+\d+[A-Z]?\s*[-]?\s*(.+)?$",
    r"^Pasal\s+\d+[A-Z]?$",
]
AYAT_PATTERNS = [
    r"^\(\d+\)\s+(.+)",
    r"^\[\d+\]\s+(.+)",
    r"^\d+\.\s+(.+)",
    r"^[a-z]\)\s+(.+)",
    r"^angka \(\d+\)\s+(.+)",
]
PENJELASAN_UMUM_PATTERNS = [
    r"^PENJELASAN\s+UMUM\s*$",
]
PENJELASAN_PASAL_PATTERNS = [
    r"^PENJELASAN\s+PASAL\s+\d+",
]
ATURAN_PATTERNS = [
    r"^ATURAN\s+PERALIHAN\s*$",
    r"^ATURAN\s+TAMBAHAN\s*$",
    r"^Ketentuan\s+Peralihan\s*$",
]
LAMPIRAN_PATTERNS = [
    r"^LAMPIRAN\s+[IVXLCDM\d]+\s*$",
    r"^Lampiran\s+\d+\s*$",
]


def is_bab_start(line: str) -> bool:
    return any(re.match(p, line, re.IGNORECASE) for p in BAB_PATTERNS)

def is_bagian_start(line: str) -> bool:
    return any(re.match(p, line, re.IGNORECASE) for p in BAGIAN_PATTERNS)

def is_paragraf_start(line: str) -> bool:
    return any(re.match(p, line, re.IGNORECASE) for p in PARAGRAF_PATTERNS)

def is_pasal_start(line: str) -> bool:
    return any(re.match(p, line, re.IGNORECASE) for p in PASAL_PATTERNS)

def is_ayat_start(line: str) -> bool:
    return any(re.match(p, line, re.IGNORECASE) for p in AYAT_PATTERNS)

def is_penjelasan_umum_start(line: str) -> bool:
    return any(re.match(p, line, re.IGNORECASE) for p in PENJELASAN_UMUM_PATTERNS)

def is_penjelasan_pasal_start(line: str) -> bool:
    return any(re.match(p, line, re.IGNORECASE) for p in PENJELASAN_PASAL_PATTERNS)

def is_aturan_start(line: str) -> bool:
    return any(re.match(p, line, re.IGNORECASE) for p in ATURAN_PATTERNS)

def is_lampiran_start(line: str) -> bool:
    return any(re.match(p, line, re.IGNORECASE) for p in LAMPIRAN_PATTERNS)


def parse_regulation_structure(text: str) -> ParsedRegulation:
    regulation = ParsedRegulation(
        meta=RegulationMeta(),
        nodes=[]
    )

    lines = text.split("\n")
    current_bab = None
    current_bagian = None
    current_paragraf = None
    current_pasal = None
    current_ayat = None
    in_preamble = True
    in_penjelasan_umum = False
    in_penjelasan_pasal = False
    in_aturan = False
    bab_counter = 0
    bagian_counter = 0
    paragraf_counter = 0
    pasal_counter = 0
    ayat_counter = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if in_preamble:
            if is_bab_start(line):
                in_preamble = False
            elif is_penjelasan_umum_start(line):
                in_penjelasan_umum = True
                regulation.elucidation_general += line + "\n"
                continue
            elif is_penjelasan_pasal_start(line):
                in_penjelasan_umum = False
                in_penjelasan_pasal = True
                regulation.elucidation_per_pasal += line + "\n"
                continue
            elif is_aturan_start(line):
                regulation.elucidation_per_pasal += f"[ATURAN] {line}\n"
                in_aturan = True
                continue
            else:
                regulation.preamble += line + "\n"
                continue

        if is_bab_start(line):
            bab_counter += 1
            current_bab = {
                "type": "bab",
                "number": bab_counter,
                "heading": line,
                "content": "",
                "children": []
            }
            regulation.nodes.append(current_bab)
            current_bagian = None
            current_paragraf = None
            current_pasal = None
            current_ayat = None
            continue

        if is_bagian_start(line):
            bagian_counter += 1
            current_bagian = {
                "type": "bagian",
                "number": bagian_counter,
                "heading": line,
                "content": "",
                "children": []
            }
            if current_bab is not None:
                current_bab["children"].append(current_bagian)
            else:
                regulation.nodes.append(current_bagian)
            current_paragraf = None
            current_pasal = None
            current_ayat = None
            continue

        if is_paragraf_start(line):
            paragraf_counter += 1
            current_paragraf = {
                "type": "paragraf",
                "number": paragraf_counter,
                "heading": line,
                "content": "",
                "children": []
            }
            target = (current_bagian and current_bagian["children"]) or \
                     (current_bab and current_bab["children"]) or \
                     regulation.nodes
            target.append(current_paragraf)
            current_pasal = None
            current_ayat = None
            continue

        if is_pasal_start(line):
            pasal_counter += 1
            ayat_counter = 0
            current_pasal = {
                "type": "pasal",
                "number": pasal_counter,
                "heading": "",
                "content": line,
                "children": []
            }
            target = (current_paragraf and current_paragraf["children"]) or \
                     (current_bagian and current_bagian["children"]) or \
                     (current_bab and current_bab["children"]) or \
                     regulation.nodes
            target.append(current_pasal)
            current_ayat = None
            continue

        if is_ayat_start(line) and current_pasal is not None:
            ayat_counter += 1
            current_ayat = {
                "type": "ayat",
                "number": ayat_counter,
                "content": line
            }
            current_pasal["children"].append(current_ayat)
            current_pasal["content"] += "\n" + line
            continue

        if is_penjelasan_umum_start(line):
            in_penjelasan_umum = True
            in_penjelasan_pasal = False
            regulation.elucidation_general += line + "\n"
            continue

        if is_penjelasan_pasal_start(line):
            in_penjelasan_pasal = True
            in_penjelasan_umum = False
            regulation.elucidation_per_pasal += line + "\n"
            continue

        if is_aturan_start(line):
            in_aturan = True
            regulation.elucidation_per_pasal += f"[ATURAN] {line}\n"
            continue

        # Append to current context
        if current_ayat is not None:
            current_ayat["content"] += " " + line
            current_pasal["content"] += " " + line
        elif current_pasal is not None:
            current_pasal["content"] += " " + line
        elif current_paragraf is not None:
            current_paragraf["content"] += " " + line
        elif current_bagian is not None:
            current_bagian["content"] += " " + line
        elif current_bab is not None:
            current_bab["content"] += " " + line
        elif in_penjelasan_umum:
            regulation.elucidation_general += line + " "
        elif in_penjelasan_pasal or in_aturan:
            regulation.elucidation_per_pasal += line + " "
        else:
            regulation.preamble += line + " "

    regulation.full_text = build_rag_text(regulation)
    return regulation


def node_to_text(node: Dict, depth: int = 0) -> str:
    indent = "  " * depth
    t = node["type"]

    if t == "bab":
        text = f"BAB {node['number']}"
        if node.get("heading"):
            text += f" -- {node['heading']}"
        text += "\n"
        for child in node.get("children", []):
            text += node_to_text(child, depth + 1)
        return text
    elif t == "bagian":
        text = f"{indent}Bagian {node['number']}"
        if node.get("heading"):
            text += f" -- {node['heading']}"
        text += "\n"
        if node.get("content"):
            text += f"{indent}  {node['content']}\n"
        for child in node.get("children", []):
            text += node_to_text(child, depth + 1)
        return text
    elif t == "paragraf":
        text = f"{indent}Paragraf {node['number']}"
        if node.get("heading"):
            text += f" -- {node['heading']}"
        text += "\n"
        if node.get("content"):
            text += f"{indent}  {node['content']}\n"
        for child in node.get("children", []):
            text += node_to_text(child, depth + 1)
        return text
    elif t == "pasal":
        text = f"{indent}Pasal {node['number']}\n"
        if node.get("content"):
            text += f"{indent}  {node['content']}\n"
        for child in node.get("children", []):
            text += node_to_text(child, depth + 1)
        return text
    elif t == "ayat":
        return f"{indent}({node['number']}) {node.get('content', '')}\n"
    return ""


def build_rag_text(regulation: ParsedRegulation) -> str:
    parts = []
    if regulation.preamble:
        parts.append(f"PRAMBUEL\n{regulation.preamble}")
    for node in regulation.nodes:
        parts.append(node_to_text(node, 0))
    if regulation.elucidation_general:
        parts.append(f"PENJELASAN UMUM\n{regulation.elucidation_general}")
    if regulation.elucidation_per_pasal:
        parts.append(f"PENJELASAN\n{regulation.elucidation_per_pasal}")
    return "\n\n".join(parts)


# =============================================================================
# ChromaDB Exporter
# =============================================================================

def export_to_chroma(regulation: ParsedRegulation, chroma_batch: List, chroma_ids: List):
    doc = regulation.to_rag_document()
    text = doc["text"]
    chunk_size = 512
    overlap = 64

    words = text.split()
    for i in range(0, len(words), max(1, chunk_size - overlap)):
        chunk_words = words[i:i + chunk_size]
        if len(chunk_words) < 10:
            continue
        chunk = " ".join(chunk_words)
        chunk_id = f"{regulation.meta.frbr_uri.replace('/', '_')}_{i // max(1, chunk_size - overlap)}"

        chroma_batch.append({
            "text": chunk,
            "metadata": {
                **doc["metadata"],
                "chunk_index": i // max(1, chunk_size - overlap),
                "chunk_id": chunk_id,
            }
        })
        chroma_ids.append(chunk_id)


def flush_batch(chroma_batch: List, chroma_ids: List, chroma_dir: Path):
    if not chroma_batch:
        return

    try:
        import chromadb
        from sentence_transformers import SentenceTransformer

        client = chromadb.PersistentClient(path=str(chroma_dir))
        col = client.get_or_create_collection(
            name="indonesian_regulations_pasal",
            metadata={"description": "Indonesian regulations from JDIH sources"}
        )

        embedder = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

        texts = [d["text"] for d in chroma_batch]
        embeddings = embedder.encode(texts, show_progress_bar=False).tolist()
        metadatas = [d["metadata"] for d in chroma_batch]

        col.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=chroma_ids
        )
        log.info("Flushed %d documents to ChromaDB", len(chroma_batch))
    except ImportError:
        log.warning("ChromaDB or sentence-transformers not installed. Skipping ChromaDB export.")
        log.info("Install with: pip install chromadb sentence-transformers")
    except Exception as e:
        log.error("Failed to flush batch to ChromaDB: %s", e)

    chroma_batch.clear()
    chroma_ids.clear()


# =============================================================================
# Main Scraper Class
# =============================================================================

SCRAPER_FNS = {
    "peraturan": scrape_peraturan_list,
    "bpk": scrape_bpk_list,
    "jdih_kemenkeu": lambda *a, **k: scrape_jdih_generic(*a, domain_key="jdih_kemenkeu", **k),
    "jdih_kemendagri": lambda *a, **k: scrape_jdih_generic(*a, domain_key="jdih_kemendagri", **k),
    "jdih_kemnaker": lambda *a, **k: scrape_jdih_generic(*a, domain_key="jdih_kemnaker", **k),
    "jdih_esdm": lambda *a, **k: scrape_jdih_generic(*a, domain_key="jdih_esdm", **k),
    "jdih_setneg": lambda *a, **k: scrape_jdih_generic(*a, domain_key="jdih_setneg", **k),
}


class RegulationScraper:
    def __init__(self, domain: str = "peraturan", reg_type: str = "all",
                 max_pages: int = 10, max_pdfs: int = 0):
        self.domain = domain
        self.reg_type = reg_type
        self.max_pages = max_pages
        self.max_pdfs = max_pdfs
        self.stats = defaultdict(int)

        for d in [RAW_DIR, PARSED_DIR, CHROMA_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    def run_list_only(self) -> List[Dict]:
        domains_to_scrape = [self.domain] if self.domain != "all" else list(DOMAINS.keys())
        all_results = []

        for dk in domains_to_scrape:
            if dk not in DOMAINS:
                log.warning("Unknown domain: %s", dk)
                continue

            log.info("=== Scraping domain: %s ===", dk)
            session = get_session(dk)
            scraper_fn = SCRAPER_FNS.get(dk)
            if not scraper_fn:
                continue

            types = list(DOMAINS[dk]["types"].keys()) if self.reg_type == "all" else [self.reg_type]

            for rt in types:
                log.info("-- Regulation type: %s --", rt)
                try:
                    for item in scraper_fn(session, rt, self.max_pages):
                        item["domain"] = dk
                        item["reg_type"] = rt
                        all_results.append(item)
                        self.stats[f"{dk}_{rt}"] += 1
                except Exception as e:
                    log.error("Error scraping %s/%s: %s", dk, rt, e)

        output_file = PARSED_DIR / f"listings_{self.domain}_{self.reg_type}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        log.info("Saved %d listings to %s", len(all_results), output_file)
        return all_results

    def run_full(self) -> Dict:
        listings = self.run_list_only()

        chroma_batch = []
        chroma_ids = []

        for item in tqdm(listings, desc="Processing PDFs"):
            pdf_url = item.get("pdf_url", "")
            if not pdf_url:
                continue

            if self.max_pdfs > 0 and self.stats["pdfs_processed"] >= self.max_pdfs:
                break

            filename = urlparse(pdf_url).path.split("/")[-1] or f"{item.get('frbr_uri', 'unknown').replace('/', '_')}.pdf"
            output_path = RAW_DIR / item.get("domain", "unknown") / filename

            text, pdf_path = extract_pdf_text(pdf_url, output_path)

            if not text:
                self.stats["pdf_failed"] += 1
                continue

            self.stats["pdf_downloaded"] += 1

            meta = RegulationMeta(
                frbr_uri=item.get("frbr_uri", ""),
                type=item.get("type", ""),
                number=item.get("number", ""),
                year=item.get("year", 0),
                title_id=item.get("title_id", ""),
                source_url=item.get("detail_url", ""),
                source_domain=item.get("domain", ""),
                pdf_url=pdf_url,
            )

            parsed = ParsedRegulation(
                meta=meta,
                full_text=text,
                preamble=text[:500],
                nodes=[]
            )

            # Save Pasal-format JSON
            parsed_output = PARSED_DIR / f"{meta.frbr_uri.replace('/', '_')}.json"
            try:
                with open(parsed_output, "w", encoding="utf-8") as f:
                    json.dump(parsed.to_pasal_json(), f, ensure_ascii=False, indent=2)
            except Exception as e:
                log.warning("Failed to save parsed JSON: %s", e)

            # Export to ChromaDB
            export_to_chroma(parsed, chroma_batch, chroma_ids)
            if len(chroma_batch) >= 100:
                flush_batch(chroma_batch, chroma_ids, CHROMA_DIR)

            self.stats["pdfs_processed"] += 1

        if chroma_batch:
            flush_batch(chroma_batch, chroma_ids, CHROMA_DIR)

        log.info("=== COMPLETE ===")
        for k, v in self.stats.items():
            log.info("  %s: %d", k, v)

        return dict(self.stats)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Pasal.id-based Indonesian regulation scraper for Arsitrad",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m scraper.pasal_scraper --domain peraturan --type UU --max-pages 5 --list-only
  python -m scraper.pasal_scraper --domain all --type all --max-pages 10 --list-only
  python -m scraper.pasal_scraper --domain peraturan --type UU --max-pages 5 --max-pdfs 20

Domains: peraturan, bpk, jdih_kemenkeu, jdih_kemendagri, jdih_kemnaker, jdih_esdm, jdih_setneg
Types:   UUD, UU, PP, PERPRES, PERMEN, PERDA (or 'all')
        """
    )
    parser.add_argument("--domain", "-d", default="peraturan")
    parser.add_argument("--type", "-t", default="UU")
    parser.add_argument("--max-pages", "-p", type=int, default=5)
    parser.add_argument("--max-pdfs", type=int, default=0)
    parser.add_argument("--list-only", action="store_true")
    parser.add_argument("--domain-list", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.domain_list:
        print("Available domains:")
        for k, v in DOMAINS.items():
            types = list(v["types"].keys())
            print(f"  {k:20s} -- {v['base_url']}")
            print(f"    Types: {', '.join(types)}")
        return

    scraper = RegulationScraper(
        domain=args.domain,
        reg_type=args.type,
        max_pages=args.max_pages,
        max_pdfs=args.max_pdfs,
    )

    if args.list_only or args.max_pdfs == 0:
        results = scraper.run_list_only()
        print(f"\nTotal items found: {len(results)}")
    else:
        stats = scraper.run_full()
        print(f"\nStats: {stats}")


if __name__ == "__main__":
    main()
