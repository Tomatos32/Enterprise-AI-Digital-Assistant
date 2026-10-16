"""Enterprise RAG Text and Document Chunking / Splitting Engine."""

import re
from typing import List, Optional
from langchain_core.documents import Document


def split_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    separators: Optional[List[str]] = None,
) -> List[str]:
    """Recursively splits a text into chunks based on semantic separators

    (Markdown headers, paragraph breaks, sentences, and punctuation).
    """
    if not text or not text.strip():
        return []

    if len(text) <= chunk_size:
        return [text.strip()]

    default_separators = [
        "\n## ",
        "\n### ",
        "\n#### ",
        "\n\n",
        "\n",
        "。\n",
        "；\n",
        "。",
        "；",
        "！",
        "？",
        "; ",
        "! ",
        "? ",
        " ",
        "",
    ]
    seps = separators or default_separators

    # Find the first separator present in text
    chosen_sep = ""
    for sep in seps:
        if sep == "":
            chosen_sep = ""
            break
        if sep in text:
            chosen_sep = sep
            break

    # Split using chosen separator
    if chosen_sep:
        splits = text.split(chosen_sep)
    else:
        splits = list(text)

    # Recombine splits into chunks respecting chunk_size and chunk_overlap
    chunks: List[str] = []
    current_chunk = ""

    for s in splits:
        piece = s if chosen_sep == "" else (s + chosen_sep)
        if not piece.strip():
            continue

        if len(current_chunk) + len(piece) <= chunk_size:
            current_chunk += piece
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            # Handle case where single piece itself is larger than chunk_size
            if len(piece) > chunk_size:
                # Recursively split with remaining separators
                sub_seps = [sp for sp in seps if sp != chosen_sep]
                sub_chunks = split_text(piece, chunk_size, chunk_overlap, sub_seps)
                chunks.extend(sub_chunks)
                current_chunk = ""
            else:
                # Maintain chunk_overlap from the tail of current_chunk
                if chunk_overlap > 0 and len(current_chunk) > chunk_overlap:
                    overlap_prefix = current_chunk[-chunk_overlap:]
                    # Try to align overlap to whitespace or punctuation boundary
                    boundary = max(overlap_prefix.rfind("\n"), overlap_prefix.rfind("。"), overlap_prefix.rfind(" "))
                    if boundary != -1:
                        overlap_prefix = overlap_prefix[boundary + 1 :]
                    current_chunk = overlap_prefix + piece
                else:
                    current_chunk = piece

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def split_documents(
    docs: List[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> List[Document]:
    """Splits a list of Document objects into smaller chunk Document objects,

    preserving and augmenting parent metadata with chunk index information.
    """
    chunked_docs: List[Document] = []

    for doc in docs:
        content = doc.page_content or ""
        meta = dict(doc.metadata) if doc.metadata else {}

        # If document is small enough, keep as single chunk
        if len(content) <= chunk_size:
            augmented_meta = meta.copy()
            augmented_meta["chunk_index"] = 0
            augmented_meta["total_chunks"] = 1
            augmented_meta["char_count"] = len(content)
            chunked_docs.append(Document(page_content=content, metadata=augmented_meta))
            continue

        text_chunks = split_text(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        total = len(text_chunks)

        for idx, chunk in enumerate(text_chunks):
            augmented_meta = meta.copy()
            augmented_meta["chunk_index"] = idx
            augmented_meta["total_chunks"] = total
            augmented_meta["char_count"] = len(chunk)

            # Preserve section header if detected
            first_line = chunk.splitlines()[0].strip()
            if first_line.startswith("#"):
                augmented_meta["section_header"] = re.sub(r"^#+\s*", "", first_line)

            chunked_docs.append(Document(page_content=chunk, metadata=augmented_meta))

    return chunked_docs
