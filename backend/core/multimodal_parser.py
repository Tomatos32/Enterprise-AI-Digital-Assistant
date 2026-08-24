"""Enterprise Multimodal Document Parser with Column Layout Reconstruction,

Cross-Page Table Merging, and Multi-Level Excel Header Flattening.
"""

from io import BytesIO
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Union

from langchain_core.documents import Document
import openpyxl
from pydantic import BaseModel, Field
import pypdf

logger = logging.getLogger(__name__)


class ParsedChunk(BaseModel):
    """Structured representation of a parsed multimodal document chunk."""

    content: str = Field(..., description="Markdown or text content of the chunk")
    chunk_type: str = Field("text", description="Type of chunk: 'text' or 'table'")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata associated with the chunk")

    def to_langchain_document(self) -> Document:
        """Converts to a LangChain Document object for vector store compatibility."""
        meta = dict(self.metadata)
        meta["chunk_type"] = self.chunk_type
        return Document(page_content=self.content, metadata=meta)


class MultimodalDocumentParser:
    """Unified Multimodal Document Parser supporting complex PDF layouts and multi-sheet Excel workbooks."""

    # =========================================================================
    # 1. PDF Parsing with Multi-Column Reordering and Table Recognition
    # =========================================================================

    @classmethod
    def _extract_page_layout_text(cls, page: pypdf.PageObject, detect_columns: bool = True) -> str:
        """Extracts text from a PDF page, performing column detection and reordering when needed."""
        extracted_text = page.extract_text() or ""
        if not detect_columns or not extracted_text.strip():
            return extracted_text.strip()

        # Heuristic / Coordinate-based multi-column layout detection
        lines = extracted_text.splitlines()
        left_column: List[str] = []
        right_column: List[str] = []
        is_multi_column = False

        # Detect typical multi-column patterns: large internal horizontal whitespace gaps
        for line in lines:
            # Check for multiple spaces or tabs separating distinct column fragments
            parts = re.split(r"\s{4,}|\t+", line.strip())
            if len(parts) >= 2 and all(len(p.strip()) > 0 for p in parts[:2]):
                is_multi_column = True
                left_column.append(parts[0].strip())
                right_column.append(" ".join(p.strip() for p in parts[1:]))
            else:
                if is_multi_column:
                    # Append non-split lines to left or flush if appropriate
                    left_column.append(line.strip())
                else:
                    left_column.append(line.strip())

        if is_multi_column and right_column:
            # Reconstruct in natural reading order: Left column top-to-bottom, then Right column
            reordered = "\n".join(left_column) + "\n\n" + "\n".join(right_column)
            return reordered.strip()

        return extracted_text.strip()

    @classmethod
    def _extract_markdown_tables_from_text(cls, text: str) -> List[Dict[str, Any]]:
        """Identifies embedded tabular structures formatted with pipes or aligned columns."""
        tables = []
        lines = text.splitlines()
        current_table_lines: List[str] = []
        in_table = False

        for line in lines:
            line_str = line.strip()
            # Pipe-separated table detection
            if line_str.startswith("|") and line_str.endswith("|"):
                in_table = True
                current_table_lines.append(line_str)
            elif in_table:
                # Table ended
                if len(current_table_lines) >= 2:
                    table_obj = cls._parse_raw_markdown_table(current_table_lines)
                    if table_obj:
                        tables.append(table_obj)
                current_table_lines = []
                in_table = False

        if in_table and len(current_table_lines) >= 2:
            table_obj = cls._parse_raw_markdown_table(current_table_lines)
            if table_obj:
                tables.append(table_obj)

        return tables

    @staticmethod
    def _parse_raw_markdown_table(table_lines: List[str]) -> Optional[Dict[str, Any]]:
        """Parses a markdown table into headers, rows, and structured representation."""
        if not table_lines:
            return None

        # Filter out delimiter row (e.g. |---|---|)
        cleaned_rows = []
        for row in table_lines:
            if re.match(r"^\|(\s*:?-+:?\s*\|)+$", row.strip()):
                continue
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            cleaned_rows.append(cells)

        if not cleaned_rows:
            return None

        headers = cleaned_rows[0]
        data_rows = cleaned_rows[1:]

        # Build clean markdown table string
        md_lines = []
        md_lines.append("| " + " | ".join(headers) + " |")
        md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for r in data_rows:
            # Pad or truncate row to match headers count
            row_cells = r + [""] * max(0, len(headers) - len(r))
            row_cells = row_cells[: len(headers)]
            md_lines.append("| " + " | ".join(row_cells) + " |")

        md_content = "\n".join(md_lines)
        return {
            "headers": headers,
            "rows": data_rows,
            "column_count": len(headers),
            "row_count": len(data_rows),
            "markdown": md_content,
        }

    @classmethod
    def parse_pdf(
        cls,
        file_input: Union[str, Path, bytes, BytesIO],
        detect_columns: bool = True,
        merge_cross_page_tables: bool = True,
        source_name: str = "document.pdf",
    ) -> List[ParsedChunk]:
        """Parses PDF document with multi-column layout reordering and cross-page table merging."""
        if isinstance(file_input, (str, Path)):
            path_obj = Path(file_input)
            source_name = path_obj.name
            reader = pypdf.PdfReader(str(path_obj))
        elif isinstance(file_input, bytes):
            reader = pypdf.PdfReader(BytesIO(file_input))
        else:
            reader = pypdf.PdfReader(file_input)

        chunks: List[ParsedChunk] = []
        pending_table: Optional[Dict[str, Any]] = None

        for page_idx, page in enumerate(reader.pages):
            page_num = page_idx + 1
            raw_page_text = cls._extract_page_layout_text(page, detect_columns=detect_columns)

            # Detect tables on page
            tables_on_page = cls._extract_markdown_tables_from_text(raw_page_text)

            # Handle cross-page table continuation
            if merge_cross_page_tables and tables_on_page:
                first_table = tables_on_page[0]
                if pending_table is not None:
                    # Check if first table is continuation of pending table
                    same_cols = first_table["column_count"] == pending_table["column_count"]
                    same_headers = first_table["headers"] == pending_table["headers"]
                    if same_cols or same_headers:
                        # Append rows to pending table
                        pending_table["rows"].extend(first_table["rows"])
                        pending_table["row_count"] += first_table["row_count"]
                        pending_table["end_page"] = page_num
                        # Rebuild merged markdown
                        md_lines = ["| " + " | ".join(pending_table["headers"]) + " |"]
                        md_lines.append("| " + " | ".join(["---"] * len(pending_table["headers"])) + " |")
                        for r in pending_table["rows"]:
                            cells = r + [""] * max(0, len(pending_table["headers"]) - len(r))
                            cells = cells[: len(pending_table["headers"])]
                            md_lines.append("| " + " | ".join(cells) + " |")
                        pending_table["markdown"] = "\n".join(md_lines)
                        tables_on_page = tables_on_page[1:]
                    else:
                        # Flush previous pending table
                        chunks.append(
                            ParsedChunk(
                                content=pending_table["markdown"],
                                chunk_type="table",
                                metadata={
                                    "source": source_name,
                                    "start_page": pending_table["start_page"],
                                    "end_page": pending_table["end_page"],
                                    "table_meta": {
                                        "columns": pending_table["headers"],
                                        "row_count": pending_table["row_count"],
                                        "is_merged_cross_page": pending_table["start_page"]
                                        != pending_table["end_page"],
                                    },
                                },
                            )
                        )
                        pending_table = None

            # Process text paragraphs excluding recognized tables
            text_without_tables = raw_page_text
            for t in tables_on_page:
                text_without_tables = text_without_tables.replace(t["markdown"], "")

            # Split text into readable semantic paragraphs
            clean_paragraphs = [
                p.strip() for p in re.split(r"\n\s*\n+", text_without_tables) if len(p.strip()) > 15
            ]
            for para in clean_paragraphs:
                chunks.append(
                    ParsedChunk(
                        content=para,
                        chunk_type="text",
                        metadata={"source": source_name, "page": page_num, "layout": "reordered_column"},
                    )
                )

            # Store any standalone tables found on current page
            for t_idx, t in enumerate(tables_on_page):
                if merge_cross_page_tables and t_idx == len(tables_on_page) - 1:
                    # Last table on page could potentially continue onto next page
                    pending_table = {
                        "headers": t["headers"],
                        "rows": list(t["rows"]),
                        "column_count": t["column_count"],
                        "row_count": t["row_count"],
                        "markdown": t["markdown"],
                        "start_page": page_num,
                        "end_page": page_num,
                    }
                else:
                    chunks.append(
                        ParsedChunk(
                            content=t["markdown"],
                            chunk_type="table",
                            metadata={
                                "source": source_name,
                                "page": page_num,
                                "table_meta": {
                                    "columns": t["headers"],
                                    "row_count": t["row_count"],
                                    "is_merged_cross_page": False,
                                },
                            },
                        )
                    )

        # Flush final pending table if any
        if pending_table is not None:
            chunks.append(
                ParsedChunk(
                    content=pending_table["markdown"],
                    chunk_type="table",
                    metadata={
                        "source": source_name,
                        "start_page": pending_table["start_page"],
                        "end_page": pending_table["end_page"],
                        "table_meta": {
                            "columns": pending_table["headers"],
                            "row_count": pending_table["row_count"],
                            "is_merged_cross_page": pending_table["start_page"] != pending_table["end_page"],
                        },
                    },
                )
            )

        return chunks

    # =========================================================================
    # 2. Excel Parsing with Multi-Sheet and Multi-Level Header Flattening
    # =========================================================================

    @classmethod
    def _flatten_excel_headers(cls, sheet: openpyxl.worksheet.worksheet.Worksheet, max_header_rows: int = 3) -> List[str]:
        """Inspects merged cells and top rows to construct flattened composite column names."""
        # Unroll values in top N rows
        top_rows: List[List[str]] = []
        for r_idx in range(1, min(max_header_rows + 1, sheet.max_row + 1)):
            row_vals = []
            for c_idx in range(1, sheet.max_column + 1):
                cell_val = sheet.cell(row=r_idx, column=c_idx).value
                # Check if cell is part of merged range
                for merged_range in sheet.merged_cells.ranges:
                    if (
                        merged_range.min_row <= r_idx <= merged_range.max_row
                        and merged_range.min_col <= c_idx <= merged_range.max_col
                    ):
                        # Use top-left cell value
                        cell_val = sheet.cell(
                            row=merged_range.min_row, column=merged_range.min_col
                        ).value
                        break
                row_vals.append(str(cell_val).strip() if cell_val is not None else "")
            top_rows.append(row_vals)

        if not top_rows:
            return [f"Col_{i+1}" for i in range(sheet.max_column)]

        # Determine effective header depth (rows with non-empty categories)
        flattened_headers = []
        num_cols = sheet.max_column

        for col_i in range(num_cols):
            hierarchy = []
            for row_j in range(len(top_rows)):
                val = top_rows[row_j][col_i] if col_i < len(top_rows[row_j]) else ""
                if val and val not in hierarchy:
                    hierarchy.append(val)

            if hierarchy:
                flattened_headers.append("_".join(hierarchy))
            else:
                flattened_headers.append(f"Column_{col_i + 1}")

        return flattened_headers

    @classmethod
    def parse_excel(
        cls,
        file_input: Union[str, Path, bytes, BytesIO],
        max_header_rows: int = 2,
        source_name: str = "workbook.xlsx",
    ) -> List[ParsedChunk]:
        """Parses multi-sheet Excel workbooks with merged cell and hierarchical header support."""
        if isinstance(file_input, (str, Path)):
            path_obj = Path(file_input)
            source_name = path_obj.name
            wb = openpyxl.load_workbook(str(path_obj), data_only=True)
        elif isinstance(file_input, bytes):
            wb = openpyxl.load_workbook(BytesIO(file_input), data_only=True)
        else:
            wb = openpyxl.load_workbook(file_input, data_only=True)

        chunks: List[ParsedChunk] = []

        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            if sheet.max_row is None or sheet.max_row <= 0 or sheet.max_column <= 0:
                continue

            headers = cls._flatten_excel_headers(sheet, max_header_rows=max_header_rows)
            start_data_row = max_header_rows + 1

            data_rows = []
            for r_idx in range(start_data_row, sheet.max_row + 1):
                row_cells = []
                is_empty_row = True
                for c_idx in range(1, sheet.max_column + 1):
                    val = sheet.cell(row=r_idx, column=c_idx).value
                    # Check merged cell top-left value
                    for merged_range in sheet.merged_cells.ranges:
                        if (
                            merged_range.min_row <= r_idx <= merged_range.max_row
                            and merged_range.min_col <= c_idx <= merged_range.max_col
                        ):
                            val = sheet.cell(
                                row=merged_range.min_row, column=merged_range.min_col
                            ).value
                            break
                    val_str = str(val).strip() if val is not None else ""
                    if val_str:
                        is_empty_row = False
                    row_cells.append(val_str)

                if not is_empty_row:
                    data_rows.append(row_cells)

            if not data_rows:
                continue

            # Build Markdown Table representation
            md_lines = [
                f"### 工作表: {sheet_name}",
                "| " + " | ".join(headers) + " |",
                "| " + " | ".join(["---"] * len(headers)) + " |",
            ]
            for r in data_rows:
                # Pad to headers length
                padded = r + [""] * max(0, len(headers) - len(r))
                padded = padded[: len(headers)]
                md_lines.append("| " + " | ".join(padded) + " |")

            table_md = "\n".join(md_lines)
            chunks.append(
                ParsedChunk(
                    content=table_md,
                    chunk_type="table",
                    metadata={
                        "source": source_name,
                        "sheet_name": sheet_name,
                        "table_meta": {
                            "columns": headers,
                            "row_count": len(data_rows),
                            "sheet_name": sheet_name,
                        },
                    },
                )
            )

        return chunks

    # =========================================================================
    # 3. Universal Entrypoint
    # =========================================================================

    @classmethod
    def parse_document(
        cls,
        file_path: Union[str, Path],
        detect_columns: bool = True,
        merge_cross_page_tables: bool = True,
    ) -> List[ParsedChunk]:
        """Universal document parsing entrypoint dispatching by file extension."""
        path_obj = Path(file_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")

        suffix = path_obj.suffix.lower()
        if suffix == ".pdf":
            return cls.parse_pdf(
                path_obj,
                detect_columns=detect_columns,
                merge_cross_page_tables=merge_cross_page_tables,
                source_name=path_obj.name,
            )
        elif suffix in [".xlsx", ".xls"]:
            return cls.parse_excel(path_obj, source_name=path_obj.name)
        elif suffix in [".md", ".markdown", ".txt", ".csv"]:
            content = path_obj.read_text(encoding="utf-8", errors="ignore")
            # Extract tables if present
            tables = cls._extract_markdown_tables_from_text(content)
            chunks = []
            if tables:
                for t in tables:
                    chunks.append(
                        ParsedChunk(
                            content=t["markdown"],
                            chunk_type="table",
                            metadata={
                                "source": path_obj.name,
                                "table_meta": {"columns": t["headers"], "row_count": t["row_count"]},
                            },
                        )
                    )
                # Remaining text
                clean_text = content
                for t in tables:
                    clean_text = clean_text.replace(t["markdown"], "")
                paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", clean_text) if len(p.strip()) > 15]
                for p in paragraphs:
                    chunks.append(
                        ParsedChunk(content=p, chunk_type="text", metadata={"source": path_obj.name})
                    )
            else:
                paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", content) if len(p.strip()) > 15]
                for p in paragraphs:
                    chunks.append(
                        ParsedChunk(content=p, chunk_type="text", metadata={"source": path_obj.name})
                    )
            return chunks
        else:
            # Fallback
            text = path_obj.read_text(encoding="utf-8", errors="ignore")
            return [ParsedChunk(content=text, chunk_type="text", metadata={"source": path_obj.name})]
