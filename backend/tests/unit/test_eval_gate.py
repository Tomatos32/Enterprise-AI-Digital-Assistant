"""Unit tests for RAGAS Evaluation Strict Gate and Evaluation Report Generation."""

import os
import json
import pytest
from benchmark.eval_ragas import RAGASEvaluator, run_evaluation


@pytest.fixture
def temp_dataset_path(tmp_path):
    """Creates a temporary benchmark dataset for testing gate triggers."""
    dataset = {
        "samples": [
            {
                "question": "公司加班餐补标准是多少？",
                "ground_truth": "加班餐补为每餐 30 元，需在 OA 系统申请。",
                "contexts": ["公司员工晚上加班满 2 小时可享受每餐 30 元餐补，需在 OA 提报。"],
                "answer": "加班满 2 小时可享受 30 元加班餐补，在 OA 申请。"
            },
            {
                "question": "年假未休完如何处理？",
                "ground_truth": "当年未休完的年假可顺延至次年 3 月 31 日，逾期作废。",
                "contexts": ["员工年休假原则上当年休完，特殊情况可顺延至次年 3 月 31 日，逾期自动清零。"],
                "answer": "年假可顺延至次年 3 月 31 日前休完，逾期自动作废。"
            }
        ]
    }
    file_path = tmp_path / "test_eval_dataset.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False)
    return str(file_path)


@pytest.fixture
def low_quality_dataset_path(tmp_path):
    """Creates a low quality benchmark dataset where context overlap is zero."""
    dataset = {
        "samples": [
            {
                "question": "公司的核心价值观是什么？",
                "ground_truth": "客户第一，诚信正直，追求卓越。",
                "contexts": ["今天天气晴朗，适合户外运动。"],
                "answer": "完全不相关的幻觉回答内容。"
            }
        ]
    }
    file_path = tmp_path / "low_eval_dataset.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False)
    return str(file_path)


def test_eval_ragas_strict_gate_pass(temp_dataset_path, tmp_path):
    """Test strict gate evaluation passes on high quality dataset."""
    report_md = str(tmp_path / "eval_report_pass.md")
    report = run_evaluation(
        dataset_path=temp_dataset_path,
        mode="offline",
        threshold=0.90,
        recall_threshold=0.88,
        strict_gate=True,
        report_md_path=report_md
    )

    assert report["passed_gate"] is True
    assert report["faithfulness_score"] >= 0.90
    assert report["context_recall_score"] >= 0.88
    assert os.path.exists(report_md)

    with open(report_md, "r", encoding="utf-8") as f:
        content = f.read()
    assert "✅ PASSED" in content
    assert "Faithfulness" in content


def test_eval_ragas_strict_gate_blocked_on_low_quality(low_quality_dataset_path, tmp_path):
    """Test strict gate evaluation blocks (passed_gate=False) on poor dataset."""
    report_md = str(tmp_path / "eval_report_fail.md")
    evaluator = RAGASEvaluator(
        threshold=0.90,
        recall_threshold=0.88,
        mode="offline",
        strict_gate=True
    )
    report = evaluator.run(low_quality_dataset_path, report_md)

    assert report["passed_gate"] is False
    assert len(report["bad_cases"]) > 0
    assert os.path.exists(report_md)

    with open(report_md, "r", encoding="utf-8") as f:
        content = f.read()
    assert "❌ BLOCKED" in content
    assert "Bad Cases Analysis" in content
