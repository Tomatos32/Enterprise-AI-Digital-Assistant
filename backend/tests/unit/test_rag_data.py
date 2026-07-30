"""Unit Tests for Sample KB Data Loading & RAG Pipeline Integration."""

import pytest
from pathlib import Path
from backend.rag.loader import (
    load_markdown_document,
    load_pdf_document,
    load_excel_document,
    load_sample_kb_documents,
)


@pytest.fixture
def sample_kb_dir():
    """Returns the sample_kb directory path."""
    product_root = Path(__file__).resolve().parent.parent.parent.parent
    return product_root / "docs" / "sample_kb"


def test_markdown_policy_loading(sample_kb_dir):
    """Tests loading Markdown policies (01_HR, 02_PROCUREMENT, 03_IT, 04_FINANCE)."""
    hr_file = sample_kb_dir / "01_HR_行政与人事规章.md"
    assert hr_file.exists(), "HR Markdown file must exist"

    docs = load_markdown_document(hr_file)
    assert len(docs) == 1
    doc = docs[0]
    assert doc.metadata["category"] == "HR"
    assert doc.metadata["format"] == "md"
    assert "考勤与打卡管理制度" in doc.page_content


def test_procurement_sop_thresholds(sample_kb_dir):
    """Tests Procurement SOP rules and Human-in-the-loop threshold definitions."""
    proc_file = sample_kb_dir / "02_PROCUREMENT_采购与审批SOP.md"
    assert proc_file.exists()

    docs = load_markdown_document(proc_file)
    assert len(docs) == 1
    content = docs[0].page_content
    assert "5,000 元" in content
    assert "50,000 元" in content
    assert "Interrupt" in content or "Human-in-the-loop" in content or "主管审批" in content


def test_pdf_procurement_sop_loading(sample_kb_dir):
    """Tests loading PDF format procurement SOP."""
    pdf_file = sample_kb_dir / "pdf" / "采购与审批SOP_图文版.pdf"
    assert pdf_file.exists(), "PDF SOP file must exist"

    docs = load_pdf_document(pdf_file)
    assert len(docs) >= 1
    assert docs[0].metadata["category"] == "PROCUREMENT"
    assert docs[0].metadata["format"] == "pdf"
    assert "Enterprise Procurement SOP" in docs[0].page_content


def test_excel_inventory_loading(sample_kb_dir):
    """Tests loading Excel inventory file into Markdown Table representation."""
    excel_file = sample_kb_dir / "excel" / "办公设备采购清单与库存表.xlsx"
    assert excel_file.exists(), "Excel inventory file must exist"

    docs = load_excel_document(excel_file)
    assert len(docs) >= 1
    sheet_doc = docs[0]
    assert sheet_doc.metadata["format"] == "xlsx"
    assert "MacBook Pro 16" in sheet_doc.page_content
    assert "Herman Miller" in sheet_doc.page_content


def test_full_sample_kb_recursion(sample_kb_dir):
    """Tests recursive loading of all sample_kb files."""
    all_docs = load_sample_kb_documents(sample_kb_dir)
    # 4 Markdown + 1 PDF + 1 Excel = 6 documents total
    assert len(all_docs) >= 6
    categories = {doc.metadata["category"] for doc in all_docs}
    assert "HR" in categories
    assert "PROCUREMENT" in categories
    assert "IT" in categories
    assert "FINANCE" in categories
