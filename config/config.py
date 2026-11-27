from environs import Env

env = Env()
env.read_env(".env", override=False)


def _parse_id_list(var_name: str) -> list[int]:
    """Безопасно парсит список числовых Telegram ID из переменной окружения."""
    raw = env(var_name, "").strip()
    if not raw:
        return []
    ids: list[int] = []
    for item in raw.split(","):
        cleaned = item.strip()
        if cleaned.isdigit():
            ids.append(int(cleaned))
    return ids


db_user = env("DB_USER", "root")
db_password = env("DB_PASSWORD", "root")
db_host = env("DB_HOST", "db") # Внутри Docker база данных будет доступна по имени сервиса 'db'
db_name = env("DB_NAME", "tbot_db")
db_port = env.int("DB_PORT", 3306)

redis_host = env("REDIS_HOST", "redis") # Внутри Docker Redis доступен по имени сервиса 'redis'
redis_port = env.int("REDIS_PORT", 6379)
redis_db = env.int("REDIS_DB", 0)
redis_fsm_db = env.int("REDIS_FSM_DB", 1)
redis_password = env("REDIS_PASSWORD", "")
redis_ttl = env.int("REDIS_TTL", 600)

proxy_login = env("PROXY_LOGIN", "")
proxy_password = env("PROXY_PASSWORD", "")
proxy_host = env("PROXY_HOST", "")
proxy_port = env("PROXY_PORT", "")

BOT_TOKEN = env("BOT_TOKEN")
BOT_USERNAME = env("BOT_USERNAME", "").lstrip("@").strip()
ADMINS_ID = _parse_id_list("ADMINS_ID")
FOUNDERS_ID = _parse_id_list("FOUNDERS_ID")

# Настройки Telegram Mini App (Web App)
WEBAPP_URL = env("WEBAPP_URL", "").strip()
WEBAPP_PORT = env.int("WEBAPP_PORT", 8000)
# Опционально для локальной отладки UI в обычном браузере (в продакшене оставить пустым)
WEBAPP_DEV_USER_ID = env("WEBAPP_DEV_USER_ID", "").strip()

DATABASE_URL = f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"

_redis_auth = f":{redis_password}@" if redis_password else ""
REDIS_CACHE_URL = f"redis://{_redis_auth}{redis_host}:{redis_port}/{redis_db}"
REDIS_FSM_URL = f"redis://{_redis_auth}{redis_host}:{redis_port}/{redis_fsm_db}"

graylog_host = env("GRAYLOG_HOST", "graylog")
graylog_port = env.int("GRAYLOG_PORT", 12201)
