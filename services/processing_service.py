from services.telegram_service import TelegramService
from core.image.image_generator import generate_final_id_image
from core.pdf.extractor import get_pdf_metadata
from pathlib import Path
import tempfile
import magic

class ProcessingService:
    def __init__(self, telegram_service: TelegramService):
        self.telegram = telegram_service

    async def process_pdf_from_telegram(self, file_id: str, chat_id: int) -> bool:
        try:
            # Step 1: Send initial message and keep its ID
            message_id = await self.telegram.send_message(chat_id, "📥 Downloading your PDF...")

            # Step 2: Download PDF
            pdf_bytes = await self.telegram.download_file(file_id)
            await self.telegram.edit_message(chat_id, message_id, "🧩 Checking file type...")

            # Step 3️⃣: Validate file type (must be a PDF)
            file_type = magic.from_buffer(pdf_bytes, mime=True)
            if file_type != "application/pdf":
                await self.telegram.edit_message(
                    chat_id,
                    message_id,
                    f"❌ The uploaded file is not a PDF.\n"
                    f"Detected type: `{file_type}`.\n\n"
                    "Please send a **single-page PDF** file instead."
                )
                return False
            await self.telegram.edit_message(chat_id, message_id, "📄 Validating PDF...")

            # Step 3: Validate PDF
            metadata = get_pdf_metadata(pdf_bytes)
            page_count = metadata.get("page_count", 1)

            if page_count != 1:
                await self.telegram.edit_message(
                    chat_id, message_id,
                    f"❌ Invalid PDF: Found {page_count} pages.\nPlease send a single-page document."
                )
                return False

            await self.telegram.edit_message(chat_id, message_id, "✅ Valid PDF detected. Processing...")

            # Step 4: Process PDF
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                pdf_file = temp_path / "input.pdf"
                pdf_file.write_bytes(pdf_bytes)

                output_dir = temp_path / "output"
                output_dir.mkdir(exist_ok=True)

                await self.telegram.edit_message(chat_id, message_id, "🔄 Generating your ID card...")
                image_bytes = generate_final_id_image(
                    pdf_path=pdf_file,
                    output_dir=output_dir,
                    font_amharic="./fonts/truetype/abyssinica/AbyssinicaSIL-Regular.ttf",
                    font_english="./fonts/truetype/noto/NotoSans-Regular.ttf",
                    font_size=27,
                    boldness=1
                )

            # Step 5: Send the image
            await self.telegram.edit_message(chat_id, message_id, "📤 Uploading your ID card...")
            await self.telegram.send_photo_bytes(chat_id, image_bytes, "id_card.png")

            # Step 6: Final success
            await self.telegram.edit_message(chat_id, message_id, "✅ ID card generation complete!")
            return True

        except Exception as e:
            await self.telegram.edit_message(chat_id, message_id, f"❌ Error: {str(e)}")
            return False
