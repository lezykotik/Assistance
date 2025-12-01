# assistant/core/command_handler.py

from typing import Dict, Any
from core.assistant_core import AssistantCore
from commands import general_commands # Используйте ваши реальные пути импорта

class CommandHandler:
    def __init__(self, core: AssistantCore):
        self.core = core
        self._register_default_commands()

    def _register_default_commands(self):
        """Регистрирует стандартные команды."""
        # Эти команды теперь могут быть вызваны через core.process_input
        # если они не перехватываются состояниями.
        self.core.register_command("greet", general_commands.greet_command)
        self.core.register_command("time", general_commands.time_command)
        # self.core.register_command("help", general_commands.help_command) # Помощь обрабатывается в ядре
        # Добавляйте другие команды здесь, которые не требуют специальной обработки состояний