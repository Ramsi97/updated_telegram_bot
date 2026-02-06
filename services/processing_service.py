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
        status_msg = None
        try:
            # Step 1: Send initial progress message
            status_msg = await self.bot.send_message(chat_id=chat_id, text="📥 Downloading your PDF...")

            # Step 2: Download PDF using Aiogram's built-in methods
            file = await self.bot.get_file(file_id=file_id)
            pdf_bytes_io = await self.bot.download_file(file_path=file.file_path)
            pdf_bytes = pdf_bytes_io.read() # Get the raw bytes

            if status_msg:
                await self.bot.edit_message_text(
                    text="🧩 Checking file type...", 
                    chat_id=chat_id, 
                    message_id=status_msg.message_id
                )

            # Step 3: Validate file type
            file_type = magic.from_buffer(pdf_bytes, mime=True)
            if file_type != "application/pdf":
                if status_msg:
                    await self.bot.edit_message_text(
                        text=f"❌ Error: Not a PDF. Detected: `{file_type}`", 
                        chat_id=chat_id, 
                        message_id=status_msg.message_id
                    )
                return False

            # Step 4: Validate PDF Metadata
            metadata = get_pdf_metadata(pdf_bytes)
            page_count = metadata.get("page_count", 1)

            if page_count != 1:
                if status_msg:
                    await self.bot.edit_message_text(
                        text=f"❌ Invalid PDF: Found {page_count} pages. Please send 1 page.",
                        chat_id=chat_id, 
                        message_id=status_msg.message_id
                    )
                return False

            if status_msg:
                await self.bot.edit_message_text(
                    text="🔄 Generating your ID card...", 
                    chat_id=chat_id, 
                    message_id=status_msg.message_id
                )

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
            photo = BufferedInputFile(image_bytes, filename="id_card.png")
            
            await self.bot.send_photo(
                chat_id=chat_id, 
                photo=photo, 
                caption="✅ Your ID Card is ready!"
            )
            
            # Clean up the progress message
            if status_msg:
                await self.bot.delete_message(
                    chat_id=chat_id, 
                    message_id=status_msg.message_id
                )
            return True

        except Exception as e:
            if status_msg:
                try:
                    await self.bot.edit_message_text(
                        text=f"❌ Error: {str(e)}", 
                        chat_id=chat_id, 
                        message_id=status_msg.message_id
                    )
                except Exception:
                    pass
            print(f"Processing Error: {e}")
            return False