from environs import Env

env = Env()
env.read_env(".env", override=True)

db_user = env("DB_USER")
db_password = env("DB_PASSWORD")
db_host = env("DB_HOST")
db_name = env("DB_NAME")
db_port = env("DB_PORT")

proxy_login = env("PROXY_LOGIN")
proxy_password = env("PROXY_PASSWORD")
proxy_host = env("PROXY_HOST")
proxy_port = env("PROXY_PORT")


BOT_TOKEN = env("BOT_TOKEN")
ADMINS_ID = list(map(int, env("ADMINS_ID").split(",")))
DATABASE_URL = f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
