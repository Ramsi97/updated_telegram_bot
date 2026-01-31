# core/pdf/pdf_to_image_converter.py
import fitz  # PyMuPDF
from pathlib import Path

def pdf_to_image(pdf_path: str | Path, output_dir: str | Path, dpi: int = 400) -> Path:
    
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ✅ Open PDF
    pdf = fitz.open(pdf_path)
    page = pdf.load_page(0)

    # 🧠 DPI → zoom factor (72 DPI is default)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    # ✅ Render page to image with scaling
    pix = page.get_pixmap(matrix=mat, alpha=False)

    # ✅ Save as PNG (lossless)
    image_path = output_dir / f"{pdf_path.stem}_page1.png"
    pix.save(image_path)

    pdf.close()
    return image_path
