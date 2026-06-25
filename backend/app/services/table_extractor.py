"""
Table Extractor Service
Uses pdfplumber to accurately detect and extract table structure from PDFs.
Tables are converted to Markdown for clean embedding and retrieval.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("[WARN] pdfplumber not installed. Table extraction disabled. Run: pip install pdfplumber")


@dataclass
class ExtractedTable:
    """Represents a table extracted from a PDF page."""
    page_number: int
    table_index: int          # Index of the table on the page (0-based)
    markdown: str             # Table rendered as markdown
    raw_data: List[List]      # Raw cell data
    metadata: Dict[str, Any] = field(default_factory=dict)


def _clean_cell(cell) -> str:
    """Clean a table cell value."""
    if cell is None:
        return ""
    text = str(cell).strip()
    # Collapse internal whitespace/newlines
    text = re.sub(r"\s+", " ", text)
    # Escape pipe characters that would break markdown
    text = text.replace("|", "\\|")
    return text


def _table_to_markdown(rows: List[List]) -> Optional[str]:
    """
    Convert a 2D list of cell values into a Markdown table string.
    Returns None if the table is empty or has only one row.
    """
    if not rows:
        return None

    # Filter out completely empty rows
    non_empty_rows = [row for row in rows if any(cell for cell in row if cell)]
    if len(non_empty_rows) < 2:
        return None

    # Determine column count (handle jagged tables)
    col_count = max(len(row) for row in non_empty_rows)

    # Pad all rows to the same width
    padded = []
    for row in non_empty_rows:
        cleaned = [_clean_cell(cell) for cell in row]
        while len(cleaned) < col_count:
            cleaned.append("")
        padded.append(cleaned)

    # Build markdown
    lines = []
    # Header row
    lines.append("| " + " | ".join(padded[0]) + " |")
    # Separator
    lines.append("| " + " | ".join(["---"] * col_count) + " |")
    # Data rows
    for row in padded[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def extract_tables_from_pdf(pdf_path: str) -> List[ExtractedTable]:
    """
    Extract all tables from a PDF file using pdfplumber.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of ExtractedTable objects (one per table found).
    """
    if not PDFPLUMBER_AVAILABLE:
        return []

    extracted: List[ExtractedTable] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                if not tables:
                    continue

                for t_idx, raw_table in enumerate(tables):
                    md = _table_to_markdown(raw_table)
                    if not md:
                        continue

                    row_count = len(raw_table)
                    col_count = max(len(r) for r in raw_table) if raw_table else 0

                    extracted.append(ExtractedTable(
                        page_number=page_num,
                        table_index=t_idx,
                        markdown=md,
                        raw_data=raw_table,
                        metadata={
                            "row_count": row_count,
                            "col_count": col_count,
                        }
                    ))

    except Exception as e:
        print(f"[ERROR] Table extraction error: {e}")

    print(f"[INFO] Extracted {len(extracted)} tables from PDF")
    return extracted


def tables_to_chunks(
    tables: List[ExtractedTable],
    subject: str = "",
    filename: str = "",
) -> List[tuple]:
    """
    Convert ExtractedTable objects into (text, metadata) tuples
    ready for embedding and Pinecone upload.

    Args:
        tables: List of ExtractedTable objects.
        subject: Subject name for metadata tagging.
        filename: Source PDF filename.

    Returns:
        List of (chunk_text, metadata_dict) tuples.
    """
    chunks = []
    for table in tables:
        # Build a descriptive text block around the markdown table
        text = (
            f"[Table on Page {table.page_number}]\n"
            f"{table.markdown}"
        )

        metadata = {
            "content_type": "table",
            "page_number": table.page_number,
            "table_index": table.table_index,
            "subject": subject,
            "filename": filename,
            "has_table": True,
            "row_count": table.metadata.get("row_count", 0),
            "col_count": table.metadata.get("col_count", 0),
            "section": f"Table on Page {table.page_number}",
            "topic": "table",
        }

        chunks.append((text, metadata))

    return chunks
