# Используем официальный легкий образ Python
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем uv (современный супербыстрый пакетный менеджер)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Копируем конфигурационные файлы проекта
COPY pyproject.toml uv.lock ./

# Синхронизируем зависимости (uv автоматически создаст папку .venv)
RUN uv sync

# Копируем весь остальной код
COPY . .

# Делаем скрипт точки входа исполняемым (на случай, если слетели права в Windows)
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# АКТИВАЦИЯ СРЕДЫ: Добавляем путь к виртуальному окружению в PATH
ENV PATH="/app/.venv/bin:$PATH"

# Устанавливаем entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Передаем команду запуска бота аргументом в entrypoint
CMD ["python", "bot.py"]