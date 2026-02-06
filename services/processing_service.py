import io
import magic
import tempfile
from pathlib import Path
from aiogram import Bot, types
from aiogram.types import BufferedInputFile

# Keep your existing core imports
from core.image.image_generator import generate_final_id_image
from core.pdf.extractor import get_pdf_metadata

class ProcessingService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def process_pdf_from_telegram(self, file_id: str, chat_id: int) -> bool:
        # Step 1: Send initial progress message
        # In aiogram, we store the message object to edit it easily
        status_msg = await self.bot.send_message(chat_id, "📥 Downloading your PDF...")

        try:
            # Step 2: Download PDF using Aiogram's built-in methods
            file = await self.bot.get_file(file_id)
            # This downloads the file directly into a BytesIO object (memory)
            pdf_bytes_io = await self.bot.download_file(file.file_path)
            pdf_bytes = pdf_bytes_io.read() # Get the raw bytes

            await self.bot.edit_message_text("🧩 Checking file type...", chat_id, status_msg.message_id)

            # Step 3: Validate file type
            file_type = magic.from_buffer(pdf_bytes, mime=True)
            if file_type != "application/pdf":
                await self.bot.edit_message_text(
                    f"❌ Error: Not a PDF. Detected: `{file_type}`", 
                    chat_id, status_msg.message_id
                )
                return False

            # Step 4: Validate PDF Metadata
            metadata = get_pdf_metadata(pdf_bytes)
            page_count = metadata.get("page_count", 1)

            if page_count != 1:
                await self.bot.edit_message_text(
                    f"❌ Invalid PDF: Found {page_count} pages. Please send 1 page.",
                    chat_id, status_msg.message_id
                )
                return False

            await self.bot.edit_message_text("🔄 Generating your ID card...", chat_id, status_msg.message_id)

            # Step 5: Process using your existing Core logic
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                pdf_file = temp_path / "input.pdf"
                pdf_file.write_bytes(pdf_bytes)

                output_dir = temp_path / "output"
                output_dir.mkdir(exist_ok=True)

                image_bytes = generate_final_id_image(
                    pdf_path=pdf_file,
                    output_dir=output_dir,
                    font_amharic="./fonts/truetype/abyssinica/AbyssinicaSIL-Regular.ttf",
                    font_english="./fonts/truetype/noto/NotoSans-Regular.ttf",
                    font_size=27,
                    boldness=1
                )

            # Step 6: Send the result as a Photo
            # Aiogram uses BufferedInputFile to send raw bytes from memory
            photo = BufferedInputFile(image_bytes, filename="id_card.png")
            
            await self.bot.send_photo(chat_id, photo, caption="✅ Your ID Card is ready!")
            
            # Clean up the progress message
            await self.bot.delete_message(chat_id, status_msg.message_id)
            return True

        except Exception as e:
            await self.bot.edit_message_text(f"❌ Error: {str(e)}", chat_id, status_msg.message_id)
            print(f"Processing Error: {e}")
            return False