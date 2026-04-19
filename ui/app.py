from __future__ import annotations

"""Streamlit UI for Arsitrad v2."""

import html
import os
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


def inject_base_css() -> None:
    if st is None:
        return
    st.markdown(
        """
        <style>
        .arsitrad-card {
            background: #0f172a;
            color: #e2e8f0;
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 18px 20px;
            margin-bottom: 12px;
            white-space: pre-wrap;
            line-height: 1.55;
            font-size: 0.97rem;
        }
        .arsitrad-meta {
            color: #94a3b8;
            font-size: 0.88rem;
            margin-bottom: 10px;
        }
        .arsitrad-disclaimer {
            border-left: 4px solid #f59e0b;
            background: rgba(245, 158, 11, 0.08);
            padding: 12px 14px;
            border-radius: 10px;
            color: #e2e8f0;
            margin-bottom: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
    confidence_label = build_confidence_label(result.retrieval.confidence)
    meta = (
        f"Confidence: {result.retrieval.confidence:.2f} ({confidence_label})"
        f" · Mode: {'GGUF' if result.used_model else 'Fallback'}"
        f" · Query: {html.escape(result.retrieval.standalone_query)}"
    )
    st.markdown(f"<div class='arsitrad-meta'>{meta}</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='arsitrad-card'>{html.escape(result.answer)}</div>",
        unsafe_allow_html=True,
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
                "content": "Tanyakan regulasi bangunan, PBG, KDB/KDH, RDTR, RTRW, atau standar SNI yang kamu butuhkan.",
            }
        ]

    for message in st.session_state["arsitrad_messages"]:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                st.markdown(
                    f"<div class='arsitrad-card'>{html.escape(message['content'])}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(message["content"])

    prompt = st.chat_input(settings["default_question"])
    if prompt:
        st.session_state["arsitrad_messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Mencari regulasi terbaik..."):
                history = st.session_state["arsitrad_messages"][:-1]
                result = engine.answer(prompt, history=history)
                render_inference_result(result)
                st.session_state["arsitrad_messages"].append(
                    {
                        "role": "assistant",
                        "content": result.answer,
                        "confidence": result.retrieval.confidence,
                        "used_model": result.used_model,
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

    st.title(settings["app_title"])
    st.caption("Semantic chunking · E5 embeddings · pgvector hybrid retrieval · GGUF Gemma 4")

    with st.sidebar:
        st.markdown("### Status")
        st.write("Confidence tinggi >= 0.75")
        st.write("Confidence sedang >= 0.60")
        st.write("Confidence rendah < 0.60")
        st.markdown("### Disclaimer")
        st.info(settings["disclaimer"])

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
