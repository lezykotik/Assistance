# assistant/main.py

from core.assistant_core import AssistantCore
from core.command_handler import CommandHandler
from integrations import telegram_bot
# from assistant.integrations import website_api # Пока не используем
# from assistant.integrations import desktop_app # Пока не используем
import time
import sys  # Для sys.exit


def main():
    print("Инициализация ассистента...")

    # 1. Инициализация ядра ассистента
    core = AssistantCore()

    # 2. Инициализация обработчика команд
    command_handler = CommandHandler(core)

    # 3. Запуск интеграций
    telegram_bot_instance = None
    try:
        telegram_bot_instance = telegram_bot.TelegramBot(core)
        print("Telegram бот запущен. Для остановки нажмите Ctrl+C.")
    except ImportError:
        print("Модуль telegram_bot не найден. Пропустили запуск Telegram бота.")
    except ValueError as ve:
        print(f"Ошибка конфигурации Telegram бота: {ve}")
    except Exception as e:
        print(f"Непредвиденная ошибка при запуске Telegram бота: {e}")

    # Здесь можно было бы запустить и другие интеграции
    # try:
    #     website_api.start_api(core)
    # except Exception as e:
    #     print(f"Ошибка при запуске Website API: {e}")

    # try:
    #     desktop_app.run_app(core)
    # except Exception as e:
    #     print(f"Ошибка при запуске Desktop App: {e}")

    print("Ассистент запущен. Основной поток активен.")

    # --- Бесконечный цикл для поддержания работы основного потока ---
    try:
        while True:
            time.sleep(1)  # Просто ждем, потребляя минимум ресурсов
    except KeyboardInterrupt:
        print("\nПолучен сигнал KeyboardInterrupt. Завершение работы...")
        # Если нужно что-то сохранить перед выходом, можно добавить здесь
        # Например, сохранение users_data в файл или базу данных
        # if telegram_bot_instance and telegram_bot_instance.bot:
        #     telegram_bot_instance.bot.stop_polling() # Останавливаем poller явно
        sys.exit(0)  # Корректный выход
    except Exception as e:
        print(f"\nПроизошла неожиданная ошибка в основном цикле: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Важно: Запускайте из директории, которая СОДЕРЖИТ папку 'Assistance'
    # Например, из 'E:\projects\' выполните:
    # python Assistance/main.py
    main()