import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import config

async def test_connection():
    print("⏳ Пытаюсь подключиться к базе данных MySQL...")
    print(f"Ссылка: {config.DATABASE_URL}")
    try:
        # Пытаемся подключиться (echo=True выведет все детали в консоль)
        engine = create_async_engine(config.DATABASE_URL, echo=True)
        async with engine.begin() as conn:
            print("✅ Ура! Подключение к базе данных работает идеально!")
    except Exception as e:
        print("\n❌ ОШИБКА ПОДКЛЮЧЕНИЯ:")
        print(e)

if __name__ == "__main__":
    asyncio.run(test_connection())