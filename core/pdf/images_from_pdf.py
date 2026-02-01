import fitz
import io
import numpy as np
import cv2  # Import cv2
from PIL import Image

def extract_images_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    extracted_images = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        image_list = page.get_images(full=True)

        for img in image_list:
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            # 1. Open with PIL (This is in RGB)
            pil_img = Image.open(io.BytesIO(image_bytes))
            
            # 2. Convert to NumPy array
            numpy_img = np.array(pil_img)
            
            # 3. FIX THE COLOR: Convert RGB to BGR for OpenCV
            # We check if it has 3 channels (RGB) or 4 (RGBA)
            if len(numpy_img.shape) == 3:
                if numpy_img.shape[2] == 3:  # RGB
                    numpy_img = cv2.cvtColor(numpy_img, cv2.COLOR_RGB2BGR)
                elif numpy_img.shape[2] == 4:  # RGBA
                    numpy_img = cv2.cvtColor(numpy_img, cv2.COLOR_RGBA2BGR)
            
            extracted_images.append(numpy_img)

    num_found = len(extracted_images)
    return {
        "photo": extracted_images[0] if num_found > 0 else None,
        "qrcode": extracted_images[1] if num_found > 1 else None
    }