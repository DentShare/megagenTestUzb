from aiogram.fsm.state import State, StatesGroup

class CourierState(StatesGroup):
    viewing_route = State() # Viewing proposed route
    delivering = State() # Active delivery mode
    delivering_combined = State() # Delivering combined route, tracking individual deliveries
    
    # Store prepared route details in state
    # sorted_order_ids: list[int]
    # route_data: list[dict] - полные данные о заказах
    # combined_route_ids: list[int] - ID заказов в объединенном маршруте
    # delivered_order_ids: list[int] - ID уже доставленных заказов