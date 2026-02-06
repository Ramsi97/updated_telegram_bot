from datetime import datetime, timedelta
from aiogram import Router, types, F
from aiogram.filters import CommandStart, StateFilter
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
            await bot.send_message(chat_id=user_id, text="⏳ 10 minutes passed! Processing your PDFs automatically...")
            await processor.process_multiple_pdfs(files, user_id)
        await state_context.clear()

# --- HANDLERS ---

# --- KEYBOARDS ---

def get_main_kb():
    kb = [
        [types.KeyboardButton(text="📄 One PDF"), types.KeyboardButton(text="📚 Multiple PDFs")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, persistent=True)

def get_collecting_kb(count: int):
    kb = [
        [types.KeyboardButton(text=f"✅ Done (Collected: {count})")],
        [types.KeyboardButton(text="🔙 Back to Menu")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, persistent=True)

# --- HANDLERS ---

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(text=WELCOME_TEXT, reply_markup=get_main_kb(), disable_web_page_preview=True)

# 2. Handle Mode Selection
@router.message(F.text == "📄 One PDF")
async def single_mode(message: types.Message, state: FSMContext):
    await state.set_state(PDFBotStates.waiting_single_pdf)
    await message.answer("✅ Mode: Single PDF\nPlease send your PDF file.", reply_markup=get_main_kb())

@router.message(F.text == "📚 Multiple PDFs")
async def multi_mode(message: types.Message, state: FSMContext):
    await state.set_state(PDFBotStates.waiting_multiple_pdfs)
    await state.update_data(pdf_list=[]) 
    await message.answer("✅ Mode: Multiple PDFs\nSend PDFs one by one, then click 'Done' below.", reply_markup=get_collecting_kb(0))

@router.message(F.text == "🔙 Back to Menu")
async def back_to_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔙 Returned to main menu.", reply_markup=get_main_kb())

# 3. Handle Single PDF File
@router.message(PDFBotStates.waiting_single_pdf, F.document)
async def process_single_pdf_file(message: types.Message, state: FSMContext, processor):
    if message.document.mime_type != "application/pdf":
        return await message.answer("❌ Error: Please send a PDF file.")

    await message.answer("🔄 Processing your single ID card...")
    await processor.process_pdf_from_telegram(file_id=message.document.file_id, chat_id=message.chat.id)
    await message.answer("📋 ID processed. What would you like to do next?", reply_markup=get_main_kb())
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

    # Timer logic
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
    
    await message.answer(
        f"📎 Received file #{len(pdf_list)}. Send another or click 'Done' below.", 
        reply_markup=get_collecting_kb(len(pdf_list))
    )

# 5. Handle "Done" button (Both Text and Callback)
@router.message(PDFBotStates.waiting_multiple_pdfs, F.text.startswith("✅ Done"))
@router.callback_query(F.data == "process_all")
async def process_multiple(event: types.Message | types.CallbackQuery, state: FSMContext, processor, scheduler):
    # Determine the context (could be a message or a callback)
    is_callback = isinstance(event, types.CallbackQuery)
    user_id = event.from_user.id
    message = event.message if is_callback else event

    # Cancel the 10-minute timer
    job_id = f"timer_{user_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    data = await state.get_data()
    files = data.get("pdf_list", [])
    
    if not files:
        if is_callback: await event.answer("No PDFs collected!", show_alert=True)
        else: await message.answer("You haven't sent any PDFs yet!")
        return

    await message.answer(f"🚀 Merging {len(files)} IDs... Please wait.", reply_markup=get_main_kb())
    
    await processor.process_multiple_pdfs(files, message.chat.id)
    
    if is_callback: await event.answer()
    await state.clear()

# 6. Default Document Handler (when no state is set)
@router.message(F.document, StateFilter(None))
async def process_pdf_default(message: types.Message, state: FSMContext, processor):
    if message.document.mime_type != "application/pdf":
        return await message.answer(text="❌ Error: Please send a PDF file.")

    await message.answer(text="🔄 Processing your single ID card...")
    await processor.process_pdf_from_telegram(file_id=message.document.file_id, chat_id=message.chat.id)
    await message.answer(text="📋 Processed! What next?", reply_markup=get_main_kb())
    await state.clear()

@router.message()
async def catch_all_debug(message: types.Message):
    # If the user sends random text, remind them to pick a mode
    await message.answer(text="Please select a mode or send a PDF.", reply_markup=get_main_kb())