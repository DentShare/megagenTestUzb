from aiogram.fsm.state import State, StatesGroup

class WarehouseState(StatesGroup):
    waiting_for_taxi_link = State()
