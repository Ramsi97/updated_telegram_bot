# core/pdf/extractor.py
import fitz  # PyMuPDF
from typing import Dict, Any

def get_pdf_metadata(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Extract PDF metadata including page count from PDF bytes
    """
    try:
        # Open PDF from bytes
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(pdf_document)
        pdf_document.close()
        
        return {
            "page_count": page_count
        }
        
    except Exception as e:
        # Return default in case of error
        return {
            "page_count": 0
        }