from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
from pathlib import Path
from datetime import date
from io import BytesIO

from app.config import BASE_DIR
from core.image.image_crop import crop_pdf_sections
from core.pdf.pdf_data_extractor import extract_user_data
from core.pdf.images_from_pdf import extract_images_from_pdf
from core.image.image_bg_remove import get_image_without_bg

# ======================
# 🔹 Constants and Paths
# ======================
FONT_AMHARIC_DEFAULT = "/usr/share/fonts/truetype/sil-abyssinica/AbyssinicaSIL-Regular.ttf"
FONT_ENGLISH_DEFAULT = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"

TEMPLATES_DIR = BASE_DIR / "data" / "templates"
TEMPLATE_B_PATH = TEMPLATES_DIR / "template_b.png"

# User provided coordinates for Template B (1280 x 389)
TEMPLATE_B_FIELDS = {
    # Amharic Fields
    "name_am": {"type": "text", "coords": (246, 110), "lang": "am"},
    
    # English / Numeric / Combined Fields
    "name_en": {"type": "text", "coords": (246, 140), "lang": "en"},
    "date_of_birth_et": {"type": "text", "coords": (246, 190), "lang": "en"}, # Mapping DOB Greg/Eth combo here
    "sex_en": {"type": "text", "coords": (246, 232), "lang": "en"},
    "expiry_date": {"type": "text", "coords": (246, 280), "lang": "en"},
    "phone_number": {"type": "text", "coords": (688, 45), "lang": "en"},
    "nationality": {"type": "text", "coords": (688, 100), "lang": "en"}, 
    
    # Address Fields - Coordinates provided by user
    "region_am": {"type": "text", "coords": (688, 140), "lang": "am", "size": 19},
    "region_en": {"type": "text", "coords": (688, 160), "lang": "en", "size": 19},
    "zone_am": {"type": "text", "coords": (688, 180), "lang": "am", "size": 19},
    "zone_en": {"type": "text", "coords": (688, 200), "lang": "en", "size": 19},
    "woreda_am": {"type": "text", "coords": (688, 220), "lang": "am", "size": 19},
    "woreda_en": {"type": "text", "coords": (688, 240), "lang": "en", "size": 19},
    
    # Image fields (x1, y1, x2, y2)
    "photo": {"type": "image", "coords": (40, 100, 220, 350)},
    "barcode": {"type": "image", "coords": (277, 310, 460, 376)},
    "small_image": {"type": "image", "coords": (500, 300, 570, 375)},
    "fin_code": {"type": "image", "coords": (685, 309, 918, 341)},
    "qrcode": {"type": "image", "coords": (940, 15, 1258, 338)},
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
    x, y = position
    for dx in range(int(boldness) + 1):
        for dy in range(int(boldness) + 1):
            draw.text((x + dx, y + dy), text, font=font, fill=fill)

def draw_vertical_text(base_img, position, text, font_path, font_size=20, fill=(0, 0, 0), boldness=1, scale=1):
    try:
        font = ImageFont.truetype(font_path, font_size * scale)
    except Exception as e:
        print(f"[Warning] Failed to load vertical text font: {e}")
        font = ImageFont.load_default()

    text_img = Image.new("RGBA", (500 * scale, 100 * scale), (255, 255, 255, 0))
    text_draw = ImageDraw.Draw(text_img)

    for dx in range(int(boldness * scale) + 1):
        for dy in range(int(boldness * scale) + 1):
            text_draw.text((dx, dy), text, font=font, fill=fill)

    rotated = text_img.rotate(90, expand=True)
    x, y = position
    x *= scale
    y *= scale
    base_img.paste(rotated, (x, y - rotated.height), rotated)

# ======================
# 🔹 Main Function
# ======================
def generate_final_id_image_b(
    pdf_path: Path,
    output_dir: Path,
    font_amharic: str = FONT_AMHARIC_DEFAULT,
    font_english: str = FONT_ENGLISH_DEFAULT,
    font_size: int = 20, # Base size 20
    boldness: float = 0.5, # Default boldness 0.5
    color: bool = True
) -> bytes:
    try:
        # 1️⃣ Extract data
        image_crops = crop_pdf_sections(pdf_path, output_dir, dpi=400)
        second_images = extract_images_from_pdf(pdf_path)
        text_data = extract_user_data(pdf_path)
    except Exception as e:
        raise RuntimeError(f"Error extracting data from PDF: {e}")

    # Process photo
    raw_photo = second_images.get("photo")
    processed_photo = None
    if raw_photo is not None:
        try:
            processed_photo = get_image_without_bg(raw_photo)
            if not color:
                alpha = processed_photo.getchannel('A')
                processed_photo = processed_photo.convert('L').convert('RGBA')
                processed_photo.putalpha(alpha)
        except Exception:
            if isinstance(raw_photo, np.ndarray):
                processed_photo = Image.fromarray(cv2.cvtColor(raw_photo, cv2.COLOR_BGR2RGB)).convert("RGBA")
            else:
                processed_photo = raw_photo.convert("RGBA")

    image_crops["photo"] = processed_photo
    image_crops["small_image"] = processed_photo
    image_crops["qrcode"] = second_images.get("qrcode")

    # 2️⃣ Load template B
    template_img = cv2.imread(str(TEMPLATE_B_PATH))
    if template_img is None:
        raise FileNotFoundError(f"Template B not found at {TEMPLATE_B_PATH}")
    img_pil = Image.fromarray(cv2.cvtColor(template_img, cv2.COLOR_BGR2RGB))

    # 3️⃣ Supersampling
    scale = 2
    w, h = img_pil.size
    img_large = img_pil.resize((w * scale, h * scale), Image.Resampling.LANCZOS)
    draw_large = ImageDraw.Draw(img_large)

    # Load fonts
    try:
        font_am_large = ImageFont.truetype(font_amharic, font_size * scale)
        font_en_large = ImageFont.truetype(font_english, font_size * scale)
    except:
        font_am_large = ImageFont.load_default()
        font_en_large = ImageFont.load_default()

    # 4️⃣ Format text data
    today = date.today()
    e_year, e_month, e_day = gregorian_to_ethiopian(today.year, today.month, today.day)
    date_of_issue_greg = f"{today.day:02d}/{today.month:02d}/{today.year}"
    date_of_issue_eth = f"{e_day:02d}/{e_month:02d}/{e_year}"
    expiry_eth_date = f"{e_day:02d}/{e_month:02d}/{e_year + 8}"
    expiry_date_greg = f"{today.day:02d}/{today.month:02d}/{today.year + 8}"
    
    text_data["expiry_date"] = f"{expiry_eth_date} | {expiry_date_greg}"
    text_data["nationality"] = "ኢትዮጵያዊ | Ethiopian"
    
    # Combine address fields
    address_am = f"{text_data.get('region_am', '')}, {text_data.get('zone_am', '')}, {text_data.get('woreda_am', '')}"
    text_data["address"] = address_am

    # 5️⃣ Draw text fields
    for key, field in TEMPLATE_B_FIELDS.items():
        if field["type"] != "text" or key not in text_data:
            continue

        text_to_draw = str(text_data[key])
        
        # Determine font size for this field
        current_font_size = field.get("size", font_size)
        try:
            f_am = ImageFont.truetype(font_amharic, current_font_size * scale)
            f_en = ImageFont.truetype(font_english, current_font_size * scale)
        except:
            f_am = font_am_large
            f_en = font_en_large
            
        font_use = f_am if field.get("lang") == "am" else f_en
        x, y = field["coords"]
        x *= scale
        y *= scale

        if key == "date_of_birth_et":
            text_to_draw = f"{text_data.get('date_of_birth_et', '')} | {text_data.get('date_of_birth_greg', '')}"
            font_use = f_am
        elif key == "sex_en":
            text_to_draw = f"{text_data.get('sex_am', '')} | {text_data.get('sex_en', '')}"
            font_use = f_am
        elif key == "nationality":
            font_use = f_am

        draw_bold_text(draw_large, (x, y), text_to_draw, font_use, boldness=boldness * scale)

    # 6️⃣ Paste images
    for key, field in TEMPLATE_B_FIELDS.items():
        if field["type"] != "image" or key not in image_crops:
            continue
        crop_img = image_crops[key]
        if crop_img is None: continue

        try:
            pil_crop = None
            if key == "photo" or key == "small_image":
                pil_crop = crop_img
            else:
                if isinstance(crop_img, np.ndarray):
                    if crop_img.size == 0: continue
                    pil_crop = Image.fromarray(cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB))
                else:
                    pil_crop = crop_img.convert("RGBA")

            if pil_crop is None: continue

            x1, y1, x2, y2 = field["coords"]
            target_w, target_h = (x2 - x1) * scale, (y2 - y1) * scale
            pil_crop = pil_crop.resize((target_w, target_h), Image.Resampling.LANCZOS)

            if pil_crop.mode == "RGBA":
                img_large.paste(pil_crop, (x1 * scale, y1 * scale), pil_crop)
            else:
                img_large.paste(pil_crop, (x1 * scale, y1 * scale))
        except Exception as e:
            print(f"[Warning] Could not paste {key}: {e}")

    # 7️⃣ Draw vertical text
    draw_vertical_text(img_large, (5, 165), date_of_issue_greg, font_english, 16, boldness=boldness, scale=scale)
    draw_vertical_text(img_large, (5, 325), date_of_issue_eth, font_english, 16, boldness=boldness, scale=scale)

    # 8️⃣ Final resize to 1280 x 389
    img_final = img_large.resize((w, h), Image.Resampling.LANCZOS)

    buffer = BytesIO()
    img_final.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
