from aiogram.fsm.state import State, StatesGroup

class AddClinicState(StatesGroup):
    waiting_for_name = State()
    waiting_for_doctor_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_location = State()
    waiting_for_chat_id = State()

class EditClinicState(StatesGroup):
    selecting_field = State()
    waiting_for_name = State()
    waiting_for_doctor_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_location = State()
    waiting_for_chat_id = State()

class ProductStatsState(StatesGroup):
    waiting_for_period = State()