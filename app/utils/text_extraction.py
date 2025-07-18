# app/utils/text_extraction.py ** NEW

import fitz  # PyMuPDF
import logging

logger = logging.getLogger(__name__)

def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """
    Extracts text from uploaded files (.pdf, .txt, .md).

    Args:
        file_bytes (bytes): Raw bytes from the uploaded file.
        filename (str): Original filename (used for filetype detection).

    Returns:
        str: Extracted plain text content.

    Raises:
        ValueError: If file extension is not supported.
        RuntimeError: If PDF parsing fails.
    """
    # Case-insensitive extension check for safety
    lower_name = filename.lower()
    try:
        if lower_name.endswith(".pdf"):
            # PDF parsing using PyMuPDF (fitz)
            logger.info(f"Extracting text from PDF file: {filename}")
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            return text
        elif lower_name.endswith(".txt") or lower_name.endswith(".md"):
            logger.info(f"Extracting text from plain text file: {filename}")
            return file_bytes.decode("utf-8")
        else:
            logger.warning(f"Rejected unsupported file type: {filename}")
            raise ValueError("Unsupported file format. Only PDF, TXT, and MD files are supported.")
    except Exception as e:
        logger.error(f"Text extraction failed for file {filename}: {e}", exc_info=True)
        # Do not expose internal error details in production use!
        raise RuntimeError(f"Failed to extract text: {e}")

"""
---------------------------------------------------------------
Purpose:
    Safely extracts text content from user-uploaded files for profile processing.

What It Does:
    - Handles `.pdf` (via PyMuPDF/fitz) and `.txt`/`.md` (UTF-8 decode).
    - Raises clear exceptions for unsupported or malformed files.

Used By:
    - Profile upload endpoints that accept file uploads for vectorization.

Good Practices:
    - Always wrap I/O and decoding in try/except to prevent crashes.
    - Validate file type/extension before processing (case-insensitive).
    - Avoid supporting executable/script file types.

Security & Scalability:
    - Never execute, import, or eval file contents.
    - Only extract text—do not attempt to parse macros or code.
    - Log errors server-side (never expose full exception details to users).

---------------------------------------------------------------
"""
