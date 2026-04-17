import json

from pipeline.eval.ragas_eval import EvalSample, export_results, load_golden_queries


def test_load_golden_queries_reads_json(tmp_path):
    questions_path = tmp_path / "golden_queries.json"
    questions_path.write_text(
        json.dumps(
            [
                {
                    "question": "Apa syarat PBG rumah tinggal?",
                    "ground_truth": "PBG memerlukan dokumen administratif dan teknis.",
                    "reference_contexts": ["PP 16/2021 Pasal 15"],
                    "metadata": {"region": "nasional"},
                }
            ]
        ),
        encoding="utf-8",
    )

    items = load_golden_queries(questions_path)
    assert items[0].question == "Apa syarat PBG rumah tinggal?"
    assert items[0].metadata["region"] == "nasional"


def test_export_results_supports_json_and_csv(tmp_path):
    results = [
        {
            "question": "Apa syarat PBG?",
            "answer": "Perlu dokumen administratif.",
            "contexts": ["PP 16/2021 Pasal 15"],
            "ground_truth": "PBG butuh dokumen.",
            "context_precision": 0.8,
        }
    ]

    json_path = export_results(results, tmp_path / "results.json")
    csv_path = export_results(results, tmp_path / "results.csv")

    assert json_path.exists()
    assert csv_path.exists()
    assert "context_precision" in json_path.read_text(encoding="utf-8")
    assert "Apa syarat PBG?" in csv_path.read_text(encoding="utf-8")
