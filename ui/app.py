from __future__ import annotations

# Streamlit UI for Arsitrad v2.

import html
import os
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import yaml

try:  # pragma: no cover - import guard for environments without streamlit
    import streamlit as st
except Exception:  # pragma: no cover
    st = None

from pipeline.inference import ArsitradAnswerEngine, InferenceResult

try:
    from agent.cooling import PassiveCoolingAdvisor
    from agent.disaster import DisasterDamageReporter
    from agent.permit import BuildingPermitNavigator
    from agent.settlement import SettlementUpgradingAdvisor
except Exception:  # pragma: no cover - optional imports for lightweight environments
    PassiveCoolingAdvisor = None
    DisasterDamageReporter = None
    BuildingPermitNavigator = None
    SettlementUpgradingAdvisor = None


DEFAULT_CONFIG_PATH = REPO_ROOT / "config.yaml"


def load_ui_settings(config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    v2 = config.get("v2", {})
    ui_settings = v2.get("ui", {})
    return {
        "app_title": ui_settings.get("app_title", "Arsitrad v2"),
        "disclaimer": ui_settings.get(
            "disclaimer",
            "Arsitrad adalah alat bantu informasi regulasi, bukan pengganti konsultasi profesional.",
        ),
        "default_question": ui_settings.get(
            "default_question", "Apa syarat PBG untuk rumah tinggal 2 lantai di Semarang?"
        ),
    }


def build_confidence_label(score: float) -> str:
    if score >= 0.75:
        return "Tinggi"
    if score >= 0.60:
        return "Sedang"
    return "Rendah"


def build_shell_header(app_title: str) -> str:
    safe_title = html.escape(app_title)
    return (
        "<div class='arsitrad-shell'>"
        "<div class='arsitrad-kicker'>Indonesian building-regulation copilot</div>"
        "<div class='arsitrad-title-row'>"
        f"<h1>{safe_title}</h1>"
        "<div class='arsitrad-badge'>Hybrid retrieval · GGUF-ready · 5 workflows</div>"
        "</div>"
        "<p class='arsitrad-subtitle'>"
        "Tanya regulasi PBG, RDTR, RTRW, aksesibilitas, proteksi kebakaran, dan kepemilikan bangunan dengan jawaban yang lebih rapi, tegas, dan bisa dilacak ke sumbernya."
        "</p>"
        "<div class='arsitrad-pill-row'>"
        "<span class='arsitrad-pill'>Regulatory QA</span>"
        "<span class='arsitrad-pill arsitrad-pill-soft'>Permit guidance</span>"
        "<span class='arsitrad-pill arsitrad-pill-soft'>Cooling · Disaster · Settlement</span>"
        "</div>"
        "</div>"
    )


SECTION_ORDER = ("RINGKASAN", "DETAIL REGULASI", "SARAN TEKNIS", "SUMBER")


def build_base_css() -> str:
    return """
        <style>
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.10), transparent 30%),
                radial-gradient(circle at top right, rgba(168, 85, 247, 0.08), transparent 24%),
                linear-gradient(180deg, #f8fafc 0%, #eff6ff 52%, #eef2ff 100%);
        }
        .stApp {
            background: transparent;
            color: #0f172a;
        }
        [data-testid="stHeader"] {
            background: transparent;
        }
        [data-testid="stToolbar"],
        [data-testid="stAppDeployButton"],
        [data-testid="stMainMenu"] {
            display: none;
        }
        [data-testid="stMainBlockContainer"] {
            max-width: 1120px;
            padding-top: 2.25rem;
            padding-bottom: 7rem;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(239, 246, 255, 0.92));
            border-right: 1px solid rgba(148, 163, 184, 0.34);
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] label {
            color: #1e293b !important;
        }
        [data-testid="stSidebar"] [data-testid="stAlert"] {
            background: rgba(255, 255, 255, 0.84);
            border: 1px solid rgba(37, 99, 235, 0.18);
            color: #1e293b;
        }
        .arsitrad-shell {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(239, 246, 255, 0.88));
            border: 1px solid rgba(96, 165, 250, 0.20);
            border-radius: 28px;
            padding: 24px 26px 22px 26px;
            margin: 0 0 18px 0;
            box-shadow: 0 28px 70px rgba(30, 64, 175, 0.14);
            backdrop-filter: blur(16px);
        }
        .arsitrad-kicker {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            border-radius: 999px;
            border: 1px solid rgba(37, 99, 235, 0.22);
            background: rgba(219, 234, 254, 0.76);
            color: #1d4ed8;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 14px;
        }
        .arsitrad-title-row {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 16px;
            flex-wrap: wrap;
        }
        .arsitrad-title-row h1 {
            margin: 0;
            font-size: clamp(2rem, 3vw, 2.7rem);
            line-height: 1.05;
            color: #0f172a;
        }
        .arsitrad-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            border-radius: 999px;
            padding: 8px 14px;
            background: rgba(255, 255, 255, 0.86);
            border: 1px solid rgba(148, 163, 184, 0.28);
            color: #334155;
            font-size: 0.82rem;
            font-weight: 600;
        }
        .arsitrad-subtitle {
            margin: 12px 0 0 0;
            color: #475569;
            line-height: 1.7;
            max-width: 820px;
            font-size: 1rem;
        }
        .arsitrad-pill-row,
        .arsitrad-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        .arsitrad-pill-row {
            margin: 16px 0 0 0;
        }
        .arsitrad-pill,
        .arsitrad-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border-radius: 999px;
            padding: 7px 12px;
            font-size: 0.82rem;
            border: 1px solid rgba(148, 163, 184, 0.28);
            background: rgba(255, 255, 255, 0.84);
            color: #1e40af;
        }
        .arsitrad-pill-soft,
        .arsitrad-chip-soft {
            background: rgba(239, 246, 255, 0.86);
            color: #334155;
        }
        .arsitrad-hero {
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(248, 250, 252, 0.88));
            border: 1px solid rgba(148, 163, 184, 0.30);
            border-radius: 22px;
            padding: 20px 22px;
            color: #1e293b;
            margin: 0 0 16px 0;
            box-shadow: 0 20px 52px rgba(30, 64, 175, 0.12);
        }
        .arsitrad-hero h3 {
            margin: 0 0 8px 0;
            font-size: 1.08rem;
            color: #0f172a;
        }
        .arsitrad-hero p {
            margin: 0;
            color: #475569;
            line-height: 1.65;
        }
        .arsitrad-section-label {
            margin: 8px 0 8px 2px;
            color: #2563eb;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }
        [data-testid="stTabs"] {
            margin-top: 0.15rem;
        }
        [data-testid="stTabs"] [role="tablist"] {
            gap: 0.45rem;
            padding: 0.3rem;
            border-radius: 18px;
            border: 1px solid rgba(148, 163, 184, 0.32);
            background: rgba(255, 255, 255, 0.68);
        }
        [data-testid="stTabs"] [role="tab"] {
            height: 42px;
            padding: 0 16px;
            border-radius: 12px;
            color: #475569;
            background: transparent;
            border: none;
        }
        [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, rgba(37, 99, 235, 0.94), rgba(59, 130, 246, 0.86));
            color: #ffffff;
            box-shadow: 0 10px 24px rgba(37, 99, 235, 0.22);
        }
        .arsitrad-card {
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.92));
            color: #1e293b;
            border: 1px solid rgba(148, 163, 184, 0.34);
            border-radius: 20px;
            padding: 18px 20px;
            margin-bottom: 14px;
            white-space: pre-wrap;
            line-height: 1.6;
            font-size: 0.97rem;
            box-shadow: 0 16px 40px rgba(30, 64, 175, 0.10);
        }
        .arsitrad-card-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 10px;
            font-weight: 700;
            font-size: 0.95rem;
            letter-spacing: 0.02em;
            color: #0f172a;
        }
        .arsitrad-card-body {
            color: #334155;
            white-space: pre-wrap;
            line-height: 1.7;
        }
        .arsitrad-meta {
            color: #64748b;
            font-size: 0.87rem;
            margin: 0 0 12px 2px;
            line-height: 1.5;
        }
        .arsitrad-disclaimer {
            background: rgba(254, 243, 199, 0.88);
            border: 1px solid rgba(245, 158, 11, 0.30);
            padding: 13px 14px;
            border-radius: 14px;
            color: #78350f;
            margin-bottom: 16px;
        }
        [data-testid="stChatMessage"] {
            background: transparent;
        }
        [data-testid="stChatInput"] {
            position: sticky;
            bottom: 1rem;
            background: rgba(255, 255, 255, 0.94);
            border: 1px solid rgba(148, 163, 184, 0.40);
            border-radius: 18px;
            padding: 0.35rem 0.5rem;
            box-shadow: 0 20px 44px rgba(30, 64, 175, 0.16);
            backdrop-filter: blur(16px);
        }
        [data-testid="stChatInput"] textarea {
            color: #0f172a !important;
        }
        [data-testid="stChatInput"] textarea::placeholder {
            color: #64748b !important;
        }
        [data-testid="stChatInputSubmitButton"] {
            border-radius: 12px;
            background: linear-gradient(135deg, rgba(37, 99, 235, 0.95), rgba(59, 130, 246, 0.86));
        }
        @media (max-width: 900px) {
            [data-testid="stMainBlockContainer"] {
                padding-top: 1.4rem;
            }
            .arsitrad-shell {
                padding: 20px 18px;
            }
        }
        </style>
    """

def inject_base_css() -> None:
    if st is None:
        return
    st.markdown(build_base_css(), unsafe_allow_html=True)


def clean_answer_text(text: str) -> str:
    cleaned = (text or "").replace("\r\n", "\n").strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
        cleaned = cleaned[1:-1].strip()
    cleaned = cleaned.replace("\n\n\n", "\n\n")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def normalize_section_heading(line: str) -> str | None:
    normalized = re.sub(r"^\d+\.\s*", "", line.strip().upper())
    return normalized if normalized in SECTION_ORDER else None


def split_answer_sections(text: str) -> tuple[str, dict[str, str]]:
    cleaned = clean_answer_text(text)
    sections: dict[str, list[str]] = {}
    current_key: str | None = None

    for raw_line in cleaned.splitlines():
        heading = normalize_section_heading(raw_line)
        if heading:
            current_key = heading
            sections.setdefault(current_key, [])
            continue
        if current_key is None:
            continue
        sections[current_key].append(raw_line)

    normalized_sections = {
        key: "\n".join(lines).strip()
        for key, lines in sections.items()
        if "\n".join(lines).strip()
    }
    return cleaned, normalized_sections


def _htmlize_body(text: str) -> str:
    return html.escape(text).replace("\n", "<br>")


def render_text_card(title: str, body: str, badge: str | None = None) -> None:
    if st is None or not body.strip():
        return
    badge_html = f"<span class='arsitrad-chip arsitrad-chip-soft'>{html.escape(badge)}</span>" if badge else ""
    st.markdown(
        (
            "<div class='arsitrad-card'>"
            f"<div class='arsitrad-card-title'><span>{html.escape(title)}</span>{badge_html}</div>"
            f"<div class='arsitrad-card-body'>{_htmlize_body(body)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_assistant_message(message: dict[str, Any]) -> None:
    if st is None:
        return

    cleaned, sections = split_answer_sections(str(message.get("content", "")))
    confidence = message.get("confidence")
    confidence_label = build_confidence_label(float(confidence)) if confidence is not None else None
    mode = "GGUF" if message.get("used_model") else "Fallback"
    query = str(message.get("standalone_query", "")).strip()

    chips: list[str] = []
    if confidence is not None and confidence_label is not None:
        chips.append(f"<span class='arsitrad-chip'>Confidence {float(confidence):.2f} · {confidence_label}</span>")
    if message.get("used_model") is not None:
        chips.append(f"<span class='arsitrad-chip arsitrad-chip-soft'>Mode {html.escape(mode)}</span>")
    if chips:
        st.markdown(f"<div class='arsitrad-chip-row'>{''.join(chips)}</div>", unsafe_allow_html=True)
    if query:
        st.markdown(f"<div class='arsitrad-meta'>Standalone query: {html.escape(query)}</div>", unsafe_allow_html=True)

    if sections:
        for heading in SECTION_ORDER:
            body = sections.get(heading)
            if body:
                render_text_card(heading.title(), body)
    else:
        render_text_card("Jawaban", cleaned)



def _build_answer_engine(config_path: str | Path = DEFAULT_CONFIG_PATH) -> ArsitradAnswerEngine:
    return ArsitradAnswerEngine(config_path=config_path)


if st is not None:  # pragma: no branch
    @st.cache_resource(show_spinner=False)
    def get_answer_engine(config_path: str | Path = DEFAULT_CONFIG_PATH) -> ArsitradAnswerEngine:
        return _build_answer_engine(config_path)
else:
    def get_answer_engine(config_path: str | Path = DEFAULT_CONFIG_PATH) -> ArsitradAnswerEngine:
        return _build_answer_engine(config_path)


def render_inference_result(result: InferenceResult) -> None:
    if st is None:
        return
    render_assistant_message(
        {
            "content": result.answer,
            "confidence": result.retrieval.confidence,
            "used_model": result.used_model,
            "standalone_query": result.retrieval.standalone_query,
        }
    )


def render_regulation_tab(config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
    if st is None:
        return
    settings = load_ui_settings(config_path)
    engine = get_answer_engine(config_path)
    st.markdown(f"<div class='arsitrad-disclaimer'>{html.escape(settings['disclaimer'])}</div>", unsafe_allow_html=True)

    if "arsitrad_messages" not in st.session_state:
        st.session_state["arsitrad_messages"] = [
            {
                "role": "assistant",
                "content": "Tanyakan regulasi bangunan, PBG, KDB/KDH, RDTR, RTRW, aksesibilitas, proteksi kebakaran, atau SBKBG yang kamu butuhkan.",
            }
        ]

    for message in st.session_state["arsitrad_messages"]:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                render_assistant_message(message)
            else:
                render_text_card("Pertanyaan", str(message["content"]))

    prompt = st.chat_input(settings["default_question"])
    if prompt:
        st.session_state["arsitrad_messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            render_text_card("Pertanyaan", prompt)

        with st.chat_message("assistant"):
            with st.spinner("Mencari regulasi terbaik..."):
                history = st.session_state["arsitrad_messages"][:-1]
                result = engine.answer(prompt, history=history)
                render_inference_result(result)
                st.session_state["arsitrad_messages"].append(
                    {
                        "role": "assistant",
                        "content": clean_answer_text(result.answer),
                        "confidence": result.retrieval.confidence,
                        "used_model": result.used_model,
                        "standalone_query": result.retrieval.standalone_query,
                    }
                )


def render_permit_tab() -> None:
    if st is None:
        return
    st.subheader("Permit Navigator")
    if BuildingPermitNavigator is None:
        st.warning("Modul permit tidak tersedia di environment ini.")
        return
    navigator = BuildingPermitNavigator()
    with st.form("permit-form"):
        building_type = st.selectbox("Tipe bangunan", ["rumah_tinggal", "apartemen", "gedung_komersial", "gedung_industri", "fasilitas_umum"])
        location = st.text_input("Lokasi", "Semarang")
        floor_area = st.number_input("Luas lantai (m²)", min_value=1.0, value=120.0)
        land_area = st.number_input("Luas tanah (m²)", min_value=1.0, value=150.0)
        height = st.number_input("Tinggi bangunan (m)", min_value=0.0, value=8.0)
        building_function = st.selectbox("Fungsi bangunan", ["hunian", "usaha", "campuran"])
        submitted = st.form_submit_button("Generate panduan")
    if submitted:
        guidance = navigator.navigate(building_type, location, floor_area, land_area, height, building_function)
        guidance["location"] = location
        st.text(navigator.format_navigation(guidance))


def render_cooling_tab() -> None:
    if st is None:
        return
    st.subheader("Passive Cooling Advisor")
    if PassiveCoolingAdvisor is None:
        st.warning("Modul passive cooling tidak tersedia di environment ini.")
        return
    advisor = PassiveCoolingAdvisor()
    with st.form("cooling-form"):
        col1, col2 = st.columns(2)
        with col1:
            length = st.number_input("Panjang (m)", min_value=1.0, value=8.0)
            width = st.number_input("Lebar (m)", min_value=1.0, value=10.0)
            height = st.number_input("Tinggi (m)", min_value=1.0, value=3.5)
        with col2:
            floors = st.number_input("Jumlah lantai", min_value=1, value=1)
            orientation = st.selectbox("Orientasi", ["utara", "selatan", "timur", "barat"])
            climate_zone = st.selectbox("Zona iklim", ["dataran_rendah_pesisir", "dataran_tinggi", "tropical_basah", "tropical_kering"])
        wall_material = st.selectbox("Material dinding", ["bata", "beton", "kayu", "batako", "hebel"])
        roof_material = st.selectbox("Material atap", ["genteng", "metal", "beton"])
        budget = st.number_input("Budget (IDR)", min_value=0.0, value=5000000.0)
        submitted = st.form_submit_button("Generate saran")
    if submitted:
        advice = advisor.advise(
            dimensions={"length_m": length, "width_m": width, "height_m": height, "floor_count": int(floors)},
            orientation=orientation,
            materials={"wall_material": wall_material, "roof_material": roof_material},
            climate_zone=climate_zone,
            budget_idr=budget,
        )
        st.text(advisor.format_advice(advice))


def render_disaster_tab() -> None:
    if st is None:
        return
    st.subheader("Disaster Damage Reporter")
    if DisasterDamageReporter is None:
        st.warning("Modul disaster tidak tersedia di environment ini.")
        return
    reporter = DisasterDamageReporter()
    with st.form("disaster-form"):
        location = st.text_input("Lokasi", "Semarang")
        disaster_type = st.selectbox("Tipe bencana", ["gempa", "banjir", "tsunami", "longsor", "puting_beliung", "kebakaran"])
        building_type = st.selectbox("Tipe bangunan", ["rumah_tinggal", "gedung_perkantoran", "sekolah", "pasar", "lainnya"])
        damage_description = st.text_area("Deskripsi kerusakan", "Dinding retak diagonal dan atap bergeser")
        floor_area = st.number_input("Luas lantai (m²)", min_value=0.0, value=60.0)
        submitted = st.form_submit_button("Generate laporan")
    if submitted:
        report = reporter.report(location, disaster_type, building_type, damage_description, floor_area)
        st.text(reporter.format_report(report))


def render_settlement_tab() -> None:
    if st is None:
        return
    st.subheader("Settlement Upgrading Advisor")
    if SettlementUpgradingAdvisor is None:
        st.warning("Modul settlement tidak tersedia di environment ini.")
        return
    advisor = SettlementUpgradingAdvisor()
    with st.form("settlement-form"):
        location = st.text_input("Lokasi permukiman", "Semarang")
        density = st.number_input("Kepadatan penduduk (orang/ha)", min_value=1.0, value=500.0)
        infrastructure = st.text_area("Infrastruktur saat ini", "jalan sempit, drainase buruk, air sumur, listrik tersedia")
        budget = st.number_input("Budget (IDR)", min_value=1.0, value=500000000.0)
        goals = st.multiselect("Prioritas", ["sanitasi", "air bersih", "jalan akses", "drainase", "proteksi kebakaran"])
        submitted = st.form_submit_button("Generate rekomendasi")
    if submitted:
        advice = advisor.advise(location, density, infrastructure, budget, goals)
        st.text(advisor.format_advice(advice))


def main(config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
    if st is None:
        raise RuntimeError("streamlit belum terpasang. Install dependency lalu jalankan ulang.")

    settings = load_ui_settings(config_path)
    st.set_page_config(page_title=settings["app_title"], layout="wide")
    inject_base_css()

    st.markdown(build_shell_header(settings["app_title"]), unsafe_allow_html=True)
    st.markdown(
        """
        <div class='arsitrad-hero'>
            <h3>Regulatory copilot, not a guess machine</h3>
            <p>
                Arsitrad dipoles untuk kerja yang lebih enak dilihat: struktur jawaban jelas, percakapan lebih fokus,
                dan workflow cepat pindah dari QA regulasi ke permit, passive cooling, disaster, atau settlement.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### Status")
        st.write("Confidence tinggi >= 0.75")
        st.write("Confidence sedang >= 0.60")
        st.write("Confidence rendah < 0.60")
        st.markdown("### Cara pakai")
        st.write("• Mulai dari pertanyaan regulasi yang spesifik")
        st.write("• Sebut kota/daerah kalau konteksnya lokal")
        st.write("• Verifikasi kutipan sebelum dipakai buat keputusan desain")
        st.markdown("### Disclaimer")
        st.info(settings["disclaimer"])

    st.markdown("<div class='arsitrad-section-label'>Workflow</div>", unsafe_allow_html=True)
    regulation_tab, permit_tab, cooling_tab, disaster_tab, settlement_tab = st.tabs(
        [
            "Regulation QA",
            "Permit Navigator",
            "Passive Cooling",
            "Disaster Reporter",
            "Settlement Upgrading",
        ]
    )

    with regulation_tab:
        render_regulation_tab(config_path=config_path)
    with permit_tab:
        render_permit_tab()
    with cooling_tab:
        render_cooling_tab()
    with disaster_tab:
        render_disaster_tab()
    with settlement_tab:
        render_settlement_tab()


if __name__ == "__main__":  # pragma: no cover
    main()
