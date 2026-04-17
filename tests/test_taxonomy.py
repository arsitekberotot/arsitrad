from pipeline.taxonomy import infer_building_use


def test_infer_building_use_does_not_treat_generic_kegiatan_usaha_as_commercial():
    text = "Kebutuhan kegiatan usaha telah dipertimbangkan dalam verifikasi penyelenggaraan SPAM."

    assert infer_building_use(text) is None


def test_infer_building_use_keeps_precise_fungsi_usaha_phrase_as_commercial():
    text = "Bangunan Gedung fungsi usaha mempunyai fungsi utama sebagai tempat melakukan kegiatan usaha."

    assert infer_building_use(text) == "commercial"
