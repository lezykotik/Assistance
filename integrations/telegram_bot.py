# assistant/integrations/telegram_bot.py

import logging
from typing import Dict, Any
import telebot
from telebot import types
import threading
import time

from core.assistant_core import AssistantCore, STATE_IN_CABINET, STATE_IDLE, STATE_AWAITING_PHONE, \
    STATE_AWAITING_SMS_CODE
from config import TELEGRAM_BOT_TOKEN, SMS_CODE_LIFETIME_SECONDS  # Импортируем настройки

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Клавиатуры
keyboard_cabinet = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
keyboard_cabinet.add(
    types.KeyboardButton("💰 Баланс"),
    types.KeyboardButton("📊 Тариф"),
    types.KeyboardButton("📅 Следующее списание"),
    types.KeyboardButton("🚪 Выйти")
)

keyboard_start = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
keyboard_start.add(types.KeyboardButton("🚀 Зарегистрироваться"))


class TelegramBot:
    def __init__(self, core: AssistantCore):
        self.core = core
        if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
            logging.error("TELEGRAM_BOT_TOKEN is not set or is invalid. Please set it in config.py.")
            raise ValueError("Telegram bot token is not configured.")

        try:
            self.bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
            self._setup_handlers()
            self._start_polling()
            logging.info("Telegram Bot initialized and started polling.")
        except Exception as e:
            logging.error(f"Failed to initialize Telegram Bot: {e}")
            raise

    def _setup_handlers(self):
        """Настраивает обработчики сообщений для Telegram бота."""

        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message: types.Message):
            user_id = str(message.from_user.id)
            logging.info(f"Received 'start' or 'help' command from user {message.from_user.username} (ID: {user_id})")

            # Проверяем состояние пользователя
            state = self.core.get_user_state(user_id)

            # Вызываем обработчик ядра, он сам определит, что ответить
            user_input = {
                'command': 'help',  # Команда 'help' обрабатывает и /start
                'data': {
                    'user_id': user_id,
                    'username': message.from_user.username
                }
            }
            response = self.core.process_input(user_input)

            # Отправляем клавиатуру в зависимости от состояния
            if self.core.get_user_data(user_id).get('registered'):
                self.bot.send_message(message.chat.id, response, reply_markup=keyboard_cabinet)
            else:
                self.bot.send_message(message.chat.id, response, reply_markup=keyboard_start)

        @self.bot.message_handler(func=lambda message: True)
        def handle_message(message: types.Message):
            """Обрабатывает все остальные текстовые сообщения."""
            user_id = str(message.from_user.id)
            user_name = message.from_user.username
            text = message.text.strip()
            logging.info(f"Received message from user {user_name} (ID: {user_id}): '{text}'")

            # --- Обработка кнопок клавиатуры ---
            # Если сообщение соответствует кнопке, превращаем его в команду
            if text == "🚀 Зарегистрироваться":
                user_input = {'command': 'register', 'data': {'user_id': user_id, 'username': user_name}}
                response = self.core.process_input(user_input)
                self.bot.send_message(message.chat.id, response)
                self.bot.send_message(message.chat.id, "Пожалуйста, введите ваш номер телефона:",
                                      reply_markup=types.ReplyKeyboardRemove())  # Убираем клавиатуру

            elif text == "🚪 Выйти":
                user_input = {'command': 'logout', 'data': {'user_id': user_id, 'username': user_name}}
                response = self.core.process_input(user_input)
                self.bot.send_message(message.chat.id, response, reply_markup=keyboard_start)

            elif text == "💰 Баланс":
                user_input = {'command': 'show_balance', 'data': {'user_id': user_id, 'username': user_name}}
                response = self.core.process_input(user_input)
                self.bot.send_message(message.chat.id, response, reply_markup=keyboard_cabinet)

            elif text == "📊 Тариф":
                user_input = {'command': 'show_tariff', 'data': {'user_id': user_id, 'username': user_name}}
                response = self.core.process_input(user_input)
                self.bot.send_message(message.chat.id, response, reply_markup=keyboard_cabinet)

            elif text == "📅 Следующее списание":
                user_input = {'command': 'show_next_charge', 'data': {'user_id': user_id, 'username': user_name}}
                response = self.core.process_input(user_input)
                self.bot.send_message(message.chat.id, response, reply_markup=keyboard_cabinet)

            # --- Обработка текстовых команд и ввода данных ---
            else:
                current_state = self.core.get_user_state(user_id)
                command_name = text.lstrip('/')  # Удаляем слеш, если это команда
                command_data = {'user_id': user_id, 'username': user_name}

                # Если пользователь в состоянии ожидания номера телефона
                if current_state == STATE_AWAITING_PHONE:
                    command_name = 'enter_phone'  # Делаем из текста команду
                    command_data['phone_number'] = text

                # Если пользователь в состоянии ожидания SMS-кода
                elif current_state == STATE_AWAITING_SMS_CODE:
                    command_name = 'enter_sms_code'  # Делаем из текста команду
                    command_data['code'] = text

                # Если это не кнопка и не состояние, то пытаемся распознать как команду
                # (например, /greet)
                else:
                    if text.startswith('/'):  # Если это обычная команда
                        command_name = text.lstrip('/').split()[0]  # Берем только название команды
                        # Парсинг аргументов для обычных команд, если они есть
                        args = text.split()[1:] if len(text.split()) > 1 else []
                        if command_name == 'greet' and args:
                            command_data['name'] = args[0]  # Пример парсинга аргумента для /greet

                user_input = {'command': command_name, 'data': command_data}
                response = self.core.process_input(user_input)

                # Отправляем клавиатуру в зависимости от нового состояния после обработки
                new_state = self.core.get_user_state(user_id)
                if new_state == STATE_IN_CABINET:
                    self.bot.send_message(message.chat.id, response, reply_markup=keyboard_cabinet)
                elif new_state == STATE_AWAITING_PHONE or new_state == STATE_AWAITING_SMS_CODE:
                    # Оставляем клавиатуру пустой, чтобы пользователь вводил текст
                    self.bot.send_message(message.chat.id, response, reply_markup=types.ReplyKeyboardRemove())
                else:  # STATE_IDLE или другие
                    self.bot.send_message(message.chat.id, response, reply_markup=keyboard_start)

            logging.info(f"Sent response to user {user_name}: '{response}'")

        logging.info("Telegram message handlers set up.")

    def _start_polling(self):
        """Запускает режим опроса сервера Telegram."""
        self.poll_thread = threading.Thread(target=self.bot.polling, kwargs={'none_stop': True, 'interval': 1})
        self.poll_thread.daemon = True
        self.poll_thread.start()
        logging.info("Telegram polling started in a separate thread.")