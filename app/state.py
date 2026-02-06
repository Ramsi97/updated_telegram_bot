from aiogram.fsm.state import State, StatesGroup

class PDFBotStates(StatesGroup):
    choosing_mode = State()
    waiting_single_pdf = State()
    waiting_multiple_pdfs = State()