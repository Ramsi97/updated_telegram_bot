
import camelot
from pathlib import Path
import pdfplumber

def extract_user_data(pdf_path: str | Path, debug: bool = False) -> dict:
    """
    Extract user data from Ethiopian ID PDF using Camelot.
    Converts English name to Amharic using `fidel.Transliterate`.

    Args:
        pdf_path (str | Path): Path to the PDF file.
        debug (bool): Whether to print extracted data for debugging.

    Returns:
        dict: Extracted user information.
    """
    pdf_path = str(pdf_path)    

    try:
        # Extract table data from the PDF
        tables = camelot.read_pdf(pdf_path, pages="all", flavor="stream", suppress_stdout=False)
        if len(tables) == 0:
            raise ValueError("No tables found in the PDF.")

        table = tables[0].df

        # Build the data dictionary
        data_extracted = {
            "name_en": table[1][1],
            "date_of_birth_greg": table[0][5],
            "date_of_birth_et": table[0][4],
            "sex_am": table[0][7],
            "sex_en": table[0][8],
            "phone_number": table[0][13],
            "region_am": table[1][4],
            "region_en": table[1][5],
            "zone_am": table[1][7],
            "zone_en": table[1][8],
            "woreda_am": table[1][10],
            "woreda_en": table[1][11],
        }


        x0, y0, x1, y1 = 170.7, 218.43, 300.0, 227.43
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]

            # Crop the page to the bounding box
            region = page.crop((x0, y0, x1, y1))

            # Extract the text inside the region
            text = region.extract_text()
            data_extracted["name_am"] = text
        if debug:
            print("✅ Extracted Data:")
            for k, v in data_extracted.items():
                print(f"  {k}: {v}")

        return data_extracted

    except Exception as e:
        print(f"❌ Failed to extract data: {e}")
        return {}