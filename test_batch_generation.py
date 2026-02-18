import os
import sys
import io
import math
from pathlib import Path
from PIL import Image
from io import BytesIO
import tempfile

# Add project root to path
sys.path.append(os.getcwd())

from core.image.image_generator import generate_final_id_image

def test_batch_generation():
    # 1. Find a sample PDF
    sample_pdf = None
    possible_samples = [
        "storage/temp/efayda_Basha Wayu Bancha.pdf",
        "storage/uploads/gebre.pdf"
    ]
    
    for s in possible_samples:
        if Path(s).exists():
            sample_pdf = Path(s)
            break
            
    if not sample_pdf:
        # Search for any PDF
        pdfs = list(Path(".").rglob("*.pdf"))
        if pdfs:
            sample_pdf = pdfs[0]
            
    if not sample_pdf:
        print("❌ No sample PDF found to test with.")
        return

    print(f"📂 Using sample PDF: {sample_pdf}")

    # Settings from processing_service.py
    A4_WIDTH = 2480
    A4_HEIGHT = 3508
    ID_WIDTH = 1021
    ID_HALF_WIDTH = 510.5
    ID_FULL_HEIGHT = 321
    TARGET_HEIGHT = 638
    TARGET_ROW_WIDTH = 2200
    # --------------------------------------------------

    output_dir = Path("storage/temp/batch_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Generate the single image once for testing
        print(f"🔄 Generating ID image...")
        image_bytes = generate_final_id_image(
            pdf_path=sample_pdf,
            output_dir=output_dir,
            font_amharic="./fonts/truetype/abyssinica/AbyssinicaSIL-Regular.ttf",
            font_english="./fonts/truetype/noto/NotoSans-Regular.ttf",
            color=True
        )

        # Reorder to [Back | Front]
        full_id_img = Image.open(io.BytesIO(image_bytes))
        front = full_id_img.crop((0, 0, int(ID_HALF_WIDTH), ID_FULL_HEIGHT))
        back = full_id_img.crop((int(ID_HALF_WIDTH), 0, ID_WIDTH, ID_FULL_HEIGHT))
        
        # Create the new row [Back | GAP | Front]
        gap = 40
        new_row_w = ID_WIDTH + gap
        new_row = Image.new('RGB', (new_row_w, ID_FULL_HEIGHT), (255, 255, 255))
        new_row.paste(back, (0, 0))
        new_row.paste(front, (int(ID_HALF_WIDTH) + gap, 0))
        # Resize for A4
        row_resized = new_row.resize((TARGET_ROW_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
        # Simulate a batch of 5
        num_ids = 5
        a4_canvas = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
        
        margin_y = (A4_HEIGHT - (num_ids * TARGET_HEIGHT)) // (num_ids + 1)
        x_pos = (A4_WIDTH - TARGET_ROW_WIDTH) // 2
        
        print(f"📄 Arranging {num_ids} IDs on A4 page...")
        for j in range(num_ids):
            y_pos = margin_y + j * (TARGET_HEIGHT + margin_y)
            a4_canvas.paste(row_resized, (x_pos, y_pos))

        # Save result
        save_path = "storage/batch_test_result_A4.png"
        a4_canvas.save(save_path)
        print(f"✅ SUCCESS: Saved A4 test result to: {os.path.abspath(save_path)}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_batch_generation()
