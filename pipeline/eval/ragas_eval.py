from __future__ import annotations

"""RAG evaluation helpers for Arsitrad v2."""

import argparse
import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Sequence


@dataclass(slots=True)
class GoldenQuery:
    question: str
    ground_truth: str
    reference_contexts: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class EvalSample:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    metadata: dict[str, object]


def load_golden_queries(path: str | Path) -> list[GoldenQuery]:
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    return [GoldenQuery(**record) for record in records]


def build_eval_samples(
    golden_queries: Sequence[GoldenQuery],
    answer_fn: Callable[[str], dict[str, object]],
) -> list[EvalSample]:
    samples: list[EvalSample] = []
    for item in golden_queries:
        result = answer_fn(item.question)
        samples.append(
            EvalSample(
                question=item.question,
                answer=str(result.get("answer", "")),
                contexts=list(result.get("contexts", [])),
                ground_truth=item.ground_truth,
                metadata={**item.metadata, **result.get("metadata", {})},
            )
        )
    return samples


def evaluate_with_ragas(samples: Sequence[EvalSample]) -> list[dict[str, object]]:
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, context_precision, faithfulness
    except Exception as exc:  # pragma: no cover - depends on optional heavy packages
        raise RuntimeError("ragas/datasets belum tersedia. Install requirements v2 terlebih dahulu.") from exc

    dataset = Dataset.from_list(
        [
            {
                "question": sample.question,
                "answer": sample.answer,
                "contexts": sample.contexts,
                "ground_truth": sample.ground_truth,
            }
            for sample in samples
        ]
    )
    results = evaluate(
        dataset,
        metrics=[context_precision, answer_relevancy, faithfulness],
    )

    rows: list[dict[str, object]] = []
    metrics_dict = results.to_pandas().to_dict(orient="records")
    for sample, metric_row in zip(samples, metrics_dict):
        rows.append({
            "question": sample.question,
            "answer": sample.answer,
            "ground_truth": sample.ground_truth,
            "contexts": sample.contexts,
            "metadata": sample.metadata,
            **metric_row,
        })
    return rows


def export_results(results: Sequence[dict[str, object]], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.suffix.lower() == ".csv":
        fieldnames: list[str] = []
        for row in results:
            for key in row.keys():
                if key not in fieldnames:
                    fieldnames.append(key)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in results:
                writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value for key, value in row.items()})
        return path

    path.write_text(json.dumps(list(results), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Arsitrad v2 RAG evaluation")
    parser.add_argument("--questions", required=True, help="Path to golden_queries.json")
    parser.add_argument("--output", required=True, help="Output path (.json or .csv)")
    parser.add_argument("--dry-run", action="store_true", help="Only print loaded golden queries")
    args = parser.parse_args()

    golden_queries = load_golden_queries(args.questions)
    if args.dry_run:
        print(json.dumps([asdict(item) for item in golden_queries], ensure_ascii=False, indent=2))
        return

    raise SystemExit(
        "Use build_eval_samples(...) from Python with a real answer_fn, then call evaluate_with_ragas(...)."
    )


if __name__ == "__main__":
    main()
