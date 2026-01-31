from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
from pathlib import Path
from datetime import date
from io import BytesIO

from app.config import BASE_DIR
from core.image.image_crop import crop_pdf_sections
from core.pdf.pdf_data_extractor import extract_user_data  # Your OCR/text extraction function

# ======================
# 🔹 Constants and Paths
# ======================
FONT_AMHARIC_DEFAULT = "/usr/local/share/fonts/AbyssinicaSIL-Regular.ttf"
FONT_ENGLISH_DEFAULT = "./fonts/truetype/noto/NotoSans-Regular.ttf"

TEMPLATES_DIR = BASE_DIR / "data" / "templates"
TEMPLATE_PATH = TEMPLATES_DIR / "template.png"

TEMPLATE_FIELDS = {
    # Amharic Fields
    "name_am": {"type": "text", "coords": (565, 215), "lang": "am"},
    "date_of_birth_et": {"type": "text", "coords": (565, 338), "lang": "am"},
    "sex_am": {"type": "text", "coords": (565, 405), "lang": "am"},
    "region_am": {"type": "text", "coords": (1315, 270), "lang": "am"},
    "zone_am": {"type": "text", "coords": (1315, 340), "lang": "am"},
    "woreda_am": {"type": "text", "coords": (1315, 420), "lang": "am"},

    # English / Numeric Fields
    "name_en": {"type": "text", "coords": (565, 260), "lang": "en"},
    "date_of_birth_greg": {"type": "text", "coords": (565, 372), "lang": "en"},
    "sex_en": {"type": "text", "coords": (680, 405), "lang": "en"},
    "expiry_date": {"type": "text", "coords": (565, 465), "lang": "en"},
    "phone_number": {"type": "text", "coords": (1315, 110), "lang": "en"},
    "region_en": {"type": "text", "coords": (1315, 305), "lang": "en"},
    "zone_en": {"type": "text", "coords": (1315, 380), "lang": "en"},
    "woreda_en": {"type": "text", "coords": (1315, 455), "lang": "en"},
    "fan_code": {"type": "text", "coords": (626, 534), "lang": "en"},

    # Image fields
    "photo": {"type": "image", "coords": (200, 250, 500, 575)},
    "qrcode": {"type": "image", "coords": (1755, 68, 2305, 618)},
    "fin_code": {"type": "image", "coords": (1325, 567, 1630, 610)},
    "small_image": {"type": "image", "coords": (1000, 524, 1100, 624)},
    "barcode": {"type": "image", "coords": (612, 524, 910, 608)},
}

# ======================
# 🔹 Helper Functions
# ======================
def gregorian_to_ethiopian(g_y, g_m, g_d):
    ethiopian_month_lengths = [30] * 12 + [5]
    new_year_offset = 11
    g = date(g_y, g_m, g_d)
    e_new_year = date(g_y, 9, new_year_offset)
    if g < e_new_year:
        e_new_year = date(g_y - 1, 9, new_year_offset)
        e_year = g_y - 1 - 7
    else:
        e_year = g_y - 7

    delta = (g - e_new_year).days
    for m_idx, ml in enumerate(ethiopian_month_lengths):
        if delta < ml:
            return e_year, m_idx + 1, delta + 1
        delta -= ml
    return e_year, 13, delta + 1


def draw_bold_text(draw, position, text, font, fill=(0, 0, 0), boldness=1):
    """Draw text thicker by offset overlaying."""
    x, y = position
    for dx in range(boldness + 1):
        for dy in range(boldness + 1):
            draw.text((x + dx, y + dy), text, font=font, fill=fill)


def draw_vertical_text(base_img, position, text, font_path, font_size=22, fill=(0, 0, 0), boldness=1, scale=1):
    """Draw sharp vertical text (rotated upward) using supersampling."""
    try:
        font = ImageFont.truetype(font_path, font_size * scale)
    except Exception as e:
        print(f"[Warning] Failed to load vertical text font: {e}")
        font = ImageFont.load_default()

    # Make a transparent canvas for the text
    text_img = Image.new("RGBA", (500 * scale, 100 * scale), (255, 255, 255, 0))
    text_draw = ImageDraw.Draw(text_img)

    # Draw bold text
    for dx in range(boldness * scale + 1):
        for dy in range(boldness * scale + 1):
            text_draw.text((dx, dy), text, font=font, fill=fill)

    # Rotate upward
    rotated = text_img.rotate(90, expand=True)

    # Paste upward relative to the position
    x, y = position
    x *= scale
    y *= scale
    base_img.paste(rotated, (x, y - rotated.height), rotated)


