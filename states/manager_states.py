from aiogram.fsm.state import State, StatesGroup

class ManagerOrderState(StatesGroup):
    browsing = State() # Viewing menus
    waiting_for_quantity = State() # Adding specific item
    cart_view = State() # Viewing cart
    waiting_for_clinic_search = State() # Searching for clinic
    selecting_clinic = State() # Picking from search results
    
    # Cart data structure in FSM:
    # cart: list[dict] -> [{'sku': str, 'name': str, 'quantity': int, 'line': str, 'diameter': float, 'length': float}]
    # order_meta: dict -> {'is_urgent': bool, 'delivery_type': str}
    # selected_clinic_id: int -> ID of the clinic for the order
