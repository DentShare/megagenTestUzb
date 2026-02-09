"""
Валидация входных данных для handlers.
"""
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator
import re


class ChatIDInput(BaseModel):
    """Валидация Chat ID."""
    
    chat_id: int = Field(..., description="Telegram Chat ID")
    
    @field_validator("chat_id")
    @classmethod
    def validate_chat_id(cls, v: int) -> int:
        """Валидация Chat ID."""
        if v <= 0:
            raise ValueError("Chat ID должен быть положительным числом")
        return v
    
    @classmethod
    def from_string(cls, text: str) -> "ChatIDInput":
        """Создать из строки."""
        try:
            return cls(chat_id=int(text.strip()))
        except ValueError:
            raise ValueError("Chat ID должен быть числом")


class QuantityInput(BaseModel):
    """Валидация количества товара."""
    
    quantity: int = Field(..., gt=0, le=10000, description="Количество товара")
    
    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        """Валидация количества."""
        if v <= 0:
            raise ValueError("Количество должно быть положительным числом")
        if v > 10000:
            raise ValueError("Количество не может превышать 10000")
        return v
    
    @classmethod
    def from_string(cls, text: str) -> "QuantityInput":
        """Создать из строки."""
        try:
            return cls(quantity=int(text.strip()))
        except ValueError:
            raise ValueError("Количество должно быть числом")


class TextInput(BaseModel):
    """Валидация текстового ввода."""
    
    text: str = Field(..., min_length=1, max_length=500, description="Текст")
    
    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Валидация текста."""
        v = v.strip()
        if not v:
            raise ValueError("Текст не может быть пустым")
        if len(v) > 500:
            raise ValueError("Текст не может превышать 500 символов")
        return v


class PhoneInput(BaseModel):
    """Валидация номера телефона."""
    
    phone: str = Field(..., description="Номер телефона")
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Валидация номера телефона."""
        v = v.strip()
        # Простая валидация: цифры, +, -, пробелы, скобки
        if not re.match(r'^[\d\s\+\-\(\)]+$', v):
            raise ValueError("Некорректный формат номера телефона")
        if len(v) < 7 or len(v) > 20:
            raise ValueError("Номер телефона должен быть от 7 до 20 символов")
        return v


class SearchQueryInput(BaseModel):
    """Валидация поискового запроса."""
    
    query: str = Field(..., min_length=2, max_length=100, description="Поисковый запрос")
    
    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Валидация запроса."""
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Запрос должен содержать минимум 2 символа")
        if len(v) > 100:
            raise ValueError("Запрос не может превышать 100 символов")
        return v

    @classmethod
    def from_string(cls, text: str) -> "SearchQueryInput":
        """Создать из строки."""
        return cls(query=text.strip())


def validate_input(model_class: type[BaseModel], text: str, error_message: Optional[str] = None) -> BaseModel:
    """
    Валидировать входные данные.
    
    Args:
        model_class: Класс модели Pydantic
        text: Текст для валидации
        error_message: Кастомное сообщение об ошибке
        
    Returns:
        Валидированный объект
        
    Raises:
        ValueError: При ошибке валидации
    """
    try:
        if hasattr(model_class, "from_string"):
            return model_class.from_string(text)
        else:
            # Для обычных моделей
            return model_class(text=text)
    except ValueError as e:
        if error_message:
            raise ValueError(error_message) from e
        raise

