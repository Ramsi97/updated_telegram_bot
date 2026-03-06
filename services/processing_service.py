import asyncio
import io
import traceback
import magic
import tempfile
import math
from pathlib import Path
from aiogram import Bot, types
from aiogram.types import BufferedInputFile
from PIL import Image, ImageChops, ImageOps

# Keep your existing core imports
from core.image.image_generator import generate_final_id_image
from core.image.image_generator_b import generate_final_id_image_b
from core.pdf.extractor import get_pdf_metadata

class ProcessingService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.lock = asyncio.Lock()  # Global lock to prevent parallel heavy processing

    async def _download_file_with_retry(self, file_id: str, retries: int = 3) -> bytes:
        """Downloads a file from Telegram with a retry mechanism."""
        last_exception = None
        for attempt in range(retries):
            try:
                file = await self.bot.get_file(file_id=file_id)
                pdf_bytes_io = await self.bot.download_file(file_path=file.file_path)
                return pdf_bytes_io.read()
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception) as e:
                last_exception = e
                if attempt < retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential-ish backoff: 2s, 4s...
                    print(f"⚠️ Download failed: {e}. Retrying in {wait_time}s... (Attempt {attempt + 1}/{retries})")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"❌ Download failed after {retries} attempts: {e}")
        
        raise last_exception

    async def process_pdf_from_telegram(self, file_id: str, chat_id: int, color: bool = True, template: str = "A", status_message_id: int = None) -> bool:
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

            # Step 2: Download PDF with retry (Now outside the lock)
            pdf_bytes = await self._download_file_with_retry(file_id)

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

            # Step 5: Process using Core logic (Only heavy CPU work is locked)
            async with self.lock:
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    pdf_file = temp_path / "input.pdf"
                    pdf_file.write_bytes(pdf_bytes)

                    output_dir = temp_path / "output"
                    output_dir.mkdir(exist_ok=True)

                    generator_func = generate_final_id_image_b if template == "B" else generate_final_id_image
                    
                    image_bytes = await asyncio.to_thread(
                        generator_func,
                        dpi=600,
                        font_size=35 if template == "A" else 20,
                        boldness=1.5 if template == "A" else 0.5,
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
                        text=f"❌ Error: {repr(e)}\n\n(Debugging: {error_traceback[:200]}...)", 
                        chat_id=chat_id, 
                        message_id=status_msg_id
                    )
                except Exception:
                    pass
            print(f"Processing Error: {e}\n{error_traceback}")
            return False

    async def process_multiple_pdfs(self, file_ids: list[str], chat_id: int, color: bool = True, template: str = "A", status_message_id: int = None) -> bool:
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
        
        # New Dimensions (A4 Canvas: 905x1280)
        A4_WIDTH = 905
        A4_HEIGHT = 1280
        
        # ID Target Dimensions
        ID_TARGET_W = 388
        ID_TARGET_H = 244
        GAP = 28
        
        # Scaling to fit 5 rows with margins
        TARGET_HEIGHT = ID_TARGET_H # 244
        TARGET_ROW_WIDTH = (ID_TARGET_W * 2) + GAP # 804
        
        all_rows_processed = []

        try:
            # 1. Download all PDFs in parallel with a semaphore to avoid rate limits
            semaphore = asyncio.Semaphore(5)
            
            async def download_task(fid, idx):
                async with semaphore:
                    try:
                        await self.bot.edit_message_text(
                            text=f"📥 Downloading ID #{idx+1} of {len(file_ids)}...",
                            chat_id=chat_id,
                            message_id=status_msg_id
                        )
                    except: pass
                    return await self._download_file_with_retry(fid)

            # Gather all downloads
            all_pdf_bytes = await asyncio.gather(*(download_task(fid, i) for i, fid in enumerate(file_ids)))

            # 2. Process to Wide Image (Front | Back) - Sequentially with Lock
            for i, pdf_bytes in enumerate(all_pdf_bytes):
                await self.bot.edit_message_text(
                    text=f"🔄 Processing ID #{i+1} of {len(file_ids)}...",
                    chat_id=chat_id,
                    message_id=status_msg_id
                )
                
                async with self.lock: # LOCK ONLY THE CPU INTENSIVE PART
                    with tempfile.TemporaryDirectory() as temp_dir:
                        temp_path = Path(temp_dir)
                        pdf_file = temp_path / f"input_{i}.pdf"
                        pdf_file.write_bytes(pdf_bytes)
                        
                        output_dir = temp_path / "output"
                        output_dir.mkdir(exist_ok=True)

                        generator_func = generate_final_id_image_b if template == "B" else generate_final_id_image

                        image_bytes = await asyncio.to_thread(
                            generator_func,
                            dpi=600,
                            font_size=35 if template == "A" else 20,
                            boldness=1.5 if template == "A" else 0.5,
                            color=color
                        )
                
                # 3. Reorder, Trim Whitespace, and Layout
                full_id_img = Image.open(io.BytesIO(image_bytes))
                id_w, id_h = full_id_img.size
                
                # Split in half
                front_raw = full_id_img.crop((0, 0, id_w // 2, id_h))
                back_raw = full_id_img.crop((id_w // 2, 0, id_w, id_h))
                
                # Robust helper to trim ALL whitespace from an image using threshold
                def trim_all(im, threshold=10):
                    # Convert to grayscale to find non-white areas
                    gray = im.convert("L")
                    # Invert so white becomes black
                    inv = ImageOps.invert(gray)
                    # Find bbox of non-black content (thresholded to catch off-white noise)
                    bbox = inv.point(lambda p: p > threshold and 255).getbbox()
                    if not bbox: return im
                    return im.crop(bbox)

                # Trim and resize to EXACT user requested dimensions
                # This ensures the 388x244 box is filled with content as much as possible,
                # hence the 30px gap will be between the ACTUAL card edges.
                front = trim_all(front_raw).resize((ID_TARGET_W, ID_TARGET_H), Image.Resampling.LANCZOS)
                back = trim_all(back_raw).resize((ID_TARGET_W, ID_TARGET_H), Image.Resampling.LANCZOS)
                
                # Create the new row [Front | GAP | Back]
                new_row = Image.new('RGB', (TARGET_ROW_WIDTH, TARGET_HEIGHT), (255, 255, 255))
                new_row.paste(front, (0, 0))
                new_row.paste(back, (ID_TARGET_W + GAP, 0))
                
                all_rows_processed.append(new_row)

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
                
                # Calculate margins to center the block of IDs
                # 5 IDs @ 244px + 4 gaps @ 10px = 1260px (Fits in 1280px)
                v_gap = 10
                total_block_h = (current_batch_size * TARGET_HEIGHT) + ((current_batch_size - 1) * v_gap if current_batch_size > 1 else 0)
                start_y = (A4_HEIGHT - total_block_h) // 2
                x_pos = (A4_WIDTH - TARGET_ROW_WIDTH) // 2
                
                for j in range(current_batch_size):
                    y_pos = start_y + j * (TARGET_HEIGHT + v_gap)
                    a4_canvas.paste(all_rows_processed[start_idx + j], (x_pos, y_pos))

                # 6. Apply mirroring for printing
                a4_canvas = a4_canvas.transpose(Image.FLIP_LEFT_RIGHT)

                # 7. Send the A4 page
                out_io = io.BytesIO()
                a4_canvas.save(out_io, format='PNG')
                out_io.seek(0)
                
                await self.bot.send_document(
                    chat_id=chat_id,
                    document=BufferedInputFile(out_io.read(), filename=f"A4_IDs_PAGE_{p+1}.png"),
                    caption=f"✅ A4 Page {p+1} ({current_batch_size} IDs)\nLayout: [Back | Front] (MIRRORED)\nType: {'Color' if color else 'B&W'}"
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
                        text=f"❌ Batch Error: {repr(e)}\n\n(Debugging: {error_traceback[:200]}...)", 
                        chat_id=chat_id, 
                        message_id=status_msg_id
                    )
                except:
                    pass
            else:
                await self.bot.send_message(chat_id=chat_id, text=f"❌ Batch Error: {str(e)}")
            return False