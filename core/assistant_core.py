# assistant/core/assistant_core.py

import logging
import datetime
import random
import string
from typing import Callable, Dict, Any

# --- Правильный импорт config ---
import config  # Импортируем config один раз вверху

# -------------------------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Простые константы состояний
STATE_IDLE = "idle"  # Ожидание команды
STATE_AWAITING_PHONE = "awaiting_phone"  # Ожидание ввода номера телефона
STATE_AWAITING_SMS_CODE = "awaiting_sms_code"  # Ожидание ввода SMS-кода
STATE_IN_CABINET = "in_cabinet"  # В личном кабинете


class AssistantCore:
    def __init__(self):
        self.command_handlers: Dict[str, Callable[[Dict[str, Any]], str]] = {}
        self.users_data: Dict[str, Dict[str, Any]] = {}  # Хранилище данных пользователей (telegram_id -> data)
        self.user_states: Dict[str, str] = {}  # Текущее состояние пользователя (telegram_id -> state)
        self.sms_codes: Dict[str, Dict[
            str, Any]] = {}  # Временное хранилище SMS-кодов (telegram_id -> {'code': '...', 'timestamp': ...})
        logging.info("Assistant Core initialized.")

    def register_command(self, command_name: str, handler: Callable[[Dict[str, Any]], str]):
        """Регистрирует новую команду и её обработчик."""
        if command_name in self.command_handlers:
            logging.warning(f"Command '{command_name}' already registered. Overwriting.")
        self.command_handlers[command_name] = handler
        logging.info(f"Command '{command_name}' registered.")

    def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Получает данные пользователя, инициализируя их при первом обращении."""
        if user_id not in self.users_data:
            self.users_data[user_id] = {
                "registered": False,
                "phone_number": None,
                "balance": 0.0,  # Имитация
                "tariff": {"name": "Неизвестен", "cost": 0.0, "next_charge_date": None},
                "awaiting_sms_code": False  # Флаг для телеграм-бота
            }
            self.user_states[user_id] = STATE_IDLE
            logging.info(f"New user data initialized for user ID: {user_id}")
        return self.users_data[user_id]

    def get_user_state(self, user_id: str) -> str:
        """Получает текущее состояние пользователя."""
        return self.user_states.get(user_id, STATE_IDLE)

    def set_user_state(self, user_id: str, state: str):
        """Устанавливает новое состояние для пользователя."""
        self.user_states[user_id] = state
        logging.info(f"User ID {user_id} state changed to: {state}")

    def process_input(self, user_input: Dict[str, Any]) -> str:
        """
        Обрабатывает пользовательский ввод и возвращает ответ.

        user_input: Словарь, содержащий информацию о вводе.
                    Ожидается как минимум ключ 'command' (имя команды)
                    и опционально 'data' (дополнительные параметры).
                    'data' должен содержать 'user_id'.
        """
        user_id = user_input.get('data', {}).get('user_id')
        if not user_id:
            logging.error("Received input without user_id.")
            return "Произошла внутренняя ошибка: отсутствует идентификатор пользователя."

        command = user_input.get('command')
        data = user_input.get('data', {})

        # Обработка команд, которые могут быть вызваны в любом состоянии
        if command == 'start':
            self.set_user_state(str(user_id), STATE_IDLE)
            user_data = self.get_user_data(str(user_id))
            if user_data.get('registered'):
                return "Снова здравствуйте! Вы в личном кабинете. Что хотите сделать?"
            else:
                return "Добро пожаловать! Для начала работы, пожалуйста, зарегистрируйтесь."

        current_state = self.get_user_state(str(user_id))

        # Логика для обработки команд в зависимости от состояния
        if current_state == STATE_AWAITING_PHONE and command == 'enter_phone':
            return self.handle_enter_phone(str(user_id), data.get('phone_number'))
        elif current_state == STATE_AWAITING_SMS_CODE and command == 'enter_sms_code':
            return self.handle_enter_sms_code(str(user_id), data.get('code'))
        elif current_state == STATE_IN_CABINET:
            # Команды, доступные в личном кабинете
            if command == 'show_balance':
                return self.handle_show_balance(str(user_id))
            elif command == 'show_tariff':
                return self.handle_show_tariff(str(user_id))
            elif command == 'show_next_charge':
                return self.handle_show_next_charge(str(user_id))
            elif command == 'logout':  # Пример команды выхода
                self.set_user_state(str(user_id), STATE_IDLE)
                return "Вы вышли из личного кабинета. Для возврата используйте команду /start."
            # Если команда не распознана в кабинете, передаем ее дальше
            pass

            # Обработка команд, которые могут быть вызваны из любого состояния
        if command == 'register':
            return self.handle_register_request(str(user_id))
        elif command == 'help':
            return self.handle_help(str(user_id))

        # Если команда не была обработана по состоянию или общим командам
        handler = self.command_handlers.get(command)
        if handler:
            try:
                response = handler(data)
                logging.info(f"Command '{command}' processed successfully. Response: {response}")
                return response
            except Exception as e:
                logging.error(f"Error processing command '{command}': {e}", exc_info=True)
                return "Произошла ошибка при обработке команды."
        else:
            logging.warning(f"Unknown command received: '{command}' in state '{current_state}'.")
            return "Извините, я не знаю такой команды."

    # --- Новые обработчики для регистрации и кабинета ---

    def handle_register_request(self, user_id: str) -> str:
        """Обрабатывает запрос на регистрацию, просит номер телефона."""
        self.set_user_state(user_id, STATE_AWAITING_PHONE)
        return "Пожалуйста, введите ваш номер телефона (например, +79991234567):"

    def handle_enter_phone(self, user_id: str, phone_number: str) -> str:
        """Обрабатывает ввод номера телефона."""
        if not phone_number or not phone_number.startswith('+'):  # Простая валидация
            return "Неверный формат номера телефона. Пожалуйста, начните с '+' и укажите код страны."

        # Имитация генерации и отправки SMS-кода
        code = self._generate_sms_code()
        self._store_sms_code(user_id, code)

        user_data = self.get_user_data(user_id)
        user_data['phone_number'] = phone_number
        self.set_user_state(user_id, STATE_AWAITING_SMS_CODE)

        logging.info(f"Generated SMS code for {user_id}: {code}")
        # Здесь предполагается, что 'config' доступен
        return (f"На ваш номер {phone_number} отправлен код подтверждения. "
                f"Пожалуйста, введите его (действителен {config.SMS_CODE_LIFETIME_SECONDS} сек.):")

    def handle_enter_sms_code(self, user_id: str, sms_code: str) -> str:
        """Обрабатывает ввод SMS-кода."""
        stored_code_info = self.sms_codes.get(user_id)

        if not stored_code_info:
            self.set_user_state(user_id, STATE_IDLE)  # Вернуть в обычный режим, если код устарел или не существует
            return "Время действия кода истекло или код не был сгенерирован. Пожалуйста, начните регистрацию заново (/register)."

        # --- Используем config здесь ---
        if (datetime.datetime.now() - stored_code_info['timestamp']).total_seconds() > config.SMS_CODE_LIFETIME_SECONDS:
            # -----------------------------
            del self.sms_codes[user_id]  # Удаляем устаревший код
            self.set_user_state(user_id, STATE_IDLE)
            return "Время действия кода истекло. Пожалуйста, начните регистрацию заново (/register)."

        if sms_code == stored_code_info['code']:
            # Код верный
            user_data = self.get_user_data(user_id)
            user_data['registered'] = True
            # Имитация установки начального баланса и тарифа
            user_data['balance'] = random.uniform(500.0, 2000.0)
            today = datetime.date.today()
            next_charge_date = today + datetime.timedelta(days=random.randint(10, 30))
            user_data['tariff'] = {
                "name": random.choice(["Базовый", "Оптимальный", "Безлимит", "Стандарт"]),
                "cost": round(random.uniform(300, 1000), 2),
                "next_charge_date": next_charge_date.strftime("%Y-%m-%d")
            }

            del self.sms_codes[user_id]  # Удаляем использованный код
            self.set_user_state(user_id, STATE_IN_CABINET)

            logging.info(f"User {user_id} successfully registered.")
            return (f"Регистрация прошла успешно! Добро пожаловать в ваш личный кабинет.\n"
                    f"Ваш номер телефона: {user_data['phone_number']}.\n"
                    f"Для получения списка команд используйте /help.")
        else:
            # Код неверный
            return "Неверный код подтверждения. Пожалуйста, попробуйте еще раз."

    def handle_show_balance(self, user_id: str) -> str:
        """Показывает баланс пользователя."""
        user_data = self.get_user_data(user_id)
        if not user_data.get('registered'):
            return "Пожалуйста, зарегистрируйтесь, чтобы увидеть баланс."
        return f"Ваш текущий баланс: {user_data['balance']:.2f} руб."

    def handle_show_tariff(self, user_id: str) -> str:
        """Показывает тариф пользователя."""
        user_data = self.get_user_data(user_id)
        if not user_data.get('registered'):
            return "Пожалуйста, зарегистрируйтесь, чтобы увидеть тариф."
        tariff = user_data['tariff']
        return (f"Ваш тариф: {tariff['name']}\n"
                f"Стоимость: {tariff['cost']:.2f} руб.\n"
                f"Дата следующего списания: {tariff['next_charge_date']}")

    def handle_show_next_charge(self, user_id: str) -> str:
        """Показывает дату следующего списания."""
        user_data = self.get_user_data(user_id)
        if not user_data.get('registered'):
            return "Пожалуйста, зарегистрируйтесь, чтобы увидеть дату списания."
        next_charge_date = user_data['tariff']['next_charge_date']
        if next_charge_date:
            return f"Следующее списание по тарифу произойдет: {next_charge_date}"
        else:
            return "Информация о следующем списании недоступна."

    def handle_help(self, user_id: str) -> str:
        """Отображает помощь."""
        user_data = self.get_user_data(user_id)
        current_state = self.get_user_state(user_id)

        help_text = "Доступные команды:\n"

        if not user_data.get('registered'):
            help_text += "/register - Начать регистрацию\n"
            if current_state == STATE_AWAITING_PHONE:
                help_text += "Отправьте ваш номер телефона (например, +79991234567).\n"
            elif current_state == STATE_AWAITING_SMS_CODE:
                help_text += "Отправьте полученный SMS-код.\n"
        else:
            help_text += "/show_balance - Показать баланс\n"
            help_text += "/show_tariff - Показать ваш тариф\n"
            help_text += "/show_next_charge - Когда следующее списание\n"
            help_text += "/logout - Выйти из личного кабинета\n"

        help_text += "/help - Показать это сообщение"
        return help_text

    # --- Вспомогательные методы ---

    def _generate_sms_code(self) -> str:
        """Генерирует случайный SMS-код."""
        # Используем глобально импортированный config
        length = config.SMS_CODE_LENGTH
        characters = string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    def _store_sms_code(self, user_id: str, code: str):
        """Сохраняет SMS-код и время его генерации."""
        # Используем глобально импортированный config
        self.sms_codes[user_id] = {
            'code': code,
            'timestamp': datetime.datetime.now()
        }
        # Тут можно добавить логику очистки устаревших кодов, но пока просто храним
        # Это можно делать в отдельном потоке или при каждом обращении
