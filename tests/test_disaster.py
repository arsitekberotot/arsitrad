from agent.disaster import DisasterDamageReporter, classify_disaster_damage


def test_classify_disaster_damage_returns_damage_key():
    result = classify_disaster_damage(
        "gempa",
        "Dinding retak diagonal, atap bergeser, dan lantai tidak rata.",
    )

    assert result["damage_key"] == "rusak_sedang"
    assert result["repair_priority"] == 2



def test_disaster_report_uses_classification_key_for_recommendations():
    reporter = DisasterDamageReporter()
    report = reporter.report(
        "Semarang",
        "gempa",
        "rumah_tinggal",
        "Dinding retak diagonal, atap bergeser, dan lantai tidak rata.",
        60,
        [],
    )

    assert report["damage_classification"] == "rusak_sedang"
    assert report["repair_priority"] == 2
    assert report["recommendations"][0]["action"] == "Evaluasi struktural oleh ahli sipil"
    assert report["total_estimated_cost_idr"] == 1800000
