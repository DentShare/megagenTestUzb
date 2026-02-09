"""
Скрипт для принудительного удаления webhook и проверки статуса бота.
"""
import asyncio
import sys
from aiogram import Bot
from config import config

async def fix_webhook():
    """Удаляет webhook и проверяет статус бота."""
    bot = Bot(token=config.BOT_TOKEN)
    
    try:
        # Получаем информацию о webhook
        webhook_info = await bot.get_webhook_info()
        print(f"Webhook URL: {webhook_info.url}")
        print(f"Pending updates: {webhook_info.pending_update_count}")
        print(f"Last error date: {webhook_info.last_error_date}")
        print(f"Last error message: {webhook_info.last_error_message}")
        
        # Удаляем webhook
        result = await bot.delete_webhook(drop_pending_updates=True)
        print(f"\nWebhook deleted: {result}")
        
        # Проверяем еще раз
        webhook_info = await bot.get_webhook_info()
        print(f"\nAfter deletion:")
        print(f"Webhook URL: {webhook_info.url}")
        print(f"Pending updates: {webhook_info.pending_update_count}")
        
        print("\n✅ Webhook успешно удален! Теперь можно запускать бота.")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(fix_webhook())

