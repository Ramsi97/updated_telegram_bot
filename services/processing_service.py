import asyncio
import io
import traceback
import magic
import tempfile
import math
from pathlib import Path
from aiogram import Bot, types
from aiogram.types import BufferedInputFile
from PIL import Image

# Keep your existing core imports
from core.image.image_generator import generate_final_id_image
from core.pdf.extractor import get_pdf_metadata

class ProcessingService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def process_pdf_from_telegram(self, file_id: str, chat_id: int, color: bool = True, status_message_id: int = None) -> bool:
        status_msg_id = status_message_id
        try:
            # Step 1: Send or Edit initial progress message
            if status_msg_id:
                try:
                    await self.bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text="📥 Downloading your PDF...")
                except Exception:
                    msg = await self.bot.send_message(chat_id=chat_id, text="📥 Downloading your PDF...")
                    status_msg_id = msg.message_id
            else:
                msg = await self.bot.send_message(chat_id=chat_id, text="📥 Downloading your PDF...")
                status_msg_id = msg.message_id

            # Step 2: Download PDF
            file = await self.bot.get_file(file_id=file_id)
            pdf_bytes_io = await self.bot.download_file(file_path=file.file_path)
            pdf_bytes = pdf_bytes_io.read()

            await self.bot.edit_message_text(
                text="🧩 Checking file type...", 
                chat_id=chat_id, 
                message_id=status_msg_id
            )

            # Step 3: Validate file type
            file_type = magic.from_buffer(pdf_bytes, mime=True)
            if file_type != "application/pdf":
                await self.bot.edit_message_text(
                    text=f"❌ Error: Not a PDF. Detected: `{file_type}`", 
                    chat_id=chat_id, 
                    message_id=status_msg_id
                )
                return False

            # Step 4: Validate PDF Metadata
            metadata = get_pdf_metadata(pdf_bytes)
            page_count = metadata.get("page_count", 1)

            if page_count != 1:
                await self.bot.edit_message_text(
                    text=f"❌ Invalid PDF: Found {page_count} pages. Please send 1 page.",
                    chat_id=chat_id, 
                    message_id=status_msg_id
                )
                return False

            await self.bot.edit_message_text(
                text="🔄 Generating your ID card...", 
                chat_id=chat_id, 
                message_id=status_msg_id
            )

            # Step 5: Process using Core logic
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                pdf_file = temp_path / "input.pdf"
                pdf_file.write_bytes(pdf_bytes)

                output_dir = temp_path / "output"
                output_dir.mkdir(exist_ok=True)

                image_bytes = await asyncio.to_thread(
                    generate_final_id_image,
                    pdf_path=pdf_file,
                    output_dir=output_dir,
                    font_amharic="./fonts/truetype/abyssinica/AbyssinicaSIL-Regular.ttf",
                    font_english="./fonts/truetype/noto/NotoSans-Regular.ttf",
                    font_size=27,
                    boldness=1,
                    color=color
                )

            # Step 6: Send the result
            photo = BufferedInputFile(image_bytes, filename="id_card.png")
            await self.bot.send_photo(
                chat_id=chat_id, 
                photo=photo, 
                caption=f"✅ Your ID Card is ready! ({'Color' if color else 'B&W'})"
            )
            
            # Clean up the progress message
            try:
                await self.bot.delete_message(chat_id=chat_id, message_id=status_msg_id)
            except Exception:
                pass
            return True

        except Exception as e:
            error_traceback = traceback.format_exc()
            if status_msg_id:
                try:
                    await self.bot.edit_message_text(
                        text=f"❌ Error: {str(e)}\n\n(Debugging: {error_traceback[:200]}...)", 
                        chat_id=chat_id, 
                        message_id=status_msg_id
                    )
                except Exception:
                    pass
            print(f"Processing Error: {e}\n{error_traceback}")
            return False

    async def process_multiple_pdfs(self, file_ids: list[str], chat_id: int, color: bool = True, status_message_id: int = None) -> bool:
        status_msg_id = status_message_id
        if status_msg_id:
            try:
                await self.bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text=f"🚀 Starting batch processing of {len(file_ids)} PDFs...")
            except Exception:
                msg = await self.bot.send_message(chat_id=chat_id, text=f"🚀 Starting batch processing of {len(file_ids)} PDFs...")
                status_msg_id = msg.message_id
        else:
            msg = await self.bot.send_message(chat_id=chat_id, text=f"🚀 Starting batch processing of {len(file_ids)} PDFs...")
            status_msg_id = msg.message_id
        
        # A4 Size at 300 DPI
        A4_WIDTH = 2480
        A4_HEIGHT = 3508
        ID_HALF_WIDTH = 1240 # Template width 2480 / 2
        ID_FULL_HEIGHT = 727
        
        # Scaling to fit 5 rows with margins
        TARGET_HEIGHT = 700
        TARGET_ROW_WIDTH = A4_WIDTH # We use the full A4 width for the [Back | Front] row
        
        all_rows_processed = []

        try:
            for i, file_id in enumerate(file_ids):
                await self.bot.edit_message_text(
                    text=f"🔄 Processing ID #{i+1} of {len(file_ids)}...",
                    chat_id=chat_id,
                    message_id=status_msg_id
                )
                
                # 1. Download
                file = await self.bot.get_file(file_id=file_id)
                pdf_bytes_io = await self.bot.download_file(file_path=file.file_path)
                pdf_bytes = pdf_bytes_io.read()
                
                # 2. Process to Wide Image (Front | Back)
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    pdf_file = temp_path / f"input_{i}.pdf"
                    pdf_file.write_bytes(pdf_bytes)
                    
                    output_dir = temp_path / "output"
                    output_dir.mkdir(exist_ok=True)

                    image_bytes = await asyncio.to_thread(
                        generate_final_id_image,
                        pdf_path=pdf_file,
                        output_dir=output_dir,
                        font_amharic="./fonts/truetype/abyssinica/AbyssinicaSIL-Regular.ttf",
                        font_english="./fonts/truetype/noto/NotoSans-Regular.ttf",
                        font_size=27,
                        boldness=1,
                        color=color
                    )
                    
                    # 3. Reorder to [Back | Front]
                    full_id_img = Image.open(io.BytesIO(image_bytes))
                    # Template: Front is 0-1240, Back is 1240-2480
                    front = full_id_img.crop((0, 0, ID_HALF_WIDTH, ID_FULL_HEIGHT))
                    back = full_id_img.crop((ID_HALF_WIDTH, 0, A4_WIDTH, ID_FULL_HEIGHT))
                    
                    # Create the new row [Back | Front]
                    new_row = Image.new('RGB', (A4_WIDTH, ID_FULL_HEIGHT))
                    new_row.paste(back, (0, 0))
                    new_row.paste(front, (ID_HALF_WIDTH, 0))
                    
                    # 4. Resize for A4 fit
                    row_resized = new_row.resize((TARGET_ROW_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
                    all_rows_processed.append(row_resized)

            # 5. Batch rows into A4 pages (5 per page)
            num_pages = math.ceil(len(file_ids) / 5)
            
            for p in range(num_pages):
                await self.bot.edit_message_text(
                    text=f"📄 Generating A4 page {p+1} of {num_pages}...",
                    chat_id=chat_id,
                    message_id=status_msg_id
                )
                
                start_idx = p * 5
                end_idx = min(start_idx + 5, len(file_ids))
                current_batch_size = end_idx - start_idx
                
                # Create A4 canvas
                a4_canvas = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
                
                if current_batch_size > 0:
                    margin_y = (A4_HEIGHT - (current_batch_size * TARGET_HEIGHT)) // (current_batch_size + 1)
                else:
                    margin_y = 0
                
                for j in range(current_batch_size):
                    y_pos = margin_y + j * (TARGET_HEIGHT + margin_y)
                    a4_canvas.paste(all_rows_processed[start_idx + j], (0, y_pos))

                # 6. Send the A4 page
                out_io = io.BytesIO()
                a4_canvas.save(out_io, format='PNG')
                out_io.seek(0)
                
                await self.bot.send_document(
                    chat_id=chat_id,
                    document=BufferedInputFile(out_io.read(), filename=f"A4_IDs_PAGE_{p+1}.png"),
                    caption=f"✅ A4 Page {p+1} ({current_batch_size} IDs)\nLayout: [Back | Front]\nType: {'Color' if color else 'B&W'}"
                )

            try:
                await self.bot.delete_message(chat_id=chat_id, message_id=status_msg_id)
            except Exception:
                pass
            await self.bot.send_message(chat_id=chat_id, text=f"✅ All {len(file_ids)} IDs processed and sent!")
            return True

        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"Batch Processing Error: {e}\n{error_traceback}")
            if status_msg_id:
                try:
                    await self.bot.edit_message_text(
                        text=f"❌ Batch Error: {str(e)}\n\n(Debugging: {error_traceback[:200]}...)", 
                        chat_id=chat_id, 
                        message_id=status_msg_id
                    )
                except:
                    pass
            else:
                await self.bot.send_message(chat_id=chat_id, text=f"❌ Batch Error: {str(e)}")
            return False