"""RAG Document Loader & Parser Utilities for Enterprise AI Digital Assistant."""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import openpyxl
from pypdf import PdfReader
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

SUPPORTED_KB_SUFFIXES = (".md", ".pdf", ".xlsx", ".xls", ".txt")


def extract_metadata_from_filename(file_path: Path) -> Dict[str, Any]:
    """Extracts default metadata fields based on document filename conventions."""
    name = file_path.name.upper()
    category = "GENERAL"
    if "SECURITY" in name or "安全" in name or "保密" in name:
        category = "SECURITY"
    elif "CS" in name or "客服" in name or "售后" in name:
        category = "CS"
    elif "HR" in name or "人事" in name or "行政" in name:
        category = "HR"
    elif "PROCUREMENT" in name or "PROC" in name or "采购" in name:
        category = "PROCUREMENT"
    elif "FINANCE" in name or "财务" in name or "报销" in name:
        category = "FINANCE"
    elif "IT_" in name or "_IT" in name or "IT" in name.split("_") or "运维" in name:
        category = "IT"

    return {
        "source": str(file_path),
        "filename": file_path.name,
        "category": category,
        "format": file_path.suffix.lstrip(".").lower()
    }


def load_markdown_document(file_path: Path) -> List[Document]:
    """Loads a Markdown file into Document objects."""
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    meta = extract_metadata_from_filename(file_path)
    meta["title"] = text.splitlines()[0].lstrip("#").strip() if text else file_path.stem
    return [Document(page_content=text, metadata=meta)]


def load_text_document(file_path: Path) -> List[Document]:
    """Loads a plain text (.txt) file into Document objects."""
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    meta = extract_metadata_from_filename(file_path)
    meta["title"] = file_path.stem
    return [Document(page_content=text, metadata=meta)]


def load_pdf_document(file_path: Path) -> List[Document]:
    """Loads a PDF file into Document objects."""
    reader = PdfReader(str(file_path))
    meta = extract_metadata_from_filename(file_path)
    documents = []
    
    for idx, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        page_meta = meta.copy()
        page_meta["page"] = idx + 1
        documents.append(Document(page_content=page_text, metadata=page_meta))
        
    return documents


def load_excel_document(file_path: Path) -> List[Document]:
    """Loads an Excel file and converts sheet data into Markdown table Document."""
    wb = openpyxl.load_workbook(str(file_path), data_only=True)
    meta = extract_metadata_from_filename(file_path)
    documents = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        
        # Build Markdown Table representation
        header = rows[0]
        header_line = "| " + " | ".join(str(cell or "") for cell in header) + " |"
        sep_line = "| " + " | ".join("---" for _ in header) + " |"
        
        body_lines = []
        for r in rows[1:]:
            row_str = "| " + " | ".join(str(cell or "") for cell in r) + " |"
            body_lines.append(row_str)
            
        md_table_text = f"# Excel Sheet: {sheet_name}\n\n" + "\n".join([header_line, sep_line] + body_lines)
        sheet_meta = meta.copy()
        sheet_meta["sheet"] = sheet_name
        documents.append(Document(page_content=md_table_text, metadata=sheet_meta))

    return documents


def _load_single_kb_file(path: Path) -> List[Document]:
    """Dispatches a single supported knowledge document to its format-specific parser."""
    suffix = path.suffix.lower()
    if suffix == ".md":
        return load_markdown_document(path)
    if suffix == ".pdf":
        return load_pdf_document(path)
    if suffix in (".xlsx", ".xls"):
        return load_excel_document(path)
    if suffix == ".txt":
        return load_text_document(path)
    return []


def load_sample_kb_documents(kb_dir: Path) -> List[Document]:
    """Recursively loads all sample_kb files (Markdown, PDF, Excel, Text)."""
    docs: List[Document] = []
    if not kb_dir.exists():
        return docs

    for path in sorted(kb_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_KB_SUFFIXES:
            try:
                loaded = _load_single_kb_file(path)
                for doc in loaded:
                    doc.metadata.setdefault("source_type", "builtin")
                docs.extend(loaded)
            except Exception as exc:
                logger.warning("Failed to load sample KB document %s: %s", path, exc)

    return docs


def load_uploaded_data_documents(
    data_dir: Path,
    category_overrides: Optional[Dict[str, str]] = None,
) -> List[Document]:
    """Loads top-level admin-uploaded documents from data_dir without traversing subdirs (e.g. qdrant_storage)."""
    docs: List[Document] = []
    if not data_dir.exists() or not data_dir.is_dir():
        return docs

    overrides = category_overrides or {}
    for path in sorted(data_dir.iterdir()):
        if not path.is_file():
            continue
        if path.name.startswith(".") or path.suffix.lower() not in SUPPORTED_KB_SUFFIXES:
            continue
        try:
            loaded = _load_single_kb_file(path)
            override_cat = overrides.get(path.name)
            for doc in loaded:
                doc.metadata["filename"] = path.name
                doc.metadata["source"] = str(path)
                doc.metadata["source_type"] = "uploaded"
                if override_cat and str(override_cat).strip():
                    doc.metadata["category"] = str(override_cat).strip().upper()
            docs.extend(loaded)
        except Exception as exc:
            logger.warning("Skipped unreadable uploaded knowledge document %s: %s", path.name, exc)

    return docs
