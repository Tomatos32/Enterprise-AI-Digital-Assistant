"""Unit Tests for RAGAS Quality Evaluation Pipeline and Gate Runner."""

import os
import pytest
from benchmark.eval_ragas import RAGASEvaluator, run_evaluation


BENCHMARK_DATASET_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "benchmark",
    "test-dataset.json"
)


def test_dataset_loading():
    """Verifies that the benchmark dataset contains 30 valid samples."""
    evaluator = RAGASEvaluator(threshold=0.90, mode="offline")
    samples = evaluator.load_dataset(BENCHMARK_DATASET_PATH)

    assert len(samples) == 30
    for sample in samples:
        assert "id" in sample
        assert "question" in sample
        assert "ground_truth" in sample
        assert "contexts" in sample
        assert "answer" in sample
        assert isinstance(sample["contexts"], list)
        assert len(sample["contexts"]) > 0


def test_offline_evaluation_execution():
    """Verifies offline evaluation metrics computation and gate passing."""
    report = run_evaluation(
        dataset_path=BENCHMARK_DATASET_PATH,
        mode="offline",
        threshold=0.90
    )

    assert report["total_samples"] == 30
    assert 0.0 <= report["faithfulness_score"] <= 1.0
    assert 0.0 <= report["answer_relevance_score"] <= 1.0
    assert 0.0 <= report["context_recall_score"] <= 1.0
    assert report["faithfulness_score"] >= 0.90
    assert report["passed_gate"] is True
    assert report["mode"] == "offline"


def test_gate_threshold_blocking():
    """Verifies that gate blocks execution when faithfulness is below threshold."""
    evaluator = RAGASEvaluator(threshold=0.9999, mode="offline")
    report = evaluator.run(BENCHMARK_DATASET_PATH)

    assert report["passed_gate"] is False
    assert report["faithfulness_score"] < report["threshold"]


def test_invalid_dataset_file_raises_error():
    """Verifies FileNotFoundError on invalid dataset file path."""
    evaluator = RAGASEvaluator(threshold=0.90, mode="offline")
    with pytest.raises(FileNotFoundError):
        evaluator.load_dataset("non_existent_dataset.json")
