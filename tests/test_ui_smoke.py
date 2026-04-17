from ui.app import build_confidence_label, load_ui_settings


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
