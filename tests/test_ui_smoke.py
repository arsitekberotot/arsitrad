from ui.app import (
    build_confidence_label,
    clean_answer_text,
    load_ui_settings,
    split_answer_sections,
)


def test_build_confidence_label_bands():
    assert build_confidence_label(0.9) == "Tinggi"
    assert build_confidence_label(0.65) == "Sedang"
    assert build_confidence_label(0.4) == "Rendah"


def test_load_ui_settings_reads_v2_defaults(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(
        """
        v2:
          ui:
            app_title: "Arsitrad v2"
            disclaimer: "Legal advisory only"
            default_question: "Apa itu PBG?"
        """,
        encoding="utf-8",
    )

    settings = load_ui_settings(config)
    assert settings["app_title"] == "Arsitrad v2"
    assert settings["disclaimer"] == "Legal advisory only"
    assert settings["default_question"] == "Apa itu PBG?"


def test_clean_answer_text_strips_wrapping_quotes_and_blank_runs():
    raw = '"RINGKASAN\n\nHalo\n\n\nDETAIL REGULASI\n\nIsi"'
    cleaned = clean_answer_text(raw)

    assert cleaned.startswith("RINGKASAN")
    assert cleaned.endswith("Isi")
    assert '"' not in cleaned
    assert "\n\n\n" not in cleaned


def test_split_answer_sections_parses_numbered_headings():
    cleaned, sections = split_answer_sections(
        '"1. RINGKASAN\nRingkas.\n\nDETAIL REGULASI\nDetail.\n\nSARAN TEKNIS\nSaran.\n\nSUMBER\n[1] Permen"'
    )

    assert cleaned.startswith("1. RINGKASAN")
    assert sections["RINGKASAN"] == "Ringkas."
    assert sections["DETAIL REGULASI"] == "Detail."
    assert sections["SARAN TEKNIS"] == "Saran."
    assert sections["SUMBER"] == "[1] Permen"
