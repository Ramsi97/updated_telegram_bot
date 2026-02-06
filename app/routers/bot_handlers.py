from datetime import datetime, timedelta
from aiogram import Router, types, F
from aiogram.filters import CommandStart    
from aiogram.fsm.context import FSMContext

from app.state import PDFBotStates
from utils.texts import WELCOME_TEXT, SINGLE_MODE_SELECTED

router = Router()

# --- TIMEOUT FUNCTION ---
async def auto_process_timeout(user_id: int, bot, dp, processor):
    """Triggered by APScheduler if user doesn't click Done within 10 mins"""
    state_context = dp.fsm.get_context(bot, user_id, user_id)
    state_data = await state_context.get_data()
    current_state = await state_context.get_state()

    if current_state == PDFBotStates.waiting_multiple_pdfs:
        files = state_data.get("pdf_list", [])
        if files:
            await bot.send_message(user_id, "⏳ 10 minutes passed! Processing your PDFs automatically...")
            await processor.process_multiple_pdfs(files, user_id)
        await state_context.clear()

# --- HANDLERS ---

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    # Always clear state on /start to avoid getting stuck
    await state.clear()
    
    kb = [
        [   
            types.KeyboardButton(text="📄 One PDF"),
            types.KeyboardButton(text="📚 Multiple PDFs")
        ]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(
        text=WELCOME_TEXT, 
        reply_markup=keyboard, 
        disable_web_page_preview=True
    )

# 2. Handle Mode Selection
@router.message(F.text == "📄 One PDF")
async def single_mode(message: types.Message, state: FSMContext):
    await state.set_state(PDFBotStates.waiting_single_pdf)
    # ReplyKeyboardRemove hides the "One/Multiple" buttons to clean the screen
    await message.answer("✅ Mode: Single PDF\nPlease send your PDF file.", reply_markup=types.ReplyKeyboardRemove())

@router.message(F.text == "📚 Multiple PDFs")
async def multi_mode(message: types.Message, state: FSMContext):
    await state.set_state(PDFBotStates.waiting_multiple_pdfs)
    await state.update_data(pdf_list=[]) 
    await message.answer("✅ Mode: Multiple PDFs\nSend PDFs one by one. I will wait for you to click 'Done'.", reply_markup=types.ReplyKeyboardRemove())

# 3. Handle Single PDF File
@router.message(PDFBotStates.waiting_single_pdf, F.document)
async def process_single_pdf_file(message: types.Message, state: FSMContext, processor):
    if message.document.mime_type != "application/pdf":
        return await message.answer("❌ Error: Please send a PDF file.")

    await message.answer("🔄 Processing your single ID card...")
    await processor.process_pdf_from_telegram(message.document.file_id, message.chat.id)
    await state.clear()

# 4. Handle File Collection (Multiple)
@router.message(PDFBotStates.waiting_multiple_pdfs, F.document)
async def collect_files(message: types.Message, state: FSMContext, scheduler, bot, dp, processor):
    if message.document.mime_type != "application/pdf":
        return await message.answer("❌ Please only send PDF files.")
    
    data = await state.get_data()
    pdf_list = data.get("pdf_list", [])
    pdf_list.append(message.document.file_id)
    await state.update_data(pdf_list=pdf_list)

    # --- TIMER LOGIC ---
    user_id = message.from_user.id
    job_id = f"timer_{user_id}"

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        auto_process_timeout,
        'date',
        run_date=datetime.now() + timedelta(minutes=10),
        args=[user_id, bot, dp, processor],
        id=job_id
    )
    # -------------------
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=f"✅ Done (Collected: {len(pdf_list)})", callback_query_data="process_all")]
    ])
    await message.answer(f"📎 Received file #{len(pdf_list)}. Send another or click Done below.", reply_markup=kb)

# 5. Handle "Done" button
@router.callback_query(F.data == "process_all")
async def process_multiple(callback: types.CallbackQuery, state: FSMContext, processor, scheduler):
    # Cancel the 10-minute timer since they clicked Done manually
    user_id = callback.from_user.id
    job_id = f"timer_{user_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    data = await state.get_data()
    files = data.get("pdf_list", [])
    
    if not files:
        return await callback.answer("You haven't sent any PDFs yet!", show_alert=True)

    await callback.message.answer(f"🚀 Merging {len(files)} IDs... Please wait a moment.")
    
    # Call your processor
    await processor.process_multiple_pdfs(files, callback.message.chat.id)
    
    await callback.answer() # Close the "loading" state on the button
    await state.clear()

    # Bottom of app/routers/bot_handlers.py

@router.message()
async def catch_all_debug(message: types.Message):
    print(f"👻 DEBUG: Bot received a message: {message.text}")
    await message.answer(f"I am receiving messages! You sent: {message.text}")