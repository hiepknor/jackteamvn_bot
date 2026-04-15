from aiogram.fsm.state import State, StatesGroup


class AddProductState(StatesGroup):
    """State group for adding products"""
    raw_lines = State()
    confirm = State()


class EditProductState(StatesGroup):
    """State group for editing products"""
    product_id = State()
    new_raw_line = State()
    confirm = State()


class DeleteProductState(StatesGroup):
    """State group for deleting products"""
    product_ids = State()
    confirm = State()


class SearchState(StatesGroup):
    """State group for searching"""
    keyword = State()
