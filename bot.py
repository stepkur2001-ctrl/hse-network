import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я HSE Network — помогаю студентам находить тиммейтов для хакатонов, стартапов и кейс-чемпионатов!\n\n"
        "🔍 Найди команду или участника прямо сейчас 👇",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(
                text="🚀 Открыть HSE Network",
                web_app=types.WebAppInfo(url="https://hse-network.onrender.com")
            )]
        ])
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())