# assistant/commands/general_commands.py

import datetime
from typing import Dict, Any

# Эти команды теперь будут вызываться либо напрямую, либо ядро будет их перехватывать
# в зависимости от состояния. Пока оставим как есть.

def greet_command(data: Dict[str, Any]) -> str:
    """Обработчик команды приветствия."""
    name = data.get('name', 'друг')
    return f"Привет, {name}! Чем могу помочь?"

def time_command(data: Dict[str, Any]) -> str:
    """Обработчик команды для получения текущего времени."""
    now = datetime.datetime.now()
    return f"Сейчас {now.strftime('%H:%M:%S')}."

# Команда help теперь обрабатывается внутри AssistantCore для корректного отображения в зависимости от состояния.
# def help_command(data: Dict[str, Any]) -> str:
#     """Обработчик команды помощи."""
#     # В реальном приложении здесь нужно будет динамически получать список команд
#     available_commands = [
#         "/greet [имя] - поздороваться",
#         "/time - узнать текущее время",
#         "/help - показать список команд"
#     ]
#     return "Доступные команды:\n" + "\n".join(available_commands)