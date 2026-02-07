from aiogram.fsm.state import State, StatesGroup

class PDFBotStates(StatesGroup):
    choosing_mode = State()
    choosing_color = State()
    waiting_single_pdf = State()
    waiting_multiple_pdfs = State()