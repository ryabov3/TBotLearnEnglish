from environs import Env

env = Env()
env.read_env(".env", override=True)

db_user = env("DB_USER", "root")
db_password = env("DB_PASSWORD", "root")
db_host = env("DB_HOST", "db") # Внутри Docker база данных будет доступна по имени сервиса 'db'
db_name = env("DB_NAME", "tbot_db")
db_port = env.int("DB_PORT", 3306)

proxy_login = env("PROXY_LOGIN", "")
proxy_password = env("PROXY_PASSWORD", "")
proxy_host = env("PROXY_HOST", "")
proxy_port = env("PROXY_PORT", "")

BOT_TOKEN = env("BOT_TOKEN")
ADMINS_ID = list(map(int, env("ADMINS_ID").split(",")))

DATABASE_URL = f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"

graylog_host = env("GRAYLOG_HOST", "graylog")
graylog_port = env.int("GRAYLOG_PORT", 12201)