# ======================
# 🔹 Main Function
# ======================
def generate_final_id_image(
    pdf_path: Path,
    output_dir: Path,
    font_amharic: str = FONT_AMHARIC_DEFAULT,
    font_english: str = FONT_ENGLISH_DEFAULT,
    font_size: int = 24,
    boldness: int = 1
) -> bytes:
    """Generate a final sharp ID image (PNG bytes) from PDF data."""
    try:
        # 1️⃣ Extract cropped images and text
        image_crops = crop_pdf_sections(pdf_path, output_dir, dpi=400)
        text_data = extract_user_data(pdf_path)
    except Exception as e:
        raise RuntimeError(f"Error extracting data from PDF: {e}")

    # 2️⃣ Load base template
    template_img = cv2.imread(str(TEMPLATE_PATH))
    if template_img is None:
        raise FileNotFoundError(f"Template not found at {TEMPLATE_PATH}")
    img_pil = Image.fromarray(cv2.cvtColor(template_img, cv2.COLOR_BGR2RGB))

    # 3️⃣ Supersampled drawing canvas
    scale = 2
    w, h = img_pil.size
    img_large = img_pil.resize((w * scale, h * scale), Image.Resampling.LANCZOS)
    draw_large = ImageDraw.Draw(img_large)

    # Load fonts
    try:
        font_am_large = ImageFont.truetype(font_amharic, font_size * scale)
    except Exception as e:
        print(f"[Warning] Failed to load Amharic font: {e}")
        font_am_large = ImageFont.load_default()
    try:
        font_en_large = ImageFont.truetype(font_english, font_size * scale)
    except Exception as e:
        print(f"[Warning] Failed to load English font: {e}")
        font_en_large = font_am_large

    # 4️⃣ Generate date data
    today = date.today()
    e_year, e_month, e_day = gregorian_to_ethiopian(today.year, today.month, today.day)
    date_of_issue_greg = f"{today.day:02d}/{today.month:02d}/{today.year}"
    date_of_issue_eth = f"{e_day:02d}/{e_month:02d}/{e_year}"
    expiry_eth_date = f"{e_day:02d}/{e_month:02d}/{e_year + 8}"
    expiry_date_greg = f"{today.day:02d}/{today.month:02d}/{today.year + 8}"
    text_data["expiry_date"] = f"{expiry_eth_date} | {expiry_date_greg}"

    # 5️⃣ Draw text fields
    for key, field in TEMPLATE_FIELDS.items():
        if field["type"] != "text" or key not in text_data:
            continue

        text_to_draw = str(text_data[key])
        font_use = font_am_large if field.get("lang") == "am" else font_en_large
        x, y = field["coords"]
        x *= scale
        y *= scale

        # Handle combined or special fields
        if key == "sex_en":
            am_text = text_data.get("sex_am", "")
            am_width = draw_large.textlength(am_text, font=font_am_large)
            x = (TEMPLATE_FIELDS["sex_am"]["coords"][0] * scale) + am_width + 10
            text_to_draw = "| " + text_to_draw
        elif key == "date_of_birth_greg":
            continue
        elif key == "date_of_birth_et" and "date_of_birth_greg" in text_data:
            text_to_draw = f"{text_data['date_of_birth_et']} | {text_data['date_of_birth_greg']}"
            font_use = font_en_large

        draw_bold_text(draw_large, (x, y), text_to_draw, font_use, boldness=boldness * scale)

    # 6️⃣ Paste cropped images
    for key, field in TEMPLATE_FIELDS.items():
        if field["type"] != "image" or key not in image_crops:
            continue
        crop_img = image_crops[key]
        if crop_img is None or crop_img.size == 0:
            continue
        try:
            pil_crop = Image.fromarray(cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB))
            x1, y1, x2, y2 = field["coords"]
            target_w, target_h = (x2 - x1) * scale, (y2 - y1) * scale
            pil_crop = pil_crop.resize((target_w, target_h), Image.Resampling.LANCZOS)
            img_large.paste(pil_crop, (x1 * scale, y1 * scale))
        except Exception as e:
            print(f"[Warning] Could not paste {key}: {e}")

    # 7️⃣ Draw vertical date text (both)
    draw_vertical_text(img_large, (155, 290), date_of_issue_greg, font_english, 22, boldness=1, scale=scale)
    draw_vertical_text(img_large, (155, 520), date_of_issue_eth, font_english, 22, boldness=1, scale=scale)

    # 8️⃣ Downscale with LANCZOS to preserve sharpness
    img_final = img_large.resize((w, h), Image.Resampling.LANCZOS)

    # 9️⃣ Return as high-quality PNG bytes
    buffer = BytesIO()
    img_final.save(buffer, format="PNG", optimize=True, dpi=(300, 300))
    return buffer.getvalue()
